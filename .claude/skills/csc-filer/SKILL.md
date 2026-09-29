---
name: csc-filer
description: "Enters a Hawaii campaign committee's contributions, expenditures, receipts and loans into the Campaign Spending Commission's Candidate Filing System (csc.hawaii.gov/CFS) through a browser it drives, runs the portal validations, and reconciles cash-on-hand to the bank statement. Then it stops: the treasurer clicks File Report, never Claude. Trigger: 'enter this period's report', 'file the CSC report', 'reconcile to the bank', 'add these contributions to the portal'."
---

# csc-filer — driving the Hawaii CFS portal

**ON ENTRY, read the two sibling files. They are peers, not a chain.**

| File | What it is | Read it for |
|---|---|---|
| **`FILING-GUIDE.md`** | §0 "START HERE", the orientation, then everything learned filing real reports | prior period paper → log in and let the portal *tell* you the report name, period and deadline → verify committee and depositories → bank CSV → Squarespace (and any ActBlue) CSVs → Filing Confirmations. Also processor-fee booking and the deposit-basis rule. |
| **`PORTAL-MAP.md`** | the portal reference manual | every frame path, menu id, `cn_*`/`sa_*`/`sb_*`/`sc_*`/`sd_*` field, radio value and category code, plus the gotchas that cost time |

**Refresh the map at the start of a filing session:** with the driver running and logged in,
`python .claude/skills/csc-filer/tools/probe_portal.py --tmp .tmp/csc` reads the menu ids, name
types, category lists and radio maps off the live portal into `PORTAL-MAP.generated.md`. A
hand-maintained map of someone else's UI goes stale silently; a probed one cannot.

## Hard rules

- **NEVER click "File Report."** Do all entry, edit, delete, validation and reconciliation, then
  hand off. Filing is the irreversible, legally certified submission and is always the treasurer's
  own click. Same for the Termination-of-Registration form and any "Submit" that certifies.
- **Never ask for, type, or store the portal password or any bank login.** The treasurer logs in
  by hand in the browser window the driver opens. If the session has expired, say so and wait.
- **Verify the committee after every login.** Read the Org Report (menu `item_21`, frame
  `cc_xorg_report`): committee name and depository account number. Tell the treasurer what you
  see before touching anything.
- **Show the delta before entering it.** Before any `batch` or scripted entry, put the rows you are
  about to add, delete or change in a table in the conversation and wait for a yes. Deleting from
  the portal is one row at a time and is not undoable from here.
- **Pre-transliterate non-ASCII** (ʻokina, kahakō): the portal silently strips them.
- **Address1 + City + State + Zip are required on EVERY row** by the form, even though the statute
  only itemizes donors above $100 aggregate (`FILING-GUIDE.md` §7).
- **Nothing in `data/` is ever committed to git.** It holds donor names, addresses and bank
  activity. The kit's `.gitignore` already excludes it; do not change that.

## The driver

**Launch through `tools/csc_launch.py`, never `node` directly.** It caps the browser to one
instance, checks free memory, writes a pidfile, and stops the driver cleanly so Chromium is not
left running.

    python .claude/skills/csc-filer/tools/csc_launch.py --status
    python .claude/skills/csc-filer/tools/csc_launch.py --start        # opens the portal in a Chromium window
    python .claude/skills/csc-filer/tools/csc_launch.py --stop

(On a Mac use `python3`.) The window opens on https://csc.hawaii.gov/CFS. **Tell the treasurer to
log in there.** Their session is saved in `.csc_profile/` inside the kit (gitignored), so after the
first time it usually autofills.

Then drive it:

    python .claude/skills/csc-filer/tools/csc_cmd.py "<command>"      # one command, prints the reply
    python .claude/skills/csc-filer/tools/csc_js.py <frameSubstr> <file.js>   # multi-line JS from a file

Commands: `goto:<url> | frames | shot | js:<frameSubstr>::<code> | batch | batch:<n> | readpop |
shotpop | clearcookies | quit`

- Control, status and output files live in `.tmp/csc/`: `csc_ctrl.txt`, `csc_status.txt`,
  `csc_js_out.json`, screenshots `csc_<n>_<tag>.png`.
- `js:<sub>::<code>` runs `code` in the first frame whose URL contains `<sub>` (`top` = main frame).
  Read `PORTAL-MAP.md` §1 before choosing `<sub>`; the outer/inner frame trap is the number one
  time sink.
- **`readpop` / `shotpop`** read or screenshot the newest popup tab. The disclosure preview, File
  Report and Filing Confirmations open in a NEW tab the main page cannot see; this is how you read
  cash-on-hand.
- **`batch`** enters Schedule A contributions from `data/batch_schedule_a.csv`, skipping keys
  already in `data/entered_ledger.csv`. It always asks the PORTAL whether a donor already has a name
  record (search the name grid, exact match on the name cell, wrapper-row guard) so carried-over
  donors do not get duplicated. `batch:3` enters at most three rows; use it for the first run.
- All data is server-side. A hang or restart loses nothing; stop the driver with `--stop` and start
  it again.

### The batch CSV

`data/batch_schedule_a.csv`, one monetary contribution per row, with these headers (the ActBlue
column names; a Squarespace export is mapped onto them by reading its header row, see
`FILING-GUIDE.md` §3):

`Donor First Name, Donor Last Name, Donor Addr1, Donor Addr2, Donor City, Donor State, Donor ZIP,
Donor Occupation, Donor Employer, Date, Amount, Deposit No., Non-Resident`

`Date` is `MM/DD/YYYY` and is the **bank credit date**, `Amount` is gross, `Deposit No.` is
optional, `Non-Resident` is `Y` or blank. Rows with an empty `Donor Addr1` are skipped until the
address is supplied. Build this file yourself from the reconciled data and show it to the
treasurer before running `batch`.

## Workflow (a typical preliminary or final disclosure report)

1. **Orient.** `FILING-GUIDE.md` §0, all six rows, in order.
2. **Scope the report on a deposit basis.** Include only money that hit or left the committee
   BANK ACCOUNT by the period-end date. Sources: the bank CSV, the Squarespace donations CSVs,
   any ActBlue CSVs (paid and refunded), any other processor exports, the treasurer's own list of checks written. Map each
   contribution to the deposit that carried it.
3. **Reconcile and build the delta** (delete / keep / add) against what is already in the portal.
   Pull the live Schedule A and B grids, match by (name, date, amount, deposit), and HARD-COUNT
   before proposing any deletion. Show the delta and wait.
4. **Delete** out-of-scope rows one at a time (Date link → `#sc_b_del_t` → `.swal2-confirm`),
   re-scanning the live grid each iteration.
5. **Add** contributions (`batch`), then expenditures, other receipts, loans and in-kind through
   scripted entry (`FILING-GUIDE.md` §6, entry-script pattern).
6. **In-kind**: non-monetary Schedule A row at fair market value PLUS a matching Schedule B
   expenditure to the vendor, or cash-on-hand is overstated.
7. **Validate**: Contribution Limit, Employer/Occupation, Non-Resident (menu items 31, 30, 33).
   Clean = "No Records Found"; non-resident shows the percentage (cap 30%).
8. **Reconcile cash-on-hand**: Preview Disclosure (item 28 → period + "Disclosure Report" radio →
   Preview) → `readpop` → **Section III Line 6 "Cash on Hand at the Closing"** must equal the bank's
   period-end balance to the penny. Line 15 = total receipts, Line 16 = Schedule B total, Line 10 =
   surplus/deficit.
9. **Write the working paper**: `data/periods/<period>/transactions.md` with the scope, every
   treatment decision, the Line 6 tie-out and anything left open. The next period starts from it.
10. **Stop.** Report the totals and the Line-6-ties-to-bank confirmation, flag anything open, and
    tell the treasurer that File Report (menu item 34) is theirs to click.

## Where things go in this kit

| What | Where |
|---|---|
| Bank CSV exports | `data/bank/` |
| Squarespace donations exports | `data/squarespace/` |
| ActBlue and other processor exports | `data/actblue/`, `data/processors/` |
| The Schedule A batch file and its ledger | `data/batch_schedule_a.csv`, `data/entered_ledger.csv` |
| Per-period working paper and entry scripts | `data/periods/<period>/transactions.md`, `.../scripts/` |
| Browser session | `.csc_profile/` |
| Driver control files, screenshots, logs | `.tmp/csc/` |

`data/`, `.csc_profile/`, `.tmp/` and `.env` are gitignored. Tooling updates arrive with `git pull`;
nothing under those folders is touched by it.
