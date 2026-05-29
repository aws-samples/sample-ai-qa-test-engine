"""Custom functions registry and execution.

Extended with FunctionRegistry class for bundled + user function management.
"""

import importlib.util
import inspect
from pathlib import Path
from typing import Any, Callable


def get_function_from_module(module: Any, function_name: str) -> Callable:
    """Get a function from module, supporting dot notation.

    Args:
        module: The loaded Python module
        function_name: Function name (e.g., "calculate_discount" or "user_service.create_user")

    Returns:
        The callable function

    Raises:
        AttributeError: If function not found
    """
    if '.' in function_name:
        parts = function_name.split('.')
        obj = getattr(module, parts[0])
        for part in parts[1:]:
            obj = getattr(obj, part)
        return obj
    else:
        return getattr(module, function_name)


class FunctionRegistry:
    """Registry for custom test functions.

    Loads bundled utility functions and user-supplied functions into a unified
    registry. Provides validation and execution with reserved parameter injection.
    """

    def __init__(self):
        self._modules: list[Any] = []

    def load_from_file(self, file_path: Path) -> None:
        """Load functions from a Python file.

        The file's parent directory is added to sys.path so that
        sibling files can import each other.

        Args:
            file_path: Path to .py file containing functions

        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If file can't be loaded
        """
        import sys

        if not file_path.exists():
            raise FileNotFoundError(f"Functions file not found: {file_path}")

        # Add parent dir to sys.path so files can import siblings
        parent_dir = str(file_path.parent.resolve())
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        spec = importlib.util.spec_from_file_location(
            f"custom_functions_{file_path.stem}", file_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load functions file: {file_path}")

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise RuntimeError(f"Error loading functions file {file_path}: {e}") from e

        self._modules.append(module)

    def load_from_directory(self, dir_path: Path) -> int:
        """Load all .py files from a directory as function modules.

        The directory is added to sys.path so files can import each other.
        Files starting with _ are skipped.

        Args:
            dir_path: Directory containing .py function files

        Returns:
            Number of files loaded

        Raises:
            FileNotFoundError: If directory doesn't exist
        """
        import sys

        if not dir_path.exists():
            raise FileNotFoundError(f"Functions directory not found: {dir_path}")

        # Add dir to sys.path so files can import each other
        resolved = str(dir_path.resolve())
        if resolved not in sys.path:
            sys.path.insert(0, resolved)

        count = 0
        for py_file in sorted(dir_path.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            self.load_from_file(py_file)
            count += 1
        return count

    def load_bundled(self, functions_dir: Path) -> None:
        """Load all .py files from a bundled functions directory.

        Args:
            functions_dir: Directory containing bundled function files
        """
        if not functions_dir.exists():
            return

        for py_file in sorted(functions_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            self.load_from_file(py_file)

    def get_function(self, name: str) -> Callable:
        """Get a function by name from loaded modules.

        Searches modules in reverse order (last loaded = highest priority,
        so user functions override bundled ones).

        Args:
            name: Function name (supports dot-notation)

        Returns:
            The callable function

        Raises:
            AttributeError: If function not found in any module
        """
        for module in reversed(self._modules):
            try:
                return get_function_from_module(module, name)
            except AttributeError:
                continue

        raise AttributeError(f"Function '{name}' not found in any loaded module")

    def has_function(self, name: str) -> bool:
        """Check if a function exists in the registry."""
        try:
            self.get_function(name)
            return True
        except AttributeError:
            return False

    def validate_feature(self, feature_data: dict) -> list[str]:
        """Validate that all function calls in feature data reference existing functions.

        Ported from test_translator/utils/execution.py::validate_function_calls_from_data.

        Args:
            feature_data: Feature dictionary (translated JSON)

        Returns:
            List of error messages (empty if all valid)
        """
        errors = []
        for scenario in feature_data.get('scenarios', []):
            scenario_name = scenario.get('name', 'Unknown')
            for step_idx, step in enumerate(scenario.get('steps', []), 1):
                function_call = step.get('function_call')
                if function_call is not None:
                    func_name = function_call['function_name']
                    original_text = step.get('original_text', '')
                    if not self.has_function(func_name):
                        errors.append(
                            f"Scenario '{scenario_name}', Step {step_idx} ('{original_text}'): "
                            f"Function '{func_name}' not found"
                        )
        return errors

    def call(
        self,
        name: str,
        parameters: dict[str, Any],
        nova_act: Any = None,
        context: dict | None = None,
    ) -> Any:
        """Execute a function by name with resolved parameters.

        Handles reserved parameter injection (nova_act, context).

        Args:
            name: Function name
            parameters: Resolved parameters dict
            nova_act: Nova Act browser instance (injected if function accepts it)
            context: Execution context dict (injected if function accepts it)

        Returns:
            Function return value
        """
        func = self.get_function(name)
        sig = inspect.signature(func)

        # Inject reserved parameters if function accepts them
        resolved_params = dict(parameters)
        if 'nova_act' in sig.parameters and nova_act is not None:
            resolved_params['nova_act'] = nova_act
        if 'context' in sig.parameters and context is not None:
            resolved_params['context'] = context

        return func(**resolved_params)
