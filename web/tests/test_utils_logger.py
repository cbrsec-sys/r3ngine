import logging
from django.test import TestCase
from reNgine.utils.logger import get_module_logger, format_exception_for_log, ModuleLogger


class TestGetModuleLogger(TestCase):
    def test_returns_module_logger_instance(self):
        logger = get_module_logger(__name__)
        self.assertIsInstance(logger, ModuleLogger)

    def test_log_line_info_does_not_raise(self):
        logger = get_module_logger(__name__)
        logger.log_line("[TEST]", "ACTION", "message", level="info")

    def test_log_line_invalid_level_raises(self):
        logger = get_module_logger(__name__)
        with self.assertRaises(ValueError):
            logger.log_line("[TEST]", "ACTION", "message", level="trace")

    def test_standard_methods_pass_through(self):
        logger = get_module_logger(__name__)
        logger.info("info %s", "msg")
        logger.debug("debug %s", "msg")
        logger.warning("warn %s", "msg")
        logger.error("err %s", "msg")

    def test_format_exception_for_log_includes_type(self):
        exc = ValueError("bad input")
        result = format_exception_for_log(exc)
        self.assertIn("ValueError", result)
        self.assertIn("bad input", result)

    def test_format_exception_for_log_empty_message(self):
        exc = ValueError("")
        result = format_exception_for_log(exc)
        self.assertIn("ValueError", result)
        self.assertIn("(no message)", result)
