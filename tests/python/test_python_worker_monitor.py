"""Exercise real interpreter monitoring and tree termination with harmless workers."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.evaluation.python_worker_monitor import run_monitored


class PythonWorkerMonitorTests(unittest.TestCase):
    def test_actual_interpreter_identity_and_allocation(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_monitored("import os,time,json; payload=bytearray(32*1024*1024); print(json.dumps({'pid':os.getpid()}),flush=True); time.sleep(.7)",
                directory, seconds=10, memory_bytes=1024**3, interval=.05)
            output = json.loads((Path(directory)/"output.log").read_text(encoding="utf-8").strip())
            self.assertTrue(result["identityVerified"])
            self.assertEqual(result["workerPid"], output["pid"])
            self.assertGreater(result["peakSampledWorkerWorkingSetBytes"], 32*1024**2)
            self.assertEqual(result["exitCode"], 0)
            self.assertIsNone(result["stopReason"])

    def test_deadline_terminates_worker_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_monitored("import time; time.sleep(30)", directory, seconds=.3, memory_bytes=1024**3, interval=.05)
            self.assertTrue(result["identityVerified"])
            self.assertEqual(result["stopReason"], "worker_time_limit")
            self.assertNotEqual(result["exitCode"], 0)
            self.assertLess(result["elapsedSeconds"], 10)

    def test_memory_limit_terminates_allocating_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_monitored("import time; payload=bytearray(64*1024*1024); time.sleep(30)",
                directory, seconds=10, memory_bytes=48*1024**2, interval=.05)
            self.assertEqual(result["stopReason"], "working_set_limit")
            self.assertGreater(result["peakSampledWorkerWorkingSetBytes"], 48*1024**2)
            self.assertNotEqual(result["exitCode"], 0)

    def test_disk_limit_terminates_worker_without_deleting_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            artifact=root/"artifact.bin"
            code="from pathlib import Path; import time; Path("+repr(str(artifact))+").write_bytes(b'x'*1048576); time.sleep(30)"
            result=run_monitored(code,root/"monitor",seconds=10,memory_bytes=1024**3,interval=.05,
                artifact_paths=[artifact],artifact_limit_bytes=512*1024)
            self.assertEqual(result["stopReason"],"artifact_limit")
            self.assertGreater(result["peakSampledArtifactBytes"],512*1024)
            self.assertEqual(artifact.stat().st_size,1048576)
            self.assertNotEqual(result["exitCode"],0)
