#!/usr/bin/env python3
"""Pull ActBlue contribution CSVs for the committee through the ActBlue CSV API.

    python tools/actblue_pull.py --start 2026-07-25 --end 2026-08-08

Credentials: the ActBlue "Client UUID" and "Client Secret" (created by the committee's
ActBlue admin under Dashboard -> Tools -> API credentials). They are read from the
environment variables ACTBLUE_CLIENT_UUID / ACTBLUE_CLIENT_SECRET when set, otherwise
prompted for with no echo. They are never printed, logged, or written to disk.

API: POST /csvs -> 202 {id}; poll GET /csvs/<id> until status == "complete" -> download_url.
The date range must be 6 months or less. Always pulls refunded_contributions too: an empty
refunds file is what rules out a clawback.
"""
import argparse
import base64
import getpass
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

API = "https://secure.actblue.com/api/v1"
HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(os.environ.get("CSC_ROOT") or HERE.parents[3])


def _dotenv():
    """KEY=VALUE lines from <kit>/.env, which is gitignored and filled in by the treasurer."""
    out = {}
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def get_creds():
    env = dict(_dotenv(), **{k: v for k, v in os.environ.items() if k.startswith("ACTBLUE_")})
    uuid = env.get("ACTBLUE_CLIENT_UUID") or (sys.stdin.isatty() and getpass.getpass("ActBlue Client UUID (hidden): "))
    secret = env.get("ACTBLUE_CLIENT_SECRET") or (sys.stdin.isatty() and getpass.getpass("ActBlue Client Secret (hidden): "))
    if not uuid or not secret:
        raise SystemExit("ActBlue credentials not found. Ask the treasurer to add ACTBLUE_CLIENT_UUID=... and "
                         "ACTBLUE_CLIENT_SECRET=... to a file named .env in the kit folder (never paste them in chat), "
                         "or download the CSVs from the ActBlue dashboard instead.")
    return uuid.strip(), secret.strip()


def req(url, uuid, secret, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    tok = base64.b64encode(f"{uuid}:{secret}".encode()).decode()
    r.add_header("Authorization", "Basic " + tok)
    r.add_header("Content-Type", "application/json")
    r.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=90) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def pull(uuid, secret, csv_type, start, end, outdir):
    st, body = req(f"{API}/csvs", uuid, secret, "POST", {
        "csv_type": csv_type, "date_range_start": start, "date_range_end": end,
    })
    if st == 401:
        print(f"  {csv_type}: HTTP 401 - the UUID/secret pair was rejected")
        return None
    if st not in (200, 201, 202):
        print(f"  {csv_type}: POST failed HTTP {st}: {body[:300]}")
        return None
    cid = json.loads(body).get("id")
    print(f"  {csv_type}: queued id={cid}", flush=True)
    url = None
    for _ in range(60):
        time.sleep(5)
        st, body = req(f"{API}/csvs/{cid}", uuid, secret)
        if st != 200:
            print(f"  {csv_type}: poll HTTP {st}: {body[:200]}")
            return None
        d = json.loads(body)
        if d.get("status") == "complete":
            url = d.get("download_url")
            break
        if d.get("status") in ("failed", "error"):
            print(f"  {csv_type}: job {d.get('status')}: {body[:200]}")
            return None
    if not url:
        print(f"  {csv_type}: timed out waiting for completion")
        return None
    with urllib.request.urlopen(url, timeout=180) as resp:
        raw = resp.read()
    dest = outdir / f"actblue_{csv_type}_{start}_{end}.csv"
    dest.write_bytes(raw)
    rows = max(0, raw.decode("utf-8", "replace").strip().count("\n"))
    print(f"  {csv_type}: {rows} data rows -> {dest}")
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD")
    ap.add_argument("--types", default="paid_contributions,refunded_contributions")
    ap.add_argument("--outdir", default=str(ROOT / "data" / "actblue"))
    a = ap.parse_args()
    outdir = pathlib.Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    uuid, secret = get_creds()
    print(f"ActBlue pull {a.start} .. {a.end}", flush=True)
    for t in [x.strip() for x in a.types.split(",") if x.strip()]:
        pull(uuid, secret, t, a.start, a.end, outdir)


if __name__ == "__main__":
    sys.exit(main())
