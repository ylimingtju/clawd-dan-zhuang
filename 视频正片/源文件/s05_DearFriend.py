# -*- coding: utf-8 -*-
"""05《Dear Friend》—— 撕纸拼贴定格动画。
意象：一颗被撕成两半的黄纸星星分别从左右飘来。Clawd 左看、右看，举起双臂把它们“招”到一起；
两半在头顶对上，一条半透明纸胶带“啪”地贴住裂缝，星星亮起，Clawd 开心地踮脚——破碎、修补、继续追寻。
画法：角色每个色块都是撕下来的纸片（撕裂边缘 + 白色纤维毛边 + 纸纹），色块之间有纸边与投影，整体投影落在卡纸上；一拍三（10fps）定格。
"""
import math
import numpy as np
import cv2
import engine as E
import fx
from scene_base import Scene


def star_pts(cx, cy, R, r, rot=-90):
    out = []
    for i in range(10):
        a = math.radians(rot + i * 36)
        rr = R if i % 2 == 0 else r
        out.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return out


class S05(Scene):
    key = '05'
    filename = '05_Dear Friend'
    style = '撕纸拼贴定格'
    no = 5
    core = 4.0
    step = 3

    def setup(self):
        h, w = 1080, 1920
        board = fx.paper(h, w, '#C9A27A', seed=55, fiber=0.03, grain=0.05)
        lay = np.zeros((h, w, 4), np.float32)
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">'
               '<path d="M-20,-20 L1940,-20 L1940,560 C1700,600 1500,540 1250,585 C1000,630 700,560 420,600 C250,625 80,585 -20,610 Z" fill="#BFD7E6"/>'
               '<path d="M1380,140 C1500,120 1640,150 1700,240 C1710,330 1560,360 1460,330 C1360,300 1320,200 1380,140 Z" fill="#F4DFA6"/>'
               '<path d="M-20,905 C300,880 700,925 1000,900 C1300,875 1650,920 1940,895 L1940,1100 L-20,1100 Z" fill="#E9D9BF"/>'
               '<path d="M160,170 L420,150 L430,330 L170,345 Z" fill="#F6F1E6"/>'
               '<path d="M185,190 L405,175 L412,312 L192,322 Z" fill="#E8C8C0"/></svg>')
        lay = E.svg_rgba(svg)
        lay = fx.torn_paper(lay, 0, 0, seed=500, rim=6)
        board = fx.drop_shadow(board, lay[..., 3], 6, 8, 6, 0.3)
        board = E.over(board, lay)
        # 胶带
        tape = np.zeros((h, w), np.float32)
        for (cx, cy, ang) in [(170, 165, -20), (425, 150, 25), (1840, 120, 30)]:
            box = cv2.boxPoints(((cx, cy), (110, 30), ang)).astype(np.int32)
            cv2.fillConvexPoly(tape, box, 1.0)
        board = E.over_rgb(board, E.hexrgb('#EFE6C8'), tape * 0.7)
        self.bg = board

    def star_half(self, cx, cy, side, rot, R=112, r=46):
        """左半 / 右半纸星：外轮廓取星形一侧的顶点，中线是锯齿撕口。"""
        pts = star_pts(0, 0, R, r)
        rng = np.random.default_rng(77)
        ys = np.linspace(-R, r, 13)
        tear = [(5 * rng.uniform(-1, 1) if 0 < k < 12 else 0.0, y) for k, y in enumerate(ys)]
        if side > 0:
            poly = [pts[i] for i in (0, 1, 2, 3, 4, 5)] + tear[::-1][1:-1]
        else:
            poly = [pts[i] for i in (5, 6, 7, 8, 9, 0)] + tear[1:-1]
        gap = 3 * side
        c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        pp = [(cx + (x + gap) * c - y * s, cy + (x + gap) * s + y * c) for (x, y) in poly]
        return 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in pp) + ' Z'

    def pose(self, t):
        K = E.K
        p = E.pose(x=960, y=900, s=0.92)
        p['eye_dx'] = K(t, [(-0.4, 0), (0.4, -16), (1.0, -16), (1.3, 16), (1.8, 16), (2.2, 0)])
        p['eye_dy'] = K(t, [(-0.4, -8), (0.4, -14), (1.8, -14), (2.3, -18), (2.8, -10)])
        p['armL'] = K(t, [(-0.4, 0), (1.5, 0), (2.0, 110, 'back'), (2.4, 80), (2.9, 70), (4.4, 60)])
        p['armR'] = K(t, [(-0.4, 0), (1.6, 0), (2.1, 110, 'back'), (2.4, 80), (2.9, 70), (4.4, 60)])
        p['sq'] = K(t, [(1.4, 1.0), (1.6, 0.94), (1.9, 1.04), (2.2, 1.0), (2.55, 0.92), (2.75, 1.05), (3.0, 1.0)])
        p['hop'] = K(t, [(2.6, 0), (2.8, 26, 'out'), (3.0, 0, 'in')])
        p['lean'] = K(t, [(-0.4, 0), (0.4, 3), (1.0, 3), (1.3, -3), (1.8, -3), (2.2, 0)]) + 2 * math.sin(t * 3) * E.seg(t, 3.0, 3.4)
        p['eye_mode'] = 'happy' if 2.6 < t < 4.0 else 'open'
        p['hair'] = 1.2 * math.sin(t * 2.2)
        p['skirt'] = 1.8 * math.sin(t * 2.4 + 0.5)
        return p

    def frame(self, t, p=None, trans=False):
        rng = np.random.default_rng(int(round((t + 10) * 100)))
        jit = (rng.uniform(-1.2, 1.2), rng.uniform(-1.2, 1.2))       # 定格手作抖动（每张一个固定量）
        p = dict(self.pose(t) if p is None else p)
        p['x'] += jit[0]
        p['y'] += jit[1]
        img = self.bg.copy()
        K = E.K
        meet = 2.3
        lx = K(t, [(-0.4, 470), (meet, 960, 'io')])
        ly = K(t, [(-0.4, 300), (meet, 215, 'io')]) + 10 * math.sin(t * 2.5) * (t < meet)
        rx = K(t, [(-0.4, 1460), (meet, 960, 'io')])
        ry = K(t, [(-0.4, 340), (meet, 215, 'io')]) + 10 * math.sin(t * 2.2 + 1) * (t < meet)
        lr = K(t, [(-0.4, -28), (meet, 0)])
        rr = K(t, [(-0.4, 24), (meet, 0)])
        bounce = 10 * math.sin(math.pi * E.seg(t, meet, meet + 0.3))
        glow = E.smooth((t - 2.6) / 0.5)
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">'
        if glow > 0:                                               # 星星亮起：纸条光芒
            for i in range(12):
                a = math.radians(i * 30 + 8)
                r0, r1 = 130, 130 + 90 * glow
                svg += (f'<path d="M{960 + r0 * math.cos(a - 0.05):.1f},{215 + r0 * math.sin(a - 0.05):.1f} '
                        f'L{960 + r1 * math.cos(a):.1f},{215 + r1 * math.sin(a):.1f} '
                        f'L{960 + r0 * math.cos(a + 0.05):.1f},{215 + r0 * math.sin(a + 0.05):.1f} Z" fill="#FBE7A1"/>')
        svg += f'<path d="{self.star_half(lx, ly - bounce, -1, lr)}" fill="#F5C93E"/>'
        svg += f'<path d="{self.star_half(rx, ry - bounce, 1, rr)}" fill="#EDBB2F"/>'
        svg += '</svg>'
        st = fx.torn_paper(E.svg_rgba(svg), 0, 0, seed=505, rim=5)
        ch = fx.torn_paper(E.render_char(5, p, 'flat'), p['x'] - 960, p['y'] - 900, seed=52, rim=5)
        img = fx.drop_shadow(img, ch[..., 3], 10, 12, 7, 0.38)
        img = E.over(img, ch)
        img = fx.drop_shadow(img, st[..., 3], 8, 10, 6, 0.32)
        img = E.over(img, st)
        if t > meet + 0.2:                                         # 纸胶带贴住裂缝
            k = E.ease_back((t - meet - 0.2) / 0.15)
            tape = np.zeros((1080, 1920), np.float32)
            box = cv2.boxPoints(((960, 205 - bounce), (36, 190 * min(1, k)), 8)).astype(np.int32)
            cv2.fillConvexPoly(tape, box, 1.0)
            img = E.over_rgb(img, E.hexrgb('#F4B6C8'), tape * 0.62)
        return np.clip(img, 0, 1)
