from __future__ import annotations

import importlib
import unittest
from unittest.mock import patch


class RuntimeLoggingTests(unittest.TestCase):
    def test_logging_failures_do_not_abort_tool_execution(self) -> None:
        module_names = (
            "copilot_image_gen.server",
            "copilot_image_gen.session",
            "copilot_image_gen.transport.signalr_ws",
        )
        failures = (
            OSError(22, "Invalid argument"),
            UnicodeEncodeError("ascii", "\u2026", 0, 1, "ordinal not in range"),
            ValueError("I/O operation on closed file"),
        )

        for module_name in module_names:
            module = importlib.import_module(module_name)
            for failure in failures:
                with self.subTest(module=module_name, failure=type(failure).__name__):
                    with patch("builtins.print", side_effect=failure):
                        module._log("runtime progress")


if __name__ == "__main__":
    unittest.main()
