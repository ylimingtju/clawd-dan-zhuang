# -*- coding: utf-8 -*-
"""13《有趣》—— 蜡笔涂鸦。
意象：横格作业纸上，一颗红皮球滚到 Clawd 脚边。她低头歪着身子看，伸手戳一下——球“嘣”地弹起来，
落下时正好砸在她头上，又弹走了；她先一愣，然后笑弯了眼，原地蹦了一下，长辫甩起来。发现、尝试、回应。
画法：角色与场景都是蜡笔：斜向排线填色 + 蜡质颗粒（露出纸色）、抖动的粗线；笔迹每 4 帧换一次，有手绘的轻微“沸腾”。
"""
import math
import numpy as np
import cv2
import engine as E
import fx
from scene_base import Scene


class S13(Scene):
    key = '13'
    filename = '13_有趣'
    style = '蜡笔涂鸦'
    no = 13
    core = 4.0

    def setup(self):
        h, w = 1080, 1920
        pg = fx.paper(h, w, '#FBF8F0', seed=131, fiber=0.0, grain=0.02)
        for y in range(120, h, 54):
            pg[y:y + 2] = pg[y:y + 2] * 0.55 + E.hexrgb('#9FC3E6') * 0.45
        pg[:, 180:183] = pg[:, 180:183] * 0.4 + E.hexrgb('#E58A8A') * 0.6
        self.page = pg
        dood = E.svg_rgba('<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">'
                          '<circle cx="1660" cy="190" r="80" fill="#FFC93C"/>'
                          '<path d="M-20,945 C300,925 700,960 1100,935 C1500,912 1800,950 1950,930 L1950,1100 L-20,1100 Z" fill="#8FCB6B"/>'
                          '<g fill="#F27BA5"><circle cx="300" cy="905" r="20"/><circle cx="420" cy="915" r="16"/><circle cx="1500" cy="900" r="18"/></g>'
                          '<g fill="#FFFFFF" opacity="0.0"></g></svg>')
        self.dood = dood
        rays = np.zeros((h, w), np.float32)
        for k in range(10):
            a = k * 2 * math.pi / 10
            cv2.line(rays, (int(1660 + 105 * math.cos(a)), int(190 + 105 * math.sin(a))),
                     (int(1660 + 150 * math.cos(a)), int(190 + 150 * math.sin(a))), 1.0, 9, cv2.LINE_AA)
        self.rays = rays

    def ball(self, t):
        K = E.K
        if t < 0.9:
            x = K(t, [(-0.4, 1760), (0.9, 1300, 'out')])
            y = 905
        elif t < 1.3:
            x, y = 1300, 905
        elif t < 2.15:                     # 被戳后弹起，落到头顶
            k = (t - 1.3) / 0.85
            x = E.lerp(1300, 985, k)
            y = E.lerp(905, 400, k) - 520 * 4 * k * (1 - k) * 0.6
        elif t < 3.2:                      # 从头顶弹走，向左落地再弹
            k = (t - 2.15) / 1.05
            x = E.lerp(985, 420, k)
            y0 = E.lerp(400, 905, min(1, k * 1.25))
            y = y0 - 300 * math.sin(math.pi * min(1, k * 1.25)) * 0.9 if k < 0.8 else 905 - 80 * math.sin(math.pi * (k - 0.8) / 0.2)
        else:
            x = K(t, [(3.2, 420), (4.4, 330, 'out')])
            y = 905
        spin = -(x - 1760) / 38
        return x, y, spin

    def pose(self, t):
        K = E.K
        p = E.pose(x=960, y=930, s=0.9)
        p['eye_dx'] = K(t, [(-0.4, 6), (0.4, 16), (1.3, 18), (1.6, 6), (2.0, 2), (2.3, -10), (2.9, -16), (3.3, 0)])
        p['eye_dy'] = K(t, [(-0.4, 4), (0.5, 12), (1.3, 14), (1.6, -16), (2.05, -18), (2.3, 6), (2.9, 4), (3.3, 0)])
        p['lean'] = K(t, [(0.3, 0), (0.9, 7), (1.3, 8), (1.5, 0), (2.2, 0), (2.3, 4), (2.6, -2), (3.0, 0)])
        p['dx'] = K(t, [(0.3, 0), (0.9, 24), (1.4, 24), (1.7, 0)])
        p['armR'] = K(t, [(-0.4, 6), (0.9, 10), (1.15, -4), (1.3, 30, 'out'), (1.6, 10), (2.9, 10), (3.1, 90), (3.6, 70), (4.4, 60)])
        p['armL'] = K(t, [(-0.4, 6), (2.9, 6), (3.1, 90), (3.6, 70), (4.4, 60)])
        p['sq'] = K(t, [(2.1, 1.0), (2.2, 0.86), (2.4, 1.05, 'out'), (2.6, 1.0), (2.95, 0.92), (3.1, 1.06), (3.4, 0.95), (3.55, 1.0)])
        p['hop'] = K(t, [(3.0, 0), (3.2, 40, 'out'), (3.4, 0, 'in')])
        p['eye_mode'] = 'happy' if 2.75 < t < 4.0 else 'open'
        p['eye_open'] = K(t, [(2.2, 1.0), (2.25, 1.0)])
        # 长辫在 back() 里；用头发摆动带动
        p['hair'] = K(t, [(2.1, 0), (2.25, 8), (2.5, -6), (2.75, 3), (3.0, 0), (3.2, -9), (3.45, 7), (3.7, -3), (4.0, 0)])
        p['skirt'] = -0.6 * p['lean'] + K(t, [(3.0, 0), (3.2, 4), (3.45, -3), (3.7, 0)])
        return p

    def frame(self, t, p=None, trans=False):
        p = dict(self.pose(t) if p is None else p)
        boil = int((t + 0.4) * 30 / 4) % 3
        img = self.page.copy()
        d = fx.crayon_fill(self.dood, 0, 0, seed=140, boil=boil)
        img = E.over_rgb(img, d[..., :3], d[..., 3])
        img = E.over_rgb(img, E.hexrgb('#F5A623'), fx.crayon_line(self.rays, 0, 0, 141, boil) * 0.9)
        bx, by, spin = self.ball(t)
        r = 46
        # 球落地时压扁
        sqb = 1 - 0.2 * max(0, 1 - abs(by - 905) / 20) * (abs(by - 905) < 20 and 1.3 < t < 3.2)
        bsv = E.svg_rgba(f'<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">'
                         f'<g transform="translate({bx:.1f},{by - r * sqb:.1f}) scale({1 / max(sqb, 0.6):.3f},{sqb:.3f}) rotate({math.degrees(spin):.1f})">'
                         f'<circle r="{r}" fill="#E8453C"/><path d="M{-r},0 Q0,{-r * 0.6} {r},0" fill="none" stroke="#FFFFFF" stroke-width="12"/></g></svg>')
        ox, oy = p['x'] + p['dx'] * p['s'] - 960, 0
        ch = fx.crayon_fill(E.render_char(13, p, 'flat'), ox, oy, seed=132, boil=boil)
        a = E.render_char(13, p, 'flat')[..., 3]
        img = E.over_rgb(img, E.hexrgb('#FBF8F0'), a * 0.85)          # 先垫纸色，避免背景透出
        img = E.over_rgb(img, ch[..., :3], ch[..., 3])
        la = fx.crayon_line(E.line_alpha(13, p, sw=1.6), ox, oy, 134, boil)
        img = E.over_rgb(img, E.hexrgb('#2D2A3A'), la)
        bf = fx.crayon_fill(bsv, 0, 0, seed=142, boil=boil)
        img = E.over_rgb(img, E.hexrgb('#FBF8F0'), bsv[..., 3] * 0.8)
        img = E.over_rgb(img, bf[..., :3], bf[..., 3])
        bl = cv2.morphologyEx(bsv[..., 3], cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8))
        img = E.over_rgb(img, E.hexrgb('#2D2A3A'), fx.crayon_line(bl, 0, 0, 143, boil))
        # 撞头时的“嘣”线
        if 2.12 < t < 2.5:
            k = (t - 2.12) / 0.38
            m = np.zeros((1080, 1920), np.float32)
            hx, hy = 985, 400
            for j in range(5):
                ang = math.radians(200 + j * 35)
                cv2.line(m, (int(hx + 70 * math.cos(ang)), int(hy + 70 * math.sin(ang))),
                         (int(hx + (90 + 50 * k) * math.cos(ang)), int(hy + (90 + 50 * k) * math.sin(ang))), 1.0, 7, cv2.LINE_AA)
            img = E.over_rgb(img, E.hexrgb('#2D2A3A'), m * (1 - k))
        return np.clip(img, 0, 1)
