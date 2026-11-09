# -*- coding: utf-8 -*-
"""
2026-11-09 利用者指摘の反映:
  コナステの未取得5枠（No.297〜301）は、SP限定6称号（実機No.397〜402）を除いた実機の掲載順で
  クエスト中堅／上級者／ワールドトラベラー／エンドコンテンツ／伝説の勇者 に対応する。
  エンドコンテンツ＝通常クエスト全128種を受注、伝説の勇者＝通常クエスト全128種をクリア と読み替える。
index.html の sourceData、animalotta_comparison.json、animalotta_konaste330.csv、animalotta_arcade438.csv を更新する。
再実行しても結果は同じ（冪等）。
"""
import json, re, csv, os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'index.html')

MAP = {297: 395, 298: 396, 299: 403, 300: 404, 301: 405}
SP_ONLY = [397, 398, 399, 400, 401, 402]
KONASTE_COND = {
    404: '通常クエスト全128種を受注（コナステ版にSPクエストがないため、実機条件からSP部分を除いた読み替え）',
    405: '通常クエスト全128種をクリア＝達成率100%（実機条件からSP部分を除いた読み替え）',
}
PROOF = 'SP限定の6称号（実機No.397〜402）を除いた実機の掲載順から推定（2026-11-09 利用者指摘）。画像上は未取得の「？」'
SP_NOTE_MAPPED = {
    395: '通常クエストのみの条件。SP限定6件を除いた実機の掲載順から、コナステ枠No.297に対応すると推定（2026-11-09 利用者指摘）',
    396: '通常クエストのみの条件。SP限定6件を除いた実機の掲載順から、コナステ枠No.298に対応すると推定（2026-11-09 利用者指摘）',
    403: '通常クエストのみの条件。SP限定6件を除いた実機の掲載順から、コナステ枠No.299に対応すると推定（2026-11-09 利用者指摘）',
    404: '実機ブログでは通常・SP全クエストの受注と推測。コナステ版ではSPクエストがないため「通常クエスト全128種を受注」と読み替え、枠No.300に対応すると推定',
    405: '実機では通常・SPの全クエストをクリア。コナステ版では「通常クエスト全128種をクリア（達成率100%）」と読み替え、枠No.301に対応すると推定',
}
SP_NOTE_EXCLUDED = 'SPクエストが条件。コナステ版にSPクエストは存在せず（利用者報告）、未取得5枠はSPを除いた順序で通常クエスト称号に対応するため、枠自体がないと判断（2026-11-09）'

html = open(INDEX, encoding='utf-8').read()
m = re.search(r'(<script id="sourceData" type="application/json">)(.*?)(</script>)', html, re.S)
DB = json.loads(m.group(2))
arcade = {a['arcade_id']: a for a in DB['arcade']}
slots = {s['slot']: s for s in DB['slots']}

for slot, aid in MAP.items():
    s = slots[slot]; a = arcade[aid]
    s['arcade_id'] = aid; s['predicted'] = a['name']; s['proof'] = PROOF; s['obtained'] = False; s['screen'] = None
    a['availability'] = '未取得（枠推定）'; a['konaste_slot'] = slot; a['sp_note'] = SP_NOTE_MAPPED[aid]
    if aid in KONASTE_COND: a['konaste_condition'] = KONASTE_COND[aid]
for aid in SP_ONLY:
    a = arcade[aid]
    a['availability'] = 'コナステ枠なし（SP限定）'; a['konaste_slot'] = None; a['sp_note'] = SP_NOTE_EXCLUDED
    a.pop('konaste_condition', None)
DB['excluded'] = sorted(set(DB['excluded']) | set(SP_ONLY))
DB['questCandidates'] = list(range(395, 406))
meta = DB['meta']
meta.update({
    'identifiedViaOrder': 121, 'questUnknownSlots': 0, 'provenExcluded': len(DB['excluded']), 'questUnresolvedExcluded': 0,
    'edition': 'SPクエスト除外の順序でクエスト5枠を同定した版 v2.1',
    'spDefinitelyGated': SP_ONLY, 'spPossiblyGated': [], 'normalQuestCandidates': [395, 396, 403, 404, 405],
    'questMappingDate': '2026-11-09',
    'questMappingConclusion': '実機No.395〜405の11件からSP限定の6件（397〜402）を除くと5件が残り、コナステの未取得5枠（No.297〜301）に掲載順で対応する。エンドコンテンツと伝説の勇者はSP部分を除いた条件（全128種の受注／クリア）に読み替え。獲得時の画面で名称の確認が必要。',
})

# index.html
html = html[:m.start(2)] + json.dumps(DB, ensure_ascii=False, separators=(',', ':')) + html[m.end(2):]
open(INDEX, 'w', encoding='utf-8').write(html)
# comparison.json（difficulty を除く）
comp = {k: DB[k] for k in ('arcade', 'slots', 'excluded', 'questCandidates', 'meta')}
json.dump(comp, open(os.path.join(ROOT, 'animalotta_comparison.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

def rewrite_csv(path, fn):
    raw = open(path, 'rb').read(); crlf = b'\r\n' in raw
    rows = list(csv.reader(raw.decode('utf-8-sig').splitlines()))
    rows = fn(rows)
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, lineterminator='\r\n' if crlf else '\n'); w.writerows(rows)

def fix_konaste(rows):
    for r in rows[1:]:
        slot = int(r[0])
        if slot in MAP:
            a = arcade[MAP[slot]]
            r[3] = ''; r[4] = 'いいえ'; r[5] = str(MAP[slot]); r[6] = a['name']
            r[7] = a['condition'] + (('／コナステ版：' + a['konaste_condition']) if a.get('konaste_condition') else '')
            r[8] = PROOF
    return rows
def fix_arcade(rows):
    for r in rows[1:]:
        aid = int(r[0])
        if aid in MAP.values() or aid in SP_ONLY:
            a = arcade[aid]
            r[5] = a['availability']; r[6] = str(a['konaste_slot'] or ''); r[7] = a['sp_note']
            if a.get('konaste_condition'): r[2] = a['condition'] + '／コナステ版：' + a['konaste_condition']
    return rows
rewrite_csv(os.path.join(ROOT, 'animalotta_konaste330.csv'), fix_konaste)
rewrite_csv(os.path.join(ROOT, 'animalotta_arcade438.csv'), fix_arcade)
print('quest mapping applied: excluded', len(DB['excluded']), 'unknown slots', sum(1 for s in DB['slots'] if s['arcade_id'] is None))
