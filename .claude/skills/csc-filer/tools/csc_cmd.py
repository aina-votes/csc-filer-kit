#!/usr/bin/env python3
"""Send one command to the running csc_driver and print what it reported back.

    python tools/csc_cmd.py "<command>" [--wait 60]
    python tools/csc_cmd.py "js:top::document.title"
    python tools/csc_cmd.py shot
    python tools/csc_cmd.py frames

Commands: goto:<url> | frames | shot | js:<frameSubstr>::<code> | readpop | shotpop |
batch | batch:<n> | clearcookies | quit

Reads the driver's status file from the byte offset it had before the command was
written, so it prints only this command's output. Reports a timeout rather than hanging.
"""
import argparse
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(os.environ.get("CSC_ROOT") or HERE.parents[3])
OUT = pathlib.Path(os.environ.get("CSC_OUT") or ROOT / ".tmp" / "csc")
CTRL, STAT = OUT / "csc_ctrl.txt", OUT / "csc_status.txt"


def send(command, wait):
    if not STAT.exists():
        return f"NO DRIVER (no status file at {STAT}). Start it: python tools/csc_launch.py --start"
    before = STAT.stat().st_size
    CTRL.write_text(command, encoding="utf-8")
    deadline = time.time() + wait
    last, quiet_since = before, None
    while time.time() < deadline:
        time.sleep(0.5)
        size = STAT.stat().st_size
        if size > last:
            last, quiet_since = size, time.time()
            continue
        if quiet_since and time.time() - quiet_since > 1.5 and last > before:
            break
    if last == before:
        return f"TIMEOUT after {wait}s with no output. Is the driver alive? (python tools/csc_launch.py --status)"
    with STAT.open(encoding="utf-8", errors="replace") as fh:
        fh.seek(before)
        return fh.read().strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command")
    ap.add_argument("--wait", type=float, default=60)
    a = ap.parse_args()
    print(send(a.command, a.wait))


if __name__ == "__main__":
    sys.exit(main())
