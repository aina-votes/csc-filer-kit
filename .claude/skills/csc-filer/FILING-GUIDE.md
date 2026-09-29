# FILING GUIDE — how a Hawaii CSC disclosure report actually gets built

Read this together with `SKILL.md` (the workflow) and `PORTAL-MAP.md` (the portal reference).
Everything here was learned filing real reports for real committees between January and August
2026 and is written so it does not have to be learned again.

Two words used throughout: **the treasurer** is the human you are working with (the committee's
treasurer or the person the treasurer has delegated data entry to). **The agent** is you, Claude.

---

## 0. START HERE — the orientation for "enter this period's report"

Do these in this order. Each one answers a question that cost real time when it was skipped.

| # | Do this | Because |
|---|---|---|
| 1 | **Read `data/periods/<period>/transactions.md` if it exists, and the previous period's** | The prior period's Line 6 closing cash is this period's opening cash, and treatment decisions (loan vs other receipt, deferred in-kind, an uncashed check) are already made there. Never re-derive them. If this is the first period in this kit, say so and start the file. |
| 2 | **Launch the driver and have the treasurer LOG IN, before any legal research** | The CFS home screen states the current report's name, period and deadline verbatim in one sentence. §1. This is the single biggest time-saver. |
| 3 | **Verify the committee** — Org Report, `openMenuItem('ccadmin_menu_item_21')`, frame `cc_xorg_report` | Read the committee name and depository account number and tell the treasurer what you see. The Org Report also names **every committee depository**, which answers "is there another bank account?" without asking. |
| 4 | **Get the bank export** — a CSV of the account activity, dropped into `data/bank/` | §2. Identify the account by the **account number inside the file**, not the filename. |
| 5 | **Get the processor data** — Squarespace donation CSVs (Specific fund, one per fund) into `data/squarespace/`; ActBlue CSVs into `data/actblue/` only if the committee also uses ActBlue | §3 and §3b. Ask the treasurer to download them; do not reach for API credentials unless they offer them. |
| 6 | **Check `Filing Confirmations` (`item_36`)** for what has actually been filed | §5. It is the only authoritative source for filing dates and Original-vs-Amended. |

Then: enter → validate → preview Line 6 → **stop. The treasurer clicks File Report.** Never you.

---

## 1. ⭐ The portal tells you the period and deadline — ask it, do not derive it

**The CFS home screen, immediately after login, prints the answer:**

> "The next report for Candidates running in 2026 is the **2nd Preliminary Primary Report** due
> **Jul 29, 2026**, covering the period **Jul 1 - Jul 24, 2026**."

The period `<select>` (`[name=rpt_period]` on the Preview screen) gives the same thing plus the
**report id**: `488|2024-2026 2nd Preliminary Primary July 1 - July 24, 2026`.

**Two traps this avoids:**

- **The period does NOT end on the due date.** Only the June-30 report is "current through" a round
  date. Every other preliminary is current through the **fifth calendar day before its deadline**
  (HRS §11-334(a)(1), closing sentence). Jul 29 deadline → period ends **Jul 24**. A deposit that
  posts on the due date belongs to the NEXT report. Assuming "through today" silently pulls in
  out-of-period money.
- **Portal report names are not the statutory subparagraph letters.** CFS says "1C Preliminary
  Primary" and "**2nd** Preliminary Primary". There is no "1D" anywhere in the portal. Use the
  portal's string.

Deadlines the portal has not surfaced yet, for planning: late-contribution report = 3rd day before
the election if any one person aggregates >$500 in the 14th-to-4th-day window (HRS §11-338(a));
final report = period through election day, due 20 days after (HRS §11-334(a)(2)). Statute text:
https://www.capitol.hawaii.gov/hrscurrent/Vol01_Ch0001-0042F/HRS0011/ . But get the CURRENT period
from the portal.

---

## 2. Bank data — where it is and how to trust it

- Ask the treasurer to export the committee account's activity as a **CSV** covering the period
  (every bank's online banking has a "download" or "export" on the account activity page; CSV,
  not PDF). It goes in `data/bank/`. If there is also an `.xls` twin, ignore it.
- **One file per account, and the filename usually does not say which.** Typical columns:
  `Account Number, Post Date, Check, Description, Debit, Credit, Status, Balance`. **Match the
  account number in the file against the Org Report's depository account number** before using it.
- **The `Balance` column self-validates the export.** If the running balance chains correctly from
  the first row to the last, the export is gapless and there is no gap for a missing transaction
  to hide in. Say so explicitly: it is what lets you assert a variance of $0.00 rather than
  "appears to match".
- **If the export has no `Balance` column** (OFX or a plain transactions CSV), reconstruct it
  from an anchor: `balance(d) = anchor_balance - sum(txns on or before anchor date) + sum(txns on
  or before d)`. Validate with **two independent anchors**, a printed statement balance inside the
  window and the known current balance; if the forward walk lands exactly on the second anchor,
  the file is complete. `on or before` the anchor date includes that day's transactions, and the
  implied opening balance is the balance BEFORE the first row, so subtract day-one transactions
  to get it. Ask the treasurer for one statement PDF to anchor against.
- **`Status` matters.** `Pending` rows have a blank Balance and have not posted. A pending row
  dated inside the period but posting after it is next period's.
- ActBlue bank memos read `ACTBLUE STS (AMA ACTBLUE ST ... <COMMITTEE>`. **STS = ActBlue Technical
  Services**, which is also the payee name to use on Schedule B (§4).
- Routing numbers are often not printed on statements; ask the treasurer if one is needed.

---

## 3. ⭐ Squarespace donations — the primary processor for this committee

**Route, no credentials:** the treasurer logs into the committee's Squarespace site, opens the
**Donations** dashboard, clicks **View all** under Contributions, then **Export Data** →
**Download .csv**. The export offers **All funds** or a **Specific fund**. Ask for **Specific
fund**, one file per fund: per Squarespace's own documentation (support article 205811198,
"Managing donations", read 2026-09-29) the All-funds export **does not include the donation form
responses**, and a Specific-fund export does. Employer and occupation, which the portal's
Employer/Occupation validation requires, are donation-form fields, so an All-funds file will
leave every row failing that check. Files go in `data/squarespace/`. The same article says the
dashboard only covers the **new** donation block; if the site still uses the original block,
those gifts show only in Sales analytics and the bank, and the treasurer must export orders from
Commerce instead. A forum thread from June 2026 reports Specific-fund exports still missing the
form fields for some sites; if the columns are absent, the treasurer opens each contribution's
details in the dashboard and reads employer and occupation off the page.

**Column names are not fixed here.** Squarespace's export layout was not verified from a real
file when this kit was built. Read the header row of the first file you receive, map it onto the
batch CSV headers (donor name, street address, city, state, ZIP, occupation, employer, date,
gross amount), show the mapping to the treasurer, and then record the confirmed mapping in
`data/periods/<period>/transactions.md` so the next period does not re-derive it. Squarespace
collects a billing address at checkout, so real street addresses should be present; if a row has
none, it is skipped until the treasurer supplies one (§7).

**Deposits and fees.** Squarespace donations are collected by whichever processor the site is
connected to (Squarespace Payments, Stripe or PayPal) and paid out to the bank in **batches, net
of fees**. So the reconciliation is the same shape as ActBlue's below: group the donations that
fall into one payout, sum gross and fees, match the batch's **net** to a bank credit, and report
each contribution at **gross** on the bank credit date with the fee as a Schedule B expenditure
(§4). Payouts and their fee totals are listed in the processor's own payouts page (Finance →
Payouts for Squarespace Payments; the Stripe or PayPal dashboard otherwise). If the export does
not carry a payout id, match on amount and the payout lag, and write the lag you observe into the
working paper. **A batch with no matching bank credit is a finding**, exactly as in the ActBlue
section.

**Refunds** appear in the same Contributions panel; a refunded gift is removed from the period it
was deposited in, or reported as a refund expenditure if it was already filed (§4 pattern, payee =
the donor).

---

## 3b. ActBlue data, if the committee also uses it — and the reconciliation that matters

**Preferred route, no credentials:** the treasurer logs into secure.actblue.com, opens the
committee dashboard, and downloads the contributions CSV for the period (Reports, or the
Contributions list, "Download CSV"). Also download the **refunds** for the period. Files go in
`data/actblue/`.

**Optional route:** if the treasurer has created ActBlue API credentials (Dashboard → Tools → API
credentials; a Client UUID and Client Secret), `tools/actblue_pull.py --start --end` pulls
`paid_contributions` and `refunded_contributions` through the CSV API. The credentials are read
from `ACTBLUE_CLIENT_UUID` / `ACTBLUE_CLIENT_SECRET` in the environment or from a gitignored
`.env` file the treasurer fills in themselves, never printed, never written anywhere else. The
date range must be 6 months or less.

**The columns that do the work:** `Date` (gift), `Amount` (gross), `Fee`, `Disbursement Date`,
`Disbursement ID`, `Donor First/Last Name`, `Donor Addr1/City/State/ZIP`, `Donor Occupation/Employer`,
`Recurrence Number`, `Refund Date`. ActBlue supplies **real street addresses and occupation/employer**,
so an ActBlue-sourced filing needs no placeholder addresses.

**The reconciliation, and it is the whole job:** group contributions by `Disbursement ID` /
`Disbursement Date`, sum gross and fees per batch, then match each batch's **net** to a bank credit.
The lag is tight and consistent (typically disbursed Sunday → posted Wednesday, +3 days). **A batch
with no matching bank credit is a real finding, not noise.** Check in this order: (1) refunds file
empty? then not a clawback; (2) `Disbursement Date` populated? then ActBlue is not still holding it;
(3) bank export gapless? then it never arrived. The most likely cause is ActBlue **mailing a paper
check** before a new committee's bank link verifies, i.e. an uncashed check, not a missing deposit.
Under deposit-basis reporting (§9) that money is reported in the period it is deposited.

A trap seen in practice: a recurring $5 gift produced **two separate $4.80 disbursements** weeks
apart, so an amount-only match "found" the June one in a July bank credit. Match on the
disbursement-to-deposit lag as well as the amount.

---

## 4. ⭐ Booking processor fees on Schedule B

One Schedule B row per payout batch (or one per period if the processor only reports a period
total), payee = the processor, name type **OTH** with the org name in `cn_lname`,
`sb_ecat_id` **2** = Bank Charges, Merchant Fees & Adjustments, `sb_eauth_id` **1** = Directly
Related to Candidate's Campaign, purpose "Credit card processing fees on <processor>
contributions".

**Squarespace: the payee depends on which processor the site is connected to.** Read it off the
bank memo of the payout credit and the site's payments settings, then confirm the legal name and
address from the processor's own statement or invoice before the first entry, and record what
was used in the working paper so it is reused verbatim. Not yet verified for this committee.

**ActBlue, settled from prior filings, do not re-derive:**

| Field | Value |
|---|---|
| Payee | **ActBlue Technical Services** (name type **OTH**, org name in `cn_lname`) |
| Address | **366 Summer St, Somerville, MA 02144** |
| `sb_ecat_id` | **2** = Bank Charges, Merchant Fees & Adjustments |
| `sb_eauth_id` | **1** = Directly Related to Candidate's Campaign |
| Purpose | "Credit card processing fees on ActBlue contributions" |

Contributions go on Schedule A at **gross**, dated at the **bank credit date**, and the fee rides as a
matching Schedule B expenditure. That is what makes gross contributions net to the actual deposit and
Line 6 tie to the bank.

**Precedent oracle for any unfamiliar vendor or category:** the Commission publishes every filed
contribution and expenditure as open data at https://data.hawaii.gov (search "Campaign Spending
Commission"; the expenditures dataset has vendor name, address and category). Filter on the vendor
to see how other committees booked it. Do this instead of guessing a category.

---

## 5. ⭐ Filing Confirmations is the authoritative filing record

`openMenuItem('ccadmin_menu_item_36')` → frame **`cc_xCC_02`** → "DISCLOSURE / LATE CONTRIBUTIONS
REPORTS FILED": Report Name, Reporting Period, Deadline, **Filing Date**, **Amended (Y/N)**.

- This is the ONLY reliable source for **whether** and **when** something was filed.
- **The disclosure preview's Section II "Type: Amended" is cosmetic and lies on originals.** Do not
  investigate it; check this screen instead.
- **Amend Mode has no banner.** The reliable test: the Preview `rpt_period` dropdown lists **one**
  option (current report) in normal mode and **every filed report** in amend mode.
- **In that dropdown the option value (`report_id`) does not follow display or date order.**
  Select a period by its visible text, never by assuming ids are chronological, and confirm the
  period printed at the top of the preview before reading any line off it.

---

## 6. Driver mechanics — the bits that cost time

The driver is `tools/csc_driver.mjs`, started through `tools/csc_launch.py --start`. It opens a
real Chromium window on a persistent profile at `<kit>/.csc_profile`. **The treasurer logs in
inside that window, by hand.** The agent never sees, asks for, or stores the portal password.
Control files live in `<kit>/.tmp/csc/`.

- **Wait for the READY line**, which the driver writes only after a ~3 s page load and a screenshot.
  `csc_launch.py --start` waits for it; do not add fixed sleeps on top.
- **Login:** the profile autofills after the first time; the button is `input.button.button-block`
  (an INPUT, not a `<button>`). Sessions expire often. Screenshot the start page; if it is the login
  screen, ask the treasurer to log in in the window, then re-verify the committee.
- **`js:<substr>` matches the FIRST frame whose URL contains `<substr>`, which is usually the OUTER
  wrapper.** ScriptCase renders results in an inner frame
  `<app>/index.php?nmgp_opcao=pesq&script_case_init=1`. Targeting `ccadmin_validation5` reads the
  empty outer frame; you need `validation5/index.php?nmgp_opcao=pesq`. This has wasted two rounds
  on every validation for every new operator.
- **Validation results live TWO frames deep**, at `window.top.frames[0].frames[0]`, and the outer
  and inner frames share the same URL, so substring matching picks the wrong one and returns the
  blank form. Walk the frame tree from `top` instead.
- **The validation screens' period `<select>` looks pre-filled and is not.** `[name=rp_id]` renders
  the period text but its `.value` is `""`. Clicking Validate without setting it produces a
  SweetAlert *"Select Reporting Period : Required field"* on the top document and a raw DB2 error in
  a nested frame. Set it explicitly first; the option value is the full
  `489##@@2024-2026 Final Primary July 25 - August 8, 2026` style string.
- **`frames` output format is `FRAMES:\n0: <url>\n1: <url>`**; parse with `^\s*\d+:\s*(\S+)`.
- **Never find a button by text-matching across all elements.** Use the known ids, or call the
  onclick directly:
  - **Validate** = `a#sc_b_pesq_fields_right`; its onclick sets `document.F1.bprocessa.value='pesq'`
    then `nm_submit_form()`. Calling those two directly is more reliable than `.click()`.
  - **Preview Report** = `a#sub_form_b`, onclick `scBtnFn_sys_format_ok()`. Call it directly.
  - Disclosure radio = `#id-opt-rpt_name-8` (`DIS`); the group is SA/SB/SC/SD/SE/SF/SF2/DIS.
- **Menu ids that are easy to mis-hit:** `15` Sched A list, **`16` Sched C list**, `17` Sched D list,
  **`18` Sched B list**, 36 Filing Confirmations, 34 File Report → Disclosure (**treasurer only**),
  22 Org Report Amend, 28 Preview Disclosure, 29 Preview Late Contributions.
- **The name grid pages at 50.** A committee with 167 name records spans 4 pages. A "does this
  payee already exist?" check that reads only page 1 is WRONG and nearly created duplicate payee
  records. Page through with `#forward_bot`, or say you cannot answer the question.
- **The wrapper `<tr>` CONTAINS the data `<tr>`**, so counting rows or anchors double-counts and an
  "expected exactly 1" guard fails on a name that is not duplicated. Dedupe anchors by element
  identity.
- **The name form's State and Zip render late, as does the add_transaction radio.** A batch row can
  die on "State: Required field / Zip Code: Required field" with the other fields filled; the
  insert is rejected so no partial record exists and a plain re-run of `batch` fixes it.
- **On the Schedule B add form the payee renders near the BOTTOM.** A read-back guard that only
  inspects the first ~220 chars of `body.innerText` will falsely fail. Search the whole string; the
  pre-populated `sa_address_1` is a better identity check than the name.
- **The amount field applies a currency mask**, so `25.00` reads back as `$ 25.00`. Strip `$` and
  `,` before comparing or every read-back guard fails.
- Menu clicks usually work with a report popup still open. Do not assume you must close it; verify
  the frame you landed on.

**Entry-script pattern for anything beyond the built-in Schedule A batch (Schedule B, C, D rows):**
write a small Python script in `data/periods/<period>/scripts/` that drives the portal through
`csc_js.run_js`, with this shape: **fill → read every field back → compare to expected → abort on any
mismatch → submit → check for a SweetAlert error → append to an idempotent ledger keyed on
(name|date|amount).** The ledger makes a re-run safe after a crash, and a resume flag ("already on
the target form? skip navigation") avoids creating duplicate name records when a guard trips
mid-row. Copy the shape, then check every frame target against `PORTAL-MAP.md` §1 before trusting
the script's output.

**If you enter a row by hand around the batch runner, append it to `data/entered_ledger.csv`
immediately**, or the next `batch` duplicates it.

---

## 7. Small things that were true and worth keeping

- `≤$100` aggregate donors need no address by statute (HRS §11-333(b)(1)) but the portal demands
  Address1/City/State/Zip regardless. With ActBlue data you always have real ones. `cn_zip`
  accepts ZIP+4. Confirm the candidate is NOT publicly financed first (HAR §3-160-62 flips the rule
  for qualifying contributions).
- Adding a second transaction to an **existing** name: use the name-grid row's per-schedule anchor
  (href contains `cc_sb_add_edit` / `cc_sa_add` / etc.), **not** "Edit this row" → Save. It avoids
  a duplicate name record.
- Schedule A/B list grids show a **Reported (Lock)** column: `Yes` = already filed in a prior
  report. A handy sanity check that you only added to the open period.
- `sa_monetary`: `-1` = Yes (non-monetary/in-kind), **`-2` = No (monetary)**. Non-monetary rows
  additionally require a Category or the portal rejects them.
- Pre-transliterate ʻokina and kahakō: the portal silently strips non-ASCII (Mākaha → Mkaha).
- A print/View rendering can restate boilerplate that looks like a certification (the Org Report's
  "$1,000 or less" paragraph prints on every report). Read the stored field, not the recital.

---

## 8. Self-funding, loans and in-kind — the treatments that get asked about

- **Cash the candidate deposits** → Schedule C Other Receipt, category "Candidate's Own Funds" (or a
  Schedule D Loan if repayment is expected; candidate loans are unlimited but need an executed loan
  document above $100).
- **A vendor the candidate paid personally** (goods or services) → in-kind: Schedule A non-monetary
  Contribution at fair market value PLUS a matching Schedule B expenditure to the vendor. Without the
  Schedule B half the in-kind inflates cash-on-hand (Line 11 counts non-monetary in receipts) and
  Line 6 will not tie to the bank. If the candidate instead wants it as a repayable advance →
  Schedule D Loan advance + matching Schedule B expenditure.
- Candidate's own funds go in as Other Receipt or Loan, NOT as a plain Contribution.

---

## 9. Deposit basis is the rule, not a convention

HAR §3-160-30(c) deems the deposit date to be the received date, so a contribution is reported in
the period whose bank statement shows it. HAR §3-160-30(b) separately requires deposit within 7 days
of receipt, with fines, so an ActBlue check sitting uncashed is both "next period's" AND a compliance
clock the treasurer should hear about. The rules say nothing about payment processors or their fees,
which is why §4 is a settled house treatment rather than a citation.

Scope every report on this basis: include only money that hit (contributions, receipts) or left
(expenditures) the committee bank account by the period-end date, and map each contribution to the
deposit that carried it.
