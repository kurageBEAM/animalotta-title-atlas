'use strict';
/* 称号アトラス v3.1 — コナステ版のみを表示する。実機版の情報は詳細の「照合メモ」にだけ残す。
   v3.1: 獲得記録に日付を持たせ、タイムライン表示とセーブデータの書き出し／読み込みを追加。 */
const SITE_VERSION = '3.1';
const DB = JSON.parse(document.getElementById('sourceData').textContent);
const DIFF = DB.difficulty || {byId:{}, thresholds:[], tiers:[], assumptions:[], sources:{}, stars:{}, unit:'', version:'-'};
const byId = new Map(DB.arcade.map(x => [x.arcade_id, x]));
const bySlot = new Map(DB.slots.map(x => [x.slot, x]));
const RANKS = ['F','E','D','C','B','B+','A','A+','S','S+','SS'];
const RANK_IDX = Object.fromEntries(RANKS.map((r,i) => [r,i]));
const TIERS = DIFF.tiers || [];
const QUEST5 = DB.meta.normalQuestCandidates || [];
const TOTAL = DB.meta.konasteSlots || DB.slots.length;
const SNAPSHOT = DB.meta.snapshot || '2026-11-08';
const BASE_GOT = DB.slots.filter(s => s.obtained).length;
const rkc = r => 'rk-' + String(r).replace('+','p');
const cc = r => 'var(--c-' + String(r).replace('+','p') + ')';

const app = document.getElementById('app'), hero = document.getElementById('hero'), search = document.getElementById('search');
const overlay = document.getElementById('overlay'), modalContent = document.getElementById('modalContent');
let state = {view:'list', page:1, filter:'all', category:'all', query:'', sort:'slot', rank:'all', allPages:false};

const H = v => String(v ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const norm = s => String(s ?? '').normalize('NFKC').toLowerCase().replace(/[\s\-−‐ー_・．.]/g,'');
const num = n => String(n).padStart(3,'0');
const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}` };
const WD = ['日','月','火','水','木','金','土'];
function fmtDate(iso, withYear=true){ if (!iso) return '日付未設定'; const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso); if (!m) return iso; const d = new Date(+m[1], +m[2]-1, +m[3]); return `${withYear ? m[1] + '年' : ''}${+m[2]}月${+m[3]}日（${WD[d.getDay()]}）` }
function fmtDateTime(iso){ if (!iso) return 'なし'; const d = new Date(iso); if (isNaN(d)) return iso; return `${d.getFullYear()}年${d.getMonth()+1}月${d.getDate()}日 ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}` }

/* ── 保存（この端末のブラウザに自動保存。旧形式からは初回に移行） ── */
const PKEY = 'animalotta8-atlas-progress-v2', LSKEY = 'animalotta8-atlas-userchecks-v1', OVKEY = 'animalotta8-atlas-diffoverride-v1';
function blankProgress(){ return {v:2, checks:{}, overrides:{}, lastBackup:null, dirty:0, updated:null} }
function loadProgress(){
  let p = null;
  try { p = JSON.parse(localStorage.getItem(PKEY) || 'null') } catch(e) { p = null }
  if (p && p.v === 2 && p.checks && typeof p.checks === 'object') return Object.assign(blankProgress(), p, {overrides: p.overrides || {}});
  p = blankProgress();
  try { const old = JSON.parse(localStorage.getItem(LSKEY) || '{}'); for (const [k,v] of Object.entries(old)) { const base = !!bySlot.get(+k)?.obtained; if (!!v !== base) p.checks[k] = {got: !!v, date: null} } } catch(e) {}
  try { p.overrides = JSON.parse(localStorage.getItem(OVKEY) || '{}') } catch(e) {}
  return p;
}
let progress = loadProgress();
let overrides = progress.overrides;
let storageError = false;
function save(){ progress.updated = new Date().toISOString(); try { localStorage.setItem(PKEY, JSON.stringify(progress)); storageError = false } catch(e) { storageError = true } }
function touch(){ progress.dirty = (progress.dirty || 0) + 1; save() }
function qcheck(slot){ const c = progress.checks[slot]; return c === undefined ? !!bySlot.get(slot)?.obtained : !!c.got }
function userMark(slot){ return progress.checks[slot] }
function setGot(slot, got){ const base = !!bySlot.get(slot)?.obtained; if (got === base) delete progress.checks[slot]; else progress.checks[slot] = {got, date: got ? today() : null}; touch() }
function setDate(slot, date){ const c = progress.checks[slot]; if (c && c.got) { c.date = date || null; touch() } }
function setOverride(id, v){ if (v) overrides[id] = v; else delete overrides[id]; touch() }
function acquired(){ return Object.entries(progress.checks).filter(([,c]) => c && c.got).map(([k,c]) => ({slot:+k, sh:bySlot.get(+k), date:c.date})).filter(x => x.sh) }
if (!localStorage.getItem(PKEY)) save();

function arc(sh){ return sh && sh.arcade_id ? byId.get(sh.arcade_id) : null }
function titleOf(sh){ const a = arc(sh); if (sh.obtained && sh.screen) return sh.screen; return sh.predicted || a?.name || '名称未確定' }
function condOf(sh){ const a = arc(sh); return a ? (a.konaste_condition || a.condition) : '条件は未確定です' }
function catOf(sh){ return arc(sh)?.category || '未分類' }
function isPredicted(sh){ return !sh.obtained }

/* ── 難易度 ── */
function diff(id){ if (!id) return null; const d = DIFF.byId[String(id)]; if (!d) return null; const ov = d.kind === 'tiered' ? undefined : overrides[id]; const rank = ov || d.rank; return Object.assign({}, d, {auto:d.rank, rank, stars: rank ? (DIFF.stars[rank] || d.stars) : null, manual: !!ov}) }
const isTier = d => !!(d && d.kind === 'tiered' && d.tier);
const tierDesc = n => (TIERS.find(t => t.tier === n) || {}).desc || '';
function rankLabel(r){ const t = DIFF.thresholds.find(x => x.rank === r); return t ? t.label : '' }
function rankIdxByR(r){ if (r == null) return RANKS.length - 1; for (let i = 0; i < DIFF.thresholds.length; i++){ const m = DIFF.thresholds[i].max; if (m == null || r <= m) return i } return RANKS.length - 1 }
function rankBadge(d, cls=''){
  if (isTier(d)) return `<span class="rk rk-T${d.tier} ${cls}" title="努力型 Tier ${d.tier}：${H(tierDesc(d.tier))}">T${d.tier}</span>`;
  if (!d || !d.rank) return `<span class="rk rk-na ${cls}" title="難易度未付与">—</span>`;
  return `<span class="rk ${rkc(d.rank)} ${cls}" title="難易度 ${d.rank}：${H(rankLabel(d.rank))}${d.manual ? '（手動補正）' : ''}">${d.rank}${d.manual ? '<i>*</i>' : ''}</span>`;
}
function rankText(d){ return isTier(d) ? `T${d.tier}` : (d && d.rank ? d.rank : '—') }
function starsHtml(n){ if (!n) return ''; return `<span class="stars" aria-label="★${n}">${'★'.repeat(n)}<span class="dim">${'★'.repeat(5-n)}</span></span>` }
function subLabel(d){ if (isTier(d)) return `<span class="tierlbl">努力型 ${H(tierDesc(d.tier))}</span>`; return d && d.stars ? starsHtml(d.stars) : '' }
function fmtR(r){ if (r == null) return '—'; if (r >= 1e6) return '事実上不可'; return Math.round(r).toLocaleString('ja-JP') }
function fmtH(h, r){ if (h == null || r >= 1e6) return ''; if (h < 1) return `約${Math.max(1, Math.round(h*60))}分`; if (h < 10) return `約${h.toFixed(1)}時間`; return `約${Math.round(h).toLocaleString('ja-JP')}時間` }
function sortKey(id){ const d = diff(id); if (!d || !(d.rank || isTier(d))) return Infinity; const r = d.r == null ? 5e5 : Math.min(d.r, 9e5); const idx = d.rank ? RANK_IDX[d.rank] : rankIdxByR(d.r); return idx*1e6 + r }
function sortSlots(arr, mode){
  mode = mode || state.sort; if (mode === 'slot') return arr; const asc = mode === 'diffAsc';
  return [...arr].sort((a,b) => { const ka = sortKey(a.arcade_id), kb = sortKey(b.arcade_id); if (ka === kb) return a.slot - b.slot; if (ka === Infinity) return 1; if (kb === Infinity) return -1; return asc ? ka - kb : kb - ka });
}
function cellColor(d){ if (isTier(d)) return cc('T' + d.tier); if (d && d.rank) return cc(d.rank); return 'var(--c-na)' }

/* ── 絞り込み ── */
function inQuery(sh){ if (!state.query) return true; const a = arc(sh); return norm([sh.slot, sh.page, titleOf(sh), a?.condition, a?.konaste_condition, a?.category].join(' ')).includes(norm(state.query)) }
function rankOk(sh){ if (state.rank === 'all') return true; const d = diff(sh.arcade_id); if (state.rank === 'tier') return isTier(d); return !!d && d.rank === state.rank }
function filterOk(sh){
  if (state.filter === 'got') return qcheck(sh.slot);
  if (state.filter === 'missing') return !qcheck(sh.slot);
  if (state.filter === 'predicted') return !sh.obtained;
  if (state.filter === 'quest') return QUEST5.includes(sh.arcade_id);
  return true;
}
function visible(sh){ return inQuery(sh) && rankOk(sh) && filterOk(sh) && (state.category === 'all' || catOf(sh) === state.category) }
function listMode(){ return !!(state.query || state.allPages || state.category !== 'all' || state.filter !== 'all' || state.sort !== 'slot' || state.rank !== 'all') }

/* ── 共通部品 ── */
function sectionHeader(title, subtitle, right=''){ return `<div class="section-header"><div><h2>${title}</h2>${subtitle ? `<p>${subtitle}</p>` : ''}</div>${right}</div>` }
function categorySelect(){ const arr = [...new Set(DB.slots.map(catOf))]; return `<select class="sel" id="category" aria-label="カテゴリ"><option value="all">すべてのカテゴリ</option>${arr.map(c => `<option value="${H(c)}" ${state.category === c ? 'selected' : ''}>${H(c)}</option>`).join('')}</select>` }
function sortSelect(kind){
  const opts = kind === 'ranking' ? [['diffDesc','難しい順'],['diffAsc','易しい順'],['slot','枠番号順']] : [['slot','枠番号順'],['diffAsc','易しい順'],['diffDesc','難しい順']];
  return `<select class="sel" id="sortSel" aria-label="並び替え">${opts.map(([v,t]) => `<option value="${v}" ${state.sort === v ? 'selected' : ''}>${t}</option>`).join('')}</select>`;
}
function statusChips(){ const items = [['all','すべて'],['got','獲得済み'],['missing','未取得'],['predicted','名称が推定の枠'],['quest','クエスト称号 5枠']]; return `<div class="chips">${items.map(([v,t]) => `<button data-filter="${v}" class="chip ${state.filter === v ? 'active' : ''}">${t}</button>`).join('')}</div>` }
function rankChips(withTier=true){ return `<div class="chips">${RANKS.map(r => `<button data-rank="${r}" class="chip rkchip ${state.rank === r ? 'active' : ''}" title="${H(rankLabel(r))}">${r}</button>`).join('')}${withTier ? `<button data-rank="tier" class="chip ${state.rank === 'tier' ? 'active' : ''}" title="累計WIN・総WINの努力型">努力型</button>` : ''}</div>` }
function nav(){ return `<div class="pages" aria-label="ページ">${Array.from({length:17}, (_,i) => `<button class="page ${state.page === i+1 ? 'active' : ''}" data-page="${i+1}" aria-label="${i+1}ページ">${i+1}</button>`).join('')}</div>` }

function rankProgress(){
  const tot = {}, got = {}; RANKS.forEach(r => { tot[r] = 0; got[r] = 0 });
  DB.slots.forEach(s => { const d = diff(s.arcade_id); if (!d || !d.rank) return; tot[d.rank]++; if (qcheck(s.slot)) got[d.rank]++ });
  return `<div class="rankbar" aria-label="ランク別の獲得状況">${RANKS.map(r => { const t = tot[r], g = got[r], p = t ? Math.round(g/t*100) : 0; return `<button class="rankcell ${state.rank === r ? 'active' : ''}" data-rank="${r}" title="${H(rankLabel(r))}。クリックで絞り込み"><div class="rc-top"><span class="rk ${rkc(r)} sm">${r}</span><span class="rc-n">${g}<small>/${t}</small></span></div><div class="rc-bar"><i style="width:${p}%"></i></div><div class="rc-label">${starsHtml(DIFF.stars[r])}</div></button>` }).join('')}</div>`;
}
function tierProgress(){
  const tot = {}, got = {}; TIERS.forEach(t => { tot[t.tier] = 0; got[t.tier] = 0 });
  DB.slots.forEach(s => { const d = diff(s.arcade_id); if (!isTier(d)) return; tot[d.tier]++; if (qcheck(s.slot)) got[d.tier]++ });
  return `<div class="rankbar tierbar" aria-label="努力型の獲得状況">${TIERS.map(t => { const n = tot[t.tier], g = got[t.tier], p = n ? Math.round(g/n*100) : 0; return `<button class="rankcell ${state.rank === 'tier' ? 'active' : ''}" data-rank="tier" title="${H(t.desc)}。クリックで努力型だけを表示"><div class="rc-top"><span class="rk rk-T${t.tier} sm">T${t.tier}</span><span class="rc-n">${g}<small>/${n}</small></span></div><div class="rc-bar"><i style="width:${p}%"></i></div><div class="rc-label">${H(t.desc)}</div></button>` }).join('')}</div>`;
}

/* ── ヒーロー：330枠の切手シート ── */
function renderHero(){
  const got = DB.slots.filter(s => qcheck(s.slot)).length, left = TOTAL - got;
  const userDelta = got - BASE_GOT;
  const cells = DB.slots.map(s => { const d = diff(s.arcade_id), g = qcheck(s.slot), vis = visible(s); const name = titleOf(s); const lab = `${g ? '獲得済み' : '未取得'}：${name}（No.${num(s.slot)}${d && d.rank ? '、難易度 ' + d.rank : isTier(d) ? '、努力型 T' + d.tier : ''}）`; return `<button class="cell ${g ? 'got' : 'not'} ${!s.obtained && g ? 'user' : ''} ${vis ? '' : 'dim'}" style="--c:${cellColor(d)}" data-slot="${s.slot}" title="${H(lab)}" aria-label="${H(lab)}"></button>` }).join('');
  const dimmed = listMode() || state.view === 'timeline';
  const recent = acquired().filter(x => x.date).sort((a,b) => b.date < a.date ? -1 : b.date > a.date ? 1 : b.slot - a.slot)[0];
  const recentHtml = recent ? `<div class="recent">最近の獲得：${fmtDate(recent.date, false)}　${rankBadge(diff(recent.sh.arcade_id), 'sm')} ${H(titleOf(recent.sh))}　<button class="linkbtn" data-view-go="timeline">タイムラインを見る</button></div>` : `<div class="recent">称号を開いて「獲得済みにする」を押すと、その日の記録がタイムラインに残ります。</div>`;
  hero.innerHTML = `<div class="hero-top"><div class="hero-text"><h1>残り <span class="n">${left}</span> 称号</h1><p>コナステ版アニマロッタの称号${TOTAL}枠のうち、${got}枠を獲得しています${userDelta ? `（${fmtDate(SNAPSHOT, false)}の画面から${userDelta > 0 ? '+' : ''}${userDelta}件）` : ''}。右の図は称号一覧の17ページを1枚に並べたもので、色は難易度ランク、塗りつぶしが獲得済み、縁取りだけの枠が未取得です。マスを押すと条件と根拠が開きます。</p><div class="progress" role="progressbar" aria-valuenow="${got}" aria-valuemin="0" aria-valuemax="${TOTAL}"><i style="width:${Math.round(got/TOTAL*100)}%"></i></div><div class="progress-note">${Math.round(got/TOTAL*100)}% 獲得。難易度の前提は14面×100BET、1ラウンド約${(60/(DIFF.roundsPerHour||23)).toFixed(1)}分です。</div>${recentHtml}</div><div class="sheet"><div class="mosaic" role="group" aria-label="330枠の獲得状況">${cells}</div><div class="sheet-foot"><div><span class="key"><span class="sw" style="background:var(--c-C)"></span>獲得済み</span><span class="key"><span class="sw hollow" style="box-shadow:inset 0 0 0 1.5px var(--c-C)"></span>未取得</span><span class="key">色は難易度（Fの青灰からSSの金へ）、緑は努力型</span></div><div>${dimmed ? (state.view === 'timeline' ? '濃い枠は自分で獲得済みにした称号' : '薄い枠は現在の絞り込みに含まれない称号') : '左上が1ページ目、右下が17ページ目'}</div></div></div></div><div class="hero-bars"><p class="bars-note">ランク別の獲得数。押すと一覧をそのランクだけに絞り込みます。</p>${rankProgress()}${tierProgress()}</div>`;
  hero.querySelectorAll('[data-slot]').forEach(b => b.addEventListener('click', () => openSlot(+b.dataset.slot)));
  hero.querySelectorAll('[data-rank]').forEach(b => b.addEventListener('click', () => { const r = b.dataset.rank; state.rank = (state.rank === r) ? 'all' : r; if (state.view === 'timeline') state.view = 'list'; if (state.view === 'tiered' && r !== 'tier') state.view = 'list'; if (state.view === 'ranking' && r === 'tier') state.view = 'tiered'; render(); scrollToToolbar() }));
  hero.querySelector('[data-view-go]')?.addEventListener('click', () => { state.view = 'timeline'; render(); scrollToToolbar() });
}

/* ── 称号一覧 ── */
function tile(sh){
  const d = diff(sh.arcade_id), g = qcheck(sh.slot), est = isPredicted(sh), m = userMark(sh.slot);
  return `<button class="t-card ${g ? 'got' : 'not'} ${!sh.obtained && g ? 'user' : ''}" data-slot="${sh.slot}"><div class="head"><span class="no">No.${num(sh.slot)}　${sh.page}ページ</span>${rankBadge(d, 'sm')}</div><div class="name">${H(titleOf(sh))}${est ? '<span class="small-print">（推定）</span>' : ''}</div><div class="cond">${H(condOf(sh))}</div><div class="foot"><span>${subLabel(d) || H(catOf(sh))}</span><span>${g ? (m && m.got ? (m.date ? fmtDate(m.date, false) + ' 獲得' : '獲得済み（日付未設定）') : '獲得済み') : (m ? '未取得（自分で変更）' : '未取得')}</span></div></button>`;
}
function renderList(){
  const all = sortSlots(DB.slots.filter(visible)), lm = listMode();
  const shown = lm ? all : all.filter(s => s.page === state.page);
  let out = sectionHeader('称号一覧', '画面の17ページ・各20枠の並びを再現しています。未取得の枠の名称は推定です。', `<button class="btn ghost" id="allPages">${state.allPages ? 'ページ表示に戻す' : '17ページを一括表示'}</button>`);
  out += `<div class="tools">${statusChips()}${categorySelect()}${sortSelect('list')}</div><div class="tools">${rankChips()}</div>`;
  out += `<div class="board-head">${lm ? `<span class="count">${shown.length} 枠が条件に一致</span>` : nav()}<span class="count">${lm ? '絞り込み中は全ページを横断して表示' : `${state.page}ページ目`}</span></div>`;
  if (state.allPages && !state.query && state.filter === 'all' && state.category === 'all' && state.sort === 'slot' && state.rank === 'all') {
    for (let p = 1; p <= 17; p++) out += `<h3 style="margin:22px 0 10px;font-size:15px;color:var(--muted)">${p}ページ目</h3><div class="card-grid">${DB.slots.filter(s => s.page === p).map(tile).join('')}</div>`;
  } else out += shown.length ? `<div class="card-grid">${shown.map(tile).join('')}</div>` : `<div class="empty">条件に一致する称号がありません。検索語や絞り込みを変えてください。</div>`;
  out += `<p class="board-note">獲得済みの判定は${fmtDate(SNAPSHOT)}の画面画像が初期値です。各称号の詳細から「獲得済みにする」を押すと、その日の日付とともにこのブラウザに自動保存され、全体図・ランク別の数・タイムラインに反映されます。別の端末へ移すときは上部の「セーブデータ」から書き出してください。</p>`;
  return out;
}

/* ── 難易度ランキング ── */
function row(s, i){
  const d = diff(s.arcade_id), g = qcheck(s.slot);
  return `<button class="rankrow ${g ? 'got' : 'not'}" data-slot="${s.slot}"><div class="rr-rank"><div class="rr-idx">${i+1}位　No.${num(s.slot)}</div><div>${rankBadge(d)} ${subLabel(d)}</div></div><div><div class="rr-name">${H(titleOf(s))}${isPredicted(s) ? '<span class="small-print">（推定）</span>' : ''}</div><div class="rr-cond">${H(condOf(s))}　<span style="opacity:.75">${H(catOf(s))}</span></div></div><div class="rr-meta"><div><b>${fmtR(d?.r)}</b> ラウンド</div><div>${fmtH(d?.h, d?.r) || '&nbsp;'}</div><div class="${g ? 'got' : 'not'}">${g ? '獲得済み' : '未取得'}${d?.manual ? '（手動補正）' : ''}</div></div></button>`;
}
function renderRanking(){
  const mode = state.sort === 'slot' ? 'slot' : state.sort;
  const items = sortSlots(DB.slots.filter(s => visible(s) && !isTier(diff(s.arcade_id))), mode);
  let out = sectionHeader('難易度ランキング', '確率型の称号を「期待所要ラウンド数」で並べています。F〜SSと★は同じ指標の別表記で、行を開くと根拠・出典・手動補正を確認できます。', `<button class="btn ghost" id="openAssump">難易度の前提と出典</button>`);
  out += `<div class="tools">${statusChips()}${categorySelect()}${sortSelect('ranking')}</div><div class="tools">${rankChips(false)}</div>`;
  out += `<div class="board-head"><span class="count">確率型 ${items.length} 件</span><span class="count">累計WIN・総WINの67件は「努力型」タブへ</span></div>`;
  out += items.length ? `<div class="ranklist">${items.map(row).join('')}</div>` : `<div class="empty">条件に一致する称号がありません。</div>`;
  return out;
}

/* ── 努力型 ── */
function renderTiered(){
  const mode = state.sort === 'slot' ? 'slot' : state.sort;
  const items = sortSlots(DB.slots.filter(s => isTier(diff(s.arcade_id)) && inQuery(s) && filterOk(s) && (state.category === 'all' || catOf(s) === state.category)), mode);
  let out = sectionHeader('努力型（Tiered Achievement）', 'ゲーム別の累計WIN（1,000〜200万枚）と総WIN（100万〜2,000万枚）の67件。確率ではなくBET額×プレー量で決まるため、難易度ランクの代わりに枚数の段階 T1〜T5 を付けています。期待ラウンドは14面×100BET・ペイアウト85%の前提で、BETを上げれば比例して短くなります。');
  out += tierProgress();
  out += `<div class="tools">${statusChips()}${categorySelect()}${sortSelect('ranking')}</div>`;
  out += `<div class="board-head"><span class="count">努力型 ${items.length} 件</span><span class="count">ラウンド＝1回のボール抽選</span></div>`;
  out += items.length ? `<div class="ranklist">${items.map(row).join('')}</div>` : `<div class="empty">条件に一致する称号がありません。</div>`;
  return out;
}

/* ── タイムライン ── */
function renderTimeline(){
  const items = acquired().filter(x => inQuery(x.sh));
  const got = DB.slots.filter(s => qcheck(s.slot)).length;
  const groups = new Map();
  items.sort((a,b) => { const da = a.date || '9999', db2 = b.date || '9999'; return da < db2 ? 1 : da > db2 ? -1 : b.slot - a.slot });
  items.forEach(x => { const k = x.date || ''; if (!groups.has(k)) groups.set(k, []); groups.get(k).push(x) });
  let out = sectionHeader('タイムライン', '自分で「獲得済みにする」を押した称号を、日付ごとに新しい順で並べます。日付は記録した日が入り、あとから直せます。', `<button class="btn ghost" id="openSave">セーブデータ</button>`);
  out += `<div class="tl-summary"><div><b>${got}</b> / ${TOTAL} 獲得</div><div><b>${acquired().length}</b> 件を${fmtDate(SNAPSHOT, false)}以降に記録</div><div>残り <b>${TOTAL - got}</b></div>${progress.dirty ? `<div class="warn">書き出していない変更 ${progress.dirty} 件</div>` : ''}</div>`;
  if (!items.length) out += `<div class="empty">${state.query ? '検索に一致する記録がありません。' : 'まだ記録がありません。称号一覧で称号を開き「獲得済みにする」を押すと、その日の記録がここに並びます。'}</div>`;
  for (const [k, arr] of groups) {
    out += `<section class="tl-day ${k ? '' : 'tl-undated'}"><h3>${k ? fmtDate(k) : '日付未設定'}<small>　${arr.length}件</small></h3>${k ? '' : '<p class="small-print">以前の形式から引き継いだ記録です。獲得した日が分かれば入力してください。</p>'}<ul>${arr.map(x => { const d = diff(x.sh.arcade_id); return `<li class="tl-item"><button class="tl-open" data-slot="${x.slot}">${rankBadge(d, 'sm')}<span><b>${H(titleOf(x.sh))}</b><span class="small-print">　No.${num(x.slot)}　${H(catOf(x.sh))}${d && d.r != null && !isTier(d) ? `　期待 ${fmtR(d.r)}R` : ''}</span></span></button><label class="tl-date">獲得日 <input type="date" value="${H(x.date || '')}" max="${today()}" data-date-slot="${x.slot}" aria-label="${H(titleOf(x.sh))}の獲得日"></label></li>` }).join('')}</ul></section>`;
  }
  out += `<section class="tl-day tl-base"><h3>${fmtDate(SNAPSHOT)}</h3><p>開始時点。画面画像で獲得済みを確認した ${BASE_GOT} 件（この日以前の獲得日は記録していません）。</p></section>`;
  return out;
}

/* ── 描画 ── */
function render(){
  document.querySelectorAll('.tab').forEach(t => { const active = t.dataset.view === state.view; t.classList.toggle('active', active); t.setAttribute('aria-selected', String(active)) });
  if (state.view === 'tiered' && state.rank !== 'all' && state.rank !== 'tier') state.rank = 'all';
  app.innerHTML = state.view === 'list' ? renderList() : state.view === 'ranking' ? renderRanking() : state.view === 'tiered' ? renderTiered() : renderTimeline();
  renderHero();
  updateSaveBtn();
  bind();
}
function updateSaveBtn(){ const b = document.getElementById('saveBtn'); if (!b) return; b.innerHTML = `セーブデータ${progress.dirty ? `<span class="dot" title="ファイルに書き出していない変更">${progress.dirty > 99 ? '99+' : progress.dirty}</span>` : ''}`; b.title = progress.dirty ? `ファイルに書き出していない変更が ${progress.dirty} 件あります` : 'セーブデータの書き出し・読み込み' }
function scrollToToolbar(){ const t = document.getElementById('toolbar'); if (t) window.scrollTo({top: t.offsetTop, behavior: 'smooth'}) }
function bind(){
  app.querySelectorAll('[data-page]').forEach(b => b.addEventListener('click', () => { state.page = +b.dataset.page; render() }));
  app.querySelectorAll('[data-filter]').forEach(b => b.addEventListener('click', () => { state.filter = b.dataset.filter; render() }));
  app.querySelectorAll('[data-rank]').forEach(b => b.addEventListener('click', () => { const r = b.dataset.rank; state.rank = (state.rank === r) ? 'all' : r; if (r === 'tier' && state.view === 'ranking') state.view = 'tiered'; render() }));
  app.querySelectorAll('[data-slot]').forEach(b => b.addEventListener('click', () => openSlot(+b.dataset.slot)));
  app.querySelectorAll('[data-date-slot]').forEach(inp => inp.addEventListener('change', e => { setDate(+e.target.dataset.dateSlot, e.target.value); render() }));
  document.getElementById('category')?.addEventListener('change', e => { state.category = e.target.value; render() });
  document.getElementById('sortSel')?.addEventListener('change', e => { state.sort = e.target.value; render() });
  document.getElementById('allPages')?.addEventListener('click', () => { state.allPages = !state.allPages; render() });
  document.getElementById('openAssump')?.addEventListener('click', openAssumptions);
  document.getElementById('openSave')?.addEventListener('click', openSaveData);
}

/* ── 詳細 ── */
function modalHeader(name, kicker, tags){ return `<div class="small">${H(kicker)}</div><h2 id="dialogTitle">${H(name)}</h2><div class="tags">${tags.join('')}</div>` }
function mark(cls, text){ return `<span class="mark ${cls}">${H(text)}</span>` }
function modalOpen(content){
  modalContent.innerHTML = content; overlay.classList.add('show'); document.body.style.overflow = 'hidden'; document.getElementById('closeModal').focus();
  modalContent.querySelector('[data-mark]')?.addEventListener('click', e => { const slot = +e.currentTarget.dataset.mark; setGot(slot, !qcheck(slot)); render(); openSlot(slot) });
  modalContent.querySelector('[data-ov]')?.addEventListener('change', e => { setOverride(+e.target.dataset.ov, e.target.value); render(); openSlot(+e.target.dataset.ovSlot) });
  modalContent.querySelector('[data-date-slot]')?.addEventListener('change', e => { const slot = +e.target.dataset.dateSlot; setDate(slot, e.target.value); render(); openSlot(slot) });
}
function srcLinks(keys){ return (keys || []).map(k => { const s = DIFF.sources[k]; if (!s) return H(k); return s.url ? `<a href="${H(s.url)}" target="_blank" rel="noopener">${H(s.label)}</a>` : H(s.label) }).join('　') }
function diffSection(sh){
  const id = sh.arcade_id, d = diff(id); if (!d) return `<div class="detail"><h4>難易度</h4><p>この枠には難易度を付けていません。</p></div>`;
  let body;
  if (isTier(d)) body = `<div class="dgrid"><div>${rankBadge(d,'lg')}</div><div><span class="tierlbl">努力型（Tiered Achievement） Tier ${d.tier}</span><div class="small-print">${H(tierDesc(d.tier))}。確率ではなくBET額×プレー量で決まるため、難易度ランクと★の対象外です（14面×100BET前提、高BETなら短縮）。</div></div><div class="dnum"><b>${fmtR(d.r)}</b><span>期待所要ラウンド</span></div><div class="dnum"><b>${fmtH(d.h, d.r) || '—'}</b><span>目安時間（${DIFF.roundsPerHour || 23}ラウンド/時）</span></div></div>`;
  else if (d.rank) body = `<div class="dgrid"><div>${rankBadge(d,'lg')}</div><div>${starsHtml(d.stars)}<div class="small-print">${d.manual ? `手動補正中（自動推定は ${d.auto || '対象外'}）` : H(rankLabel(d.rank))}</div></div><div class="dnum"><b>${fmtR(d.r)}</b><span>期待所要ラウンド</span></div><div class="dnum"><b>${fmtH(d.h, d.r) || '—'}</b><span>目安時間（${DIFF.roundsPerHour || 23}ラウンド/時）</span></div></div>`;
  else body = `<p>コナステ版では対象外のため難易度を付けていません。</p>`;
  const basis = `<p class="small-print" style="margin-top:9px"><b>根拠（信頼度：${H(d.conf)}）</b>　${H(d.basis)}${d.note ? `　<span style="color:#8a5a00">［${H(d.note)}］</span>` : ''}</p>`;
  const src = d.src && d.src.length ? `<p class="small-print">出典：${srcLinks(d.src)}</p>` : '';
  const ov = isTier(d) ? `<p class="small-print" style="margin-top:9px">努力型は手動補正の対象外です。BET額が前提と異なる場合は、所要時間を比例で読み替えてください。</p>` : d.rank ? `<div class="ovrow"><label>手動でランクを補正 <select class="sel" data-ov="${id}" data-ov-slot="${sh.slot}"><option value="">自動（${d.auto || '対象外'}）</option>${RANKS.map(r => `<option value="${r}" ${overrides[id] === r ? 'selected' : ''}>${r}（★${DIFF.stars[r]}）</option>`).join('')}</select></label><span class="small-print">この端末に保存され、セーブデータとCSVにも含まれます。</span></div>` : '';
  return `<div class="detail"><h4>難易度（推定）</h4>${body}${basis}${src}${ov}</div>`;
}
function checkSection(sh){
  const n = sh.slot, g = qcheck(n), m = userMark(n);
  let status;
  if (m && m.got) status = `<p>自分で獲得済みにした称号です。<label class="tl-date" style="margin-left:6px">獲得日 <input type="date" value="${H(m.date || '')}" max="${today()}" data-date-slot="${n}"></label>${m.date ? '' : '<span class="small-print">　日付が未設定です</span>'}</p>`;
  else if (m && !m.got) status = `<p>画面画像では獲得済みでしたが、自分で未取得に戻しています。</p>`;
  else status = `<p class="small-print">${sh.obtained ? `${fmtDate(SNAPSHOT)}の画面画像で獲得済みを確認しています。` : '未取得です。獲得したら下のボタンで記録してください。今日の日付が入り、タイムラインに並びます。'}</p>`;
  return `<div class="detail"><h4>獲得の記録</h4>${status}<div class="actions"><button class="btn primary" data-mark="${n}">${g ? '未取得に戻す' : '獲得済みにする'}</button></div><p class="small-print" style="margin-top:8px">このブラウザに自動保存されます。別の端末で見るときは「セーブデータ」から書き出してください。</p></div>`;
}
function openSlot(n){
  const sh = bySlot.get(n); if (!sh) return; const a = arc(sh), d = diff(sh.arcade_id), g = qcheck(n), m = userMark(n);
  const tags = [mark(g ? 'got' : 'not', g ? (m && m.got ? (m.date ? `${fmtDate(m.date, false)} 獲得` : '獲得済み（自分で記録）') : '獲得済み（画像で確認）') : '未取得'), mark('', catOf(sh))];
  if (isPredicted(sh)) tags.push(mark('est', QUEST5.includes(sh.arcade_id) ? '名称はSPを除いた並び順から推定' : '名称は並び順から推定'));
  tags.push(rankBadge(d));
  let dd = modalHeader(titleOf(sh), `コナステ No.${num(n)}　${sh.page}ページ目 ${(sh.position-1)%4+1}列 ${Math.floor((sh.position-1)/4)+1}行`, tags);
  dd += `<div class="detail"><h4>獲得条件</h4><p>${H(condOf(sh))}</p>${a?.konaste_condition ? `<p class="small-print">実機版の条件「${H(a.condition)}」をコナステ向けに読み替えています。</p>` : ''}${a?.sp_note && QUEST5.includes(sh.arcade_id) ? `<p class="small-print">${H(a.sp_note)}</p>` : ''}</div>`;
  dd += diffSection(sh);
  dd += checkSection(sh);
  dd += `<details class="ref"><summary>照合メモ（参考情報）</summary><p>${H(sh.proof || '')}${a ? `　実機版の称号一覧では No.${num(a.arcade_id)}「${H(a.name)}」に対応し、条件の原文は「${H(a.condition)}」（${H(a.condition_status || '')}）。` : ''}</p></details>`;
  modalOpen(dd);
}
function openAssumptions(){
  const th = `<table class="ttable"><thead><tr><th>ランク</th><th>★</th><th>期待所要ラウンド</th><th>目安</th></tr></thead><tbody>${DIFF.thresholds.map(t => `<tr><td><span class="rk ${rkc(t.rank)}">${t.rank}</span></td><td>${starsHtml(t.stars)}</td><td>${t.max == null ? DIFF.thresholds[DIFF.thresholds.length-2].max.toLocaleString('ja-JP') + ' 超' : '〜 ' + t.max.toLocaleString('ja-JP')}</td><td>${H(t.label)}</td></tr>`).join('')}</tbody></table>`;
  const tt = `<table class="ttable"><thead><tr><th>Tier</th><th>条件</th><th>件数</th></tr></thead><tbody>${TIERS.map(t => `<tr><td><span class="rk rk-T${t.tier}">T${t.tier}</span></td><td>${H(t.desc)}</td><td>${DB.slots.filter(s => s.arcade_id && diff(s.arcade_id)?.tier === t.tier).length}</td></tr>`).join('')}</tbody></table>`;
  const as = `<ul>${DIFF.assumptions.map(a => `<li><b>${H(a.item)}</b>：${H(a.value)}　<span class="small-print">［${H(a.kind)}${a.src && a.src.length ? '：' + a.src.map(k => DIFF.sources[k]?.label || k).join('、') : ''}］</span></li>`).join('')}</ul>`;
  const srcs = `<ul>${Object.values(DIFF.sources).map(s => `<li>${s.url ? `<a href="${H(s.url)}" target="_blank" rel="noopener">${H(s.label)}</a>` : H(s.label)}</li>`).join('')}</ul>`;
  let dd = modalHeader('難易度の算出方法と前提', `難易度モデル v${DIFF.version}`, [mark('', '期待所要ラウンド数で序列化'), mark('est', '数値は推定を含む')]);
  dd += `<div class="detail"><h4>指標</h4><p>${H(DIFF.unit)}。確率系の称号はWC出現率×種別比×突破率×JP率などから、累積系の称号は必要数÷1ラウンドあたりの獲得量から期待所要ラウンド数を求め、11段階に分けています。閾値は、累計WIN・総WINの努力型67件を除いた確率型263件が各ランクに約24件ずつ並ぶよう分位点をもとに決めた固定値です。★は同じ指標の5段階表記（F/E=★1、D/C=★2、B/B+=★3、A/A+=★4、S/S+/SS=★5）。暦・連続日数が条件の称号はラウンド数が小さくても待ち時間が必要なため、一部はランクを個別に設定しています。</p></div>`;
  dd += `<div class="detail"><h4>ランク閾値（確率型）</h4>${th}</div><div class="detail"><h4>努力型のTier</h4>${tt}</div><div class="detail"><h4>前提値</h4>${as}</div><div class="detail"><h4>出典</h4>${srcs}<p class="small-print">各資料の計算値・統計・体感仮定を含みます。公式発表の確率ではありません。信頼度の表記：資料＝出典の数値を直接使用／計算＝前提値からの算出／推定＝主観的な仮定や類推／確定＝条件が自明。</p></div>`;
  dd += `<div class="detail"><h4>手動補正</h4><p class="small-print">この端末で設定した手動ランクは ${Object.keys(overrides).length} 件。</p><button class="btn" id="resetOv" style="margin-top:8px">手動補正をすべて解除</button></div>`;
  modalOpen(dd);
  document.getElementById('resetOv')?.addEventListener('click', () => { if (window.confirm('この端末の手動補正をすべて解除しますか？')) { for (const k of Object.keys(overrides)) delete overrides[k]; touch(); render(); openAssumptions() } });
}

/* ── セーブデータ ── */
function download(text, name, type){ const blob = new Blob([text], {type}), url = URL.createObjectURL(blob), link = document.createElement('a'); link.href = url; link.download = name; document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000) }
function exportSave(){
  const data = {app:'animalotta-atlas', format:2, site:SITE_VERSION, difficulty:DIFF.version, snapshot:SNAPSHOT, exported:new Date().toISOString(), progress:{v:2, checks:progress.checks, overrides:progress.overrides}};
  download(JSON.stringify(data, null, 1), `animalotta_atlas_save_${today()}.json`, 'application/json');
  progress.lastBackup = new Date().toISOString(); progress.dirty = 0; save(); render(); openSaveData();
}
function importSave(file){
  const reader = new FileReader();
  reader.onload = () => {
    let obj; try { obj = JSON.parse(String(reader.result)) } catch(e) { window.alert('読み込めませんでした。セーブデータ（JSON）ではないようです。'); return }
    const p = obj && obj.app === 'animalotta-atlas' && obj.progress && obj.progress.checks && typeof obj.progress.checks === 'object' ? obj.progress : null;
    if (!p) { window.alert('このサイトのセーブデータではありません。「セーブデータを書き出す」で作ったファイルを選んでください。'); return }
    const checks = {}; for (const [k,v] of Object.entries(p.checks)) { if (!bySlot.has(+k) || !v || typeof v !== 'object') continue; checks[k] = {got: !!v.got, date: typeof v.date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v.date) ? v.date : null} }
    const ovs = {}; for (const [k,v] of Object.entries(p.overrides || {})) if (RANKS.includes(v)) ovs[k] = v;
    const n = Object.values(checks).filter(c => c.got).length;
    if (!window.confirm(`書き出し日：${fmtDateTime(obj.exported)}\n自分で記録した獲得 ${n} 件、未取得への変更 ${Object.keys(checks).length - n} 件、手動補正 ${Object.keys(ovs).length} 件。\n\nこの端末の記録をこの内容で置き換えます。よろしいですか？`)) return;
    progress = Object.assign(blankProgress(), {checks, overrides: ovs, lastBackup: progress.lastBackup, dirty: 0}); overrides = progress.overrides; save(); render(); openSaveData();
  };
  reader.readAsText(file);
}
function openSaveData(){
  const n = acquired().length, undone = Object.values(progress.checks).filter(c => c && !c.got).length;
  let dd = modalHeader('セーブデータ', `サイト版 ${SITE_VERSION}`, [mark(storageError ? 'not' : 'got', storageError ? 'ブラウザへの保存に失敗' : 'ブラウザに自動保存中'), mark(progress.dirty ? 'est' : '', progress.dirty ? `書き出していない変更 ${progress.dirty} 件` : 'ファイルと同期済み')]);
  dd += `<div class="detail"><h4>保存の状況</h4><p>獲得チェック・獲得日・難易度の手動補正は、変更するたびにこのブラウザ（${H(location.host || 'ローカルファイル')}）へ自動保存されます。${storageError ? '<span class="warn">いまは保存に失敗しています。シークレットモードや容量不足の可能性があります。</span>' : ''}</p><ul class="small-print" style="margin:6px 0 0"><li>自分で記録した獲得：${n} 件（うち日付未設定 ${acquired().filter(x => !x.date).length} 件）／未取得に戻した称号：${undone} 件／手動補正：${Object.keys(overrides).length} 件</li><li>最終更新：${fmtDateTime(progress.updated)}</li><li>最後にファイルへ書き出した日時：${fmtDateTime(progress.lastBackup)}</li></ul></div>`;
  dd += `<div class="detail"><h4>別の端末へ移す・万一に備える</h4><div class="savegrid"><div class="savebox"><h4>書き出す</h4><p>記録をJSONファイルとして保存します。スマホとPCで引き継ぐときや、ブラウザのデータを消す前に。</p><button class="btn primary" id="doExport">セーブデータを書き出す</button></div><div class="savebox"><h4>読み込む</h4><p>書き出したファイルを選ぶと、この端末の記録をその内容で置き換えます（確認あり）。</p><button class="btn" id="doImport">ファイルを選んで読み込む</button></div></div><p class="small-print">ブラウザの履歴やサイトデータを消すと記録も消えます。iPhoneのSafariは7日間開かないとサイトデータを消すことがあるため、こまめな書き出しをおすすめします。サイトのURLが変わった場合も、書き出したファイルから戻せます。</p></div>`;
  dd += `<div class="detail"><h4>初期化</h4><p class="small-print">自分で記録した獲得・日付・未取得への変更をすべて消し、${fmtDate(SNAPSHOT)}の画面画像の状態に戻します。難易度の手動補正は残ります。</p><button class="btn" id="doReset">獲得の記録を初期化</button></div>`;
  modalOpen(dd);
  document.getElementById('doExport').addEventListener('click', exportSave);
  document.getElementById('doImport').addEventListener('click', () => document.getElementById('importFile').click());
  document.getElementById('doReset').addEventListener('click', () => { if (window.confirm(`自分で記録した獲得 ${n} 件と日付をすべて消して、画面画像の状態に戻します。この操作は元に戻せません（書き出したファイルがあれば読み込みで復元できます）。実行しますか？`)) { progress.checks = {}; touch(); render(); openSaveData() } });
}
function closeModal(){ overlay.classList.remove('show'); document.body.style.overflow = '' }

/* ── イベント ── */
document.getElementById('closeModal').addEventListener('click', closeModal);
overlay.addEventListener('click', e => { if (e.target === overlay) closeModal() });
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal() });
document.querySelectorAll('.tab').forEach(b => b.addEventListener('click', () => { state.view = b.dataset.view; state.filter = 'all'; state.category = 'all'; state.allPages = false; state.query = ''; search.value = ''; state.rank = state.view === 'tiered' ? 'tier' : 'all'; state.sort = state.view === 'list' || state.view === 'timeline' ? 'slot' : 'diffDesc'; render() }));
search.addEventListener('input', e => { state.query = e.target.value; render() });
document.getElementById('brandHome').addEventListener('click', e => { e.preventDefault(); state = {view:'list', page:1, filter:'all', category:'all', query:'', sort:'slot', rank:'all', allPages:false}; search.value = ''; render(); window.scrollTo({top:0, behavior:'smooth'}) });
document.getElementById('assumpBtn').addEventListener('click', openAssumptions);
document.getElementById('saveBtn').addEventListener('click', openSaveData);
document.getElementById('importFile').addEventListener('change', e => { const f = e.target.files && e.target.files[0]; if (f) importSave(f); e.target.value = '' });
window.addEventListener('storage', e => { if (e.key === PKEY) { progress = loadProgress(); overrides = progress.overrides; render() } });
function csvCell(s){ return '"' + String(s ?? '').replaceAll('"','""') + '"' }
document.getElementById('exportBtn').addEventListener('click', () => {
  const rows = [['コナステ枠','ページ','称号名','名称の確定','画像で獲得済','自分用獲得チェック','獲得日','獲得条件','難易度','自動推定','手動補正','★','期待ラウンド数','目安時間(h)','信頼度','算出根拠','照合No'],
    ...DB.slots.map(s => { const d = diff(s.arcade_id), m = userMark(s.slot); return [s.slot, s.page, titleOf(s), s.obtained ? '確定' : '推定', s.obtained ? 'YES' : 'NO', qcheck(s.slot) ? 'YES' : 'NO', m && m.got ? (m.date || '日付未設定') : (s.obtained && qcheck(s.slot) ? `${SNAPSHOT}以前（画像）` : ''), condOf(s), d?.rank || (isTier(d) ? 'T' + d.tier + '（努力型）' : ''), d?.auto || '', d?.manual ? 'YES' : '', d?.stars ? '★'.repeat(d.stars) : '', d && d.r != null ? (d.r >= 1e6 ? '事実上不可' : Math.round(d.r)) : '', d && d.h != null && d.r < 1e6 ? d.h : '', d?.conf || '', d?.basis || '', s.arcade_id || ''] })];
  download('﻿' + rows.map(r => r.map(csvCell).join(',')).join('\r\n'), 'animalotta_konaste_titles.csv', 'text/csv;charset=utf-8;');
});
render();
