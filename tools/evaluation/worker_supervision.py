"""Future CPU research supervision; frozen earlier runs retain their own helper.

Artifact inventories are sampled observations, not an instantaneous disk quota.
Atomic checkpoint renames may remove an inventoried file before its stat call.
Only disappearance is tolerated; other monitoring errors stop the owned worker
and are recorded before returning. No model loading or fitting occurs here.
"""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import uuid

from tools.evaluation.python_worker_monitor import BOOTSTRAP
from training.transactions.completion_adaptation import working_set


def artifact_inventory(locations):
    """Return sampled bytes and disappearing entries, deduplicating nested roots."""
    files = set()
    missing = 0

    def walk_error(error):
        nonlocal missing
        if isinstance(error, FileNotFoundError):
            missing += 1
        else:
            raise error

    for location in locations:
        location = Path(location)
        try:
            mode = location.stat().st_mode
        except FileNotFoundError:
            # Declared future outputs need not exist yet.
            continue
        if stat.S_ISREG(mode):
            files.add(location.resolve())
        elif stat.S_ISDIR(mode):
            for root, _, names in os.walk(location, onerror=walk_error):
                for name in names:
                    try:
                        files.add((Path(root) / name).resolve())
                    except FileNotFoundError:
                        missing += 1
    total = 0
    for path in files:
        try:
            total += path.stat().st_size
        except FileNotFoundError:
            missing += 1
    return total, missing


def run_monitored(code, directory, seconds, memory_bytes, interval=1.0,
                  artifact_paths=(), artifact_limit_bytes=None):
    """Bound one owned interpreter; return durable evidence even on monitor error."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise ValueError("Monitor requires a fresh directory")
    identity = directory / "identity.json"
    token = uuid.uuid4().hex
    peak = peak_artifacts = missing = 0
    worker = reason = error = None
    with (directory / "output.log").open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            [sys.executable, "-X", "utf8", "-c", BOOTSTRAP, str(identity), token, code],
            stdout=output, stderr=subprocess.STDOUT)
        launch_time = time.monotonic()
        try:
            while process.poll() is None:
                if worker is None and identity.exists():
                    try:
                        candidate = json.loads(identity.read_text(encoding="utf-8"))
                        if candidate["token"] != token:
                            raise ValueError("Worker identity token mismatch")
                        worker = candidate
                    except json.JSONDecodeError:
                        pass
                if worker is not None:
                    try:
                        peak = max(peak, working_set(worker["pid"]))
                    except OSError:
                        if process.poll() is not None:
                            break
                        time.sleep(interval)
                        if process.poll() is not None:
                            break
                        raise
                    if peak > memory_bytes:
                        reason = "working_set_limit"
                    elif time.monotonic() - worker["started"] >= seconds:
                        reason = "worker_time_limit"
                elif time.monotonic() - launch_time > 30:
                    reason = "worker_identity_timeout"
                if artifact_limit_bytes is not None:
                    size, vanished = artifact_inventory(artifact_paths)
                    missing += vanished
                    peak_artifacts = max(peak_artifacts, size)
                    if size > artifact_limit_bytes:
                        reason = "artifact_limit"
                if reason:
                    break
                time.sleep(interval)
            # Include artifacts written just before a normally exiting worker.
            if reason is None and artifact_limit_bytes is not None:
                size, vanished = artifact_inventory(artifact_paths)
                missing += vanished
                peak_artifacts = max(peak_artifacts, size)
                if size > artifact_limit_bytes:
                    reason = "artifact_limit"
        except Exception as failure:
            reason = "monitor_error"
            error = dict(type=type(failure).__name__, message=str(failure))
        finally:
            cleanup_error = None
            try:
                if process.poll() is None:
                    killed = subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True, timeout=10)
                    if killed.returncode and process.poll() is None:
                        raise RuntimeError("Could not terminate owned process tree")
                exit_code = process.wait(timeout=10)
            except Exception as failure:
                cleanup_error = dict(type=type(failure).__name__, message=str(failure))
                exit_code = process.poll()
            result = dict(
                launcherPid=process.pid, workerPid=None if worker is None else worker["pid"],
                identityVerified=worker is not None, peakSampledWorkerWorkingSetBytes=peak,
                stopReason=reason if cleanup_error is None else "cleanup_error",
                monitorError=error, cleanupError=cleanup_error, exitCode=exit_code,
                elapsedSeconds=time.monotonic()-launch_time,
                peakSampledArtifactBytes=peak_artifacts,
                disappearingArtifactEntries=missing,
                ownedLauncherStopped=process.poll() is not None)
            with (directory / "result.json").open("x", encoding="utf-8") as handle:
                json.dump(result, handle, indent=2)
            if cleanup_error is not None:
                raise RuntimeError("Owned worker cleanup failed; inspect result.json")
    return result
