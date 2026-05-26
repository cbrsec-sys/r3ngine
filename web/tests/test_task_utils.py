import os
import signal
import subprocess
import unittest
from unittest.mock import patch, MagicMock


class TestProcessGroupKill(unittest.TestCase):
    """Verify that stream_command and run_command spawn subprocesses in their own process group."""

    def _make_mock_popen(self, captured_kwargs):
        def mock_popen(args, **kwargs):
            captured_kwargs.update(kwargs)
            m = MagicMock()
            # stdout needs readline() support for stream_command's iter() loop
            # and readline() support for run_command's readline loop
            stdout_mock = MagicMock()
            stdout_mock.readline.return_value = ''  # Empty string signals EOF
            stdout_mock.__iter__ = lambda self: iter([])
            m.stdout = stdout_mock
            m.poll.return_value = 0
            m.returncode = 0
            m.pid = 99999
            m.wait.return_value = 0
            return m
        return mock_popen

    def test_stream_command_uses_setsid(self):
        captured = {}
        mock_cmd_obj = MagicMock()
        mock_cmd_obj.id = 1
        mock_cmd_obj.output = ''
        mock_cmd_obj.return_code = 0
        with patch('subprocess.Popen', side_effect=self._make_mock_popen(captured)), \
             patch('reNgine.utils.task.Command.objects.create', return_value=mock_cmd_obj):
            from reNgine.utils.task import stream_command
            list(stream_command('echo hello', scan_id=None))
        self.assertIn('preexec_fn', captured, "stream_command Popen must pass preexec_fn=os.setsid")
        self.assertIs(captured['preexec_fn'], os.setsid)

    def test_run_command_uses_setsid(self):
        captured = {}
        mock_cmd_obj = MagicMock()
        mock_cmd_obj.id = 1
        mock_cmd_obj.output = ''
        mock_cmd_obj.return_code = 0
        with patch('subprocess.Popen', side_effect=self._make_mock_popen(captured)), \
             patch('reNgine.utils.task.Command.objects.create', return_value=mock_cmd_obj):
            from reNgine.utils.task import run_command
            run_command('echo hello', scan_id=None)
        self.assertIn('preexec_fn', captured, "run_command Popen must pass preexec_fn=os.setsid")
        self.assertIs(captured['preexec_fn'], os.setsid)


if __name__ == '__main__':
    unittest.main()
