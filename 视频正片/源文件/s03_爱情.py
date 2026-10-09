# -*- coding: utf-8 -*-
"""03《爱情》—— Riso 网点印刷。
意象：一只心形气球从右上飘来，Clawd 前倾伸手去够，气球一晃躲开，Clawd 缩手、垂眼犹豫；
气球的线又慢慢落到手边，Clawd 接住，笑着左右摇摆——甜蜜里带着不安。
画法：角色与背景分色为粉 / 蓝 / 黄 / 黑四个印版，各版网点角度不同并有套色错位；墨线作为实地黑版；一拍二（15fps）。
"""
import math
import numpy as np
import cv2
import engine as E
import fx
from scene_base import Scene

PAPER = '#F5EFE4'


class S03(Scene):
    key = '03'
    filename = '03_爱情'
    style = 'Riso 网点印刷'
    no = 3
    core = 4.0
    step = 2

    def setup(self):
        h, w = 1080, 1920
        bg = np.ones((h, w, 3), np.float32)
        # 印刷背景：粉黄渐变天空（大网点）、蓝色地面带、零星小心形
        yy = np.linspace(0, 1, h, dtype=np.float32)[:, None] * np.ones((1, w), np.float32)
        tone = np.dstack([np.ones((h, w), np.float32),
                          1 - 0.22 * (1 - yy) - 0.05,
                          1 - 0.30 * yy])
        tone[860:] = E.hexrgb('#B9C9EA')
        self.bg_print = fx.riso_print(tone, cell=14)
        self.paper = fx.paper(h, w, PAPER, seed=33, fiber=0.01, grain=0.03)
        rng = np.random.default_rng(303)
        self.hearts = [(rng.uniform(100, 1820), rng.uniform(80, 760), rng.uniform(14, 26), rng.uniform(0, 6.28)) for _ in range(9)]

    def heart_path(self, cx, cy, r):
        return (f'M{cx},{cy + r * 0.9} C{cx - r * 1.6},{cy - r * 0.2} {cx - r * 0.9},{cy - r * 1.4} {cx},{cy - r * 0.5} '
                f'C{cx + r * 0.9},{cy - r * 1.4} {cx + r * 1.6},{cy - r * 0.2} {cx},{cy + r * 0.9} Z')

    def pose(self, t):
        K = E.K
        p = E.pose(x=900, y=900, s=0.95)
        sway = math.sin(t * 2 * math.pi / 1.6)
        hold = E.smooth((t - 2.9) / 0.4)
        p['lean'] = K(t, [(-0.4, 0), (0.7, 0), (1.0, 2.5), (1.5, -6), (1.9, -6.5), (2.2, 3), (2.7, 0)]) + 4.0 * sway * hold
        p['dx'] = K(t, [(0.9, 0), (1.5, 26), (2.0, 26), (2.4, -6), (2.9, 0)]) + 14 * sway * hold
        p['sq'] = K(t, [(0.9, 1.0), (1.05, 0.97), (1.5, 1.03), (2.0, 1.0), (2.2, 0.96), (2.6, 1.0)]) + 0.012 * math.sin(t * 7.8) * hold
        p['armR'] = K(t, [(-0.4, 6), (1.0, 6), (1.55, 72, 'back'), (1.95, 66), (2.3, 2), (2.9, 40), (4.4, 46)])
        p['armL'] = K(t, [(-0.4, 6), (1.9, 6), (2.2, -18), (2.8, -14), (3.2, 18), (4.4, 22)]) + 6 * sway * hold
        p['eye_dx'] = K(t, [(-0.4, 4), (0.4, 14), (1.5, 16), (2.05, -6), (2.5, -10), (2.9, 10), (3.4, 4)])
        p['eye_dy'] = K(t, [(-0.4, -4), (0.6, -14), (1.6, -16), (2.05, 8), (2.6, 10), (2.9, -6), (3.4, 0)])
        happy = 2.95 < t < 4.1
        p['eye_mode'] = 'happy' if happy else 'open'
        p['eye_open'] = E.blink(t, [0.2, 2.15])
        p['hair'] = -1.2 * p['lean'] * 0.5
        p['skirt'] = -0.8 * p['lean'] + 1.5 * math.sin(t * 3.2)
        return p

    def balloon(self, t, p):
        K = E.K
        tip = E.arm_tip(p, 'R')
        bx = K(t, [(-0.4, 1700), (0.6, 1330), (1.5, 1300), (1.95, 1420, 'out'), (2.5, 1360), (3.0, tip[0] + 40), (4.4, tip[0] + 50)])
        by = K(t, [(-0.4, 120), (0.6, 300), (1.5, 330), (1.95, 230, 'out'), (2.5, 300), (3.0, tip[1] - 300), (4.4, tip[1] - 300)])
        by += 10 * math.sin(t * 3.1)
        bx = bx if t < 3.0 else tip[0] + 40 + 16 * math.sin(t * 2.4)
        if t >= 3.0:
            by = tip[1] - 300 + 8 * math.sin(t * 3.1)
        # 线的下端：未接住时自由下垂，接住后挂在右手末端
        if t < 2.85:
            ex, ey = bx - 20 + 20 * math.sin(t * 2), by + 260
        else:
            k = E.smooth((t - 2.85) / 0.2)
            ex, ey = E.lerp(bx - 20, tip[0], k), E.lerp(by + 260, tip[1], k)
        return bx, by, ex, ey

    def frame(self, t, p=None, trans=False):
        p = dict(self.pose(t) if p is None else p)
        if trans and t > self.core:
            # 转场中 Clawd 离开：气球松手，留在原地慢慢飘高，线头自由下垂
            bx, by, _, _ = self.balloon(self.core, self.pose(self.core))
            up = t - self.core
            bx, by = bx + 160 * up, by - 420 * up
            ex, ey = bx - 20 + 15 * math.sin(t * 3), by + 250
        else:
            bx, by, ex, ey = self.balloon(t, p)
        # 角色 + 气球作为一层印刷
        lay = E.render_char(3, p, 'flat')
        # 气球画进同一层（简单 SVG）
        bal = E.svg_rgba(f'<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">'
                         f'<path d="M{bx},{by + 34} Q{(bx + ex) / 2 + 30},{(by + ey) / 2} {ex},{ey}" fill="none" stroke="#1D1B22" stroke-width="3"/>'
                         f'<path d="{self.heart_path(bx, by, 40)}" fill="#F0507F" stroke="#1D1B22" stroke-width="5"/>'
                         f'<path d="M{bx - 22},{by - 18} q8,-10 16,-6" fill="none" stroke="#FFFFFF" stroke-width="6" stroke-linecap="round"/></svg>')
        hearts = '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">'
        for (hx, hy, r, ph) in self.hearts:
            hearts += f'<path d="{self.heart_path(hx + 10 * math.sin(t * 0.9 + ph), hy - 12 * (t + 0.4), r)}" fill="#F7A6C8"/>'
        hearts += '</svg>'
        hs = E.svg_rgba(hearts)
        ox, oy = p['x'] + p['dx'] * p['s'] - 900, 0
        la = E.line_alpha(3, p, sw=1.3)
        # 角色印刷（网格随角色平移，避免网点在身上游动）
        cprint = fx.riso_print(lay[..., :3], cell=7, ox=ox, oy=oy, solid_black=la, kmax=0.62)
        bg = self.bg_print.copy()
        bg = E.over_rgb(bg, fx.riso_print(hs[..., :3] * hs[..., 3:] + (1 - hs[..., 3:]), cell=7), hs[..., 3] * 0.9)
        a = np.maximum(lay[..., 3], la)
        a_reg = E.shifted(a, 1, 0)
        img = E.over_rgb(bg, cprint, a_reg)
        bprint = fx.riso_print(bal[..., :3], cell=7, solid_black=(E.lum(bal[..., :3]) < 0.2) * bal[..., 3])
        img = E.over_rgb(img, bprint, bal[..., 3])
        return np.clip(img * self.paper / E.hexrgb(PAPER).mean() * 0.98, 0, 1)
