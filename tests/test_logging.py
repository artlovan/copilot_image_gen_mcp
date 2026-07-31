from __future__ import annotations

import importlib
import io
import unittest
from unittest.mock import patch


class RuntimeLoggingTests(unittest.TestCase):
    module_names = (
        "copilot_image_gen.server",
        "copilot_image_gen.session",
        "copilot_image_gen.transport.signalr_ws",
    )

    def test_logging_failures_do_not_abort_tool_execution(self) -> None:
        failures = (
            OSError(22, "Invalid argument"),
            UnicodeEncodeError("ascii", "\u2026", 0, 1, "ordinal not in range"),
            ValueError("I/O operation on closed file"),
        )

        for module_name in self.module_names:
            module = importlib.import_module(module_name)
            for failure in failures:
                with self.subTest(module=module_name, failure=type(failure).__name__):
                    with patch("builtins.print", side_effect=failure):
                        module._log("runtime progress")

    def test_logging_still_writes_to_working_stderr(self) -> None:
        for module_name in self.module_names:
            module = importlib.import_module(module_name)
            stderr = io.StringIO()
            with self.subTest(module=module_name):
                with patch.object(module.sys, "stderr", stderr):
                    module._log("runtime progress")
                self.assertEqual(stderr.getvalue(), "runtime progress\n")

    def test_missing_stderr_does_not_fall_back_to_stdout(self) -> None:
        for module_name in self.module_names:
            module = importlib.import_module(module_name)
            with self.subTest(module=module_name):
                with (
                    patch.object(module.sys, "stderr", None),
                    patch("builtins.print") as print_mock,
                ):
                    module._log("runtime progress")
                print_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
