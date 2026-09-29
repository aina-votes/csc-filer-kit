# csc-filer-kit — entering a Hawaii campaign committee's reports into the CSC portal

This folder is a tool for one committee's treasurer. Claude drives a browser on the treasurer's
own computer to enter contributions, expenditures, receipts and loans into the Hawaii Campaign
Spending Commission's Candidate Filing System (https://csc.hawaii.gov/CFS), runs the portal's
validations, and reconciles cash-on-hand to the bank statement. **The treasurer files. Claude never
clicks File Report.**

**Before any portal work, read `.claude/skills/csc-filer/SKILL.md`**, then its two siblings
`FILING-GUIDE.md` and `PORTAL-MAP.md`. They hold the workflow, everything learned filing real
reports, and every field name and frame path in the portal.

Standing rules for every session in this folder:

- **Never click File Report, Submit, or anything that certifies a filing.** Stop at the preview,
  report the totals and the Line 6 tie-out, and hand off.
- **Never ask for, type, store, or read a password.** The treasurer logs into the portal by hand in
  the browser window the driver opens. The session lives in `.csc_profile/`, which you do not read.
  Bank, Squarespace and ActBlue logins are the treasurer's too: ask for CSV exports, not credentials.
- **Verify the committee after every login** (Org Report) and say what you see.
- **Show every delta before entering it** and wait for a yes. Portal deletions are one row at a
  time and cannot be undone from here.
- **Nothing in `data/`, `.csc_profile/`, `.tmp/` or `.env` is ever committed or shared.** They are
  gitignored; keep them that way.
- Start the browser only through `python .claude/skills/csc-filer/tools/csc_launch.py --start`
  (`python3` on a Mac) and stop it with `--stop` when the session ends.
- `git pull` at the start of a session picks up tooling updates. Never push from this folder.
- One plain sentence before each step, and stop and say exactly what to click whenever the
  treasurer needs to do something in the browser window.
- Legal questions (what a period covers, whether something is reportable, how to treat a loan)
  are answered from `FILING-GUIDE.md` and the cited statute. If the guide does not settle it, say
  so and suggest the treasurer ask the Commission (808-586-0285, csc@hawaii.gov) or Sam.

Owner: Sam Peck (ʻĀina Votes). Operator: the committee treasurer.
