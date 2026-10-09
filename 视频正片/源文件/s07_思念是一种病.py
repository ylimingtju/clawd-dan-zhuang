# -*- coding: utf-8 -*-
"""07《思念是一种病》—— 浮世绘木刻版画。
意象：夕照下的海浪一排排向前涌。Clawd 望着远岛上那盏小灯笼，抬起戴手套的右手，隔着海慢慢挥了挥；
远处的灯笼晃一晃、亮起来回应——距离很远，联系还在。
画法：角色用平涂矿物色（普鲁士蓝、朱、墨）+ 粗刻线（带刀痕抖动）+ 自上而下的晕色（bokashi）+ 木纹肌理 + 套版错位；背景是卷浪与天空色带。
"""
import math
import numpy as np
import cv2
import engine as E
import fx
from scene_base import Scene

UKI = {'#2C3EB2': '#23408E', '#1B2780': '#172C63', '#5B6EDB': '#3B5BA8', '#D97757': '#D9774F',
       '#B65C40': '#B3583C', '#2B1F1C': '#201A1A', '#1B1311': '#201A1A', '#5A4540': '#3A2E2B',
       '#2A2F55': '#1E2244'}


class S07(Scene):
    key = '07'
    filename = '07_思念是一种病'
    style = '浮世绘木刻'
    no = 7
    core = 4.0

    def setup(self):
        h, w = 1080, 1920
        sky = fx.paper(h, w, '#EFE3C8', seed=77, fiber=0.015, grain=0.03)
        # 天空：顶部普鲁士蓝晕色带、地平线一抹橙红
        top = np.clip(1 - np.arange(h, dtype=np.float32) / 260, 0, 1)[:, None]
        sky = E.over_rgb(sky, E.hexrgb('#23408E'), top * 0.85)
        hor = np.exp(-((np.arange(h, dtype=np.float32) - 560) / 90) ** 2)[:, None]
        sky = E.over_rgb(sky, E.hexrgb('#E58A5A'), hor * 0.45)
        # 落日
        sun = (E.radial(1240, 560, 120) > 0).astype(np.float32)
        sky = E.over_rgb(sky, E.hexrgb('#D8432F'), sun * 0.9)
        # 远岛 + 小屋
        isl = np.zeros((h, w), np.float32)
        cv2.ellipse(isl, (1640, 600), (230, 46), 0, 180, 360, 1.0, -1)
        cv2.rectangle(isl, (1600, 520), (1660, 562), 1.0, -1)
        tri = np.array([[1588, 524], [1630, 488], [1672, 524]], np.int32)
        cv2.fillConvexPoly(isl, tri, 1.0)
        sky = E.over_rgb(sky, E.hexrgb('#3B4A5E'), isl)
        sky = E.over_rgb(sky, E.hexrgb('#E9C46A'), (E.radial(1630, 543, 9) > 0).astype(np.float32))
        self.sky = sky
        self.paper = fx.paper(h, w, '#EFE3C8', seed=78, fiber=0.01, grain=0.03)
        self.grain = fx.woodgrain(h, w, 79)
        shore = E.svg_rgba('<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">'
                           '<path d="M-20,1100 L-20,995 C120,960 260,975 380,958 C520,940 720,948 900,962 C1000,970 1080,985 1150,1010 '
                           'C1200,1030 1230,1070 1240,1100 Z" fill="#B88A55" stroke="#16152A" stroke-width="6"/>'
                           '<path d="M120,1010 q80,-14 160,-6 M520,990 q90,-12 180,-2 M820,1000 q70,-6 140,8" fill="none" stroke="#7A5530" stroke-width="5"/>'
                           '</svg>')
        g = fx.woodgrain(h, w, 80)
        shore[..., :3] *= (1 - 0.12 * (g[..., None] - 0.5) * 2)
        self.shore = shore

    def waves(self, t):
        """几排卷浪：每排沿横向流动，浪头带白色浪爪。"""
        svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">']
        rows = [(600, 26, 70, '#3B5BA8', 22, 0.0), (680, 36, 100, '#2C4A93', 30, 1.0),
                (790, 48, 140, '#23408E', 42, 2.0), (930, 62, 190, '#1B3270', 58, 3.0)]
        for (y0, amp, wl, col, spd, ph) in rows:
            off = (spd * t) % wl
            d = f'M-200,1100 L-200,{y0}'
            x = -200 - off
            foam = []
            while x < 2120:
                d += f' Q{x + wl * 0.25},{y0 - amp} {x + wl * 0.5},{y0} Q{x + wl * 0.75},{y0 + amp * 0.35} {x + wl},{y0}'
                foam.append((x + wl * 0.25, y0 - amp * 0.62))
                x += wl
            d += ' L2120,1100 Z'
            svg.append(f'<path d="{d}" fill="{col}" stroke="#141A33" stroke-width="5"/>')
            for (fx_, fy_) in foam:
                svg.append(f'<path d="M{fx_ - amp * 0.5},{fy_ + amp * 0.3} q{amp * 0.3},{-amp * 0.5} {amp * 0.7},{-amp * 0.2} '
                           f'q{-amp * 0.2},{amp * 0.1} {-amp * 0.25},{amp * 0.35}" fill="#F3ECDD" stroke="#141A33" stroke-width="3"/>')
        svg.append('</svg>')
        return E.svg_rgba(''.join(svg))

    def pose(self, t):
        K = E.K
        p = E.pose(x=720, y=980, s=0.88)
        wave = math.sin((t - 0.9) * 2 * math.pi / 0.62) * E.smooth((t - 0.9) / 0.25) * (1 - E.smooth((t - 2.25) / 0.3))
        p['armR'] = K(t, [(-0.4, 14), (0.4, 16), (0.95, 108, 'out'), (2.3, 104), (2.9, 40), (3.5, 30)]) + 14 * wave
        p['armL'] = K(t, [(-0.4, 10), (2.2, 10), (2.5, 2), (3.0, 16)]) + 3 * math.sin(t * 2)
        p['lean'] = K(t, [(-0.4, -1), (1.0, -4), (2.2, -4), (2.6, 1), (3.2, -1)]) + 1.2 * wave
        p['sq'] = K(t, [(2.4, 1.0), (2.6, 0.97), (2.85, 1.03), (3.1, 1.0)])
        p['hop'] = K(t, [(2.55, 0), (2.75, 10, 'out'), (2.95, 0, 'in')])
        p['eye_dx'] = K(t, [(-0.4, 10), (1.0, 16), (2.6, 16), (3.0, 12)])
        p['eye_dy'] = K(t, [(-0.4, -2), (1.2, -6), (2.6, -6), (3.0, -2)])
        p['eye_open'] = E.blink(t, [0.6, 3.6])
        p['eye_mode'] = 'happy' if 2.6 < t < 3.7 else 'open'
        wind = math.sin(t * 2.3)
        p['hat'] = 3 * wind + K(t, [(2.2, 0), (2.5, -4), (2.9, 0)])
        p['skirt'] = -3 * wind - 2
        p['hair'] = -1.5 * wind
        return p

    def frame(self, t, p=None, trans=False):
        p = dict(self.pose(t) if p is None else p)
        img = self.sky.copy()
        # 灯笼回应：被拉后晃动、变亮
        swing = 8 * math.sin((t - 2.2) * 9) * math.exp(-(t - 2.2) * 1.6) if t > 2.2 else 0
        glow = E.smooth((t - 2.2) / 0.4)
        lx, ly = 1630 + swing, 543
        img = img + E.hexrgb('#FFB347') * (E.radial(lx, ly, 70 + 60 * glow) ** 2 * (0.15 + 0.6 * glow))[..., None]
        wv = self.waves(t)
        img = E.over(img, wv)
        img = E.over(img, self.shore)
        # 角色：平涂矿物色 + 晕色 + 木纹 + 粗刻线
        ox, oy = p['x'] - 720, 0
        flat = E.render_char(7, p, 'flat')
        col = fx.palette_map(flat[..., :3], UKI) if False else flat[..., :3]
        a = flat[..., 3]
        rows = np.arange(1080, dtype=np.float32)[:, None]
        bok = np.clip((rows - 600) / 420, 0, 1)
        col = col * (1 - 0.28 * bok[..., None])
        col = col * (1 - 0.07 * (self.grain[..., None] - 0.5) * 2)
        col = E.shifted(col, 2, 1)
        img = E.over_rgb(img, col, E.shifted(a, 2, 1))
        la = fx.carve_lines(E.line_alpha(7, p, sw=1.7), ox, oy)
        img = E.over_rgb(img, E.hexrgb('#16152A'), la)
        img = img * (self.paper / E.hexrgb('#EFE3C8').mean()) ** 0.5
        return np.clip(img, 0, 1)
