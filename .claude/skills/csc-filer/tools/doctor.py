#!/usr/bin/env python3
"""Check that this kit is ready to drive the CSC portal. Prints [OK]/[FAIL] lines and ends with a
count of failures. Exit code 0 only when there are none.

    python .claude/skills/csc-filer/tools/doctor.py
"""
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(os.environ.get("CSC_ROOT") or HERE.parents[3])
fails = 0


def ok(msg):
    print("[OK]  ", msg)


def fail(msg, fix=""):
    global fails
    fails += 1
    print("[FAIL]", msg + (("  ->  " + fix) if fix else ""))


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60, shell=False).stdout.strip()
    except Exception:
        return ""


print(f"kit root: {ROOT}  ({platform.system()})")

# Python
v = sys.version_info
if v >= (3, 9):
    ok(f"Python {v.major}.{v.minor}.{v.micro}")
else:
    fail(f"Python {v.major}.{v.minor} is too old", "install Python 3.12 or newer")

# Node
node = shutil.which("node")
if node:
    nv = run([node, "--version"])
    major = int(nv.lstrip("v").split(".")[0] or 0) if nv else 0
    if major >= 18:
        ok(f"Node.js {nv}")
    else:
        fail(f"Node.js {nv or 'unknown'} is too old", "install the current LTS from https://nodejs.org")
else:
    fail("Node.js is not installed or not on PATH",
         "Windows: winget install --id OpenJS.NodeJS.LTS -e --source winget ; Mac: install the .pkg from https://nodejs.org, then restart the Claude app")

# package.json + node_modules
pkg = ROOT / "package.json"
pw = ROOT / "node_modules" / "@playwright" / "test" / "package.json"
if not pkg.exists():
    fail("package.json missing at kit root", "the kit is incomplete; re-clone it")
elif pw.exists():
    ok(f"@playwright/test {json.loads(pw.read_text(encoding='utf-8')).get('version')} installed")
else:
    fail("Playwright is not installed", "run: npm install   (in the kit folder)")

# Chromium for Playwright
if pw.exists() and node:
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    out = run([npx, "playwright", "install", "--dry-run", "chromium"]) if npx else ""
    if not out:
        fail("could not query Playwright for its browser", "run: npx playwright install chromium")
    else:
        # dry-run prints the install location; check whether the browser binary is there
        loc = ""
        for line in out.splitlines():
            if "Install location" in line:
                loc = line.split(":", 1)[1].strip()
                break
        if loc and pathlib.Path(loc).exists() and any(pathlib.Path(loc).iterdir()):
            ok(f"Chromium for Playwright present at {loc}")
        else:
            fail("Chromium for Playwright is not downloaded", "run: npx playwright install chromium")

# driver syntax
drv = HERE / "csc_driver.mjs"
if node and drv.exists():
    r = subprocess.run([node, "--check", str(drv)], capture_output=True, text=True)
    if r.returncode == 0:
        ok("csc_driver.mjs parses")
    else:
        fail("csc_driver.mjs does not parse", r.stderr.strip()[:200])
else:
    fail("csc_driver.mjs missing", "the kit is incomplete; re-clone it")

# folders + gitignore
for d in ("data", "data/bank", "data/squarespace", "data/actblue", "data/periods", ".tmp/csc"):
    (ROOT / d).mkdir(parents=True, exist_ok=True)
ok("data/ and .tmp/csc/ folders exist")
gi = (ROOT / ".gitignore").read_text(encoding="utf-8") if (ROOT / ".gitignore").exists() else ""
missing = [p for p in ("data/", ".csc_profile", ".tmp/", ".env") if p not in gi]
if missing:
    fail(f".gitignore does not exclude {missing}", "donor and bank data must never be committed; restore the kit .gitignore")
else:
    ok(".gitignore excludes data/, .csc_profile, .tmp/ and .env")

# skill files
for f in ("SKILL.md", "FILING-GUIDE.md", "PORTAL-MAP.md"):
    if (HERE.parent / f).exists():
        ok(f"{f} present")
    else:
        fail(f"{f} missing", "the kit is incomplete; re-clone it")

print()
print(f"{fails} failure(s)")
sys.exit(1 if fails else 0)
