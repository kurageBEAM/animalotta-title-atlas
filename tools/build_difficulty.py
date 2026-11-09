# -*- coding: utf-8 -*-
"""
アニマロッタ称号アトラス｜難易度推定ビルダー
- index.html 内の sourceData(JSON) を読み、全438称号に「期待所要ラウンド数」→ ランク(F〜SS)・★(1〜5) を付与する
- animalotta_difficulty.json / animalotta_difficulty.csv を書き出し、index.html の sourceData に difficulty を注入する
使い方:  python tools/build_difficulty.py  (リポジトリ直下で実行)
"""
import json, re, csv, math, random, sys, os
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'index.html')

# ───────────────────────── 前提値（すべて data.assumptions として UI に表示） ─────────────────────────
ROUNDS_PER_HOUR = 23          # 1ラウンド ≒ 2.6分（利用者申告: 2.5〜2.75分）
GAMES_PER_ROUND = 14          # 超極マルチ14面（利用者申告）
BET_PER_GAME    = 100         # 1ゲームのBET（利用者申告）
PAYOUT          = 0.85        # ペイアウト率の仮定
WIN_PER_ROUND   = GAMES_PER_ROUND*BET_PER_GAME*PAYOUT   # ≒1,190枚
WC_PER_ROUND    = 1/7         # ワンダーチャンス出現率（monnpare 体感仮定）
STAR_PER_ROUND  = 0.4         # スター獲得（14面プレー・5,000個獲得済みから校正）
APPLE_PER_ROUND = 1.3         # リンゴ（ワンダーステップ）: 14面 × 約9.6%/ゲーム
P_WIN_GAME      = 0.6         # 1ゲームで配当が発生する確率
RAINBOW_PER_ROUND = 1/500     # 虹色リンゴ（JPC直行）
QUEST_ROUNDS    = 25          # クエスト1件クリアあたり
WC_MIX   = {'STD':3/7,'ML':1/7,'SS':1/7,'DR':1/7,'FA':1/7}
WC_CLEAR = {'STD':1/8,'ML':1/7,'SS':1/7,'DR':1/7,'FA':1/8,'CP':1/8}
JP_RATE  = {'STD':.197,'ML':.337,'SS':.371,'DR':.285,'FA':.289,'CP':.216}
SLOT     = {'BIG':.20,'SUPER':.10,'ULT':.05,'GOD':.02,'CRY':.04}
CRY_CHALLENGE = 0.30          # クリスタルWC → クリスタルJPC 到達率
CRY_JP   = 0.25               # クリスタルJPC の JP 率（21.2〜35.3%）
CP_UNLOCK_WC = 140            # 5種WC突破（コンプリート解放）までの期待WC数
CP_SHARE = 1/7                # 解放後のコンプリートWC出現比
AVG_CLEAR = 0.133             # WC平均突破率 ≒ 1/7.5
AVG_JP = 0.27                 # JPC平均JP率
JP_PER_WC_ANY = sum(WC_MIX[t]*WC_CLEAR[t]*JP_RATE[t] for t in WC_MIX)   # ≒0.036

SRC = {
 'monnpare_jp':   ('アニマロッタ解析「各種JPの確率について」(2026-04)', 'https://monnpare.blogspot.com/2026/04/jp.html'),
 'monnpare_ssjpc':('アニマロッタ解析「サンシャインJPCの確率について」(2026-04)', 'https://monnpare.blogspot.com/2026/04/jpc.html'),
 'monnpare_all':  ('アニマロッタ解析「アニマロッタ全JPC確率比較」(2026-04)', 'https://monnpare.blogspot.com/2026/04/jpc_22.html'),
 'qiita_ss':      ('Qiita: アニマロッタ6 サンシャインWCの突破率 (TEA437354)', 'https://qiita.com/TEA437354/items/ac014c89fb45da984729'),
'mabo_wcjpc':    ('マボメダルゲーム「WCとJPCのルール＆確率」アニマロッタ8（ムーンライトJPC各Round突破率）', 'https://mabo-medalgame.com/animalotta-wc-jpc/'),
'nico_dic':      ('ニコニコ大百科「アニマロッタ」（ムーンライトJPCのポケット数と理論値）', 'https://dic.nicovideo.jp/a/%E3%82%A2%E3%83%8B%E3%83%9E%E3%83%AD%E3%83%83%E3%82%BF'),
'user_report':   ('利用者（コナステ版ヘビープレーヤー）の体感報告 2026-11-09', ''),
 'mgf_tree':      ('メダルゲームファン: アニマツリー各階到達確率（初代、1,000万回シミュレーション）', 'https://medalgamefan.com/animalotta/page002.htm'),
 'mgf_bg':        ('メダルゲームファン: ビンゴガーデン カード別4ラインビンゴ確率・PO理論値（初代）', 'https://medalgamefan.com/animalotta/bingogarden.htm'),
 'atwiki_prob':   ('AnimaLotta@2ch wiki「各種確率」（初代、2011年の計算値）', 'https://w.atwiki.jp/animalotta/pages/19.html'),
 'monnpare_bf':   ('アニマロッタ解析「ビンゴファームのペイアウト率」(2026-04、コナステ14面前提のシミュレーション)', 'https://monnpare.blogspot.com/2026/04/blog-post_30.html'),
 'monnpare_honey':('アニマロッタ解析「ハニーエイト・ハニーファイブのペイアウト率」(2026-04)', 'https://monnpare.blogspot.com/2026/04/blog-post_27.html'),
 'monnpare_cb':   ('アニマロッタ解析「チェーンボンバーのペイアウト率」(2026-04)', 'https://monnpare.blogspot.com/2026/04/blog-post_26.html'),
 'monnpare_hc':    ('アニマロッタ解析: ヘブンチャレンジの1,000万回シミュレーション（クエスト難易度の記事内）', 'https://monnpare.blogspot.com/'),
 'monnpare_hf':   ('アニマロッタ解析「ハッピーフラワーの設定について」(2026-04、全獲り率・ファンシーフラワー全獲り理論値)', 'https://monnpare.blogspot.com/2026/04/blog-post_19.html'),
 'monnpare_meteor':('アニマロッタ解析「最高設定時のメテオボンバー解析」(2022-04、各100万回シミュレーション)', 'https://monnpare.blogspot.com/2022/04/blog-post_6.html'),
 'monnpare_mm':   ('アニマロッタ解析「マジカルマインのシミュレーション(4) ペイアウト率及び全消し率」(2024-06、600回)', 'https://monnpare.blogspot.com/2024/06/4.html'),
 'zisaku_ts':     ('自作アニマロッタ「16-9 サンダースマッシュのPO率(2)」(2019-11、アニマロッタ5世代の自作再現シミュレーション)', 'https://zisakuanimarotta.blogspot.com/2019/11/16-9po2.html'),
 'zisaku_ht':     ('自作アニマロッタ「18-3 ヘブンツリーのPO率」(2019-12、自作再現シミュレーション)', 'https://zisakuanimarotta.blogspot.com/2019/12/18-3po.html'),
 'zisaku_max':    ('自作アニマロッタ「14-9 アニマロッタの最高設定について」(2019-09、実機109ゲームのPO率)', 'https://zisakuanimarotta.blogspot.com/2019/09/14-9.html'),
 'qiita_ml':      ('Qiita: アニマロッタ6 ムーンライトWCの突破率 (TEA437354)', 'https://qiita.com/TEA437354/items/61602956972910d9c423'),
 'qiita_std':     ('Qiita: アニマロッタ6 スターダストWCの突破率 (TEA437354)', 'https://qiita.com/TEA437354/items/162ef6e3c84fcfae7a41'),
 'mgf_wc':        ('メダルゲームファン: WCメダル獲得期待値一覧（ライン成立率・JPC突入率）', 'https://medalgamefan.com/animalotta/page003.htm'),
 'mgf_bbs':       ('メダルゲームファン掲示板: アニマロッタ コナステ 攻略･雑談', 'https://medalgamefan.com/bbs/reply.php?topicid=612'),
 'byakuryu':      ('白龍の: コナステ版のアニマップ（各マップのスター必要数）', 'https://byakuryu.seesaa.net/article/202101article_KONAST_AnimaLotta_animap.html'),
 'unyoko':        ('実機アニマロッタ8 称号一覧（unyoko氏）', 'https://blog.livedoor.jp/unyoko/archives/52152444.html'),
 'official':      ('KONAMI お知らせ: アニマロッタ アニマと星の物語 コナステ', 'https://p.eagate.573.jp/game/lotta/anknst/eacloud/p/news/datainfo_off_anm.html'),
 'snapshot':      ('2026-11-08 コナステ画面17枚の獲得状況による校正', ''),
}

ASSUMPTIONS = [
 ('1ラウンド',f'1回のボール抽選（約{60/ROUNDS_PER_HOUR:.1f}分）。マルチ系モードでは複数ゲームが同時に決着する','定義',[]),
 ('ラウンド/時間',f'{ROUNDS_PER_HOUR}ラウンド/時間（約{60/ROUNDS_PER_HOUR:.1f}分/ラウンド）','利用者申告',[]),
 ('同時プレーゲーム数',f'{GAMES_PER_ROUND}ゲーム/ラウンド × {BET_PER_GAME}BET（超極マルチ14面）','利用者申告',[]),
 ('WIN枚数/ラウンド',f'{WIN_PER_ROUND:,.0f}枚（{GAMES_PER_ROUND}ゲーム×{BET_PER_GAME}BET×ペイアウト{PAYOUT*100:.0f}%）。累計WIN系はこの値に比例して難易度が変わる','申告BET＋ペイアウト推定',[]),
 ('ワンダーチャンス出現率','1/7ラウンド','資料（体感仮定と明記）',['monnpare_jp']),
 ('WC種別の出現比','スターダスト3/7、ムーンライト・サンシャイン・ドリーム・ファンタジー各1/7','資料（仮定と明記）',['monnpare_all']),
 ('WC突破率（JPC進出）','ムーンライト・サンシャイン・ドリーム1/7、スターダスト・ファンタジー1/8、コンプリート1/8（推定）','資料（統計）',['monnpare_all']),
 ('JPCでのJP獲得率','スターダスト19.7%／ムーンライト33.7%／サンシャイン37.1%／ドリーム28.5%／ファンタジー28.9%／コンプリート21.6%','資料（計算値）',['monnpare_all','monnpare_jp','monnpare_ssjpc']),
 ('ワンダースロット倍率の出現率','ビッグ20%／スーパー10%／アルティメット5%／ゴッド2%／クリスタル4%（WC1回あたり）','推定',[]),
 ('クリスタルJPC','クリスタルWCからJPC到達30%、JP率25%（アイテム別21.2〜35.3%）','資料＋推定',['monnpare_jp']),
 ('虹色リンゴ（JPC直行）','1/500ラウンド、JPC種別は5種均等','推定',['mgf_bbs']),
 ('スター獲得',f'{STAR_PER_ROUND}個/ラウンド','校正',['snapshot']),
 ('1ゲームの配当発生率',f'{int(P_WIN_GAME*100)}%','推定',[]),
 ('コンプリートWC解放','5種WC突破まで期待約140WC（100WCで約24%、350WCで95%）','資料（試算）',['monnpare_all']),
 ('各ゲームの最高役・特殊役','2026-11-09に解析サイト6系統（アニマロッタ解析・自作アニマロッタ・メダルゲームファン・マボ・2ch wiki・ニコニコ大百科）を調査。公開シミュレーション値のある役（ビンゴファーム・ハニーエイト／ファイブ・ハッピーフラワー・ファンシーフラワー・メテオボンバー・マジカルマイン・アニマツリー・ビンゴガーデン・サンダースマッシュ・ヘブンツリー）はその値を採用し、分母は「1カード×1ゲーム」＝1ラウンドに1面で遊ぶ換算。記載のない役（セブンバルーン・BLACKOUT・惑星キャッチャー・奇跡の錬金術・アニマドロップ全消し・ミラクルルーレット等）は主観的推定のまま','資料＋推定',['monnpare_bf','monnpare_honey','monnpare_hf','monnpare_meteor','monnpare_mm','mgf_tree','mgf_bg','zisaku_ts','zisaku_ht','snapshot']),
 ('ペイアウト率の参考値','解析サイトのゲーム別PO：ビンゴファーム84%／ハニーエイト77.7〜81.3%／チェーンボンバー約80%／ハッピーフラワー86.3%／マジカルマイン107%（特定カード）／メテオボンバー91〜140%（最高設定）／ビンゴショット115%（特定カード）。実機最高設定の実測（109ゲーム）はバルーン95・ドロップ101・ガーデン91・ファーム90%。本モデルの一律85%は維持','資料（参考）',['monnpare_bf','monnpare_honey','monnpare_cb','monnpare_hf','monnpare_mm','monnpare_meteor','zisaku_max']),
 ('クエスト',f'1件クリアあたり{QUEST_ROUNDS}ラウンド、通常クエストは全128種','推定',[]),
 ('別ゲームからの類推','資料のない役のうち同じ仕組みの役は、資料のある別ゲームの値から比率で推定（アニマドロップの全消し2〜3回＝1回の率×継続率の幾何級数、ハニーファイブ5連＝ハニーエイトの連荘継続率、ミラクルマイン全消し＝マジカルマイン全消し、アニマツリー累計階＝到達階の平均）。根拠に「類推」と元ゲームを明記','類推（2026-11-09）',['monnpare_honey','monnpare_mm','mgf_tree','user_report']),
 ('ヘブンチャレンジの発生頻度','約75ラウンドに1回（利用者体感「50〜100ラウンドに1回」の中央値）。1チャレンジあたりの確率はアニマロッタ解析の1,000万回シミュレーション（5HIT 14%・7HIT 0.4%・りんご5個 0.05%）を使用。5種×2HIT（No.38）は利用者体感「5HITの2〜3倍難しい」から5%/チャレンジ','利用者体感（2026-11-09）',['user_report','monnpare_hc']),
 ('努力型（Tiered Achievement）','ゲーム別の累計WIN（1,000／1万／10万／100万／200万枚、63件）と総WIN（100万／500万／1,000万／2,000万枚、4件）は確率ではなくBET額×プレー量で決まるため F〜SS の対象から外し、枚数の段階で Tier 1〜5 を付与。期待所要ラウンドは14面×100BET×ペイアウト85%で算出（高BETなら短縮）','定義（2026-11-09 利用者レビュー）',[]),
]

# ランク閾値（期待ラウンド数の上限）
# 2026-11-09 利用者レビュー（2回目）: 各ランクの件数が均等になるよう、分位点を丸めた固定値。
# 2026-11-09 利用者レビュー（3回目）: 累計WIN・総WINの67件を「努力型（Tiered Achievement）」として F〜SS から分離し、
#   残る確率型263件が各ランク約24件になるよう再調整。
# 旧1: F200/E500/D1000/C2000/B3500/B+6000/A10000/A+15000/S25000/S+60000（低ランク側に厚い配分）
# 旧2: F60/E120/D250/C600/B1000/B+1300/A2000/A+4000/S10000/S+23000（330枠で均等）
RANKS = [('F',50),('E',150),('D',250),('C',500),('B',950),('B+',1300),('A',2000),('A+',3000),('S',6500),('S+',12500),('SS',float('inf'))]
STARS = {'F':1,'E':1,'D':2,'C':2,'B':3,'B+':3,'A':4,'A+':4,'S':5,'S+':5,'SS':5}
def _hl(lim):
    h=lim/ROUNDS_PER_HOUR
    return f'約{h:.1f}時間まで' if h<10 else f'約{h:,.0f}時間まで'
RANK_LABEL = {n:(_hl(lim) if lim!=float('inf') else f'約{RANKS[-2][1]/ROUNDS_PER_HOUR:,.0f}時間超（運極・事実上不可を含む）') for n,lim in RANKS}

def rank_of(r):
    for name, lim in RANKS:
        if r <= lim: return name
    return 'SS'

# ───────────────────────── 計算ヘルパ ─────────────────────────
def W(p):      return 1/(WC_PER_ROUND*p)            # WC1回あたり確率 p の事象を1回起こすまでの期待ラウンド数
def JPC(t):    return WC_MIX[t]*WC_CLEAR[t]          # WC1回あたり、種別 t の JPC 進出確率
def JP(t):     return JPC(t)*JP_RATE[t]              # WC1回あたり、種別 t の JP 獲得確率
def cum(n, rate): return n/rate                        # 累計 n を 1プレーあたり rate で集める
def hand(n):   return float(n)                        # 1/n の役を1回出す

def collect_all(ps):
    """互いに排反な事象（各試行で確率 ps[i]）を全て1回以上観測するまでの期待試行回数（包除原理）"""
    n=len(ps); total=0.0
    for mask in range(1, 1<<n):
        s=sum(ps[i] for i in range(n) if mask>>i & 1)
        k=bin(mask).count('1')
        total += ((-1)**(k+1))/s
    return total

def nth_order(rates, n, sims=40000, seed=7):
    """独立な指数分布（平均 rates[i] ラウンド）の n 番目に小さい値の期待値（モンテカルロ）"""
    rng=random.Random(seed); acc=0.0
    for _ in range(sims):
        ts=sorted(rng.expovariate(1/m) for m in rates)
        acc+=ts[n-1]
    return acc/sims

MAX_HANDS = [  # 15ゲームの最高役（称号id）。出現率は HANDS / put() で定義した各称号の値をそのまま参照する
 ('ビンゴガーデン ミラクル4',114),('チェーンボンバー オールイレイサー',117),('アニマツリー クライマー50',120),
 ('ハニーエイト ハッピーハニー8',121),('ビンゴファーム ハイパーファーマー',123),('ビンゴバルーン セブンバルーン',126),
 ('ハッピーフラワー フルブルーム',127),('アニマドロップ ミラクルドロップ',131),('サンダースマッシュ サンダースマッシャー',139),
 ('トゥインクルリンク 惑星キャッチャー',145),('メテオボンバー メテオール',147),('ビンゴショット BLACKOUT',153),
 ('マジカルマイン マジカルクラッシャー',157),('ビンゴエリクサー 奇跡の錬金術',161),('ヘブンツリー ヘブンクライマー35',143)]
SECRET_HANDS = [  # シークレットゲームの最高役（称号id、None は正体不明の6種目）
 ('ハニーファイブ 5連チャン',132),('クラッシュドロップ スウィートJP',134),('サンダーブレイク 最上段',141),
 ('ファンシーフラワー モーニングブルーム',148),('ミラクルマイン 全消し',162),('6種目（不明）',None)]
SECRET_UNKNOWN = 20000   # 不明な6種目の最高役を 1/20,000 プレーと仮定

# 累積達成（区分「累積達成」）: (id, 必要数) と 1プレーあたりの獲得レート
CUM_FAMILIES = [
 ('チェーンボンバー 発掘列',2.0,[(71,200),(86,1000),(100,2000)]),
 ('ビンゴガーデン ライン',0.5,[(72,100),(87,500),(101,1000)]),
 ('アニマツリー 階',2.5,[(73,1000),(88,5000),(102,10000)]),
 ('ハニーエイト/ファイブ ハチミツ',3.0,[(74,888),(89,8888),(103,88888)]),
 ('ビンゴファーム ライン',0.85,[(75,500),(90,2000),(104,5000)]),
 ('ビンゴバルーン ライン',0.7,[(77,100),(91,500),(105,1000)]),
 ('ハッピーフラワー 花',2.0,[(78,200),(92,1000),(106,2000)]),
 ('アニマドロップ 全消し',1/25,[(79,10),(93,100),(107,500)]),
 ('サンダースマッシュ 破壊',20.0,[(80,10000),(94,50000),(108,100000)]),
 ('トゥインクルリンク LINK',5.0,[(81,1000),(95,5000),(109,10000)]),
 ('メテオボンバー 宝箱',1.0,[(82,100),(96,500),(110,1000)]),
 ('ビンゴショット ライン',1.0,[(83,200),(97,1000),(111,2000)]),
 ('マジカルマイン 宝箱',1.5,[(84,200),(98,1000),(112,2000)]),
 ('ビンゴエリクサー ライン',0.7,[(85,100),(99,500),(113,1000)]),
]
WIN_PER_GAME_ROUND = WIN_PER_ROUND/GAMES_PER_ROUND    # 1ゲーム1ラウンドあたりの WIN

T = {}   # id -> dict(rounds, conf, basis, src, note, rank_override)
def put(i, rounds, conf, basis, src=(), note='', rank_override=None):
    T[i] = dict(rounds=rounds, conf=conf, basis=basis, src=list(src), note=note, rank_override=rank_override)
def na(i, basis, note=''):
    T[i] = dict(rounds=None, conf='対象外', basis=basis, src=[], note=note, rank_override=None)

# ───────────────────────── ワンダー・JPC ─────────────────────────
put(1, 1, '確定', 'プレーすれば獲得')
for i,n in [(2,'ツナガロッタ'),(3,'カラコロッタ・ツナガロッタ'),(4,'カラコロッタ')]:
    na(i, f'{n}との連動プレーが条件。コナステ版アニマロッタ単体では達成できない')
put(5, 1, '確定', 'チュートリアルを1回クリア')
put(6, 20/STAR_PER_ROUND, '計算', f'オールモードは「雲の大樹」マップでスター20個を消費して解放（白龍）。スター{STAR_PER_ROUND}個/ラウンドで約{20/STAR_PER_ROUND:.0f}ラウンド', ['byakuryu'])
put(7, W(WC_MIX['STD']*0.03), '計算', 'スターダストWCの0ライン終了率を約3%と仮定（medalgamefanのカード別0ライン率0.2〜5.4%）× STD出現比3/7', ['mgf_wc'])
for i,k,nm in [(8,'BIG','ビッグ'),(9,'SUPER','スーパー'),(10,'ULT','アルティメット'),(11,'GOD','ゴッド'),(12,'CRY','クリスタル')]:
    put(i, W(SLOT[k]), '推定', f'ワンダースロットで{nm}が選ばれる確率を{SLOT[k]*100:.0f}%/WCと仮定')
for i,t,nm in [(13,'ML','ムーンライト'),(14,'SS','サンシャイン'),(17,'DR','ドリーム'),(19,'FA','ファンタジー')]:
    put(i, W(WC_MIX[t]), '資料', f'{nm}WCの出現比1/7（全JPC確率比較の仮定）→ 期待7WC', ['monnpare_all'])
put(15, W(WC_MIX['SS']*0.0005), '推定', 'サンシャインWCは3ゲーム合計20体以上で成功（8〜13%）。全員回収は回収上限付近が必要。Qiitaの「10〜12体回収」0.5〜1.9%、「9体以下」0.001〜0.06%という分布から、全回収を0.05%/回と推定', ['qiita_ss'])
put(16, W(WC_MIX['SS']/300), '推定', '追加アニマ数は盤面状況に依存する内部仕様。利用者の体感「サンシャインWC数百回に1回」を採用し1/300回と推定（以前は0.05%/回でSS）', ['user_report','qiita_ss'], note='利用者体感で補正')
put(18, W(WC_MIX['DR']*0.02), '推定', 'ドリームWCの歩数分布は未解析。1歩も進めずに終了する確率を2%/回と仮定')
put(20, CP_UNLOCK_WC/WC_PER_ROUND, '資料', '5種WC（STD/ML/SS/DR/FA）の突破に必要なWC数：100回で約24%、350回で95%、挑戦可能まで約140WC', ['monnpare_all'])
put(21, (CP_UNLOCK_WC+1/CP_SHARE)/WC_PER_ROUND, '計算', '5種突破（約140WC）で解放後、コンプリートWCの出現比を1/7と仮定して+7WC', ['monnpare_all'])
q=1-AVG_CLEAR; put(22, ((1-q**10)/(AVG_CLEAR*q**10))/WC_PER_ROUND, '計算', '平均突破率1/7.5で10連敗に到達する期待WC数≒24回。数字付き称号は連敗数で更新', ['monnpare_all'])
put(23, W(AVG_CLEAR), '資料', 'WC平均突破率≒1/7.5（種別ごと1/7〜1/8）→ 期待7.5WC', ['monnpare_all'])
put(24, W(0.07), '推定', '3ゲーム制WCの突破のうち2ゲーム目までに決まる割合を約半数（突破率の約半分=7%/WC）と仮定', ['qiita_ml','qiita_std'])
put(25, W(0.025), '計算', 'STD WC 1ゲーム突破≒3%（×3/7）＋ML WC 1ゲーム突破3.3〜13.9%（×1/7）≒2.5%/WC', ['qiita_ml','qiita_std'])
for i,k,nm in [(26,'BIG','ビッグ'),(27,'SUPER','スーパー'),(28,'ULT','アルティメット'),(29,'GOD','ゴッド')]:
    put(i, W(SLOT[k]*AVG_CLEAR), '計算', f'{nm}出現{SLOT[k]*100:.0f}%（推定）× 平均突破率1/7.5', ['monnpare_all'])
put(30, W(SLOT['CRY']*CRY_CHALLENGE), '推定', f'クリスタル出現{SLOT["CRY"]*100:.0f}% × クリスタルチャレンジ到達30%と仮定')
for i,t,nm in [(31,'ML','ムーンライト'),(32,'SS','サンシャイン'),(33,'DR','ドリーム'),(34,'FA','ファンタジー')]:
    put(i, W(JPC(t)), '資料', f'{nm}WC出現比1/7 × 突破率1/{round(1/WC_CLEAR[t])}（全JPC確率比較の統計）', ['monnpare_all'])
put(35, CP_UNLOCK_WC/WC_PER_ROUND + W(CP_SHARE*WC_CLEAR['CP']), '計算', '5種突破（約140WC）で解放後、コンプリートWC出現比1/7 × 突破率1/8（推定）', ['monnpare_all'])
HC_ROUNDS = 75      # ヘブンチャレンジ1回あたりのラウンド数（利用者体感 50〜100 の中央値）
HC_APPLE, HC_5HIT, HC_EACH2 = 0.25, 0.14, 0.05   # 1チャレンジあたり: リンゴ1個以上（仮定）、ベット対象5HIT（解析1,000万回）、5種各2HIT（体感：5HITの2〜3倍難）
put(36, HC_ROUNDS/HC_APPLE, '推定', f'ヘブンチャレンジ（約{HC_ROUNDS}ラウンドに1回、利用者体感）中にリンゴ1個以上を獲得する確率を{HC_APPLE:.0%}/チャレンジと仮定', ['user_report'])
put(37, HC_ROUNDS/HC_5HIT, '推定', f'ヘブンチャレンジ（約{HC_ROUNDS}ラウンドに1回、利用者体感）× ベット対象アニマ5HIT {HC_5HIT:.0%}/チャレンジ（アニマロッタ解析の1,000万回シミュレーション）', ['user_report','monnpare_hc'], note='発生頻度は体感値')
put(38, HC_ROUNDS/HC_EACH2, '推定', f'ヘブンチャレンジ（約{HC_ROUNDS}ラウンドに1回、利用者体感）× 5種各2HIT {HC_EACH2:.0%}/チャレンジ（追加球なしの組合せ値1.2%に、2HITごとの追加5球と利用者体感「5HITの2〜3倍難」を加味）', ['user_report','monnpare_hc'], note='1チャレンジあたりの率は体感')
for i,nm in [(39,'スターダスト'),(40,'ムーンライト'),(41,'サンシャイン'),(42,'ドリーム'),(43,'ファンタジー')]:
    put(i, 1/(RAINBOW_PER_ROUND/5), '推定', f'虹色リンゴを1/500ラウンド、直行先JPCは5種均等と仮定 → {nm}直行は1/2,500ラウンド', ['mgf_bbs'])
put(44, collect_all([JP(t) for t in ['STD','ML','SS','DR','FA']])/WC_PER_ROUND, '計算', '5種JPのWC1回あたり獲得確率（STD1.06%／ML0.69%／SS0.76%／DR0.58%／FA0.52%）から、全5種を揃える期待WC数を包除原理で算出', ['monnpare_all'])

# ───────────────────────── ジャックポット ─────────────────────────
put(45, 60, '推定', 'ヘブンステップ（ヘブンツリーのリンゴ）。約60ラウンドに1回と仮定')
put(46, W(JP('STD')*641/803), '資料', 'STD JP（WC1回あたり1.06%）× 等倍の割合641/803（配当比641:102:45:11:4）', ['monnpare_all'])
RAINBOW_JP = sum(JP_RATE[t] for t in ('STD','ML','SS','DR','FA'))/5
put(47, 1/(RAINBOW_PER_ROUND*RAINBOW_JP), '推定', f'虹色リンゴ1/500ラウンド（仮定） × 直行先5種JPCのJP率平均{RAINBOW_JP:.1%}（STD19.7／ML33.7／SS37.1／DR28.5／FA28.9%）', ['monnpare_all'])
put(48, W(0.0006), '推定', '5,000枚以上のJPはファンタジー高倍率・スターダスト10倍・コンプリートJPなどに限られる。WC1回あたり0.06%と仮定', ['monnpare_all'])
for i,k,nm in [(49,'BIG','ビッグ'),(50,'SUPER','スーパー'),(51,'ULT','アルティメット'),(52,'GOD','ゴッド')]:
    put(i, W(SLOT[k]*AVG_CLEAR*AVG_JP), '計算', f'{nm}出現{SLOT[k]*100:.0f}%（推定）× 突破1/7.5 × JP率27%', ['monnpare_all'])
put(53, W(SLOT['CRY']*CRY_CHALLENGE*CRY_JP), '資料', 'クリスタル出現4%（推定）× JPC到達30%（推定）× クリスタルJP率25%（アイテム別21.2〜35.3%）', ['monnpare_jp'])
put(54, collect_all([SLOT[k]*AVG_CLEAR*AVG_JP for k in ['BIG','SUPER','ULT','GOD']]+[SLOT['CRY']*CRY_CHALLENGE*CRY_JP])/WC_PER_ROUND, '計算', 'ビッグ〜クリスタルの5種JPを全て揃える期待WC数（包除原理）。ゴッドJP（0.07%/WC）が支配的')
put(55, W(SLOT['CRY']*CRY_CHALLENGE*CRY_JP*0.3), '推定', 'クリスタルJPのうち倍率×2アイテム選択時の割合を30%と仮定', ['monnpare_jp'])
ML_ROUND = [0.6723, 0.5021, 0.3185, 0.1536, 0.0400]   # 1st〜Last の突破率（5球/5穴, 4/4, 3/3, 2/2, 1/1 の理論値）
def ml_cum(n):
    c=1.0
    for k in ML_ROUND[:n]: c*=k
    return c
for i,n,nm in [(56,2,'Round 2突破＝ムーンライトJP'),(57,3,'Round 3突破'),(58,4,'Round 4突破'),(59,5,'Round 5（Last）突破')]:
    put(i, W(JPC('ML')*ml_cum(n)), '資料', f'ムーンライトJPC（WC1回あたり2.04%）× 累積突破率{ml_cum(n)*100:.2f}%（{nm}）。各Round突破率は1st 67.23%・2nd 50.21%・3rd 31.85%・4th 15.36%・Last 4.00%（5球/5穴→1球/1穴の理論値）', ['mabo_wcjpc','nico_dic','monnpare_all'])
put(60, W(JP('SS')), '資料', 'サンシャインJPC（WC1回あたり2.04%）× JP率37.1%。1箇所4HITが基本形', ['monnpare_all','monnpare_ssjpc'])
put(61, W(JP('SS')/8), '推定', 'サンシャインJPのうち2箇所4HITの割合を1/8と仮定', ['monnpare_ssjpc'])
put(62, W(JP('SS')/60), '推定', 'サンシャインJPのうち3箇所以上4HITの割合を1/60と仮定', ['monnpare_ssjpc'])
put(63, W(JP('DR')), '資料', 'ドリームJPC（WC1回あたり2.04%）× JP率28.5%', ['monnpare_all'])
put(64, W(JP('DR')*0.2), '推定', 'ドリームJPのうち2倍以上の割合を20%と仮定', ['monnpare_all'])
put(65, W(JP('FA')), '資料', 'ファンタジーJPC（WC1回あたり1.79%）× JP率28.9%', ['monnpare_all','monnpare_jp'])
put(66, W(JPC('FA')*0.012), '資料', 'ファンタジーJPCで25倍以上は0.65%（monnpare）。20倍以上を約1.2%/JPCと推定 → WC1回あたり0.021%', ['monnpare_jp'])
put(67, CP_UNLOCK_WC/WC_PER_ROUND + W(CP_SHARE*WC_CLEAR['CP']*JP_RATE['CP']), '計算', '5種突破（約140WC）で解放後、コンプリートWC1/7 × 突破1/8 × JP率21.6%', ['monnpare_all'])
for i,k,nm in [(68,0.2,'×3'),(69,0.1,'×5'),(70,0.03,'×10')]:
    put(i, W(JP_PER_WC_ANY*k), '推定', f'ミラクルルーレットの出現条件・分布は未解析。JP獲得（WC1回あたり約3.6%）ごとに抽選され、{nm}が{k*100:.0f}%と仮定')

# ───────────────────────── 累積達成 ─────────────────────────
for fam, rate, items in CUM_FAMILIES:
    for i,n in items:
        put(i, cum(n, rate), '推定', f'{fam}：1プレーあたり約{rate:g}と仮定 → 累計{n:,}に約{n/rate:,.0f}プレー（1ラウンド1プレー換算）')
na(76, 'Wi-Fiアニマスロットはコナステ版に存在しない')
for i in (82,96,110): T[i]['basis'] += '。アニマロッタ解析のシミュレーションでは宝箱0.87〜1.28個/プレー（最高設定・配布カード）'; T[i]['src']=['monnpare_meteor']; T[i]['conf']='資料'
for i in (84,98,112): T[i]['basis'] += '。アニマロッタ解析の特定カード600回シミュレーションで1.50個/プレー（6箱の獲得率24/45/30/21/15/15%）'; T[i]['src']=['monnpare_mm']; T[i]['conf']='資料'
for i in (75,90,104): T[i]['basis'] += '。アニマロッタ解析のFREE個数別シミュレーション（緑FREE9個で0.853ライン＝PO83.5%、5〜15個で0.62〜1.25ライン）のうち、本サイトのペイアウト85%前提と整合する値を採用（2026-11-09 外部レポート照合で1.0から下方修正）'; T[i]['src']=['monnpare_bf']
for i in (73,88,102): T[i]['basis'] = T[i]['basis'].replace('約2.5と仮定','約2.5（メダルゲームファンの初代シミュレーションで1ゲーム平均2.45〜2.57階）'); T[i]['src']=['mgf_tree']; T[i]['conf']='資料'
for i in (79,93,107): T[i]['basis'] = T[i]['basis'].replace('と仮定','（全消し1回＝1/25ゲームの仮定と同じ値）'); T[i]['note']='全消し1回の率に連動'

# ───────────────────────── 特殊役・最高役（1/N プレー） ─────────────────────────
HANDS = {114:30000,115:3000,116:3000,117:12000,118:2000,119:10000,120:40000,121:8000,122:600,123:4000,
 126:2000,127:12000,128:25,129:300,130:2500,131:80000,132:150,133:80000,134:500,135:1000,136:20000,137:4000,138:4000,139:60000,
 140:6000,141:12000,142:400,143:15000,144:600,145:8000,146:1000,147:2500,148:12000,149:200,150:1000,151:10000,152:8000,153:60000,
 154:80,155:8000,156:1000,157:2500,158:12000,159:600,160:800,161:2000,162:3000,163:12000}
for i,n in HANDS.items():
    extra = '（2回累計）' if i==135 else ''
    put(i, hand(n), '推定', f'この役の出現率を1/{n:,}プレーと主観的に推定{extra}。2026-11-09の解析サイト調査でも出現率の記載なし。獲得状況スナップショットと整合するよう校正', ['snapshot'])
T[114]['basis'] = '3×3カードで8球中7個以上のヒットが必要（組合せ上は約1/1,850）。実際の出現率は未確認のため1/30,000プレーと保守的に推定'
T[115]['basis'] = '3×3カードで6個以上のヒット（組合せ上は約1/100）が必要だが並びにも依存。スナップショットで未獲得のため1/3,000プレーと推定'
T[131]['basis'] = '1ゲーム中に全消し4回以上。利用者報告「最難関付近」を受けて1/80,000プレーと推定（以前は1/20,000）'; T[131]['src']=['user_report','snapshot']; T[131]['note']='利用者報告で補正'
na(124, 'Wi-Fiアニマスロットはコナステ版に存在しない'); na(125, 'Wi-Fiアニマスロットはコナステ版に存在しない')

# ── 2026-11-09 解析サイト調査で得た値による上書き。分母は「1カード×1ゲーム」＝1ラウンドに1面で当該ゲームを遊ぶ換算 ──
put(114, 45000, '資料', 'ビンゴガーデン4ライン：カード別の理論値 1/24,651〜1/164,141（初代、8種カードの等重み平均 約1/45,800）。出現カードは内部状態依存のため目安', ['mgf_bg','atwiki_prob'], note='初代の理論値')
put(117, 2000, '推定', 'チェーンボンバー全消し：アニマロッタ解析のビンゴファーム記事に「ハイパーライン0.05%は一般的なカードの全消し率と同程度」とあり 1/2,000 を採用（全消し率そのものの集計はなし）', ['monnpare_bf','monnpare_cb'])
TREE_GAMES = 2.2   # アニマツリー1回の挑戦（継続込み）の平均ゲーム数 ≒ 1/(2段以下で終了する確率 約46%)
for i,f,n,n2 in [(118,30,92,113),(119,40,425,562),(120,50,1979,2765)]:
    put(i, n*TREE_GAMES, '資料', f'アニマツリー{f}階到達：メダルゲームファンの1,000万回シミュレーション（初代、2FUP70%・3FUP30%）で1回の挑戦（継続込み）あたり約1/{n:,}（2FUPのみのカードなら1/{n2:,}）× 1挑戦あたり平均{TREE_GAMES}ゲーム（2段以下で終了46%）。現行機の設定差は未反映', ['mgf_tree','atwiki_prob'], note='初代の理論値')
put(121, 370*1.8, '資料', 'ハニーエイト8連以上：1カード1ゲームあたり0.27%（=1/370、アニマロッタ解析の2万回シミュレーション速報値）× 連荘1回の挑戦あたり平均1.8ゲーム（配当獲得率44.3%）', ['monnpare_honey'])
put(122, 167, '資料', 'ビンゴファーム スーパーライン：1カード1ゲームあたり0.6%（カード比 緑95:青4.5:赤0.5 の仮定、PO率84%）。FREE個数別では緑0.24〜0.96%', ['monnpare_bf'])
put(123, 2000, '資料', 'ビンゴファーム ハイパーライン：1カード1ゲームあたり0.05%（同上）。FREE個数別では緑0.03〜0.15%・赤0.42〜0.68%', ['monnpare_bf'])
put(127, 14000, '資料', 'ハッピーフラワー全獲り：200万回シミュレーションで143回＝0.007%（1/13,986）', ['monnpare_hf'])
put(133, 500000*1.8, '資料', 'ハニーファイブ16連以上：1カード1ゲームあたり0.0002%（1/500,000）× 平均1.8ゲーム。事実上の運極', ['monnpare_honey'])
for i,side in [(137,'左側'),(138,'右側')]:
    put(i, 400, '推定', f'サンダースマッシュ{side}全消し：自作シミュレーション（アニマロッタ5世代の再現、35配置×1万回）で片側全消しは平均0.5%/ゲーム（配置により0.04〜2.0%）。左右別の集計はないため半分の0.25%＝1/400を採用。筆者自身が確証はないと注記', ['zisaku_ts'], note='自作シミュレーション値')
put(139, 2000, '推定', 'サンダースマッシュ両側全消し：同シミュレーションで平均0.05%/ゲーム（1/2,000、配置により0〜0.23%）。以前の主観推定1/60,000から大幅に軽くなる', ['zisaku_ts'], note='自作シミュレーション値')
HT_CONT, HT_FLOORS = 0.48, 3.1
ht_n = math.ceil(35/HT_FLOORS)-1   # 35階に必要な連続継続回数
put(143, (1/HT_CONT**ht_n)*(1/(1-HT_CONT)), '推定', f'ヘブンツリー35階：自作シミュレーションの継続率41.7〜54.1%・平均3.0〜3.18階/ゲームから継続率{HT_CONT:.0%}・{HT_FLOORS}階/ゲームと置き、{ht_n}回連続継続（約1/{HT_CONT**-ht_n:,.0f}挑戦）× 1挑戦平均{1/(1-HT_CONT):.1f}ゲームで導出', ['zisaku_ht'], note='自作シミュレーションから導出')
put(147, 700, '資料', 'メテオボンバー全消し：アニマロッタ解析の各100万回シミュレーションで0.39%／0.12%（最高設定の2カード）、0.16%（配布カード、20万回）。中間の約0.14%＝1/700を採用', ['monnpare_meteor'])
put(148, 950, '資料', 'ファンシーフラワー全獲り：理論値 20C3/25C8＝0.1054%（1/949）、10万回シミュレーションで0.117%', ['monnpare_hf'])
put(157, 1/0.003, '推定', 'マジカルマイン全消し：特定カード600回のシミュレーションで0.3%（試行が少なく誤差大）→ 1/333', ['monnpare_mm'], note='試行600回の暫定値')
# ── 別ゲームの資料からの類推（2026-11-09 利用者指示） ──
DROP1, DROP4 = 25.0, 80000.0                     # 全消し1回（仮定 1/25）、4回以上（利用者報告 1/80,000）
DROP_Q = (DROP1/DROP4)**(1/3)                    # 1ゲーム内で全消しがさらに1回続く確率 ≒ 6.8%
for i,k in [(129,2),(130,3)]:
    put(i, DROP1/DROP_Q**(k-1), '推定', f'アニマドロップ1ゲーム中の全消し{k}回：全消し1回を1/{DROP1:.0f}ゲーム（仮定）、4回以上を1/{DROP4:,.0f}（利用者報告）とし、その間を「追加の全消しが続く確率 {DROP_Q*100:.1f}%」の幾何級数でつないだ類推', ['user_report','snapshot'], note='類推（全消し1回と4回の間を補間）')
HONEY_R = (0.0002/0.27)**(1/8)                   # ハニーエイト: 8連以上0.27% → 16連以上0.0002% から1連あたりの継続率 ≒ 40.6%
put(132, (0.0027/HONEY_R**3)**-1*1.8, '推定', f'ハニーファイブ5連：ハニーエイトの8連以上0.27%・16連以上0.0002%（アニマロッタ解析）から1連あたりの継続率を{HONEY_R*100:.1f}%と置き、5連以上＝0.27%÷継続率^3≒{0.0027/HONEY_R**3*100:.1f}%/ゲーム × 平均1.8ゲーム。ハニーファイブ固有の盤面差は未反映', ['monnpare_honey'], note='類推（ハニーエイトの連荘率から）')
put(162, 1/0.003, '推定', 'ミラクルマイン全消し：同じ盤面構造のマジカルマイン全消し（600回シミュレーションで0.3%→1/333）と同じ率と仮定。ミラクルマイン固有の継続要素は未反映', ['monnpare_mm'], note='類推（マジカルマインから）')
put(145, 949, '資料', 'トゥインクルリンクのプラネットボーナス：アニマロッタ解析のファンシーフラワー記事に「全獲り（8球中に特定の5マス）はプラネットボーナスと同確率」との記述。理論値 20C3/25C8＝0.1054%（1/949）を適用', ['monnpare_hf'], note='資料の「同確率」記述による')

# ───────────────────────── アルティメット（最高役 N 種） ─────────────────────────
rates=[T[i]['rounds'] for _,i in MAX_HANDS]
for n in range(3,16):
    put(161+n, nth_order(rates, n), '計算', f'15ゲームの最高役（各1/{min(rates):,.0f}〜1/{max(rates):,.0f}プレー。解析サイトの公開値がある9ゲームはその値、他は推定）のうち{n}種類が揃うまでの期待ラウンド数（順序統計のモンテカルロ）', ['snapshot'])
srates=[T[i]['rounds'] if i else SECRET_UNKNOWN for _,i in SECRET_HANDS]
for n in range(3,7):
    put(174+n, nth_order(srates, n), '推定', f'シークレットゲームの最高役を「ハニーファイブ5連・クラッシュドロップ スウィートJP・サンダーブレイク最上段・ファンシーフラワー全獲り・ミラクルマイン全消し・不明1種（1/{SECRET_UNKNOWN:,}）」とみなし、{n}種類が揃うまでの期待ラウンド数（順序統計のモンテカルロ）')

# ───────────────────────── メダル・モード ─────────────────────────
put(181, W(SLOT['CRY']), '推定', 'クリスタルリンゴ（クリスタルWC）の出現を4%/WCと仮定')
put(182, 600, '推定', '虹色リンゴ（1/500ラウンド）とクリスタルリンゴ（1/175ラウンド）を含む全7種を揃える')
put(183, 150, '推定', '1ゲーム（1ラウンド）でリンゴ3個以上。約150ラウンドに1回と仮定')
put(184, 200, '推定', '3ゲームBETで無配当5連続。狙えば（ヒットしにくいゲームを3つ選ぶ）数百ラウンド以内。無作為プレーでは稀')
for i in (185,186,187): put(i, cum(1000, WIN_PER_GAME_ROUND), '計算', f'累計WIN 1,000枚 ÷ 1ゲーム{WIN_PER_GAME_ROUND:.0f}枚/ラウンド')
put(188, 1/APPLE_PER_ROUND, '計算', f'リンゴ（ワンダーステップ）は約{APPLE_PER_ROUND}個/ラウンド（14面ハッピーフラワーで9.6%/ゲーム）', ['monnpare_jp'])
for i in list(range(189,192))+list(range(193,195))+list(range(196,206)):
    put(i, cum(10000, WIN_PER_GAME_ROUND), '計算', f'累計WIN 10,000枚 ÷ 1ゲーム{WIN_PER_GAME_ROUND:.0f}枚/ラウンド')
put(192, cum(100, APPLE_PER_ROUND), '計算', f'リンゴ約{APPLE_PER_ROUND}個/ラウンド → 100個', ['monnpare_jp'])
na(195, 'Wi-Fiアニマスロットはコナステ版に存在しない')
for i in list(range(206,209))+list(range(210,222)):
    put(i, cum(100000, WIN_PER_GAME_ROUND), '計算', f'累計WIN 100,000枚 ÷ 1ゲーム{WIN_PER_GAME_ROUND:.0f}枚/ラウンド')
put(209, cum(1000, APPLE_PER_ROUND), '計算', f'リンゴ約{APPLE_PER_ROUND}個/ラウンド → 1,000個', ['monnpare_jp'])
for i in range(222,237): put(i, cum(1000000, WIN_PER_GAME_ROUND), '計算', f'累計WIN 1,000,000枚 ÷ 1ゲーム{WIN_PER_GAME_ROUND:.0f}枚/ラウンド。BET額に比例して短縮')
for i in range(237,252): put(i, cum(2000000, WIN_PER_GAME_ROUND), '計算', f'累計WIN 2,000,000枚 ÷ 1ゲーム{WIN_PER_GAME_ROUND:.0f}枚/ラウンド。BET額に比例して短縮')
put(252, cum(10000, APPLE_PER_ROUND), '計算', f'リンゴ約{APPLE_PER_ROUND}個/ラウンド → 10,000個', ['monnpare_jp'])
put(253, 1/P_WIN_GAME**3, '計算', f'シングル3ゲーム全てで配当：{P_WIN_GAME}^3')
put(254, 1/0.25**3, '推定', 'BETの2倍以上の配当を25%/ゲームと仮定：0.25^3')
put(255, 1/0.15**3, '推定', 'BETの3倍以上の配当を15%/ゲームと仮定：0.15^3')
for i,n,nm in [(256,6,'マルチ6'),(257,15,'オールモード15'),(258,8,'超マルチ8'),(259,10,'超超マルチ10'),(260,12,'極マルチ12'),(261,14,'超極マルチ14'),(262,9,'ナインビンゴ9'),(263,9,'ナインビンゴカスタム9'),(264,9,'ナインビンゴ超カスタム9')]:
    put(i, 1/P_WIN_GAME**n, '計算', f'{nm}ゲーム全てで配当：{P_WIN_GAME}^{n}（そのモードをプレーしている前提）')
put(265, 1/0.75**9, '推定', '配当しやすいゲーム9面同一種：配当率75%と仮定 0.75^9')
put(266, 1/0.35**9, '推定', '配当しづらいゲーム9面同一種：配当率35%と仮定 0.35^9')
put(267, 4000, '推定', 'ライン宝箱からBET30倍。約4,000ラウンドに1回と仮定')
put(268, 1/0.35**5, '推定', 'ラウンド合計がBET以上となる確率を35%と仮定：0.35^5')

# ───────────────────────── スター・アニマップ ─────────────────────────
for i,n in [(269,1_000_000),(270,5_000_000),(271,10_000_000),(272,20_000_000)]:
    put(i, cum(n, WIN_PER_ROUND), '計算', f'総WIN {n:,}枚 ÷ {WIN_PER_ROUND:,.0f}枚/ラウンド（{GAMES_PER_ROUND}面×{BET_PER_GAME}BET×PO{PAYOUT*100:.0f}%）。BET額に比例して短縮', ['snapshot'])
for i,n in [(273,100),(274,500),(275,1000),(276,5000)]:
    put(i, cum(n, STAR_PER_ROUND), '計算', f'スター{n:,}個 ÷ '+str(STAR_PER_ROUND)+'個/ラウンド', ['snapshot'])
MAPS = [(277,'アニマロッタ4「おとぎの国」1ページ目',490+510+255),(279,'アニマロッタ5「雲の大樹」1ページ目',490+510+510+255),(281,'アニマロッタ6「星の物語」1ページ目',490+510+510+510+665),(283,'アニマロッタ7「アニマランド」1ページ目',490+510+510+510+1330+350),(285,'アニマロッタ8 1ページ目',490+510+510+510+1330+700+350)]
for i,nm,stars in MAPS:
    put(i, cum(stars, STAR_PER_ROUND), '推定', f'{nm}：マップは順に解放されると仮定し、累計スター約{stars:,}個（フェスティバル490／天空510／おとぎ510／大樹510／星の物語1,330、他は推定）', ['byakuryu'])
for i in (278,280,282,284,286): na(i, 'コナステ版のアニマップ構成（2ページ目）に対応する枠が見当たらない')
for i in range(287,297): na(i, 'コナステ版に対応する枠が見当たらない（アニマ固定・サイズ変更・スタンプショップ・BGM・ガチャ等）')
put(297, 500, '推定', 'スターを消費してコンプリート条件を短縮。必要スター数は未確認')
put(298, 500 + W(JPC('ML')*0.3), '推定', '短縮後に該当JPCで JP 獲得（JPC 2.04%/WC × JP率約30%）')

# ───────────────────────── ショップ・演出 / 応援・スタンプ ─────────────────────────
for i in range(299,316): na(i, 'ワンダーBGM・背景の変更機能に対応する枠がコナステ版に見当たらない')
for i in range(316,336): na(i, '他プレイヤーとの応援・スタンプ送受信・ご当地スタンプはコナステ版に対応する枠が見当たらない')
for i,n,r in [(336,10,100),(337,50,800),(338,100,3000)]:
    put(i, r, '推定', f'スタンプ{n}種類。入手経路（ショップ・イベント）に依存するため約{r:,}ラウンドと仮定')
na(339, 'スタンプ受信機能に対応する枠が見当たらない'); na(340, 'スタンプ受信機能に対応する枠が見当たらない')

# ───────────────────────── アニマ育成・交流 ─────────────────────────
for i,n,r in [(341,10,1000),(342,30,2000),(343,50,4000),(345,100,10000)]:
    put(i, r, '推定', f'アニマの動き{n}種類。アニマップでスター購入（1枠10〜150個）が主な入手経路と仮定', ['byakuryu'])
put(344, 6000, '推定', '必要数が未確定（原典でも不明）。50種と100種の間と仮定')
put(346, 5, '確定', 'アニマを2匹登録'); put(347, 20, '推定', 'アニマを5匹登録（登録枠の解放を含む）')
put(348, 20, '推定', 'タッチは手動操作。1ラウンド5回程度'); put(349, 200, '推定', 'タッチ1,000回'); put(350, 1000, '推定', 'タッチ5,000回')
for i in range(351,387): na(i, '応援・アニマ解禁・ミニマ・応援団はコナステ版に対応する枠が見当たらない')

# ───────────────────────── アニマクエスト ─────────────────────────
put(387, 1, '確定', 'クエストを受注'); put(388, 10, '推定', '最初のクエストをクリア')
put(389, 100, '推定', 'クエスト10回失敗（期限切れ等）')
for i,n in [(390,10),(391,50),(392,100),(393,300)]:
    put(i, n*QUEST_ROUNDS, '推定', f'クエスト{n}回クリア × 1件約{QUEST_ROUNDS}ラウンド')
put(394, 32*QUEST_ROUNDS, '推定', '通常クエスト128種の25%=32件 × 約25ラウンド')
put(395, 64*QUEST_ROUNDS, '推定', '通常クエスト（全128種）の達成率50%=64件 × 約25ラウンド')
put(396, 96*35, '推定', '通常クエスト（全128種）の達成率75%=96件。後半は難化するとみて1件35ラウンド')
for i in range(397,403): na(i, 'SPクエストが条件。コナステ版にSPクエストは存在せず、未取得5枠はSPを除いた順序で通常クエスト称号に対応するため、対応する枠もないと判断', 'SP限定')
put(403, 128*QUEST_ROUNDS, '推定', '通常クエスト全128種を受注（受注のみ、クリア不要）。1件約25ラウンドで入れ替わると仮定')
put(404, 128*QUEST_ROUNDS, '推定', 'コナステ版では「通常クエスト全128種を受注」と読み替え（ワールドトラベラーと同条件）。1件約25ラウンドで入れ替わると仮定', note='SP部分を除いた読み替え')
put(405, 128*45, '推定', 'コナステ版では「通常クエスト全128種をクリア（達成率100%）」と読み替え。終盤のクエストは難化するとみて1件45ラウンド', note='SP部分を除いた読み替え')

# ───────────────────────── 季節・プレー日数 ─────────────────────────
for i,nm in [(406,'3〜5月'),(407,'6〜8月'),(408,'9〜11月'),(409,'12〜2月')]:
    put(i, 1/JP_PER_WC_ANY/WC_PER_ROUND, '計算', f'{nm}の期間中にJPを1回（JPはWC1回あたり約3.6% → 期待28WC）。該当する季節を待つ必要あり', ['monnpare_all'], note='暦条件')
put(410, 4/JP_PER_WC_ANY/WC_PER_ROUND, '計算', '四季それぞれでJP1回。最短でも約1年のプレー期間が必要', ['monnpare_all'], note='暦条件（最短1年）', rank_override='B')
put(411, 1, '確定', '初プレーから丸1年経過後に再プレー。操作は1回だが1年の経過が必要', note='時間条件（1年）', rank_override='C')
for i,h in [(412,24),(413,168),(414,720),(415,1000)]:
    put(i, h*ROUNDS_PER_HOUR, '計算', f'累計プレー{h}時間 × {ROUNDS_PER_HOUR}ラウンド/時間')
put(416, 70, '推定', '曜日7種類すべてでプレー（最短1週間）。1日10ラウンド換算', note='暦条件')
put(417, 50, '推定', '土日のプレー合計5日（最短3週間）', note='暦条件', rank_override='D')
for i,d in [(418,2),(419,3),(420,4),(421,5),(422,6),(423,7),(424,8)]:
    put(i, d*10, '推定', f'{d}日連続プレー（1日10ラウンド換算）', note='連続ログイン条件')
put(425, 8*ROUNDS_PER_HOUR, '計算', f'1日合計8時間 × {ROUNDS_PER_HOUR}ラウンド/時間')

# ───────────────────────── Wi-Fi / 称号収集 ─────────────────────────
for i in range(426,430): na(i, 'Wi-Fi連動機能はコナステ版に存在しない')
# 430〜438 は後で分布から算出

# ───────────────────────── 努力型（Tiered Achievement） ─────────────────────────
# 累計WIN・総WINの称号は確率ではなくプレー量で決まるため、F〜SS のランクではなく枚数段階の Tier 1〜5 を付ける。
TIER_DESC = {1:'累計WIN 1,000枚', 2:'累計WIN 1万枚／総WIN 100万枚', 3:'累計WIN 10万枚／総WIN 500万枚',
             4:'累計WIN 100万枚／総WIN 1,000万枚', 5:'累計WIN 200万枚／総WIN 2,000万枚'}
TIERED = {}
for i in (185,186,187): TIERED[i] = 1
for i in [189,190,191,193,194]+list(range(196,206)): TIERED[i] = 2
for i in [206,207,208]+list(range(210,222)): TIERED[i] = 3
for i in range(222,237): TIERED[i] = 4
for i in range(237,252): TIERED[i] = 5
TIERED.update({269:2, 270:3, 271:4, 272:5})   # 総WIN 100万／500万／1,000万／2,000万枚
assert len(TIERED) == 67

# ───────────────────────── 読み込み・組み立て ─────────────────────────
html = open(INDEX, encoding='utf-8').read()
m = re.search(r'(<script id="sourceData" type="application/json">)(.*?)(</script>)', html, re.S)
DB = json.loads(m.group(2))
arcade = {a['arcade_id']: a for a in DB['arcade']}
sp_gated = set(DB['meta'].get('spDefinitelyGated', [])) | set(DB['meta'].get('spPossiblyGated', []))

def obtainable(i):
    a = arcade[i]
    if a['availability'].startswith('コナステ枠なし'): return False
    if i in sp_gated: return False
    return True

# 称号収集（%）: コナステ枠ありの称号の期待ラウンド分布から算出
pool = sorted(T[i]['rounds'] for i in range(1,430) if obtainable(i) and T.get(i) and T[i]['rounds'] is not None)
total_slots = DB['meta']['konasteSlots']
def pct_rounds(p):
    k = math.ceil(p*total_slots)
    return pool[k-1] if k-1 < len(pool) else None
for i,p in [(438,.10),(437,.20),(436,.30),(435,.50),(434,.70),(433,.80),(432,.90),(431,.95)]:
    r = pct_rounds(p)
    if r is None:
        put(i, 10**6, '計算', f'全{total_slots}枠の{int(p*100)}%={math.ceil(p*total_slots)}称号が必要。SP条件など達成不能な枠を含むため実質不可', rank_override='SS')
    else:
        put(i, r, '計算', f'全{total_slots}枠の{int(p*100)}%={math.ceil(p*total_slots)}称号。難易度順に{math.ceil(p*total_slots)}番目の称号の期待ラウンド数（約{r:,.0f}）を所要とみなす', ['snapshot'])
put(430, 10**6, '計算', f'全{total_slots}枠の獲得。最も重いSS称号（事実上不可）の所要に支配される', rank_override='SS', note='事実上不可の可能性')

missing = [i for i in range(1,439) if i not in T]
assert not missing, f'未定義: {missing}'

def hours(r): return r/ROUNDS_PER_HOUR
def fmt_rounds(r):
    if r is None: return ''
    if r >= 10**6: return '—'
    return f'{r:,.0f}'

out = {}
for i in range(1,439):
    t = T[i]; a = arcade[i]
    r = t['rounds']
    ob = obtainable(i) and r is not None
    tier = TIERED.get(i) if ob else None
    rank = None
    if ob and not tier:
        rank = t['rank_override'] or rank_of(r)
    out[str(i)] = {
        'r': None if r is None else round(r, 1),
        'h': None if r is None else round(hours(r), 1),
        'rank': rank, 'stars': STARS[rank] if rank else None,
        'kind': 'tiered' if tier else ('prob' if ob else None), 'tier': tier,
        'conf': t['conf'] if ob else '対象外', 'basis': t['basis'], 'src': t['src'], 'note': t['note'],
        'obtainable': ob,
    }

thresholds = [{'rank':n,'max':None if lim==float('inf') else lim,'hours':None if lim==float('inf') else lim/ROUNDS_PER_HOUR,'label':RANK_LABEL[n],'stars':STARS[n]} for n,lim in RANKS]
difficulty = {
    'version': '1.8', 'built': '2026-11-09', 'roundsPerHour': ROUNDS_PER_HOUR,
    'profile': f'{GAMES_PER_ROUND}面×{BET_PER_GAME}BET／約{60/ROUNDS_PER_HOUR:.1f}分/ラウンド／ペイアウト{PAYOUT*100:.0f}%仮定',
    'unit': f'期待所要ラウンド数（1ラウンド=1回のボール抽選、約{60/ROUNDS_PER_HOUR:.1f}分）',
    'thresholds': thresholds, 'stars': STARS,
    'tiers': [{'tier': n, 'label': f'T{n}', 'desc': TIER_DESC[n]} for n in range(1,6)],
    'assumptions': [{'item':a,'value':b,'kind':c,'src':d} for a,b,c,d in ASSUMPTIONS],
    'sources': {k:{'label':v[0],'url':v[1]} for k,v in SRC.items()},
    'byId': out,
}

# ─── 書き出し ───
json.dump(difficulty, open(os.path.join(ROOT,'animalotta_difficulty.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=1)
with open(os.path.join(ROOT,'animalotta_difficulty.csv'),'w',encoding='utf-8-sig',newline='') as f:
    w = csv.writer(f)
    w.writerow(['実機番号','称号名','コナステ枠番号','コナステ対象','難易度ランク','★','期待ラウンド数','期待時間(h)','信頼度','算出根拠','補足','出典'])
    for i in range(1,439):
        a=arcade[i]; d=out[str(i)]
        w.writerow([i,a['name'],a['konaste_slot'] or '', 'YES' if d['obtainable'] else 'NO', d['rank'] or (f"T{d['tier']}（努力型）" if d['tier'] else '対象外'), '★'*d['stars'] if d['stars'] else '', fmt_rounds(d['r']), '' if d['h'] is None or d['r']>=10**6 else d['h'], d['conf'], d['basis'], d['note'], ' / '.join(SRC[s][0] for s in d['src'])])

DB['difficulty'] = difficulty
new_json = json.dumps(DB, ensure_ascii=False, separators=(',',':'))
html = html[:m.start(2)] + new_json + html[m.end(2):]
open(INDEX,'w',encoding='utf-8').write(html)

# ─── サマリ ───
from collections import Counter
slots = {s['arcade_id']: s for s in DB['slots'] if s['arcade_id']}
c_all = Counter(); c_obt = Counter(); c_miss = Counter()
for i in range(1,439):
    d=out[str(i)]
    if not d['obtainable']: continue
    key = d['rank'] or f"T{d['tier']}"
    c_all[key]+=1
    s = slots.get(i)
    if s: (c_obt if s['obtained'] else c_miss)[key]+=1
print('rank  total  obtained(img)  missing(img)')
for n,_ in RANKS: print(f'{n:<4}  {c_all[n]:>5}  {c_obt[n]:>13}  {c_miss[n]:>12}')
for n in range(1,6): print(f'T{n:<3}  {c_all[f"T{n}"]:>5}  {c_obt[f"T{n}"]:>13}  {c_miss[f"T{n}"]:>12}')
print('対象外:', sum(1 for i in range(1,439) if not out[str(i)]['obtainable']))
print('conf:', Counter(out[str(i)]['conf'] for i in range(1,439)))
