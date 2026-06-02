"""Translation cache manager.

Provides content-hash based caching for translated feature JSON.
Cache files are git-committable so team members benefit from existing translations.
"""

import hashlib
import json
from pathlib import Path
from typing import Optional


class LocalCacheManager:
    """Local file-based cache with content-hash invalidation.

    Stores translated JSON alongside a hash file for the source .feature content.
    Cache is invalidated when the source file's content hash changes.
    """

    def __init__(self, cache_dir: Path):
        """Initialize cache manager.

        Args:
            cache_dir: Directory to store cached translations (e.g., 'translated/')
        """
        self.cache_dir = cache_dir

    def _hash_path(self, source_path: Path) -> Path:
        """Get the hash file path for a source file."""
        return self.cache_dir / f".{source_path.stem}.hash"

    def _json_path(self, source_path: Path) -> Path:
        """Get the cached JSON path for a source file."""
        return self.cache_dir / f"{source_path.stem}.json"

    def _compute_hash(self, source_path: Path) -> str:
        """Compute SHA-256 hash of source file content."""
        content = source_path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def is_stale(self, source_path: Path) -> bool:
        """Check if cached translation is stale (source changed).

        Args:
            source_path: Path to the source .feature file

        Returns:
            True if cache is missing or stale, False if fresh
        """
        hash_file = self._hash_path(source_path)
        json_file = self._json_path(source_path)

        # No cache exists
        if not hash_file.exists() or not json_file.exists():
            return True

        # Compare stored hash with current
        stored_hash = hash_file.read_text().strip()
        current_hash = self._compute_hash(source_path)
        return stored_hash != current_hash

    def get(self, source_path: Path) -> Optional[dict]:
        """Get cached translation for a feature file.

        Args:
            source_path: Path to the source .feature file

        Returns:
            Cached feature dict, or None if stale/missing
        """
        if self.is_stale(source_path):
            return None

        json_file = self._json_path(source_path)
        try:
            with open(json_file, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def put(self, source_path: Path, feature_data: dict) -> Path:
        """Cache a translated feature.

        Stores the JSON and the source file's content hash.

        Args:
            source_path: Path to the source .feature file
            feature_data: Translated feature dictionary

        Returns:
            Path to the cached JSON file
        """
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Write JSON (deterministic output for git-friendliness)
        json_file = self._json_path(source_path)
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(feature_data, f, indent=2, sort_keys=False, ensure_ascii=False)

        # Write hash
        hash_file = self._hash_path(source_path)
        current_hash = self._compute_hash(source_path)
        hash_file.write_text(current_hash + "\n")

        return json_file

    def clear(self) -> int:
        """Clear all cached files.

        Returns:
            Number of files removed
        """
        if not self.cache_dir.exists():
            return 0

        count = 0
        for f in self.cache_dir.glob("*.json"):
            f.unlink()
            count += 1
        for f in self.cache_dir.glob(".*.hash"):
            f.unlink()
            count += 1
        return count

    def list_cached(self) -> list[Path]:
        """List all cached JSON files.

        Returns:
            List of paths to cached JSON files
        """
        if not self.cache_dir.exists():
            return []
        return sorted(self.cache_dir.glob("*.json"))
