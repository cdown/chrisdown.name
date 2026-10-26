import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Event

spec = importlib.util.spec_from_file_location('python_env', Path(__file__).resolve().parents[1] / '_scripts/python_env.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class PythonEnvironmentTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / 'requirements.txt').write_text('Pillow==13.0.0\n')
        self.environment = bootstrap.PythonEnvironment(self.root)

    def install(self, command):
        if 'venv' in command:
            self.environment.python.parent.mkdir(parents=True, exist_ok=True)
            self.environment.python.touch()

    def test_first_run_installs_privately_and_warm_run_is_offline(self):
        with patch.object(bootstrap.subprocess, 'check_call', side_effect=self.install) as run:
            self.environment.prepare()
            commands = [call.args[0] for call in run.call_args_list]
            self.assertEqual(4, len(commands))
            pip = commands[1]
            self.assertIn('--isolated', pip)
            self.assertIn('--require-virtualenv', pip)
            self.assertIn('--only-binary=:all:', pip)
            self.assertTrue(all(str(self.environment.python) == command[0] for command in commands[1:]))
            self.assertEqual(bootstrap.PREFLIGHT, commands[-1][-1])
        with patch.object(bootstrap.subprocess, 'check_call', side_effect=AssertionError('Unexpected reinstall')):
            self.assertEqual(self.environment.python, self.environment.prepare())

    def test_requirements_and_interpreter_changes_get_fresh_environments(self):
        (self.root / 'requirements.txt').write_text('Pillow==13.0.1\n')
        self.assertNotEqual(self.environment.path, bootstrap.PythonEnvironment(self.root).path)
        with patch.object(bootstrap.sys, 'executable', '/different/python'):
            self.assertNotEqual(self.environment.path, bootstrap.PythonEnvironment(self.root).path)

    def test_failed_install_has_no_ready_marker_and_retries(self):
        def fail(command):
            self.install(command)
            if 'install' in command:
                raise subprocess.CalledProcessError(1, command)
        with patch.object(bootstrap.subprocess, 'check_call', side_effect=fail):
            with self.assertRaises(subprocess.CalledProcessError):
                self.environment.prepare()
        self.assertFalse(self.environment.ready.exists())
        with patch.object(bootstrap.subprocess, 'check_call', side_effect=self.install) as run:
            self.environment.prepare()
            self.assertEqual(3, run.call_count)
        self.assertTrue(self.environment.ready.is_file())

    def test_missing_encoder_does_not_mark_environment_ready(self):
        def fail(command):
            self.install(command)
            if bootstrap.PREFLIGHT in command:
                raise subprocess.CalledProcessError(1, command)
        with patch.object(bootstrap.subprocess, 'check_call', side_effect=fail):
            with self.assertRaises(subprocess.CalledProcessError):
                self.environment.prepare()
        self.assertFalse(self.environment.ready.exists())

    def test_missing_interpreter_and_bad_marker_are_repaired(self):
        self.environment.path.mkdir(parents=True)
        self.environment.ready.write_text(self.environment.key)
        with patch.object(bootstrap.subprocess, 'check_call', side_effect=self.install) as run:
            self.environment.prepare()
            self.assertEqual(4, run.call_count)
        self.environment.ready.write_text('incomplete')
        with patch.object(bootstrap.subprocess, 'check_call', side_effect=self.install) as run:
            self.environment.prepare()
            self.assertEqual(3, run.call_count)

    def test_commands_ignore_python_environment_and_user_packages(self):
        with patch.object(self.environment, 'prepare', return_value=self.environment.python), patch.object(bootstrap.os, 'execv') as execute:
            self.environment.run(['_scripts/optimise_media.py', 'output path'])
        execute.assert_called_once_with(str(self.environment.python),
                                        [str(self.environment.python), '-E', '-s', '_scripts/optimise_media.py', 'output path'])

    def test_concurrent_preparations_install_only_once(self):
        installing, proceed = Event(), Event()
        def install(command):
            self.install(command)
            if 'install' in command:
                installing.set()
                if not proceed.wait(5):
                    raise AssertionError('Concurrent preparation timed out')
        with patch.object(bootstrap.subprocess, 'check_call', side_effect=install) as run, ThreadPoolExecutor(2) as pool:
            first = pool.submit(self.environment.prepare)
            self.assertTrue(installing.wait(5))
            second = pool.submit(bootstrap.PythonEnvironment(self.root).prepare)
            proceed.set()
            self.assertEqual(first.result(), second.result())
            self.assertEqual(4, run.call_count)


if __name__ == '__main__':
    unittest.main()
