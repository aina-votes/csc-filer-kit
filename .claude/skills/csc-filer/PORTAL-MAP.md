# CFS PORTAL MAP

The portal reference for the `csc-filer` skill: every frame path, element id, field name, radio
value and category code, organised by portal surface. `SKILL.md` is the workflow; this is the
manual. **Read this before driving the portal, not after something fails.**

Machine-verifiable parts (menu ids, name types, category lists, radio maps) can be refreshed
against the live portal by **`tools/probe_portal.py`**, which writes `PORTAL-MAP.generated.md`.
Run it once after login at the start of a filing session. The gotchas below are *not* probeable
and are maintained by hand.

Provenance is noted where it matters. Portal is **ScriptCase v1.3.5** unless stated.

---

## 1. Frames and navigation — the trap that costs the most time

**Every ScriptCase screen is a page inside a page.** JS aimed at the wrong one finds nothing and
returns empty, silently. `js:<substr>` in the driver matches the **first** frame whose URL contains
`<substr>`, which is usually the OUTER wrapper.

| Surface | OUTER wrapper holds | INNER `index.php?nmgp_opcao=pesq` holds |
|---|---|---|
| Name grid `cc_name_grid/` | the **search box** (`cn_fullname`) | the **result rows** and **`#sc_b_new_top`** |
| Validations `ccadmin_validationN/` | the **form** (period select, Validate button) | the **result grid** — the verdict |

Both halves bite in opposite directions, which is why this is the #1 time sink:

- Searching a name? target the **outer** frame.
- Reading rows, clicking "Add New Name & Transaction", or reading a validation verdict? target the
  **inner** frame — `js:nmgp_opcao=pesq::…`.

Reading a validation from the outer frame returns the blank form and **hides whether the check
passed**. (Verified again 2026-07-29; a copied validation script shipped with this bug and was patched.)

`frames` output is `FRAMES:\n0: <url>\n1: <url>` — parse with `^\s*\d+:\s*(\S+)`. A naive
`split(" ")[-1]` picks up the literal `FRAMES:` line.

**Driver ctrl-file races:** after a menu click the target frame reloads. A js command sent too soon
fills a form that is about to be replaced. Read a field back between steps.

### Popups

Preview/Print Report, File Report and Filing Confirmations open **new tabs** the driver's main
`page` cannot see. Use `readpop` / `shotpop` to read
`ctx.pages()[last]`. While a report popup is open, other menu clicks **silently no-op** on the main
page — close it first. (Contradicted once: 2026-07-29 menu clicks worked fine with a popup open.
⚠️ **CONFLICT** — treat as "verify the frame you landed on" rather than a hard rule.)

`readpop` can return a **stale** popup; verify a unique period marker in the text and re-read up to
~5×.

---

## 2. Menu item IDs

`openMenuItem('ccadmin_menu_item_<N>')`

| N | Screen | | N | Screen |
|---|---|---|---|---|
| 3 | Add Transaction | | 28 | Preview Disclosure |
| 8 | Amend Mode | | 29 | Preview Late Contributions |
| 15 | Schedule A list | | 30 | Employer/Occupation validation |
| 16 | Schedule C list | | 31 | Contribution Limit validation |
| 17 | Schedule D list | | 33 | Non-Resident validation |
| 18 | Schedule B list | | 34 | **File Disclosure — the treasurer's step, never the agent's** |
| 19 | Schedule E list | | 36 | Filing Confirmations |
| 20 | Schedule F list | | 39–45 | Export Data (Name table, SA, SB, SC, SD, SE, SF) |
| 21 | Org Report View/Print | | 54 / 55 | Org Report submenu |
| 22 | **Org Report Amend** | | 56 / 57 | Immediate-family limit validations |
| 23 | Change Password | | 12 | Logout |

To enumerate live: the items are `a`/`li`/`div` with `onclick` containing `openMenuItem`. They do
**not** carry `id="ccadmin_menu_item_N"` on the element itself — querying by that id returns
nothing. Match the onclick attribute.

---

## 3. Login and committee identity

- **Login button is `input.button.button-block`** — an INPUT, not a `<button>`.
  `document.querySelector('button')` clicks a hidden element and nothing happens.
- The Chrome profile **autofills the LAST-used login**. If more than one committee has ever
  logged in from this profile, the wrong one can be autofilled.
- **Verify the committee after every login** — Org Report (item_21, frame `cc_xorg_report`): read
  committee name + depository account number. The Org Report also lists **every depository**, which
  is how you answer "is there a second bank account?" without asking.
- Sessions expire often mid-run: the menu frame keeps working but data grids return "Unauthorized
  user". Relaunch → login → re-verify committee → re-enable Amend Mode if it was on.
- **All data is server-side.** Nothing is lost on a hang or relaunch. A hung driver's Chrome
  releases the profile lock when the node process is killed (TaskStop).
- **Parallel campaigns cannot share `.csc_profile`** (Chrome SingletonLock). Copy it:
  `cp -r .csc_profile .csc_profile_<committee>`, strip `lockfile`/`Singleton*`, and start the driver
  with `CSC_PROFILE` pointing at the copy. This kit is built for ONE committee; you will not need this.
- Logout (`item_12`) closes the tab before the server logout finishes, so the session survives and
  a relaunch auto-logs back in. To actually switch committees: `ctx.clearCookies()`.

---

## 4. Name grid and name form

**Flow:** Add Transaction (item_3) → `/CFS/cc_name_grid/` → `/CFS/cc_name_form/` → the schedule
form → back to grid.

### Name form `cc_name_form`

`cn_name_type` select:

| Value | Meaning |
|---|---|
| `IND` | Individual |
| `OTH` | Other Entity — a business/agency payee. Put the org name in **`cn_lname`** ("Last / Business Name"); fname/occupation/employer get disabled |
| `NCC` | Noncandidate Committee — PACs, union political accounts |
| `CAN` | Candidate |
| `IMM` | Immediate Family |
| `PP` | Political Party |

Fields: `cn_fname`, `cn_lname`, `cn_address1`, `cn_address2`, `cn_city`, `cn_state`, `cn_zip`
(accepts ZIP+4), `cn_occupation`, `cn_employer`.

`add_transaction` radios — which schedule opens next:

| id | value | Schedule |
|---|---|---|
| `id-opt-add_transaction-1` | `N` | none |
| `id-opt-add_transaction-2` | `SA` | Contribution |
| `id-opt-add_transaction-3` | `SC` | Other Receipt |
| `id-opt-add_transaction-4` | `SD` | Loan |
| `id-opt-add_transaction-5` | `SB` | Expenditure |
| `id-opt-add_transaction-6` | `SE` | Unpaid Expenditure |
| `id-opt-add_transaction-7` | `SF` | Durable Asset |

Buttons: submit `#sc_b_ins_t`, update `#sc_b_upd_t`, back `#sc_b_sai_t`.

⚠️ **The radio renders slightly after the rest of the form.** Clicking
`id-opt-add_transaction-2` immediately fails with `Cannot read properties of null`. 3 of 50 rows hit
this on 2026-07-29. **Wait for the element**; do not click blind. The post-failure screenshot shows a
fully-populated form, which is misleading — it renders in the gap between the error and the capture.
The `batch` runner now waits (fixed 2026-07-29); this still applies to anything you hand-drive.

### Adding a transaction to an EXISTING name — the only reliable path

Search the name (autocomplete pair: visible `cn_fullname_autocomp` + hidden `cn_fullname`, **set
both** and dispatch input/change, else the grid keeps the previous filter), then in the filtered row
click the **per-schedule anchor** whose `href` contains the target form:

`SA=cc_sa_add` · `SC=cc_sc_add_edit` · `SD=cc_sd_add_edit` · `SB=cc_sb_add_edit` · SE · SF
(in that column order, right after "Edit this row").

**DO NOT** click "Edit this row" (`nm_gp_submit4`) → pick a radio → Save (`sc_b_upd_t`). That opens
the modal without `Form_Action` and errors *"The following global variables are missing: SB_ID;
Form_Action;"*. The `add_transaction` + `sc_b_ins_t` path is only for **Add NEW Name & Transaction**,
which creates a duplicate name record.

⚠️ **WRAPPER-ROW MISCLICK.** `[...querySelectorAll('tr')].find(tr => tr.innerText.includes(payee))`
can match an OUTER wrapper `<tr>` whose first schedule link belongs to the **first data row** —
silently attaching the transaction to the wrong name. Exclude other names in the match, or use the
search box, and **read the payee back off the transaction form before submitting.**

---

## 5. Schedule A — contributions (`cc_sa_add`)

`sa_date` · `sa_deposit_no` (blank for non-monetary; free text, gaps harmless) · `sa_amount` ·
`sa_desc` · `sa_ecat_id` (Category) · `sa_qcc` / `sa_qcc_period` (public financing only).

| Radio | `-1` | `-2` |
|---|---|---|
| `sa_resident` | `Y` = **non-resident** | `N` = resident |
| `sa_monetary` | `Y` = **non-monetary / in-kind** | `N` = monetary (cash) |
| `isminor` | | `-2` = not a minor |
| `returnscreen` | `-1` = go to list | `-2` = `N`, loop back to Add Transaction (**batch mode**) |

`sa_monetary` reads as the question "**Non-Monetary?**" — so `-2` = No = an ordinary cash gift.

- **Non-monetary contributions REQUIRE `sa_ecat_id`** or the portal rejects: *"A value in the
  Category field is required for a non-monetary contribution."* Categories are the same list as
  Schedule B.
- **Address1 + City + State + Zip are required by the FORM on every row**, regardless of the
  statutory $100 itemisation threshold. For ≤$100-aggregate donors with no known street address, use
  `"- "` placeholders in Address1/City with the real State + ZIP from the card-AVS ZIP.
- **Non-HI small donors fail on "State: Required field"** — set State from the card-AVS ZIP and
  re-run.

### In-kind: always book BOTH sides

An in-kind good/service = a **non-monetary Sched A contribution** at FMV (HAR §3-160-30(e)) **PLUS a
matching Sched B expenditure** to the vendor. Hawaii's Line 11 counts *"Monetary AND Non-Monetary"*
in receipts, so a lone non-monetary row **inflates Line 6** and breaks the bank tie. Sched B has no
non-monetary flag, so the offset is an ordinary expenditure row. Proven: a $64 USPS PO Box in-kind
pushed Line 6 to $1,949.57; the offsetting $64 Sched B row brought it back to $1,885.57 = bank.

### Editing / deleting

- **Edit**: Sched A list (item_15) → the row's **DATE-text `<a>`** → `cc_sa_edit` → set fields →
  **`#sc_b_upd_t`** (not `ins`). The form closing back to the list means it saved.
- **Delete**: same date link → `#sc_b_del_t` → `.swal2-confirm`.
- ⚠️ **Row hashes go STALE after paging** — ScriptCase regenerates
  `nm_gp_submit5('/CFS/cc_sa_edit/',…,'@SC_par@…<hash>')` per grid render. Never store hashes across
  pages. Re-scan the live grid each iteration.
- ⚠️ **Grid cell indices SHIFT** — some rows carry a leading empty `<td>`, and in-kind rows have an
  empty deposit cell. Match by regex or known values, never by fixed index.
- Finding a row in a long list: the quick-search box is flaky. Set
  `select[name=nmgp_quant_linhas]` = 50 and page with `#forward_bot`. The list is alphabetical by
  last name. `#rec_f0_bot` + `#brec_bot` record-jump did not advance reliably.

---

## 6. Schedule B — expenditures (`cc_sb_add_edit`)

`sb_date` · `sb_check_no` (opt) · `sb_amount` · `sb_desc` (Purpose) · `sb_public_fund` radio
(defaults N).

`sb_eauth_id` — Authorized Use: **`1`** = Directly Related to Candidate's Campaign.

`sb_ecat_id` — Category (**full list re-read live 2026-08-28**; the previous table held only 9 of these 24 and led to a near-miss on a food expenditure):

| id | Category | | id | Category |
|---|---|---|---|---|
| `1` | Advertising, Media & Collateral Materials | | `13` | Office Supplies |
| `2` | Bank Charges, Merchant Fees & Adjustments | | `16` | Printing, Postage, Mailing & Freight |
| `3` | Candidate Fundraiser Tickets | | `17` | Contract, Employee & Professional Services |
| `4` | Donations | | `18` | Surveys, Polls, Research & Voter Lists |
| `5` | Contribution to Political Party | | `21` | Taxes & Insurance |
| `6` | Durable Assets (Supplies/Equipment) | | `22` | Travel & Lodging |
| `8` | Filing Fee, Escheat, Fine | | `24` | Vehicle, Gas & Parking |
| **`9`** | **Food & Beverages** | | `25` | Membership & Subscription Fees |
| `12` | Campaign Headquarters | | `26` | Conference Fees |
| `27` | Events & Activities | | `28` | Employee/Volunteer Gifts |
| `29` | Refund — Return of Contribution | | `46` | Qualified Child Care |
| `47` | Vital Household Dependent Care | | | |


**Payee name is read-only on the expenditure form** — it cannot be reassigned. Delete and re-add.

⚠️ On the Sched B add form the **payee renders near the BOTTOM**, under "Name", after the category
list. A read-back guard that only inspects the first ~220 chars of `body.innerText` falsely fails —
search the whole string.

⚠️ **Sched B row links**: the row's first `<a>` can be the payee-NAME link (→ name grid, wrong
place). The edit link is the `<a>` whose innerText is the **DATE**.

⚠️ **Delete-confirm SweetAlert lives IN THE FRAME** (`cc_sb_*` document), unlike form-validation
swals which are in the TOP document. Check the frame first.

---

## 7. Schedule C — other receipts (`cc_sc_add` / `cc_sc_add_edit`)

`sc_date` · `sc_deposit_no` · `sc_amount` · `sc_desc` · `sc_ecat_id`.

`sc_ecat_id` — Category (read live 2026-07-29):

| id | Category |
|---|---|
| `2` | **Candidate's Own Funds** |
| `3` | Interest |
| `4` | Public Funds |
| `5` | Rebate |
| `6` | **Refund** |
| `7` | Sale of Durable Asset |
| `8` | Other |

⚠️ Do not confuse with Schedule B's Refund, which is `sb_ecat_id` = **29**. Same word, different
schedule, different id.

**Candidate's own money** goes here (or Schedule D), **not** Schedule A — the portal tip says so and
it is the treatment used across these committees. Category 2 for money given with no expectation of
repayment; Schedule D if the committee owes it back.

---

## 8. Schedule D — loans (`cc_sd_add_edit`)

`sd_date` (deposit date, or the date a personally-paid advance was made) · `sd_loan_source` select
(**`CAN`** = Candidate = unlimited; Financial Institution; Immediate Family; Other Entity) ·
`sd_deposit_no` (opt) · `sd_amount` (auto-formats to `"$ n"`) · `sd_purpose`.
`returnscreen`: `id-opt-returnscreen-2` (`N`) = Add-Transaction; `-1` (`L`) = Sched-D list.

The on-screen form has **no interest / term / collateral fields**.

- **Executed Loan Document required for every loan >$100** (exactly $100 is *not* "in excess") —
  link on the Add Loan screen; must reach CSC by 4:30pm on the report due date, HAR §3-160-39(a)(2).
- **Candidate pays a vendor directly from personal funds** = Sched D loan advance (dated when paid)
  + matching Sched B expenditure. Loans-in − expenditures-out = cash on hand.
- **Repayments** go on Sched D (Schedules → Receipt → Schedule D → Add Payment), **never** Sched B.
  Modal `cc_sd_pay_add_edit`: `sd_date`, `sd_check_no`, `sd_repay_amount`, `sd_forgiven` Y/N,
  `sd_resident` Y/N, `sd_loan_pay_off` Y/N; submit `sc_b_ins_t`.
  ⚠️ CFS **accepts repayments exceeding the loan balance** and then shows a parenthesised negative
  "($64.00)". Useful for spotting real overpayments; presumably trips validation at File time.
- **Forgiving a candidate loan** = Sched D forgiveness + offsetting Sched C Other Receipt
  (Candidate's Own Funds). Forgiving a **non-candidate** loan offsets as a Sched A contribution,
  subject to limits.
- Authoritative doc: CFS Manual pp.30–32 (loans), pp.26+ (Sched C).
  `https://ags.hawaii.gov/campaign/files/2025/12/CFS-Manual.pdf`

---

## 9. Validations

| Check | Menu |
|---|---|
| Employer / Occupation | `item_30` |
| Contribution Limit | `item_31` |
| Non-Resident | `item_33` |
| Immediate-family limit variants | `item_56` / `item_57` |

Flow: select the period (`rp_id`, index 1) → submit → **read the result from the INNER
`?nmgp_opcao=pesq` frame** (§1).

Submit is `a#sc_b_pesq_fields_right` — its onclick sets `document.F1.bprocessa.value='pesq'` then
`nm_submit_form()`. Calling those two directly is more reliable than `.click()`.

**"No Records Found" = clean.** Non-Resident instead prints the percentage against the 30% cap, and
its denominator is a useful independent check on Schedule A: it equals total **election-period**
contributions, so `prior periods + this period` should reconcile to the penny.

Never find the button by text-matching `/preview|validate/i` across all elements — it grabs hidden
inputs and unrelated labels.

---

## 10. Preview and the disclosure report

Preview/Print (item_28) → select period → radio **`#id-opt-rpt_name-8`** (`DIS`; the group is
SA/SB/SC/SD/SE/SF/SF2/DIS) → **Preview Report `a#sub_form_b`**, onclick `scBtnFn_sys_format_ok()` —
call it directly. The report opens as an **HTML page in a new tab** (`ccadmin_prev_dis`), not a PDF;
read it with `readpop`. **`readpop` writes the full text to `.tmp/csc/csc_pop_text.txt`; the status
echo shows only the first ~700 chars, so read the file**, or Line 6 is off the end of what you saw.

Lines that matter:

| Line | |
|---|---|
| 2 | Cash on hand, beginning of this period — must equal the prior report's Line 6 |
| **6** | **Cash on hand at closing — must equal the bank's period-end balance to the penny** |
| 10 | Surplus / deficit (cash − debts owed); negative is normal for a loan-funded committee |
| 11(a)(i)/(ii) | Contributions ≤$100 / >$100, **both including non-monetary** |
| 13 | Other receipts (Schedule C) |
| 15 | Total receipts |
| 16 | Expenditures made (Schedule B) |

**Section II "Type: Amended" on an unfiled report is a COSMETIC ARTIFACT.** Filing Confirmations
(`item_36`, frame `cc_xCC_02`) is the authoritative Original-vs-Amended and filing-date record; it
recorded one committee's 1C as Amended = **N** despite the preview saying "Amended". Do not re-investigate —
[[reference_csc_preview_type_amended_artifact]].

---

## 11. Amend mode

- **No banner anywhere.** The Sched A list and edit forms read `amend:false` even when it is on.
- **The reliable signal:** the Preview `rpt_period` dropdown lists **one** option (current report
  only) in normal mode, and **every filed report** once Amend Mode (item_8) is on.
- **Amend-mode edits route to filed reports BY TRANSACTION DATE** — there is no per-report
  selection. Redating an entry (6/15 → 7/15) **moves it between filed reports** and re-derives both
  Line 6s.

---

## 12. Organizational Report

**View/Print** = item_21, frame `cc_xorg_report`. **Amend** = item_22, frame `ccadmin_OrgEdit_All`
with a bank sub-form `ccadmin_Bank_Edit`.

Tabs (client-side; all fields are in the DOM at once, so you can set them without clicking tabs):
Candidate/Candidate Committee · Depository (Bank) · Chairperson · Treasurer · Deputy Chairperson ·
Deputy Treasurers · **$1,000 or Less Filer**

Fields: `or_cc_candidate_name` `or_cc_committee_name` `or_cc_address1/2` `or_cc_city` `or_cc_state`
`or_cc_zip` `or_cc_bus_phone` `or_cc_res_phone` `or_cc_url` `or_cc_office` `or_cc_county`
`or_cc_district` `or_cc_party` `or_cc_bank_name` `or_cc_bank_acct_no` · bank address
`orgbk_address1/2` `orgbk_city` `orgbk_state` `orgbk_zip` · chair `or_ch_*` · treasurer `or_tr_*`
(incl. `or_tr_email`) · deputies `or_dc_*`, `or_t1_*`…`or_t5_*`.

Buttons: `#sc_Amend_top` ("Amend") · `#sc_sc_btn_0_top` ("No Changes") · **`#sc_b_upd_b` ("File
Report")**.

⚠️ **The commit button is labelled "File Report"** and carries: *"By clicking the 'File Report'
button, the candidate and treasurer of the candidate committee affirms their acknowledgement and
certification … that the information on this electronically filed report is true, complete, and
accurate."* That is a certification — **the treasurer's step, not the agent's**
([[feedback_never_file_government_reports_yourself]]). Staged edits live only in the browser until
it is clicked, so navigating away discards them.

### ⚠️ The `$1,000 or Less Filer` boilerplate trap — cost real time on 2026-07-29

The **View/Print** Org Report prints this paragraph **unconditionally**, whether or not the election
was made:

> "The candidate committee has indicated that aggregate contributions and aggregate expenditures for
> the election period will total $1,000 or less. Therefore, pursuant to HRS section 11-339, …"

**It is not a statement that the election is on file.** The actual setting is the radio
`or_1000_limit` on the Amend form (item_22): `id-opt-or_1000_limit-1` = `Y` (Yes),
`id-opt-or_1000_limit-2` = `N` (No). **Read the radio, never the printed recital.**

Getting this backwards produces a false compliance alarm — HRS §11-322(b) would require an amendment
within 10 days and row 1B of the CSC fine schedule prices a failure to amend at $50.

---

## 13. Errors and recovery

- **Form-validation errors are SweetAlert2 in the TOP document**: `.swal2-container.swal2-shown`,
  confirm `.swal2-confirm`. NOT the hidden `id_message_display_*` elements — those exist but are
  0×0, so an `offsetParent` check fails (swal is `position:fixed`).
- **Delete-confirm swals live IN THE FRAME**, not the top document. Check both.
- `setVal` must dispatch `input`, `change` **and** `blur` or ScriptCase never registers the value.
- **Pre-transliterate non-ASCII.** The portal silently strips ʻokina/kahakō (Mākaha → Mkaha).

---

## 14. Bulk reads

**Export Data grids** (`ccadmin_ExportSA` etc., menu 39–45) are the fastest full-schedule read: set
`select[name=nmgp_quant_linhas]` = 50 + dispatch change, then loop `#forward_bot`, scraping `tr`
cells per page until content repeats (18 pages = 867 Sched A rows in ~2 min). The grid includes the
**Non-Monetary flag** column that the disclosure aggregates hide. The on-grid Print button does not
open a readable popup — scrape the grid.

The Schedule A/B list grids also carry a **Reported (Lock)** column: `Yes` = already filed in a prior
report. A cheap sanity check that you only added to the open period.

---

## 15. The `batch` runner — what it does and does not do

`csc_driver_*.mjs` `batch` enters **Schedule A contributions only**, from `BATCH_CSV`, skipping keys
already in `LEDGER`. Row key = `last~first~date~amount` lowercased.

**FIXED 2026-07-29.** For the record, because the old behaviour is still described in older notes:
the runner used to create a NEW name record per row unless the donor was already in its own
per-period `LEDGER` — so every donor carried over from an earlier report got a **second name
record**. Older notes call that "cosmetic". **It is not**: CFS's contribution-limit and
employer/occupation validations **aggregate by name record**, so a donor split across two records can
show as two smaller amounts and *pass* a check they should fail.

`trySearchExisting` was also looking for the search box in the INNER frame, where it does not exist,
so the lookup silently never ran at all.

Both are fixed in `csc_driver.mjs`: the runner
now **always asks the portal**, searches the OUTER frame, matches the name cell on exact equality,
requires the row to carry exactly one Schedule-A anchor (the wrapper-row guard), and logs a warning
if a donor already has multiple name records. The `seenDonors` ledger-guess is gone.

The old sentinel-row workaround (`<last>~<first>~01/01/1900~0.00|SENTINEL|…`) is **obsolete** — do
not re-apply it.

Other batch gotchas:

- A repeat donor whose (name, date, amount) is **identical** to an already-entered row collides on
  the dedup key and gets **skipped**. Drop that key from the ledger to force it.
- **Anything entered by hand does not reach the ledger**, so a later `batch` re-enters it. This
  produced a duplicate contribution row on 2026-07-29. Append a ledger line for every manual entry.
- Rows with a blank `Donor Addr1` are skipped entirely.

---

## 16. Filing Confirmations — the authoritative record

`item_36`, frame `cc_xCC_02` → "DISCLOSURE / LATE CONTRIBUTIONS REPORTS FILED": Report Name,
Reporting Period, Deadline, **Filing Date**, **Amended (Y/N)**.

The only reliable source for **whether** and **when** something was filed. It corrected a project
note claiming a 1C was filed 7/24 — it was filed **07/09/2026**.

---

## 17. Report naming

**The portal home screen states the current report's name, period and deadline verbatim.** Read it;
do not derive it.

> "The next report for Candidates running in 2026 is the **2nd Preliminary Primary Report** due
> **Jul 29, 2026**, covering the period **Jul 1 - Jul 24, 2026**."

The period select gives the same plus the report id: `488|2024-2026 2nd Preliminary Primary July 1 -
July 24, 2026`.

- **The period does NOT end on the due date.** Only the June-30 report is current through a round
  date; every other preliminary is current through the **fifth calendar day before its deadline**
  (HRS §11-334(a)(1), closing sentence).
- **Portal names are not the statutory subparagraph letters.** CFS says "1C Preliminary Primary" and
  "**2nd** Preliminary Primary". **There is no "1D" anywhere in CFS** — that label was an
  extrapolation from §11-334(a)(1)(D) and it is wrong. Name working-paper folders after the portal's
  string.
