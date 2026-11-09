# -*- coding: utf-8 -*-
"""
index.html の UI 部分（CSS / body / アプリJS）を tools/ui/ のパーツから組み立て直す。
sourceData(JSON) はそのまま維持する（データは tools/build_difficulty.py が更新）。
使い方:  python tools/assemble_ui.py
"""
import re, os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI = os.path.join(ROOT, 'tools', 'ui')
INDEX = os.path.join(ROOT, 'index.html')

def rd(p): return open(p, encoding='utf-8').read()
html = rd(INDEX)
base_css = rd(os.path.join(UI, 'base.css')).strip()
extra_css = rd(os.path.join(UI, 'extra.css')).strip()
body = rd(os.path.join(UI, 'body.html')).strip()
app_js = rd(os.path.join(UI, 'app.js')).strip()

# 1) <style>...</style>
s0 = html.index('<style>') + len('<style>'); s1 = html.index('</style>')
html = html[:s0] + base_css + '\n' + extra_css + '\n' + html[s1:]
# 2) body: </head><body> ... までを置換（sourceData の直前まで）
b0 = html.index('</head>'); b1 = html.index('<script id="sourceData"')
html = html[:b0] + body + '\n' + html[b1:]
# 3) 最後の <script>...</script>（アプリJS）
m = list(re.finditer(r'<script>(.*?)</script>', html, re.S))[-1]
html = html[:m.start()] + '<script>\n' + app_js + '\n</script>' + html[m.end():]
# 4) meta description
html = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="コナステ版アニマロッタの称号330枠を、獲得状況と推定難易度（F〜SS・★・努力型T1〜T5）で一覧・並び替え・絞り込みできる個人用の称号帳。">', html)
html = re.sub(r'<meta name="theme-color" content="[^"]*">', '<meta name="theme-color" content="#f3f6fa">', html)
html = re.sub(r'<title>[^<]*</title>', '<title>称号アトラス｜コナステ版アニマロッタ</title>', html)
open(INDEX, 'w', encoding='utf-8').write(html)
print('assembled', len(html), 'bytes')
