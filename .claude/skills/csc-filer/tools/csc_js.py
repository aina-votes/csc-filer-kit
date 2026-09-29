#!/usr/bin/env python3
"""Run a multi-line JS payload in a driver frame and return the parsed result.

Avoids shell-quoting problems with long JS. From Python:

    import sys; sys.path.insert(0, ".claude/skills/csc-filer/tools")
    from csc_js import run_js
    out = run_js("cc_name_form", js_source, wait=60)

Or from the command line, reading the JS from a file:

    python tools/csc_js.py <frameSubstr> path/to/snippet.js
"""
import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(os.environ.get("CSC_ROOT") or HERE.parents[3])
OUT = pathlib.Path(os.environ.get("CSC_OUT") or ROOT / ".tmp" / "csc")


def run_js(frame_substr, js, wait=60):
    ctrl, stat, jsout = OUT / "csc_ctrl.txt", OUT / "csc_status.txt", OUT / "csc_js_out.json"
    before_stat = stat.stat().st_size if stat.exists() else 0
    before_js = jsout.stat().st_mtime if jsout.exists() else 0
    one_line = " ".join(line.strip() for line in js.strip().splitlines())
    ctrl.write_text(f"js:{frame_substr}::{one_line}", encoding="utf-8")
    deadline = time.time() + wait
    while time.time() < deadline:
        time.sleep(0.4)
        if jsout.exists() and jsout.stat().st_mtime > before_js:
            time.sleep(0.3)
            try:
                v = json.load(open(jsout, encoding="utf-8"))
            except Exception:
                continue
            return json.loads(v) if isinstance(v, str) and v.strip()[:1] in "[{" else v
        if stat.exists() and stat.stat().st_size > before_stat:
            with stat.open(encoding="utf-8", errors="replace") as fh:
                fh.seek(before_stat)
                txt = fh.read()
            if "NO_FRAME" in txt or "CMD_ERR" in txt:
                return {"_error": txt.strip()[:400]}
    return {"_error": f"timeout after {wait}s"}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    print(json.dumps(run_js(sys.argv[1], pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")), indent=1))
