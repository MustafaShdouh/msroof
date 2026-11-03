"""Monitor the real Windows interpreter, including virtualenv redirectors.

Future research runs may use this helper. The completed adaptation is NOT rerun.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from training.transactions.completion_adaptation import working_set

BOOTSTRAP = """import json,os,sys,time
from pathlib import Path
with Path(sys.argv[1]).open('x',encoding='utf-8') as handle:
    json.dump(dict(pid=os.getpid(),token=sys.argv[2],started=time.monotonic()),handle)
exec(compile(sys.argv[3],'<monitored-worker>','exec'),{'__name__':'__main__'})
"""


def run_monitored(code, directory, seconds, memory_bytes, interval=1.0,
                  artifact_paths=(), artifact_limit_bytes=None):
    """Run trusted local Python code, with PID handshake and process-tree cleanup.

    Deadline covers the whole worker after its handshake. Memory is sampled,
    not an instantaneous hard OS reservation. Directory must be new/empty.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    identity = directory / "identity.json"
    if any(directory.iterdir()):
        raise ValueError("Monitor requires a fresh directory")
    token = uuid.uuid4().hex
    peak, peak_artifacts, reason, worker = 0, 0, None, None
    with (directory / "output.log").open("w", encoding="utf-8") as output:
        process = subprocess.Popen([sys.executable, "-X", "utf8", "-c", BOOTSTRAP, str(identity), token, code],
                                   stdout=output, stderr=subprocess.STDOUT)
        launch_time = time.monotonic()
        try:
            while process.poll() is None:
                if worker is None and identity.exists():
                    try:
                        candidate = json.loads(identity.read_text(encoding="utf-8"))
                        if candidate["token"] != token: raise ValueError("Worker identity token mismatch")
                        worker = candidate
                    except json.JSONDecodeError:
                        pass
                if worker is not None:
                    try: peak = max(peak, working_set(worker["pid"]))
                    except OSError:
                        if process.poll() is not None: break
                        # The interpreter can exit just before its launcher reports exit.
                        time.sleep(interval)
                        if process.poll() is not None: break
                        raise
                    if peak > memory_bytes: reason = "working_set_limit"
                    elif time.monotonic() - worker["started"] >= seconds: reason = "worker_time_limit"
                elif time.monotonic() - launch_time > 30:
                    reason = "worker_identity_timeout"
                if artifact_limit_bytes is not None:
                    files=set()
                    for location in artifact_paths:
                        location=Path(location)
                        if location.is_file(): files.add(location.resolve())
                        elif location.is_dir(): files.update(p.resolve() for p in location.rglob("*") if p.is_file())
                    artifact_bytes=sum(p.stat().st_size for p in files)
                    peak_artifacts=max(peak_artifacts,artifact_bytes)
                    if artifact_bytes > artifact_limit_bytes: reason = "artifact_limit"
                if reason:
                    break
                time.sleep(interval)
        finally:
            if process.poll() is None:
                # Kill the owned launcher AND its descendants, not only the redirector.
                killed = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=10)
                if killed.returncode and process.poll() is None:
                    raise RuntimeError("Could not terminate owned process tree")
            exit_code = process.wait(timeout=10)
    result = dict(launcherPid=process.pid, workerPid=None if worker is None else worker["pid"],
        identityVerified=worker is not None, peakSampledWorkerWorkingSetBytes=peak,
        stopReason=reason, exitCode=exit_code, elapsedSeconds=time.monotonic()-launch_time,
        peakSampledArtifactBytes=peak_artifacts)
    with (directory / "result.json").open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    return result
