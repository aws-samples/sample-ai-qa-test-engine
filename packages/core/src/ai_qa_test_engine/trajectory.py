"""Trajectory caching for step replay.

Records Nova Act trajectories after successful execution and stores them
for replay on subsequent runs. When a step has a cached trajectory,
it is replayed (re-executing recorded actions without AI model calls),
saving time and API costs.

Uses the nova-act-samples trajectory_replay module for actual replay logic.

Cache storage:
- Local mode: trajectories/ directory in user's test repo (git-committable)
- AgentCore mode: S3 prefix (future)
"""

import hashlib
import json
import logging
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TrajectoryCache:
    """Manages trajectory recording and replay caching.

    Trajectories are keyed by a hash of (feature_name, scenario_name, step_index, step_text).
    This means if a step's text changes, the cache is invalidated for that step.
    """

    def __init__(self, cache_dir: Path):
        """Initialize trajectory cache.

        Args:
            cache_dir: Directory to store trajectory files (e.g., 'trajectories/')
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _step_key(self, feature_name: str, scenario_name: str, step_index: int, step_text: str) -> str:
        """Generate a unique cache key for a step."""
        content = f"{feature_name}::{scenario_name}::{step_index}::{step_text}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _trajectory_path(self, step_key: str) -> Path:
        """Get the path for a step's cached trajectory JSON."""
        return self.cache_dir / f"{step_key}_trajectory.json"

    def _meta_path(self, step_key: str) -> Path:
        """Get the path for a step's metadata."""
        return self.cache_dir / f"{step_key}_meta.json"

    def has_trajectory(self, feature_name: str, scenario_name: str, step_index: int, step_text: str) -> bool:
        """Check if a cached trajectory exists for a step."""
        key = self._step_key(feature_name, scenario_name, step_index, step_text)
        return self._trajectory_path(key).exists()

    def save_trajectory(
        self,
        feature_name: str,
        scenario_name: str,
        step_index: int,
        step_text: str,
        trajectory_file_path: str | None,
    ) -> None:
        """Save a trajectory after successful step execution.

        Args:
            feature_name: Name of the feature
            scenario_name: Name of the scenario
            step_index: Step number (1-indexed)
            step_text: Original step text
            trajectory_file_path: Path to Nova Act's trajectory JSON file
        """
        if not trajectory_file_path:
            return

        src = Path(trajectory_file_path)
        if not src.exists():
            logger.warning(f"Trajectory file not found: {src}")
            return

        key = self._step_key(feature_name, scenario_name, step_index, step_text)
        dest = self._trajectory_path(key)

        # Copy trajectory JSON to cache
        shutil.copy2(src, dest)

        # Save metadata
        meta = {
            "feature_name": feature_name,
            "scenario_name": scenario_name,
            "step_index": step_index,
            "step_text": step_text,
            "trajectory_file": dest.name,
            "source_file": str(src),
        }
        with open(self._meta_path(key), "w") as f:
            json.dump(meta, f, indent=2)

        logger.info(f"Trajectory cached: step {step_index} → {dest.name}")

    def get_trajectory_path(self, feature_name: str, scenario_name: str, step_index: int, step_text: str) -> Path | None:
        """Get the cached trajectory file path for a step.

        Returns:
            Path to cached trajectory JSON, or None if not cached.
        """
        key = self._step_key(feature_name, scenario_name, step_index, step_text)
        path = self._trajectory_path(key)
        return path if path.exists() else None

    def is_step_no_cache(self, step_text: str) -> bool:
        """Check if a step should skip trajectory cache.

        Steps skip cache only if they have @no-cache annotation.
        Variable steps are handled by keying on the resolved instruction text.
        """
        return "@no-cache" in step_text.lower()

    def clear(self) -> int:
        """Clear all cached trajectories.

        Returns:
            Number of trajectory entries removed.
        """
        if not self.cache_dir.exists():
            return 0

        count = 0
        for entry in self.cache_dir.iterdir():
            if entry.is_file() and entry.suffix == ".json":
                entry.unlink()
                count += 1
        return count


def replay_cached_trajectory(nova, trajectory_path: Path, strict: bool = False) -> bool:
    """Replay a cached trajectory in the current browser session.

    Uses the nova-act-samples trajectory_replay module to re-execute
    recorded actions and validate browser state.

    Args:
        nova: Active NovaActQa (NovaAct) session
        trajectory_path: Path to the cached trajectory JSON
        strict: If True, validation failures raise errors

    Returns:
        True if replay succeeded, False if it failed (fallback to act())
    """
    try:
        from examples.trajectory.trajectory_replay.runner import (
            load_trajectory,
            replay_trajectory,
        )

        trajectory = load_trajectory(str(trajectory_path))
        replay_trajectory(nova, trajectory, strict=strict)
        logger.info(f"Trajectory replayed successfully: {trajectory_path.name}")
        return True

    except ImportError:
        logger.warning(
            "nova-act-samples trajectory_replay module not available. "
            "Install nova-act-samples or add it to PYTHONPATH for replay support. "
            "Falling back to Nova Act."
        )
        return False

    except Exception as e:
        logger.warning(f"Trajectory replay failed ({e}), falling back to Nova Act")
        return False
