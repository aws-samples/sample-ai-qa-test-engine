"""Browser backend abstraction.

Manages Nova Act browser session creation with mode switching
(headed, headless, agentcore). Uses NovaActClient for workflow management
and NovaActQa for the expect() assertion API.
"""

import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from nova_act import Workflow

from ai_qa_test_engine.config import AppConfig
from ai_qa_test_engine.nova_act_client import NovaActClient


# Lazy import to avoid requiring nova_act_qa at import time
def _get_nova_act_qa():
    """Lazy import NovaActQa (our ported QA wrapper)."""
    from ai_qa_test_engine.nova_act_qa import NovaActQa
    return NovaActQa


def make_workflow_name(feature_name: str, scenario_name: str) -> str:
    """Generate a per-scenario workflow definition name.

    API limit: 40 chars, pattern [a-zA-Z0-9_-].
    Budget: "tt-" (3) + feature (18) + "-" (1) + scenario (18) = 40

    Ported from test_translator/tests/test_runner.py.
    """
    feature_slug = re.sub(r"[^\w]+", "-", feature_name).strip("-").lower()
    scenario_slug = re.sub(r"[^\w]+", "-", scenario_name).strip("-").lower()
    return f"tt-{feature_slug[:18]}-{scenario_slug[:18]}"


@contextmanager
def create_browser_session(
    config: AppConfig,
    base_url: str,
    workflow_name: str,
) -> Generator:
    """Create a browser session based on configured mode.

    Uses NovaActClient.get_workflow_kwargs() for workflow discovery/creation
    (same as test_translator), then creates NovaActQa with the expect() API.

    Args:
        config: Application configuration
        base_url: Starting URL for the browser
        workflow_name: Nova Act workflow definition name

    Yields:
        NovaActQa instance ready for use (has .act(), .expect(), .screenshot())
    """
    NovaActQa = _get_nova_act_qa()

    # Use NovaActClient to discover/create workflow definition (proven logic from test_translator)
    workflow_kwargs = NovaActClient.get_workflow_kwargs(
        workflow_definition_name=workflow_name
    )

    # Determine headless from browser_mode
    headless = config.browser_mode == "headless"

    # Build NovaActQa kwargs
    nova_kwargs = {
        'starting_page': base_url,
        'headless': headless,
    }

    # Video recording
    if config.enable_video_recording:
        video_dir = config.resolve_video_recording_dir()
        video_dir.mkdir(parents=True, exist_ok=True)
        nova_kwargs['record_video'] = True
        nova_kwargs['logs_directory'] = str(video_dir)

    # Start workflow and browser session
    with Workflow(**workflow_kwargs) as workflow:
        nova_kwargs['workflow'] = workflow
        with NovaActQa(**nova_kwargs) as nova:
            yield nova
