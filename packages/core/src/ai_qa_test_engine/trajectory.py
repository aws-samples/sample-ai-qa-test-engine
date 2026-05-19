"""Trajectory caching for step replay.

Records Nova Act trajectories after successful execution and stores them
for potential replay on subsequent runs. When a step has a cached trajectory
and the trajectory is replayable, it can be replayed instead of re-executing
via Nova Act (saving time and API calls).

Current status:
- Recording: ✅ Saves trajectory file paths after successful act() calls
- Replay: 🚧 Infrastructure ready, waiting for Nova Act SDK replay API
- Fallback: ✅ If replay fails or no cache, falls back to Nova Act

Cache storage:
- Local mode: trajectories/ directory in user's test repo (git-committable)
- AgentCore mode: S3 prefix (future)
"""

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


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

    def _step_key(self, feature_name: str, scenario_name: str, step_index: int, step_text: str) -> str:
        """Generate a unique cache key for a step."""
        content = f"{feature_name}::{scenario_name}::{step_index}::{step_text}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _step_dir(self, step_key: str) -> Path:
        """Get the directory for a step's cached trajectory."""
        return self.cache_dir / step_key

    def has_trajectory(self, feature_name: str, scenario_name: str, step_index: int, step_text: str) -> bool:
        """Check if a cached trajectory exists for a step.

        Args:
            feature_name: Name of the feature
            scenario_name: Name of the scenario
            step_index: Step number (1-indexed)
            step_text: Original step text (used for cache invalidation)

        Returns:
            True if a valid cached trajectory exists
        """
        key = self._step_key(feature_name, scenario_name, step_index, step_text)
        step_dir = self._step_dir(key)
        meta_file = step_dir / "meta.json"
        return meta_file.exists()

    def save_trajectory(
        self,
        feature_name: str,
        scenario_name: str,
        step_index: int,
        step_text: str,
        trajectory_file_path: str | None,
        replayable: bool,
    ) -> None:
        """Save a trajectory after successful step execution.

        Args:
            feature_name: Name of the feature
            scenario_name: Name of the scenario
            step_index: Step number
            step_text: Original step text
            trajectory_file_path: Path to Nova Act's trajectory file (may be None)
            replayable: Whether Nova Act marked this trajectory as replayable
        """
        if not trajectory_file_path:
            return

        key = self._step_key(feature_name, scenario_name, step_index, step_text)
        step_dir = self._step_dir(key)
        step_dir.mkdir(parents=True, exist_ok=True)

        # Copy trajectory file to cache
        src = Path(trajectory_file_path)
        if src.exists():
            dest = step_dir / src.name
            shutil.copy2(src, dest)

            # Save metadata
            meta = {
                "feature_name": feature_name,
                "scenario_name": scenario_name,
                "step_index": step_index,
                "step_text": step_text,
                "trajectory_file": src.name,
                "replayable": replayable,
            }
            meta_file = step_dir / "meta.json"
            with open(meta_file, "w") as f:
                json.dump(meta, f, indent=2)

    def get_trajectory(self, feature_name: str, scenario_name: str, step_index: int, step_text: str) -> dict | None:
        """Get cached trajectory metadata for a step.

        Args:
            feature_name: Name of the feature
            scenario_name: Name of the scenario
            step_index: Step number
            step_text: Original step text

        Returns:
            Metadata dict with trajectory info, or None if not cached
        """
        key = self._step_key(feature_name, scenario_name, step_index, step_text)
        step_dir = self._step_dir(key)
        meta_file = step_dir / "meta.json"

        if not meta_file.exists():
            return None

        with open(meta_file) as f:
            return json.load(f)

    def is_step_no_cache(self, step_text: str) -> bool:
        """Check if a step has @no-cache annotation.

        Steps with @no-cache always use Nova Act, never replay.

        Args:
            step_text: Original step text

        Returns:
            True if step should skip cache
        """
        return "@no-cache" in step_text.lower()

    def clear(self) -> int:
        """Clear all cached trajectories.

        Returns:
            Number of trajectory entries removed
        """
        if not self.cache_dir.exists():
            return 0

        count = 0
        for entry in self.cache_dir.iterdir():
            if entry.is_dir():
                shutil.rmtree(entry)
                count += 1
        return count
