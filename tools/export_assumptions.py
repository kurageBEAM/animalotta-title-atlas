# -*- coding: utf-8 -*-
"""
index.html の難易度データから、仮定・類推・情報不足の称号をゲーム別に並べた調整リストを書き出す。
  research/assumptions_by_game.md   … 人が読む用（右端が記入欄）
  research/assumptions_by_game.csv  … 表計算用
使い方:  python tools/export_assumptions.py   （build_difficulty.py の後に実行）
"""
import sys, os, json, re, csv, collections
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
db = json.loads(re.search(r'<script id="sourceData"[^>]*>(.*?)</script>', html, re.S).group(1))
arc = {a['arcade_id']: a for a in db['arcade']}
slot = {s['arcade_id']: s for s in db['slots']}
D = db['difficulty']

GAMES = ['ハニーエイト','ハニーファイブ','ビンゴガーデン','チェーンボンバー','アニマツリー','ヘブンツリー','ビンゴファーム','ビンゴバルーン',
         'ハッピーフラワー','ファンシーフラワー','アニマドロップ','クラッシュドロップ','サンダースマッシュ','サンダーブレイク','トゥインクルリンク',
         'メテオボンバー','ビンゴショット','マジカルマイン','ミラクルマイン']
GAME_ORDER = ['ビンゴガーデン','チェーンボンバー','アニマツリー','ハニーエイト','ビンゴファーム','ビンゴバルーン','ハッピーフラワー','アニマドロップ',
              'サンダースマッシュ','トゥインクルリンク','メテオボンバー','ビンゴショット','マジカルマイン','ビンゴエリクサー','ヘブンツリー',
              'ハニーファイブ','クラッシュドロップ','サンダーブレイク','ファンシーフラワー','ミラクルマイン']
SECRET = {'ハニーファイブ','クラッシュドロップ','サンダーブレイク','ファンシーフラワー','ミラクルマイン'}
WC_KEYS = [('ワンダースロット','ワンダースロット（倍率抽選）'),('ミラクルルーレット','ミラクルルーレット'),('ヘブンチャレンジ','ヘブンチャレンジ・ヘブンステップ（ヘブンツリー上部）'),
           ('ヘブンステップ','ヘブンチャレンジ・ヘブンステップ（ヘブンツリー上部）'),('虹色リンゴ','虹色リンゴ（JPC直行）'),('虹りんご','虹色リンゴ（JPC直行）'),('虹色りんご','虹色リンゴ（JPC直行）'),
           ('クリスタル','クリスタルWC・クリスタルJP'),('スターダスト','スターダストWC・JPC'),('ムーンライト','ムーンライトWC・JPC'),('サンシャイン','サンシャインWC・JPC'),
           ('ドリーム','ドリームWC・JPC'),('ファンタジー','ファンタジーWC・JPC'),('コンプリート','コンプリートWC・JPC'),('ワンダーチャンス','ワンダーチャンス全般'),('WC','ワンダーチャンス全般'),('JP','ジャックポット全般')]
CAT_FALLBACK = {'アルティメット':'アルティメット（15ゲームの最高役）','スター・アニマップ':'アニマップ（スター）','ショップ・演出':'ショップ・演出',
                '応援・スタンプ':'応援・スタンプ','アニマ育成・交流':'アニマ育成・交流（タッチ・動き）','アニマクエスト':'アニマクエスト',
                '季節・プレー日数':'季節・プレー日数（暦条件）','称号収集':'称号収集','メダル・モード':'メダル・モード共通','ワンダー・JPC':'ワンダーチャンス全般','ジャックポット':'ジャックポット全般'}
ORDER2 = ['ワンダースロット（倍率抽選）','スターダストWC・JPC','ムーンライトWC・JPC','サンシャインWC・JPC','ドリームWC・JPC','ファンタジーWC・JPC','コンプリートWC・JPC',
          'クリスタルWC・クリスタルJP','ミラクルルーレット','虹色リンゴ（JPC直行）','ヘブンチャレンジ・ヘブンステップ（ヘブンツリー上部）','ワンダーチャンス全般','ジャックポット全般',
          'アルティメット（15ゲームの最高役）','メダル・モード共通','アニマップ（スター）','ショップ・演出','応援・スタンプ','アニマ育成・交流（タッチ・動き）','アニマクエスト','季節・プレー日数（暦条件）','称号収集']

def group_of(a, d):
    cat = a['category']
    if cat in ('アルティメット','スター・アニマップ','ショップ・演出','応援・スタンプ','アニマ育成・交流','アニマクエスト','季節・プレー日数','称号収集'):
        return CAT_FALLBACK[cat]
    text = a['name'] + ' ' + (a.get('konaste_condition') or a['condition'])
    for g in GAMES:
        if g in text:
            if g == 'ハニーファイブ' and 'ハニーエイト' in text: return 'ハニーエイト'
            return g
    if 'エリクサー' in text: return 'ビンゴエリクサー'
    text2 = text + ' ' + d['basis']
    for k, g in WC_KEYS:
        if k in text2: return g
    return CAT_FALLBACK.get(cat, cat)

def kind_of(d):
    b = d['basis'] + d.get('note', '')
    if any(k in b for k in ('未解析','不明','未確定','記載なし','資料がない','資料なし','公開値なし')): return '不足'
    if '類推' in b: return '類推'
    return '仮定'

rows = []
for k, d in D['byId'].items():
    i = int(k)
    if not d.get('obtainable'): continue
    conf = d.get('conf')
    if not (conf == '推定' or (conf == '計算' and 'と仮定' in d['basis'])): continue
    a = arc[i]; s = slot.get(i)
    rows.append(dict(id=i, game=group_of(a, d), name=a['name'], cond=(a.get('konaste_condition') or a['condition']), r=d['r'],
                     rank=d.get('rank') or (f"T{d['tier']}" if d.get('tier') else '—'), got=bool(s and s['obtained']), kind=kind_of(d), basis=d['basis'], note=d.get('note', '')))
def gkey(g): return (0, GAME_ORDER.index(g)) if g in GAME_ORDER else (1, ORDER2.index(g) if g in ORDER2 else 99)
rows.sort(key=lambda r: (gkey(r['game']), r['id']))
def fr(r): return '事実上不可' if r is None or r >= 1e6 else f'{round(r):,}'
def hours(r): return '' if r is None or r >= 1e6 else f'{r/(D.get("roundsPerHour") or 23):.1f}h'
groups = collections.OrderedDict()
for r in rows: groups.setdefault(r['game'], []).append(r)

md = ['# 仮定・不足のある称号の調整リスト（ゲーム別）', '',
      f"難易度データ v{D['version']}（{D['built']}）。解析サイトの数値がなく、体感や類推で置いた値を使っている称号を、ゲーム（または仕組み）ごとに並べました。全 {len(rows)} 件。", '',
      '## 記入のしかた', '',
      '- 右端の「調整」欄に、次のいずれかを書いてください。', '  - ランクで指定：`A`、`S+` など（その称号の期待ラウンドをそのランクの中央値に置き換えます）',
      '  - 確率で指定：`1/500`（1ゲームあたり）、`WC100回に1回`、`300ラウンドに1回` など', '  - 体感で指定：`もっと難しい`、`もっと易しい`、`このまま`',
      '  - 累積系は「1ゲームで平均いくつ取れるか」（例：`ハチミツ 2個/ゲーム`）でも可', '',
      '- 「区分」の意味：**仮定**＝主観で置いた値／**類推**＝別ゲームの公開値からの比率推定／**不足**＝必要な情報自体が不明（出現頻度・必要数など）。',
      f"- 「現在」は 期待所要ラウンド（1ラウンド＝1回のボール抽選、約2.6分、14面×100BET前提）とランク。目安時間は{D.get('roundsPerHour') or 23}ラウンド/時。",
      '- 獲得列は2026-11-08の画面での獲得状況（済／未）。', '',
      '返していただいたら `tools/build_difficulty.py` の該当 `put()` を書き換え、根拠に「利用者報告」を付けて再ビルドします。', '']
for g, items in groups.items():
    md.append(f"## {g}{'（シークレットゲーム）' if g in SECRET else ''}　{len(items)}件"); md.append('')
    md.append('| No. | 称号 | 獲得条件 | 区分 | 現在の仮定（根拠） | 現在 | 獲得 | 調整（記入欄） |'); md.append('|---:|---|---|:---:|---|---|:---:|---|')
    for r in items:
        b = (r['basis'] + (f"［{r['note']}］" if r['note'] else '')).replace('|', '／')
        cur = f"{r['rank']}（{fr(r['r'])}R{'・' + hours(r['r']) if hours(r['r']) else ''}）"
        md.append(f"| {r['id']} | {r['name']} | {r['cond'].replace('|', '／')} | {r['kind']} | {b} | {cur} | {'済' if r['got'] else '未'} |  |")
    md.append('')
os.makedirs(os.path.join(ROOT, 'research'), exist_ok=True)
open(os.path.join(ROOT, 'research', 'assumptions_by_game.md'), 'w', encoding='utf-8').write('\n'.join(md))
with open(os.path.join(ROOT, 'research', 'assumptions_by_game.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f); w.writerow(['ゲーム／仕組み', 'No.', '称号', '獲得条件', '区分', '現在の仮定（根拠）', '現在ランク', '期待ラウンド', '獲得', '調整（記入欄）'])
    for r in rows: w.writerow([r['game'], r['id'], r['name'], r['cond'], r['kind'], r['basis'] + (f"［{r['note']}］" if r['note'] else ''), r['rank'], fr(r['r']), '済' if r['got'] else '未', ''])
print('rows', len(rows), dict(collections.Counter(r['kind'] for r in rows)))
