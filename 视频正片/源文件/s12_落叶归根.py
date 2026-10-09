# -*- coding: utf-8 -*-
"""12《落叶归根》—— 皮影戏。
意象：暖黄的幕布后面，Clawd 从远处一路走来：离幕布远时影子模糊、发淡，越走越近越清晰——
最后停在一座窗口亮着灯的小屋前，抬眼望着窗，伸出一只手；叶子一片片飘落。从远行到靠近。
画法：角色是透光的染色皮革（被背光照透的色彩、深色皮边轮廓），手臂关节有铆钉，
三根操纵杆从下方伸上来；场景同为皮影：镂空窗格的小屋、剪影树枝与落叶；远近用虚实与大小表现。
"""
import math
import numpy as np
import cv2
import engine as E
import fx
from scene_base import Scene


def carve_pattern(seed=12):
    """镂刻纹样（设计坐标）：成排的小圆孔与月牙，随角色姿势一起变换。"""
    rng = np.random.default_rng(seed)
    out = []
    for j, y in enumerate(range(640, 1110, 34)):
        for x in range(480 + (17 if j % 2 else 0), 1200, 34):
            if rng.random() < 0.5:
                out.append(f'<circle cx="{x}" cy="{y}" r="5.5"/>')
            else:
                out.append(f'<path d="M{x - 8},{y} a8,8 0 0 1 16,0 a8,5 0 0 0 -16,0 Z"/>')
    return ''.join(out)


class S12(Scene):
    key = '12'
    filename = '12_落叶归根'
    style = '皮影戏'
    no = 12
    core = 4.0

    def setup(self):
        h, w = 1080, 1920
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        glow = np.clip(1 - np.hypot((xx - 980) / 1300, (yy - 470) / 820), 0, 1) ** 0.9
        screen = E.hexrgb('#B26E34') * (1 - glow[..., None]) + E.hexrgb('#F6DCA2') * glow[..., None]
        screen *= (1 - 0.05 * (E.noise(h, w, 3, 121)[..., None] - 0.5))
        self.light = screen.copy()
        # 场景皮影：小屋（窗格镂空）、树枝
        sc = E.svg_rgba('<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">'
                        '<path d="M1380,940 L1380,640 L1520,520 L1660,640 L1660,940 Z" fill="#3A1E12"/>'
                        '<path d="M1360,650 L1520,505 L1680,650" fill="none" stroke="#2A140B" stroke-width="22"/>'
                        '<rect x="1450" y="680" width="140" height="120" fill="#000" />'
                        '<path d="M-20,140 C200,120 380,170 520,250 M180,150 C200,230 170,320 120,380 M360,190 C380,260 360,330 330,380 M470,230 C520,300 520,360 500,420"'
                        ' fill="none" stroke="#2A140B" stroke-width="16" stroke-linecap="round"/>'
                        '</svg>')
        win = np.zeros((h, w), np.float32)
        cv2.rectangle(win, (1450, 680), (1590, 800), 1.0, -1)
        for x in range(1450, 1600, 35):
            cv2.line(win, (x, 680), (x, 800), 0.0, 6)
        for y in range(680, 810, 40):
            cv2.line(win, (1450, y), (1590, y), 0.0, 6)
        self.win = win
        self.scene = sc
        rng = np.random.default_rng(122)
        self.leaves = [(rng.uniform(80, 1500), rng.uniform(-200, 600), rng.uniform(0.7, 1.2), rng.uniform(0, 6.28)) for _ in range(9)]
        self.pattern = carve_pattern()
        # 木框
        frame = np.zeros((h, w), np.float32)
        frame[:34] = 1
        frame[1046:] = 1
        self.frame_m = frame

    def pose(self, t):
        K = E.K
        arrive = E.smooth(E.seg(t, -0.4, 2.5))
        p = E.pose(x=E.lerp(470, 980, arrive), y=E.lerp(935, 945, arrive), s=E.lerp(1.0, 0.80, arrive))
        walking = t < 2.5
        ph = (t + 0.4) / 0.42
        if walking:
            k = abs(math.sin(math.pi * ph))
            p['hop'] = 9 * k
            side = 1 if int(ph) % 2 == 0 else -1
            p['legs'] = (12 * k * (side > 0), 0, 12 * k * (side < 0), 0)
            p['armL'] = 10 + 16 * side * k
            p['armR'] = 10 - 16 * side * k
            p['lean'] = -2 + 1.5 * side * k
        else:
            p['sq'] = K(t, [(2.5, 0.96), (2.7, 1.0)])
            p['armR'] = K(t, [(2.5, 10), (3.0, 10), (3.5, 58), (4.4, 62)])
            p['armL'] = K(t, [(2.5, 10), (4.4, 8)])
            p['lean'] = K(t, [(2.5, -2), (3.0, 0), (3.5, -3)])
        p['eye_dx'] = K(t, [(-0.4, 8), (2.4, 8), (2.9, 16)])
        p['eye_dy'] = K(t, [(-0.4, 0), (2.6, 0), (3.0, -8)])
        p['eye_open'] = E.blink(t, [1.2, 3.9])
        p['hair'] = -2 * p['lean']
        p['skirt'] = 2.5 * math.sin(math.pi * ph) * walking
        return p

    def frame(self, t, p=None, trans=False):
        p = dict(self.pose(t) if p is None else p)
        near = E.smooth(E.seg(t, -0.4, 2.5))
        img = self.light.copy()
        warm = E.smooth((t - 2.8) / 0.8)
        img = E.over_rgb(img, E.hexrgb('#24110A'), self.scene[..., 3] * 0.92)
        wl = E.hexrgb('#FFE08A') * (0.65 + 0.35 * warm)
        img = E.over_rgb(img, wl, self.win)
        img = img + E.hexrgb('#FFC86A') * (E.radial(1520, 740, 260) ** 2 * 0.25 * warm)[..., None]
        # 落叶（剪影小叶片）
        for (x0, y0, sc, ph) in self.leaves:
            y = (y0 + 120 * (t + 0.4) * sc) % 1150 - 60
            x = x0 + 40 * math.sin((t + ph) * 1.6)
            ang = 30 * math.sin((t + ph) * 2.2)
            leaf = cv2.ellipse2Poly((int(x), int(y)), (int(18 * sc), int(8 * sc)), int(ang), 0, 360, 20)
            m = np.zeros((1080, 1920), np.float32)
            cv2.fillConvexPoly(m, leaf, 1.0)
            img = E.over_rgb(img, E.hexrgb('#4A2414'), m * 0.85)
        # 角色：透光皮革 + 镂刻 + 铆钉 + 操纵杆
        flat = E.render_char(12, p, 'flat')
        a = flat[..., 3]
        leather = np.clip(flat[..., :3] * 1.25, 0, 1) ** 1.2
        leather = leather * 0.55 + leather * self.light * 0.65
        # （镂刻圆孔已去掉：在角色身上读起来像意义不明的斑点）
        la = E.line_alpha(12, p, sw=1.5)
        leather = leather * (1 - la[..., None]) + E.hexrgb('#1E0E08') * la[..., None]
        lay = np.dstack([leather, np.maximum(a, la)])
        # 操纵杆
        rods = np.zeros((1080, 1920), np.float32)
        for side in ('L', 'R'):
            tx, ty = E.arm_tip(p, side)
            cv2.line(rods, (int(tx), int(ty)), (int(tx + (40 if side == 'R' else -40)), 1080), 1.0, 4, cv2.LINE_AA)
        bx, by = E.to_screen(p, (800, 900))
        cv2.line(rods, (int(bx), int(by)), (int(bx + 10), 1080), 1.0, 5, cv2.LINE_AA)
        # 远处：模糊、发淡；近处：清晰
        blur_r = 7 * (1 - near)
        if blur_r > 0.3:
            lay = E.blur(lay, blur_r)
            rods = E.blur(rods, blur_r)
        lay[..., 3] *= 0.72 + 0.28 * near
        img = E.over_rgb(img, E.hexrgb('#2A140B'), rods * (0.5 + 0.4 * near))
        img = E.over(img, lay)
        # 铆钉
        for side in ('L', 'R'):
            E.apply_pose_state(p)
            jx, jy = E.to_screen(p, (582 if side == 'L' else 1002, 842 if side == 'L' else 826))
            if near > 0.6:
                fx.soft_disc(img, jx, jy, 9 * p['s'], E.hexrgb('#C79A52'), 0.95 * near, 0.8)
        img = E.over_rgb(img, E.hexrgb('#3A2214'), self.frame_m)
        return np.clip(img, 0, 1)
