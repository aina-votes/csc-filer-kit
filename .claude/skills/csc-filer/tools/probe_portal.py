"""Probe the live CFS portal and regenerate the machine-verifiable half of PORTAL-MAP.md.

WHY THIS EXISTS: a hand-written map of someone else's UI goes stale silently and you only
find out mid-filing. Everything this script emits is read off the live DOM, so it cannot
drift. Run it once at the start of a filing session, right after login.

WHAT IT NEEDS: csc_driver.mjs already running and LOGGED IN. It talks to the driver
through the same control/status files the driver polls; it never drives Chrome itself.

USAGE
  # driver already running (python tools/csc_launch.py --start), session logged in:
  python .claude/skills/csc-filer/tools/probe_portal.py --tmp .tmp/csc
  python .claude/skills/csc-filer/tools/probe_portal.py --tmp .tmp/csc --print

By default it writes PORTAL-MAP.generated.md next to PORTAL-MAP.md. It never edits
PORTAL-MAP.md itself -- the hand-written gotchas there are not reproducible by probing.
"""
import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(os.path.dirname(HERE), "PORTAL-MAP.generated.md")

# menu items worth walking. id -> label we expect, purely for the report
MENU = {
    3: "Add Transaction", 15: "Schedule A", 16: "Schedule C", 17: "Schedule D",
    18: "Schedule B", 19: "Schedule E", 20: "Schedule F", 21: "Org Report View",
    22: "Org Report Amend", 28: "Preview Disclosure", 30: "Employer/Occupation validation",
    31: "Contribution Limit validation", 33: "Non-Resident validation",
    36: "Filing Confirmations",
}

# add_transaction radio -> the schedule form it opens, and the fields worth dumping there
SCHEDULE_FORMS = [
    ("SA", "-2", "cc_sa_add", ["sa_date", "sa_deposit_no", "sa_amount"]),
    ("SC", "-3", "cc_sc_add", ["sc_date", "sc_deposit_no", "sc_amount", "sc_desc"]),
    ("SD", "-4", "cc_sd_add", ["sd_date", "sd_amount"]),
    ("SB", "-5", "cc_sb_add_edit", ["sb_date", "sb_amount", "sb_desc"]),
]


class Driver(object):
    def __init__(self, tmp, timeout):
        self.ctrl = os.path.join(tmp, "csc_ctrl.txt")
        self.stat = os.path.join(tmp, "csc_status.txt")
        self.jsout = os.path.join(tmp, "csc_js_out.json")
        self.timeout = timeout
        if not os.path.isdir(tmp):
            sys.exit("no such driver dir: %s" % tmp)
        if not os.path.exists(self.stat):
            sys.exit("no csc_status.txt in %s -- is the driver running?" % tmp)

    def send(self, cmd, timeout=None):
        wait = timeout or self.timeout
        before = os.path.getsize(self.stat)
        with open(self.ctrl, "w", encoding="utf-8") as f:
            f.write(cmd)
        deadline = time.time() + wait
        last, quiet = before, 0
        while time.time() < deadline:
            time.sleep(0.6)
            size = os.path.getsize(self.stat)
            if size > last:
                last, quiet = size, 0
            elif size > before:
                quiet += 1
                if quiet >= 4:
                    break
        with open(self.stat, encoding="utf-8", errors="replace") as f:
            f.seek(before)
            return f.read()

    def js(self, frame, code, timeout=None):
        out = self.send("js:%s::%s" % (frame, code), timeout)
        if "NO_FRAME" in out:
            return {"__error": "NO_FRAME", "frame": frame}
        try:
            return json.load(open(self.jsout, encoding="utf-8"))
        except Exception:
            return {"__error": "unparseable", "raw": out[-200:]}

    def frames(self):
        urls = []
        for line in self.send("frames").split("\n"):
            m = re.match(r"^\s*\d+:\s*(\S+)", line)
            if m:
                urls.append(m.group(1))
        return urls

    def menu(self, item):
        self.js("top", '(()=>{openMenuItem("ccadmin_menu_item_%d");return 1;})()' % item)
        time.sleep(3)


DUMP_SELECTS = """(()=>{const out=[];document.querySelectorAll('select').forEach(s=>{
if(!s.name||/^nmgp_|^script_case|^nm_|^SC_/.test(s.name))return;
out.push({name:s.name,options:[...s.options].map(o=>o.value+'='+o.text).filter(x=>x!=='=')});});
return out;})()"""

DUMP_RADIOS = """(()=>{const g={};document.querySelectorAll('input[type=radio]').forEach(r=>{
if(!r.name||/^nmgp_|^script_case/.test(r.name))return;(g[r.name]=g[r.name]||[]).push(r.id+'='+r.value);});
return g;})()"""

DUMP_BUTTONS = """(()=>{return [...document.querySelectorAll('a,button,input[type=submit],input[type=button]')]
.filter(e=>(e.id||'').match(/^sc_b|^sub_form|^sc_Amend|^sc_sc_btn/))
.map(e=>e.id+' :: "'+((e.innerText||e.value||'').replace(/\\s+/g,' ').trim().slice(0,28))+'"');})()"""


def inner(frames, sub):
    """The ScriptCase result/content frame, not the outer wrapper."""
    for u in frames:
        if sub in u and "nmgp_opcao=pesq" in u:
            return u
    for u in frames:
        if sub in u:
            return u
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tmp", required=True,
                    help="driver control dir, normally .tmp/csc")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--timeout", type=float, default=45)
    ap.add_argument("--print", dest="show", action="store_true")
    a = ap.parse_args()

    d = Driver(os.path.abspath(a.tmp), a.timeout)
    L = []
    W = L.append

    W("# CFS PORTAL MAP — generated")
    W("")
    W("Read off the live portal by `tools/probe_portal.py`. **Do not hand-edit** — re-run the")
    W("probe instead. Hand-written gotchas that cannot be probed live in `PORTAL-MAP.md`.")
    W("")

    # committee identity, so the map is attributable and staleness is visible
    d.menu(21)
    org = d.js("cc_xorg_report",
               "document.body.innerText.replace(/\\s+/g,' ').slice(0,400)")
    W("## Session context")
    W("")
    if isinstance(org, str):
        cn = re.search(r"Committee Name:\s*(.+?)\s+\(c\)", org)
        acct = re.search(r"Account Number:\s*(\d+)", org)
        W("- Committee: **%s**" % (cn.group(1) if cn else "?"))
        W("- Depository account: **%s**" % (acct.group(1) if acct else "?"))
    ver = d.js("top", "(document.body.innerText.match(/Version\\s+[\\d.]+/)||['?'])[0]")
    W("- Portal version string: **%s**" % ver)
    W("")

    # menu map
    W("## Menu item IDs")
    W("")
    W("`openMenuItem('ccadmin_menu_item_<N>')`")
    W("")
    W("| N | Label (live) | Expected |")
    W("|---|---|---|")
    d.menu(1)
    live = d.js("top",
                "(()=>{const o={};document.querySelectorAll('a,li,div').forEach(e=>{"
                "const m=(e.getAttribute('onclick')||'').match(/item_(\\d+)/);"
                "if(m)o[m[1]]=(e.innerText||'').trim().replace(/\\s+/g,' ').slice(0,40);});return o;})()")
    if isinstance(live, dict) and "__error" not in live:
        for n in sorted((int(k) for k in live), key=int):
            exp = MENU.get(n, "")
            flag = ""
            if exp and exp.lower().split()[0] not in live[str(n)].lower():
                flag = " ⚠️"
            W("| %d | %s | %s%s |" % (n, live[str(n)], exp or "—", flag))
    W("")

    # name form: name types + add_transaction radios
    W("## Name form (`cc_name_form`)")
    W("")
    d.menu(3)
    d.js("nmgp_opcao=pesq",
         '(()=>{const b=document.querySelector("#sc_b_new_top");if(b)b.click();return 1;})()')
    time.sleep(3)
    sels = d.js("cc_name_form", DUMP_SELECTS)
    rads = d.js("cc_name_form", DUMP_RADIOS)
    if isinstance(sels, list):
        for s in sels:
            if s["name"] == "cn_name_type":
                W("**`cn_name_type`**: " + ", ".join("`%s`" % o for o in s["options"]))
                W("")
    if isinstance(rads, dict) and "add_transaction" in rads:
        W("**`add_transaction` radios**")
        W("")
        W("| id | value |")
        W("|---|---|")
        for r in rads["add_transaction"]:
            i, _, v = r.rpartition("=")
            W("| `%s` | `%s` |" % (i, v))
        W("")
    btns = d.js("cc_name_form", DUMP_BUTTONS)
    if isinstance(btns, list) and btns:
        W("**Buttons**: " + ", ".join("`%s`" % b for b in btns))
        W("")

    # per-schedule category lists — the bit most likely to be missing when you need it
    W("## Schedule forms — selects and category IDs")
    W("")
    for label, radio, frame, fields in SCHEDULE_FORMS:
        d.menu(3)
        d.js("nmgp_opcao=pesq",
             '(()=>{const b=document.querySelector("#sc_b_new_top");if(b)b.click();return 1;})()')
        time.sleep(2.5)
        ok = d.js("cc_name_form",
                  '(()=>{const r=document.querySelector("#id-opt-add_transaction%s");'
                  'if(!r)return "NO_RADIO";r.checked=true;'
                  'r.dispatchEvent(new Event("click",{bubbles:true}));return "OK";})()' % radio)
        if ok != "OK":
            W("### %s — could not open (%s)" % (label, ok))
            W("")
            continue
        # a name is required before the schedule form renders; use a throwaway that is
        # never submitted, so nothing is written to the portal
        d.js("cc_name_form",
             '(()=>{const sv=(n,v)=>{const e=document.querySelector(\'[name="\'+n+\'"]\');'
             'if(e){e.value=v;["input","change","blur"].forEach(t=>e.dispatchEvent(new Event(t,{bubbles:true})));}};'
             'sv("cn_name_type","OTH");sv("cn_lname","ZZ PROBE DO NOT SUBMIT");'
             'sv("cn_address1","1");sv("cn_city","1");sv("cn_state","HI");sv("cn_zip","96792");return 1;})()')
        d.js("cc_name_form", '(()=>{document.querySelector("#sc_b_ins_t").click();return 1;})()')
        time.sleep(3.5)
        fr = d.frames()
        if not any(frame in u for u in fr):
            W("### %s — form did not open; frames: %s" % (label, ", ".join(fr[:4])))
            W("")
            continue
        W("### %s (`%s`, radio `-%s`)" % (label, frame, radio.lstrip("-")))
        W("")
        s2 = d.js(frame, DUMP_SELECTS)
        if isinstance(s2, list):
            for s in s2:
                W("- **`%s`**" % s["name"])
                for o in s["options"]:
                    W("    - `%s`" % o)
        r2 = d.js(frame, DUMP_RADIOS)
        if isinstance(r2, dict):
            for name, opts in sorted(r2.items()):
                W("- **`%s`** radios: %s" % (name, ", ".join("`%s`" % o for o in opts)))
        W("")
        W("> Probe left an unsaved `ZZ PROBE DO NOT SUBMIT` name form open; it was never")
        W("> submitted, so nothing was written. Navigate away to discard.")
        W("")

    W("## Validation screens")
    W("")
    W("| Check | Menu | Outer frame | Result frame |")
    W("|---|---|---|---|")
    for item, label in ((31, "Contribution Limit"), (30, "Employer/Occupation"),
                        (33, "Non-Resident")):
        d.menu(item)
        fr = d.frames()
        outer = next((u for u in fr if "validation" in u and "nmgp_opcao" not in u), "?")
        res = inner(fr, "validation") or "?"
        W("| %s | `item_%d` | `%s` | `%s` |"
          % (label, item, outer.rstrip("/").split("/")[-1] or outer, res.split("/")[-2] if "/" in res else res))
    W("")
    W("Submit with `a#sc_b_pesq_fields_right`. **Read the result from the inner")
    W("`?nmgp_opcao=pesq` frame** — the outer wrapper holds only the form.")
    W("")

    text = "\n".join(L) + "\n"
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(text)
    print("wrote %s (%d lines)" % (a.out, len(L)))
    if a.show:
        print()
        print(text)


if __name__ == "__main__":
    main()
