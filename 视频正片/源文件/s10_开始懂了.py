# -*- coding: utf-8 -*-
"""10《开始懂了》—— 色粉笔画在深蓝灰色卡纸上。
意象：Clawd 举着右手，牵着一根线，线头拴着一只白色纸鸟。她看着它，停了一下，松手——
纸鸟扑着翅膀往右上飞走，线跟着飘远；她目送它，然后肩膀慢慢放下来，闭眼轻轻点头。放手、释然。
画法：角色与背景都是色粉：颜料只附着在纸纹凸起处，露出卡纸底色的颗粒；斜向笔触、晕擦软边；轮廓是深色粉笔线。
"""
import math
import numpy as np
import cv2
import engine as E
import fx
from scene_base import Scene

PAPER = '#2F3B52'


class S10(Scene):
    key = '10'
    filename = '10_开始懂了'
    style = '色粉笔'
    no = 10
    core = 4.0

    def setup(self):
        h, w = 1080, 1920
        base = fx.paper(h, w, PAPER, seed=111, fiber=0.0, grain=0.06)
        # 色粉天空：几道浅蓝笔触 + 地面一抹灰紫
        sky = np.zeros((h, w, 4), np.float32)
        sv = E.svg_rgba('<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">'
                        '<path d="M-50,260 C400,200 900,280 1400,210 C1700,170 1900,220 2000,200 L2000,330 C1600,360 1100,300 600,360 C300,390 100,350 -50,370 Z" fill="#6E86AE"/>'
                        '<path d="M-50,520 C500,470 1100,560 2000,480 L2000,560 C1300,620 600,560 -50,610 Z" fill="#53698F"/>'
                        '<path d="M-50,930 C600,900 1300,950 2000,915 L2000,1100 L-50,1100 Z" fill="#7A7393"/>'
                        '<circle cx="1560" cy="170" r="54" fill="#E8E2C6"/></svg>')
        sky = fx.pastel(sv, 0, 0, seed=112, density=0.8, angle=20, whiten=0.05)
        self.bg = E.over_rgb(base, sky[..., :3], sky[..., 3])

    def pose(self, t):
        K = E.K
        p = E.pose(x=860, y=930, s=0.9)
        p['armR'] = K(t, [(-0.4, 92), (1.4, 96), (1.75, 104), (1.95, 70, 'out'), (2.6, 18), (3.4, 6)])
        p['armL'] = K(t, [(-0.4, 6), (2.4, 6), (3.0, 0), (3.6, 4)])
        p['eye_dx'] = K(t, [(-0.4, 12), (1.6, 14), (2.2, 18), (2.9, 16), (3.3, 0)])
        p['eye_dy'] = K(t, [(-0.4, -10), (1.6, -12), (2.2, -18), (2.9, -18), (3.3, 0)])
        p['eye_open'] = E.blink(t, [1.55])
        p['eye_mode'] = 'happy' if t > 3.35 else 'open'
        p['sq'] = K(t, [(2.5, 1.0), (3.0, 1.02), (3.4, 0.955), (3.9, 0.975)])
        p['lean'] = K(t, [(-0.4, -2), (1.8, -3), (2.4, -4), (3.2, 0), (3.6, 2), (3.9, 0.5), (4.2, 1.5)])
        p['hair'] = 1.2 * math.sin(t * 1.4)
        p['skirt'] = 1.5 * math.sin(t * 1.2 + 0.4) + K(t, [(1.9, 0), (2.2, 2), (2.6, 0)])
        return p

    def bird(self, t, tip):
        K = E.K
        rel = 1.85
        if t < rel:
            bx, by = tip[0] + 150 + 10 * math.sin(t * 2.4), tip[1] - 230 + 12 * math.sin(t * 3.1)
            flap = 0.35 * math.sin(t * 6)
        else:
            k = t - rel
            bx = tip[0] + 150 + 10 * math.sin(rel * 2.4) + 330 * k + 40 * k * k
            by = tip[1] - 230 + 12 * math.sin(rel * 3.1) - 210 * k - 30 * k * k
            flap = math.sin(t * 14)
        return bx, by, flap

    def frame(self, t, p=None, trans=False):
        p = dict(self.pose(t) if p is None else p)
        img = self.bg.copy()
        tip = E.arm_tip(p, 'R')
        bx, by, flap = self.bird(t, tip)
        # 线：松手前一端在手上，之后随鸟飘走
        if t < 1.85:
            sx, sy = tip
        else:
            k = E.smooth((t - 1.85) / 0.6)
            sx, sy = E.lerp(tip[0], bx - 60, k), E.lerp(tip[1], by + 160, k)
        sag = 40 if t < 1.85 else 70
        string = f'M{sx:.1f},{sy:.1f} Q{(sx + bx) / 2 + 20:.1f},{(sy + by) / 2 + sag:.1f} {bx:.1f},{by + 18:.1f}'
        wing = 46 * flap
        wy = 50 * (0.55 + 0.45 * abs(flap)) * (1 if flap >= 0 else -0.5)
        bird = (f'<g transform="translate({bx},{by}) scale(2.1) translate({-bx},{-by})">'
                f'<path d="M{bx - 50},{by + 10} L{bx + 46},{by + 4} L{bx + 70},{by - 10} L{bx + 40},{by + 18} Z" fill="#F2EFE6"/>'
                f'<path d="M{bx - 50},{by + 10} L{bx - 66},{by - 16} L{bx - 30},{by + 8} Z" fill="#F2EFE6"/>'
                f'<path d="M{bx - 10},{by + 6} L{bx + 22},{by + 6} L{bx - 6},{by - wy} Z" fill="#DAD6CC"/></g>')
        sv = E.svg_rgba(f'<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">'
                        f'<path d="{string}" fill="none" stroke="#E8E2D2" stroke-width="6"/>{bird}</svg>')
        ox, oy = p['x'] - 860, 0
        ch = fx.pastel(E.render_char(10, p, 'flatshade'), ox, oy, seed=103, density=0.95)
        img = E.over_rgb(img, ch[..., :3], ch[..., 3])
        la = E.line_alpha(10, p, sw=1.35)
        tooth = E.shifted(E.noise(1080, 1920, 2, 104), ox, oy)
        la = la * np.clip(0.55 + 0.6 * tooth, 0, 1)
        img = E.over_rgb(img, E.hexrgb('#141A28'), la * 0.9)
        bp = fx.pastel(sv, 0, 0, seed=105, density=1.0, whiten=0.0)
        img = E.over_rgb(img, bp[..., :3], bp[..., 3])
        return np.clip(img, 0, 1)
