# -*- coding: utf-8 -*-
"""排版审核总览：python3 overview.py <输出目录>
对 13 张图统一裁切（同一裁切框，保持角色尺度一致），用 HTML 排版后由 Chrome 截图。"""
import os, sys, subprocess
from PIL import Image
from render import all_looks, CHROME

CROP = (130, 280, 1470, 1340)          # 全套统一裁切框（1340×1060）

out_dir = sys.argv[1]
src_dir = os.path.join(out_dir, '源文件')
tmp = os.path.join(src_dir, '总览排版')
os.makedirs(tmp, exist_ok=True)
tiles = []
for lk in all_looks():
    name = 'Clawd_基础角色' if lk.no == 0 else f'{lk.no:02d}_{lk.title}'
    src = os.path.join(src_dir if lk.no == 0 else out_dir, name + '.png')
    im = Image.open(src).convert('RGB').crop(CROP)
    p = os.path.join(tmp, f'tile_{lk.no:02d}.png')
    im.save(p)
    tiles.append((lk.no, lk.title, os.path.basename(p)))

TW, TH = 560, round(560 * 1060 / 1340)
cells = []
for no, title, f in tiles[1:]:
    cells.append(f'<div class="cell"><img src="{f}"><div class="lab"><b>{no:02d}</b>《{title}》</div></div>')
no, title, f = tiles[0]
cells.append(f'<div class="cell ref"><img src="{f}"><div class="lab sub">参考：Clawd 基础角色（非造型）</div></div>')
W = 5 * TW + 6 * 28
H = 130 + 3 * (TH + 84) + 2 * 28 + 70
html = f'''<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;background:#F6F3EF;}}
body{{width:{W}px;height:{H}px;font-family:"PingFang SC","Hiragino Sans GB",sans-serif;color:#2E2320;}}
h1{{margin:0;padding:44px 28px 0;font-size:40px;font-weight:600;letter-spacing:1px}}
.note{{padding:10px 28px 0;font-size:20px;color:#7A6E66}}
.grid{{display:grid;grid-template-columns:repeat(5,{TW}px);gap:28px;padding:30px 28px;}}
.cell img{{width:{TW}px;height:{TH}px;display:block;border-radius:10px}}
.lab{{height:56px;line-height:56px;font-size:28px;padding-left:4px}}
.lab b{{font-weight:600;margin-right:6px;color:#B65C40}}
.ref img{{opacity:.9;outline:3px dashed #C9BFB6;outline-offset:-3px}}
.sub{{font-size:22px;color:#7A6E66}}
</style></head><body>
<h1>Clawd × 单依纯《歌手2025》13 套造型 · 第一轮角色审核</h1>
<div class="note">按演出顺序排列 · 统一角色、视角、光照与显示尺度 · 各图为同一裁切框</div>
<div class="grid">{"".join(cells)}</div></body></html>'''
hp = os.path.join(tmp, 'overview.html')
open(hp, 'w', encoding='utf-8').write(html)
subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars',
                f'--screenshot={os.path.join(out_dir, "00_造型审核总览.png")}', f'--window-size={W},{H}',
                'file://' + os.path.abspath(hp)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print('overview', W, H)
