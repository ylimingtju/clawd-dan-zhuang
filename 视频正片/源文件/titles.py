# -*- coding: utf-8 -*-
"""片头 / 片尾共用：同一套字体、排版与 13 色块条（每块是一套造型的主色 + 标志色）。"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import engine as E

BG = '#ECE7E1'
INK = '#2E2320'
TITLE = 'Clawd 蛋装'
CHIPS = [('#F6F3EC', '#BFD3E6'), ('#EBCFDC', '#F7EAF0'), ('#24242C', '#D9AE4E'), ('#7C1F2C', '#B9C3DA'),
         ('#F2E3A2', '#FFFDF4'), ('#2D3448', '#D9B25C'), ('#2C3EB2', '#5B6EDB'), ('#23232B', '#25336A'),
         ('#B3174F', '#5E1828'), ('#F7F5F0', '#1F1F26'), ('#F8F7F3', '#CC322C'), ('#1E1E25', '#2F9E68'),
         ('#BFCCD7', '#D7AA45')]
CHIP, GAP, CHIP_Y = 48, 16, 958


def chip_x(i):
    total = 13 * CHIP + 12 * GAP
    return 960 - total / 2 + i * (CHIP + GAP) + CHIP / 2


def text_layer():
    """唯一的标题文字「Clawd 蛋装」（PIL 排版，保证中文准确）；“蛋”用 Clawd 橙色点睛。"""
    im = Image.new('RGBA', (1920, 1080), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ft = ImageFont.truetype(E.FONT_SANS, 150, index=2)
    parts = [('Clawd ', INK), ('蛋', '#D97757'), ('装', INK)]
    widths = [d.textlength(s, font=ft) for s, _ in parts]
    x = 960 - sum(widths) / 2
    for (s, c), w_ in zip(parts, widths):
        d.text((x, 150), s, font=ft, fill=c)
        x += w_
    return np.asarray(im, np.float32) / 255.0


def chips_svg(appear, pulse0=0.0):
    """13 色块：appear(i) → 0..1 出现进度；pulse0 为第 1 块（珠玉）的放大量。"""
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">']
    for i, (c1, c2) in enumerate(CHIPS):
        k = appear(i)
        if k <= 0:
            continue
        s = E.ease_back(k) * (1 + (pulse0 if i == 0 else 0))
        x = chip_x(i)
        out.append(f'<g transform="translate({x:.1f},{CHIP_Y}) scale({s:.3f})">'
                   f'<rect x="{-CHIP / 2}" y="{-CHIP / 2}" width="{CHIP}" height="{CHIP}" rx="10" fill="{c1}" stroke="{INK}" stroke-width="3"/>'
                   f'<circle cx="{CHIP / 2 - 13}" cy="{CHIP / 2 - 13}" r="7" fill="{c2}" stroke="{INK}" stroke-width="2"/></g>')
    out.append('</svg>')
    return ''.join(out)
