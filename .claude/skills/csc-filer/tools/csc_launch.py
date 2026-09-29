#!/usr/bin/env python3
"""Guarded launcher for the CSC portal driver (csc_driver.mjs). Works on Windows and macOS.

    python tools/csc_launch.py --status
    python tools/csc_launch.py --start              # opens a Chromium window on csc.hawaii.gov/CFS
    python tools/csc_launch.py --start --headless   # only after the profile already holds a login
    python tools/csc_launch.py --stop

Guards: one driver at a time (a pidfile in .tmp/csc), a free-memory preflight, and a clean
stop through the driver's own `quit` so Chromium is not left running.
Paths are relative to the kit root (the folder holding .claude/), never hard-coded.
"""
import argparse
import ctypes
import os
import pathlib
import platform
import re
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent            # .../.claude/skills/csc-filer/tools
ROOT = pathlib.Path(os.environ.get("CSC_ROOT") or HERE.parents[3])
OUT = pathlib.Path(os.environ.get("CSC_OUT") or ROOT / ".tmp" / "csc")
PIDFILE = OUT / "driver.pid"
MIN_FREE_GB = float(os.environ.get("CSC_MIN_FREE_GB", "1.0"))
RUN_MINUTES = os.environ.get("CSC_MINUTES", "420")
IS_WIN = platform.system() == "Windows"


def free_gb():
    """Free (plus inactive, on macOS) memory in GB. Returns None when unknown."""
    try:
        if IS_WIN:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            st = MEMORYSTATUSEX()
            st.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
            return st.ullAvailPhys / 1e9
        if platform.system() == "Darwin":
            vm = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
            page = int(re.search(r"page size of (\d+)", vm).group(1))
            d = dict(re.findall(r"^(.+?):\s+(\d+)\.", vm, re.M))
            return (int(d.get("Pages free", 0)) + int(d.get("Pages inactive", 0))) * page / 1e9
        with open("/proc/meminfo") as fh:
            m = re.search(r"MemAvailable:\s+(\d+)", fh.read())
            return int(m.group(1)) * 1024 / 1e9
    except Exception:
        return None


def pid_alive(pid):
    try:
        if IS_WIN:
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                                 capture_output=True, text=True).stdout
            return str(pid) in out
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def running_pid():
    try:
        pid = int(PIDFILE.read_text().strip())
    except Exception:
        return None
    if pid_alive(pid):
        return pid
    PIDFILE.unlink(missing_ok=True)
    return None


def stop(wait=25):
    pid = running_pid()
    if not pid:
        print("driver: not running")
        return True
    ctrl = OUT / "csc_ctrl.txt"
    ctrl.write_text("quit")
    deadline = time.time() + wait
    while time.time() < deadline:
        if not pid_alive(pid):
            PIDFILE.unlink(missing_ok=True)
            print("driver: stopped cleanly")
            return True
        time.sleep(1)
    if IS_WIN:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    else:
        os.kill(pid, 15)
    PIDFILE.unlink(missing_ok=True)
    print(f"driver: did not quit in {wait}s, killed pid {pid}")
    return False


def start(headless=False):
    pid = running_pid()
    if pid:
        print(f"driver: already running (pid {pid})")
        return True
    fg = free_gb()
    if fg is not None and fg < MIN_FREE_GB:
        print(f"REFUSED: only {fg:.2f} GB free (need {MIN_FREE_GB} GB). Close some apps, "
              f"or lower CSC_MIN_FREE_GB deliberately.")
        return False

    OUT.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, CSC_MINUTES=RUN_MINUTES, CSC_ROOT=str(ROOT), CSC_OUT=str(OUT))
    if headless:
        env["CSC_HEADLESS"] = "1"
    log = open(OUT / "driver_stdout.log", "ab")
    kwargs = {}
    if IS_WIN:
        kwargs["creationflags"] = 0x00000008 | 0x00000200   # DETACHED_PROCESS | NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(["node", str(HERE / "csc_driver.mjs")], cwd=str(ROOT),
                            stdout=log, stderr=log, env=env, **kwargs)
    PIDFILE.write_text(str(proc.pid))

    stat = OUT / "csc_status.txt"
    before = stat.stat().st_size if stat.exists() else 0
    deadline = time.time() + 120
    while time.time() < deadline:
        time.sleep(2)
        if proc.poll() is not None:
            print("driver exited early. Last log lines:")
            print((OUT / "driver_stdout.log").read_text(errors="replace")[-1500:])
            PIDFILE.unlink(missing_ok=True)
            return False
        try:
            text = stat.read_text(errors="replace")
            if "READY" in text[before:]:
                print(f"driver: READY (headless={headless}, pid {proc.pid}); "
                      f"control dir {OUT}")
                return True
        except OSError:
            pass
    print("driver: did not report READY within 120s; see", OUT / "driver_stdout.log")
    return False


def status():
    fg = free_gb()
    print(f"kit root : {ROOT}")
    print(f"control  : {OUT}")
    print(f"memory   : {'unknown' if fg is None else f'{fg:.2f} GB free'} (need {MIN_FREE_GB} GB to start)")
    pid = running_pid()
    print(f"driver   : {'running (pid %d)' % pid if pid else 'not running'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", action="store_true")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--headless", action="store_true")
    a = ap.parse_args()
    if a.stop:
        stop()
    if a.start:
        if not start(headless=a.headless):
            sys.exit(1)
    if a.status or not (a.start or a.stop):
        status()


if __name__ == "__main__":
    main()
