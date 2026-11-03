"""Race/failure coverage for future supervision, without fitting task models."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.evaluation.worker_supervision import artifact_inventory, run_monitored, working_set


class ArtifactInventoryTests(unittest.TestCase):
    def test_missing_roots_nested_dedup_and_checkpoint_rename_race(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stable = root / "final.bin"
            vanished = root / ".temporary"
            stable.write_bytes(b"x" * 1024)
            vanished.write_bytes(b"x" * 17)
            original = Path.stat

            def stat_after_rename(path, *args, **kwargs):
                if path.name == vanished.name:
                    raise FileNotFoundError("Checkpoint temporary file was renamed")
                return original(path, *args, **kwargs)

            with patch.object(Path, "stat", stat_after_rename):
                size, missing = artifact_inventory([root, stable, root / "not-created"])
            self.assertEqual(size, 1024)
            self.assertEqual(missing, 1)

    def test_permission_failures_are_not_treated_as_disappearance(self):
        with tempfile.TemporaryDirectory() as directory:
            denied = Path(directory) / "denied"
            denied.write_bytes(b"x")
            original = Path.stat

            def fail(path, *args, **kwargs):
                if path == denied:
                    raise PermissionError("Injected unreadable artifact")
                return original(path, *args, **kwargs)

            with patch.object(Path, "stat", fail):
                with self.assertRaises(PermissionError):
                    artifact_inventory([directory])


class WorkerSupervisionTests(unittest.TestCase):
    def test_real_interpreter_allocation_and_normal_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_monitored(
                "import os,time,json; payload=bytearray(32*1024**2); "
                "print(json.dumps({'pid':os.getpid()}),flush=True); time.sleep(.7)",
                directory, 10, 1024**3, interval=.05)
            output = json.loads((Path(directory) / "output.log").read_text().strip())
            self.assertEqual(result["workerPid"], output["pid"])
            self.assertGreater(result["peakSampledWorkerWorkingSetBytes"], 32*1024**2)
            self.assertEqual(result["exitCode"], 0)
            self.assertIsNone(result["stopReason"])
            self.assertTrue(result["ownedLauncherStopped"])

    def test_monitor_error_terminates_tree_and_persists_failure_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "child.json"
            code = ("import subprocess,sys,json,time; from pathlib import Path; "
                    "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
                    "Path(" + repr(str(marker)) + ").write_text(json.dumps({'pid':child.pid})); time.sleep(30)")

            def fail_after_child_started(_):
                if marker.exists():
                    raise PermissionError("Injected scanner failure")
                return 0, 0

            with patch("tools.evaluation.worker_supervision.artifact_inventory",
                       side_effect=fail_after_child_started):
                result = run_monitored(code, Path(directory) / "monitor",
                    10, 1024**3, interval=.05, artifact_paths=[directory],
                    artifact_limit_bytes=1024**3)
            self.assertEqual(result["stopReason"], "monitor_error")
            self.assertEqual(result["monitorError"]["type"], "PermissionError")
            self.assertNotEqual(result["exitCode"], 0)
            self.assertTrue(result["ownedLauncherStopped"])
            self.assertTrue(result["identityVerified"])
            self.assertEqual(json.loads((Path(directory)/"monitor/result.json").read_text()), result)
            for pid in (result["workerPid"], json.loads(marker.read_text())["pid"]):
                with self.assertRaises(OSError):
                    working_set(pid)

    def test_resource_limits_stop_owned_workers(self):
        scenarios = [
            ("time", "import time; time.sleep(30)", .3, 1024**3, None, "worker_time_limit"),
            ("memory", "import time; payload=bytearray(64*1024**2); time.sleep(30)",
             10, 48*1024**2, None, "working_set_limit"),
            ("disk", "from pathlib import Path; import time; Path({artifact!r}).write_bytes(b'x'*1048576); time.sleep(30)",
             10, 1024**3, 512*1024, "artifact_limit"),
        ]
        for label, code, seconds, memory, disk, reason in scenarios:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                artifact = root / "artifact.bin"
                result = run_monitored(code.format(artifact=str(artifact)), root / "monitor",
                    seconds, memory, interval=.05, artifact_paths=[artifact],
                    artifact_limit_bytes=disk)
                self.assertEqual(result["stopReason"], reason)
                self.assertNotEqual(result["exitCode"], 0)
                self.assertTrue(result["ownedLauncherStopped"])
                self.assertLess(result["elapsedSeconds"], 10)
                if label == "disk":
                    self.assertEqual(artifact.stat().st_size, 1048576)
