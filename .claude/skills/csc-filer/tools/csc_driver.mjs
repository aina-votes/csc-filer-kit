// Hawaii CSC (Campaign Spending Commission) CFS portal driver + Schedule A batch runner.
// ONE headed Chromium session on a persistent profile at <kit>/.csc_profile, so the
// treasurer logs in by hand ONCE in the window that opens and the session is reused.
// Commands are read from <kit>/.tmp/csc/csc_ctrl.txt; output goes to csc_status.txt:
//   goto:<url> | frames | shot | js:<frameSubstr>::<code> | batch | batch:<n> |
//   readpop | shotpop | clearcookies | quit
// readpop/shotpop = read innerText / screenshot the newest popup tab (report previews open a new tab).
// batch reads data/batch_schedule_a.csv, skips rows already in data/entered_ledger.csv,
// enters each contribution, logs "ROW <i> OK/FAIL" to status. batch:<n> caps rows.
// THERE IS DELIBERATELY NO login COMMAND: this driver never sees a password.
import { chromium } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
// Kit root derived from this file's own location: tools -> csc-filer -> skills -> .claude -> kit.
// Override with CSC_ROOT.
const ROOT = process.env.CSC_ROOT
  || path.resolve(fileURLToPath(import.meta.url), '../../../../..');

const PROFILE = process.env.CSC_PROFILE || path.join(ROOT, '.csc_profile');
const OUT = process.env.CSC_OUT || path.join(ROOT, '.tmp/csc');
const CTRL = OUT + '/csc_ctrl.txt';
const STAT = OUT + '/csc_status.txt';
const BATCH_CSV = process.env.CSC_BATCH_CSV || path.join(ROOT, 'data/batch_schedule_a.csv');
const LEDGER = process.env.CSC_LEDGER || path.join(ROOT, 'data/entered_ledger.csv');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let n = 0;
function status(s) { fs.appendFileSync(STAT, s + '\n'); console.log(s); }

fs.mkdirSync(OUT, { recursive: true });
const ctx = await chromium.launchPersistentContext(PROFILE, {
  headless: process.env.CSC_HEADLESS === '1', viewport: { width: 1600, height: 1000 },
  args: ['--disable-blink-features=AutomationControlled'],
});
const page = ctx.pages()[0] || (await ctx.newPage());
// Track popup/new tabs: the disclosure preview + File Report open a NEW tab the main page can't see.
let lastPopup = null;
ctx.on('page', (p) => { lastPopup = p; });
fs.writeFileSync(CTRL, '');

// GUARD: popup/preview tabs are never closed by the command handlers, so every
// Preview permanently added a Chromium renderer. Close everything but the main page.
async function reapPages(keep) {
  try {
    const ps = ctx.pages();
    let closed = 0;
    for (let i = ps.length - 1; i >= 0; i--) {
      if (ps[i] !== keep && !ps[i].isClosed()) { await ps[i].close().catch(() => {}); closed++; }
    }
    if (closed) status('REAPED ' + closed + ' extra tab(s)');
  } catch (e) {}
}

function frameList() { return page.frames().map((f, i) => `${i}: ${f.url()}`).join('\n'); }
const findFrame = (sub) => page.frames().find((f) => f.url().includes(sub));

async function dumpShot(tag) {
  n++;
  const file = `${OUT}/csc_${n}_${tag}.png`;
  await page.screenshot({ path: file }).catch(() => {});
  status(`SHOT ${n} ${tag} -> ${file}`);
  return file;
}

// ---- tiny CSV parser (quotes, commas) ----
function parseCSV(text) {
  const rows = []; let f = '', row = [], q = false;
  if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) { if (c === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else q = false; } else f += c; }
    else if (c === '"') q = true;
    else if (c === ',') { row.push(f); f = ''; }
    else if (c === '\n') { row.push(f); rows.push(row); f = ''; row = []; }
    else if (c !== '\r') f += c;
  }
  if (f.length || row.length) { row.push(f); rows.push(row); }
  return rows.filter((r) => r.some((v) => v.trim() !== ''));
}
function loadRows() {
  const rows = parseCSV(fs.readFileSync(BATCH_CSV, 'utf8'));
  const h = rows[0];
  return rows.slice(1).map((r) => Object.fromEntries(h.map((k, i) => [k, (r[i] ?? '').trim()])));
}
function ledgerKeys() {
  if (!fs.existsSync(LEDGER)) return new Set();
  return new Set(fs.readFileSync(LEDGER, 'utf8').trim().split('\n').slice(1).map((l) => l.split('|')[0]));
}
const rowKey = (r) => `${r['Donor Last Name']}~${r['Donor First Name']}~${r['Date']}~${r['Amount']}`.toLowerCase();

// ---- portal helpers ----
async function swalText() {
  return page.mainFrame().evaluate(() => {
    const sw = document.querySelector('.swal2-container.swal2-shown');
    return sw ? sw.innerText.replace(/\s+/g, ' ').trim().slice(0, 300) : null;
  }).catch(() => null);
}
async function swalDismiss() {
  await page.mainFrame().evaluate(() => document.querySelector('.swal2-confirm')?.click()).catch(() => {});
  await sleep(600);
}
async function waitFor(pred, ms, label) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    if (await pred()) return true;
    await sleep(350);
  }
  status('TIMEOUT waiting: ' + label);
  return false;
}
async function gotoAddTransaction() {
  const menu = page.frames().find((f) => f.url().includes('ccadmin_menu'));
  await menu.evaluate(() => {
    const el = [...document.querySelectorAll('a,td,span,div')].find((e) => e.textContent.trim() === 'Add Transaction' && e.children.length <= 1);
    el?.click();
  });
  return waitFor(async () => {
    const g = findFrame('cc_name_grid/index.php');
    if (!g) return false;
    return g.evaluate(() => !!document.getElementById('sc_b_new_top')).catch(() => false);
  }, 20000, 'name grid');
}

async function trySearchExisting(row) {
  // Ask the PORTAL whether this donor already has a name record. The search box lives in the
  // OUTER cc_name_grid/ frame; the result rows live in the INNER index.php?nmgp_opcao=pesq
  // frame. Targeting the wrong one returns nothing, silently.
  const outer = page.frames().find((f) => /cc_name_grid\/$/.test(f.url()) || (f.url().includes('cc_name_grid') && !f.url().includes('index.php')));
  const g = outer || findFrame('cc_name_grid');
  if (!g) return false;
  const last = row['Donor Last Name'];
  const ok = await g.evaluate((q) => {
    const inp = document.querySelector('[name="cn_fullname"]');
    if (!inp) return 'noinput';
    inp.value = q;
    ['input', 'change'].forEach((t) => inp.dispatchEvent(new Event(t, { bubbles: true })));
    const btn = [...document.querySelectorAll('a,button,input')]
      .find((e) => ((e.value || e.textContent) || '').trim() === 'Search');
    if (!btn) return 'nobtn';
    btn.click();
    return 'searched';
  }, last).catch((e) => 'err:' + e.message);
  if (ok !== 'searched') { status(`  searchExisting: ${ok}`); return false; }
  await sleep(2400);

  const g2 = findFrame('cc_name_grid/index.php');
  if (!g2) return false;
  const want = `${row['Donor Last Name']}, ${row['Donor First Name']}`
    .toLowerCase().replace(/\s+/g, ' ').trim();
  const res = await g2.evaluate((wanted) => {
    const norm = (s) => (s || '').toLowerCase().replace(/\s+/g, ' ').trim();
    const hits = [];
    for (const tr of document.querySelectorAll('tr')) {
      const anchors = [...tr.querySelectorAll('a')]
        .filter((a) => (a.getAttribute('href') || '').includes('cc_sa_add'));
      // a DATA row has exactly one Schedule-A anchor; a wrapper <tr> that contains several
      // data rows has more, and clicking its first anchor attaches to the WRONG name
      if (anchors.length !== 1) continue;
      const cell = [...tr.querySelectorAll('td')].map((td) => norm(td.innerText)).find((t) => t.includes(','));
      if (cell === wanted) hits.push({ tr, a: anchors[0] });
    }
    if (!hits.length) return 'none';
    const pick = hits[hits.length - 1];
    pick.a.click();
    return hits.length > 1 ? 'multi:' + hits.length : 'one';
  }, want).catch(() => 'none');

  if (res === 'none') return false;
  if (String(res).startsWith('multi:')) {
    status(`  ⚠ ${want} already has ${res.split(':')[1]} name records — used the last`);
  }
  return true;
}

async function fillNameForm(row) {
  const f = findFrame('cc_name_form');
  await f.evaluate((r) => {
    const set = (n, v) => {
      const e = document.querySelector(`[name=${n}]`);
      if (!e) return;
      e.value = v;
      e.dispatchEvent(new Event('input', { bubbles: true }));
      e.dispatchEvent(new Event('change', { bubbles: true }));
      e.dispatchEvent(new Event('blur', { bubbles: true }));
    };
    set('cn_name_type', 'IND');
    set('cn_fname', r.first); set('cn_lname', r.last);
    set('cn_address1', r.a1); if (r.a2) set('cn_address2', r.a2);
    set('cn_city', r.city); set('cn_state', r.state); set('cn_zip', r.zip);
    if (r.occ) set('cn_occupation', r.occ);
    if (r.emp) set('cn_employer', r.emp);
  }, {
    first: row['Donor First Name'], last: row['Donor Last Name'],
    a1: row['Donor Addr1'], a2: row['Donor Addr2'], city: row['Donor City'],
    state: row['Donor State'], zip: row['Donor ZIP'],
    occ: row['Donor Occupation'], emp: row['Donor Employer'],
  });
  // The add_transaction radio group renders a beat AFTER the rest of the form. Clicking it
  // in the same evaluate as the field fill throws "Cannot read properties of null" and kills
  // the row (3 of 50 on 2026-07-29). Wait for it. NOTE: a screenshot taken after the failure
  // shows a fully-rendered form, because it renders in the gap — do not trust that shot.
  if (!(await waitFor(async () => {
    const ff = findFrame('cc_name_form');
    return ff && await ff.evaluate(() => !!document.getElementById('id-opt-add_transaction-2')).catch(() => false);
  }, 15000, 'add_transaction radio'))) throw new Error('add_transaction radio never rendered');
  const f2 = findFrame('cc_name_form');
  await f2.evaluate(() => {
    const r = document.getElementById('id-opt-add_transaction-2'); // SA = Contribution
    r.checked = true;
    r.dispatchEvent(new Event('click', { bubbles: true }));
    r.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await sleep(300);
  await f2.evaluate(() => document.getElementById('sc_b_ins_t').click());
}

async function fillSAForm(row) {
  const f = findFrame('cc_sa_add');
  await f.evaluate((r) => {
    const set = (n, v) => {
      const e = document.querySelector(`[name=${n}]`);
      if (!e) return;
      e.focus(); e.value = v;
      e.dispatchEvent(new Event('input', { bubbles: true }));
      e.dispatchEvent(new Event('change', { bubbles: true }));
      e.dispatchEvent(new Event('blur', { bubbles: true }));
    };
    document.getElementById('id-opt-returnscreen-2').click(); // back to Add Transaction screen
    set('sa_date', r.date);
    if (r.dep) set('sa_deposit_no', r.dep);
    set('sa_amount', r.amount);
    if (r.nonres === 'Y') document.getElementById('id-opt-sa_resident-1').click();
    else document.getElementById('id-opt-sa_resident-2').click();
    document.getElementById('id-opt-sa_monetary-2').click(); // monetary contribution
    document.getElementById('id-opt-isminor-2')?.click();
  }, {
    date: row['Date'], dep: row['Deposit No.'], amount: row['Amount'],
    nonres: row['Non-Resident'],
  });
  await sleep(300);
  // verify staged values before submitting
  const staged = await f.evaluate(() => ({
    date: document.querySelector('[name=sa_date]').value,
    amount: document.querySelector('[name=sa_amount]').value.replace(/[^0-9.]/g, ''),
    ret: document.querySelector('[name=returnscreen]:checked')?.value,
  }));
  if (staged.date !== row['Date'] || parseFloat(staged.amount) !== parseFloat(row['Amount']) || staged.ret !== 'N') {
    return 'STAGE_MISMATCH ' + JSON.stringify(staged);
  }
  await f.evaluate(() => document.getElementById('sc_b_ins_t').click());
  return null;
}

async function recoverToGrid() {
  await swalDismiss();
  const sa = findFrame('cc_sa_add');
  if (sa) await sa.evaluate(() => document.getElementById('sc_Cancel_top')?.click()).catch(() => {});
  await sleep(1200);
  await gotoAddTransaction();
}

async function runBatch(maxRows) {
  const all = loadRows();
  const done = ledgerKeys();
  if (!fs.existsSync(LEDGER)) fs.writeFileSync(LEDGER, 'key|name|date|amount|ts\n');
  let processed = 0, ok = 0, fail = 0;

  for (let i = 0; i < all.length; i++) {
    const row = all[i];
    const key = rowKey(row);
    if (done.has(key)) continue;
    if (!row['Donor Addr1']) { continue; } // portal requires address — skip until enriched
    if (maxRows && processed >= maxRows) break;
    processed++;
    const label = `${row['Donor Last Name']}, ${row['Donor First Name']} $${row['Amount']} ${row['Date']}`;
    try {
      if (!(await gotoAddTransaction())) throw new Error('no grid');

      // ALWAYS ask the portal, not the ledger. The ledger only knows this period, so a
      // donor carried over from an earlier report would otherwise get a duplicate name
      // record — and CFS validations aggregate by name record.
      let onSA = await trySearchExisting(row);
      if (onSA) status(`row ${i}: existing donor path`);
      if (!onSA) {
        const g = findFrame('cc_name_grid/index.php');
        await g.evaluate(() => document.getElementById('sc_b_new_top').click());
        if (!(await waitFor(async () => {
          const f = findFrame('cc_name_form');
          return f && await f.evaluate(() => !!document.querySelector('[name=cn_fname]')).catch(() => false);
        }, 20000, 'name form'))) throw new Error('name form never appeared');
        await fillNameForm(row);
      }

      // wait for SA form (or portal error)
      if (!(await waitFor(async () => {
        if (await swalText()) return true;
        const f = findFrame('cc_sa_add');
        return f && await f.evaluate(() => !!document.querySelector('[name=sa_amount]')).catch(() => false);
      }, 25000, 'SA form'))) throw new Error('SA form never appeared');
      let sw = await swalText();
      if (sw) throw new Error('portal error after name form: ' + sw);

      const stageErr = await fillSAForm(row);
      if (stageErr) throw new Error(stageErr);

      // wait for return to grid (or portal error)
      if (!(await waitFor(async () => {
        if (await swalText()) return true;
        return !findFrame('cc_sa_add') && !!findFrame('cc_name_grid');
      }, 25000, 'grid return'))) throw new Error('no grid return after SA submit');
      sw = await swalText();
      if (sw) throw new Error('portal error on SA submit: ' + sw);

      fs.appendFileSync(LEDGER, `${key}|${label}|${new Date().toISOString()}\n`);
      done.add(key);
      ok++;
      status(`ROW ${i} OK  ${label}  [${ok} ok / ${fail} fail]`);
      await sleep(400);
    } catch (e) {
      fail++;
      const shotFile = await dumpShot(`rowfail_${i}`);
      status(`ROW ${i} FAIL ${label} :: ${e.message.slice(0, 200)} (see ${shotFile})`);
      await recoverToGrid();
    }
  }
  status(`BATCH DONE: ${ok} ok, ${fail} fail, ${processed} processed.`);
}

await page.goto('https://csc.hawaii.gov/CFS', { waitUntil: 'domcontentloaded' });
await sleep(3000);
await dumpShot('start');
status('READY. Commands: batch | batch:<n> | js | shot | frames | readpop | shotpop | clearcookies | quit');

const start = Date.now();
while (Date.now() - start < (Number(process.env.CSC_MINUTES) || 180) * 60 * 1000) {
  let cmd = '';
  try { cmd = fs.readFileSync(CTRL, 'utf8').trim(); } catch {}
  if (!cmd) { await sleep(1000); continue; }
  fs.writeFileSync(CTRL, '');
  status('CMD ' + cmd.slice(0, 200));
  try {
    if (cmd === 'quit') break;
    else if (cmd === 'frames') status('FRAMES:\n' + frameList());
    else if (cmd === 'shot') await dumpShot('shot');
    else if (cmd === 'readpop' || cmd === 'shotpop') {
      // Read/screenshot the newest popup tab (disclosure preview, File Report, Filing Confirmations).
      const pops = ctx.pages().filter((p) => p !== page);
      const p = pops[pops.length - 1] || lastPopup;
      if (!p) { status('NO_POPUP (pages=' + ctx.pages().length + ')'); }
      else {
        await p.waitForLoadState('load').catch(() => {});
        await sleep(1500);
        if (cmd === 'readpop') {
          const txt = await p.evaluate(() => (document.body ? document.body.innerText.replace(/\s+/g, ' ') : 'NOBODY')).catch((e) => 'EVAL_ERR:' + e.message);
          fs.writeFileSync(`${OUT}/csc_pop_text.txt`, txt);
          status('POPTEXT url=' + p.url() + ' len=' + txt.length + '\n' + txt.slice(0, 700));
        } else {
          n++;
          const file = `${OUT}/csc_pop_${n}.png`;
          await p.screenshot({ path: file }).catch(() => {});
          status('POPSHOT ' + n + ' url=' + p.url() + ' -> ' + file);
        }
      }
    }
    else if (cmd === 'batch') await runBatch(0);
    else if (cmd.startsWith('batch:')) await runBatch(parseInt(cmd.slice(6), 10));
    else if (cmd.startsWith('goto:')) { await page.goto(cmd.slice(5), { waitUntil: 'domcontentloaded' }); await sleep(2500); await dumpShot('goto'); }
    else if (cmd.startsWith('js:')) {
      const rest = cmd.slice(3);
      const sep = rest.indexOf('::');
      const sub = rest.slice(0, sep), code = rest.slice(sep + 2);
      const frame = sub === 'top' ? page.mainFrame() : page.frames().find((f) => f.url().includes(sub));
      if (!frame) { status('NO_FRAME ' + sub + '\n' + frameList()); continue; }
      const result = await frame.evaluate(code);
      const out = JSON.stringify(result, null, 1) ?? 'undefined';
      fs.writeFileSync(`${OUT}/csc_js_out.json`, out);
      status('JS_OK (' + out.length + ' bytes)' + (out.length < 900 ? '\n' + out : ' -> csc_js_out.json'));
    } else status('UNKNOWN_CMD');
  } catch (e) { status('CMD_ERR ' + e.message.slice(0, 400)); }
}
status('DRIVER_EXIT');
await ctx.close();
