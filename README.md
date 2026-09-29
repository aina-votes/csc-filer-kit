# CSC Filer — entering campaign finance reports with Claude

This kit lets Claude, running on your own computer, do the data entry for your committee's
reports in the Hawaii Campaign Spending Commission's filing portal (csc.hawaii.gov/CFS). You give
it your bank and ActBlue exports, it enters the rows, runs the portal's own checks, and proves
that the cash-on-hand figure matches your bank statement to the penny. Then you click File
Report. Claude never files.

This page gets you set up. It assumes you have never done any of this before. Budget half an hour.

## How it works, in one paragraph

Claude opens a real browser window on the portal. You log in there, the same way you always do;
Claude never sees or asks for your password. From then on Claude works inside that window while
you watch: it reads what is already entered, compares it with your bank and ActBlue files, shows
you a table of what it plans to add or remove, and waits for you to say yes. When the report
previews with the right cash-on-hand, it stops and tells you the File Report button is yours.
Nothing about your donors or your bank leaves your computer.

## Setup: four things you do, then one thing you paste

1. **Get Claude Pro** (or Max) at https://claude.ai. Claude Code is included with the paid plans
   and not with the free one.
2. **Install the Claude desktop app** from https://claude.ai/download and sign in with that
   account.
3. **Open the Code tab** in the app. Click **Select folder** and choose your **Documents** folder.
   When it asks which permission mode to use, choose **Bypass permissions**. That lets Claude
   install what it needs and drive the browser without stopping to ask you before every step.
   The rules in this kit still hold: it never files, and it never asks for a password.
4. **Paste the prompt below** into the message box and press Enter. Then do what Claude says.
   It will explain each step before doing it, and it will stop and tell you when you need to
   click something: an Install button on a pop-up or a Yes on a Windows prompt. Near the end a browser window opens on the CSC portal and Claude asks you
   to log in there.

When it finishes, it tells you to reopen the app on the new folder it created inside Documents.
Do that (Code tab, Select folder, choose `csc-filer-kit`). From then on, Claude knows how the
portal works, because the rules are in the folder.

### The prompt

Copy everything in the box.

```
I am not a developer. Set up my computer so you can enter my campaign committee's finance reports into the Hawaii CSC portal for me. Work one step at a time, explain each step in one plain sentence before you do it, and stop and tell me exactly what to click whenever a browser window, a pop-up, or a password prompt appears. Never ask me for a password and never store one.

The kit lives in a public GitHub repository: https://github.com/aina-votes/csc-filer-kit.git. No GitHub account is needed to download it.

Do these in order, checking each one before moving on:

1. Tell me which operating system this is and confirm that we are in my Documents folder. If we are somewhere else, stop and tell me to reopen you on Documents.
2. Check whether Git is installed (git --version). If it is not: on Windows install it with winget (winget install --id Git.Git -e --source winget) and tell me to click Yes if Windows asks to allow changes; on a Mac run xcode-select --install and tell me to click Install on the pop-up, then wait for me to say it finished.
3. Check whether Python 3 is installed (python --version, or python3 --version on a Mac). If it is not: on Windows install it with winget (winget install --id Python.Python.3.12 -e --source winget); on a Mac it comes with the developer tools from step 2.
4. Check whether Node.js is installed (node --version). If it is not: on Windows install it with winget (winget install --id OpenJS.NodeJS.LTS -e --source winget); on a Mac open https://nodejs.org in my browser, tell me to download the LTS installer for macOS and click through it, then wait for me to say it finished. If a program you just installed is not found afterwards, tell me to quit and reopen the Claude app on Documents and paste this prompt again; you will skip what is already done.
5. Download the kit into this folder with git clone. It is public, so no sign-in should appear.
6. Inside the csc-filer-kit folder, run npm install, then npx playwright install chromium. These download the browser Claude will drive. They can take a few minutes; tell me that is normal.
7. Inside the kit folder, run python .claude/skills/csc-filer/tools/doctor.py (python3 on a Mac). It must end with 0 failures. If it does not, fix what it names and run it again.
8. Run python .claude/skills/csc-filer/tools/csc_launch.py --start. A browser window opens on the CSC portal. Tell me to log in there with my committee's CFS username and password, and wait for me to say I am in. Do not ask me what they are.
9. Run python .claude/skills/csc-filer/tools/csc_cmd.py shot and look at the screenshot it names to confirm I am logged in. Then run python .claude/skills/csc-filer/tools/csc_launch.py --stop to close the browser.
10. Tell me that setup is complete and that I should now reopen you on the folder csc-filer-kit inside Documents, because the filing rules live in that folder.

If anything fails, show me the exact error text and tell me to send it to Sam.
```

## Every time after that

Open the Claude app, Code tab, choose the `csc-filer-kit` folder. Before you start, put two files
in the kit's `data` folder (Claude will tell you the exact place if you ask "where do the files
go"):

- **Your bank export.** Log into the committee's online banking, open the account activity for the
  reporting period, and download it as a **CSV** (not PDF). Put it in `data/bank`.
- **Your ActBlue export**, if the committee uses ActBlue. Log into secure.actblue.com, open the
  committee dashboard, and download the contributions CSV for the period, plus the refunds if
  there are any. Put them in `data/actblue`.

Then say what you want in plain English:

- `Enter the next report. Here is what I put in the data folder.`
- `Check what is already in the portal for this period against my bank file.`
- `Add the two checks I wrote this month: $250 to Vistaprint on 8/3 for palm cards, $1,200 to Sarah Lee on 8/5 for canvassing.`
- `Preview the report and tell me if the cash on hand matches the bank.`

Claude follows a fixed routine: it opens the browser window, asks you to log in, reads the portal
to find out which report is due and what period it covers, reads your files, shows you a table
of what it will add or remove, and waits. If the table is right, type **yes**. It enters the
rows, runs the portal's three validations, previews the report, and reports the cash-on-hand
figure against your bank balance. When they match, it stops. **You click File Report.**

Things to know:

- **Claude never asks for a password.** If it ever does, say no and text Sam.
- **Deposit basis.** A contribution is reported in the period the money hit the bank, not the
  day the donor gave it. Claude works this way on purpose; the Commission's rules require it.
- **Every donor row needs a street address in the portal**, even small ones. ActBlue supplies
  them. For a cash or check donor, have the address ready.
- **Small entries by hand are fine.** If you add something in the portal yourself, tell Claude so
  its records stay in step and it does not enter the row twice.
- **If Claude asks you to approve something and you do not understand it,** say no and ask it to
  explain. Nothing is lost by saying no.

## When you are stuck

Screenshot the message and text it to Sam with what you were trying to do. The most common
first-day problems:

| What you see | What it means | What to do |
|---|---|---|
| Claude says it cannot find Git, Python or Node after installing | The app needs restarting to see new programs | Quit the Claude app fully, reopen it on Documents, paste the prompt again; it skips what is done |
| `npm install` or `playwright install` fails with a network error | The download was interrupted | Ask Claude to run the same step again |
| The browser window opens but shows the login page every time | The saved session expired, which the portal does on its own | Log in again in that window; Claude waits |
| Claude says the committee name in the portal is not yours | The portal remembered a different login | Log out in the window, log in as your committee, tell Claude to check again |
| `[FAIL]` lines from the doctor | Something is missing on the computer | Ask Claude to fix the line it names |
| Claude says it needs a subscription | The signed-in account is on the free plan | Upgrade to Pro at claude.ai, sign out and in |

## If Claude gets stuck on your machine: the manual route

The prompt above does the installs for you. If it cannot, here is the same thing by hand.

**Windows.** Git: https://git-scm.com/download/win, the 64-bit Setup link, Next through every
screen, Install, Finish. Python: https://www.python.org/downloads/, the yellow Download button,
and on the first installer screen **tick "Add python.exe to PATH"** before clicking Install Now.
Node.js: https://nodejs.org, the LTS button, Next through every screen, Install.

**Mac.** Press Command+Space, type `terminal`, press Enter, type `xcode-select --install` and
press Enter, click Install on the pop-up. Node.js: https://nodejs.org, the LTS button for macOS,
Continue, Install, your Mac password.

**Both.** Then reopen the Claude app on Documents and paste the prompt again. It detects what is
already installed and continues from the download.
