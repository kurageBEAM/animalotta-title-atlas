# -*- coding: utf-8 -*-
"""
コナステ画面の獲得状況（tools/snapshots.json）を照合データに反映する。
  - index.html の sourceData（slots の obtained / screen / proof / confirmed、arcade の availability、meta.snapshot ほか）
  - animalotta_comparison.json
  - animalotta_konaste330.csv（画像表示名・画像で獲得済み・判定根拠・画像確認日）
  - animalotta_arcade438.csv（コナステ対応状態）
日付順にすべてのスナップショットを適用する。再実行しても結果は同じ（冪等）。
実行後は tools/build_difficulty.py → tools/assemble_ui.py → tools/export_assumptions.py を続けて実行する。
"""
import json, re, csv, os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'index.html')
SNAPS = os.path.join(ROOT, 'tools', 'snapshots.json')

snaps = sorted(json.load(open(SNAPS, encoding='utf-8'))['snapshots'], key=lambda x: x['date'])
if not snaps or not snaps[0].get('baseline'):
    sys.exit('snapshots.json の先頭は baseline: true の初回スナップショットにしてください')
FIRST = snaps[0]['date']

html = open(INDEX, encoding='utf-8').read()
m = re.search(r'(<script id="sourceData" type="application/json">)(.*?)(</script>)', html, re.S)
DB = json.loads(m.group(2))
arcade = {a['arcade_id']: a for a in DB['arcade']}
slots = {s['slot']: s for s in DB['slots']}

# 初回スナップショット：confirmed の無い獲得済み枠は初回の日付、未取得枠は confirmed を持たない
later = set()
for sn in snaps[1:]:
    later |= {int(k) for k in sn.get('new', {})}
for s in DB['slots']:
    if s['obtained'] and s['slot'] not in later and not s.get('confirmed'):
        s['confirmed'] = FIRST
    if not s['obtained']:
        s.pop('confirmed', None)

history = [{'date': FIRST, 'added': None, 'obtained': None, 'note': snaps[0].get('note', '')}]
for sn in snaps[1:]:
    date = sn['date']
    prev = [h['date'] for h in history][-1]
    for k, name in sn.get('new', {}).items():
        s = slots[int(k)]
        s['obtained'] = True; s['screen'] = name; s['confirmed'] = date
        s['proof'] = f'{date}の画面で確認（{prev}の画面では未取得の「？」）'
        if s.get('arcade_id') and s['arcade_id'] in arcade:
            arcade[s['arcade_id']]['availability'] = '獲得済み（画像確認）'
    for k, name in sn.get('renamed', {}).items():
        s = slots[int(k)]
        if s['obtained']: s['screen'] = name
    history.append({'date': date, 'added': len(sn.get('new', {})), 'obtained': None, 'note': sn.get('note', '')})

# 件数の整理
total = len(DB['slots'])
for h in history:
    h['obtained'] = sum(1 for s in DB['slots'] if s['obtained'] and (s.get('confirmed') or FIRST) <= h['date'])
history[0]['added'] = history[0]['obtained']
got = sum(1 for s in DB['slots'] if s['obtained'])
meta = DB['meta']
meta['snapshot'] = history[-1]['date']
meta['firstSnapshot'] = FIRST
meta['snapshots'] = history
meta['obtainedFromImage'] = got
meta['unrevealedFromImage'] = total - got
meta['identifiedViaOrder'] = total - got

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
    if len(rows[0]) < 10: rows[0].append('画像確認日')
    for r in rows[1:]:
        while len(r) < 10: r.append('')
        s = slots[int(r[0])]
        if s['obtained']:
            r[3] = s['screen'] or ''; r[4] = 'はい'; r[9] = s.get('confirmed') or FIRST
            if s.get('confirmed') and s['confirmed'] != FIRST: r[8] = s['proof']
        else:
            r[4] = 'いいえ'; r[9] = ''
    return rows
def fix_arcade(rows):
    for r in rows[1:]:
        a = arcade.get(int(r[0]))
        if a: r[5] = a['availability']
    return rows
rewrite_csv(os.path.join(ROOT, 'animalotta_konaste330.csv'), fix_konaste)
rewrite_csv(os.path.join(ROOT, 'animalotta_arcade438.csv'), fix_arcade)

print('snapshots applied:', ' → '.join(f"{h['date']} 獲得{h['obtained']}（+{h['added']}）" for h in history))
print(f'obtained {got} / {total}, unrevealed {total - got}')
