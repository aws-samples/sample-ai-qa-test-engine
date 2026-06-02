# Vendored: nova-act-samples trajectory replay

This directory contains trajectory replay code vendored from:
https://github.com/amazon-agi-labs/nova-act-samples/tree/main/examples/trajectory/trajectory_replay

## Source commit
Vendored on: 2026-06-02
Source repo: amazon-agi-labs/nova-act-samples (main branch)

## Changes from upstream
- Import paths rewritten from `examples.trajectory.trajectory_replay.*` and `examples.utils`
  to relative imports within this package.
- No logic changes — only import statements modified.

## Updating from upstream
1. Clone or pull https://github.com/amazon-agi-labs/nova-act-samples
2. Copy `examples/trajectory/trajectory_replay/` files here
3. Rewrite imports:
   - `from examples.trajectory.trajectory_replay.X import Y` → `from .X import Y`
   - `from examples.utils import get_logger` → use stdlib `logging.getLogger(__name__)`
4. Test with: `uv run ai-qa-test run --feature-dir examples/01-basic-navigation/ --browser-mode headless`
