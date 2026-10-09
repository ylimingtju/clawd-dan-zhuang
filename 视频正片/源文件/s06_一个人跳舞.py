# -*- coding: utf-8 -*-
"""06《一个人跳舞》—— 霓虹灯管。
意象：深夜砖墙下，Clawd 闭眼摇摆、换重心踩点、手臂交替摆动，转半圈后抬手慢摇；湿地面映出灯光。
画法：角色的轮廓线变成霓虹灯管（颜色取自相邻服装色块，白色灯芯 + 多层辉光），身体与服装压暗成夜色剪影，眼睛保持深色只亮外圈；
背景砖墙与月亮、星星灯牌同样是灯管语言；逐帧 30fps。
"""
import math
import numpy as np
import cv2
import engine as E
import fx
from scene_base import Scene

# 服装色 → 灯管色
NEON = {'#2D3448': '#3D8BFF', '#1C2132': '#3D8BFF', '#9AA5BF': '#9FD3FF', '#D9B25C': '#FFD34F',
        '#D97757': '#FF8A4F', '#B65C40': '#FF8A4F', '#2B1F1C': '#C17BFF', '#1B1311': '#C17BFF',
        '#5A4540': '#C17BFF'}


class S06(Scene):
    key = '06'
    filename = '06_一个人跳舞'
    style = '霓虹灯管'
    no = 6
    core = 4.0

    def setup(self):
        h, w = 1080, 1920
        wall = E.vgrad('#1A1430', '#120E22')
        # 砖缝
        m = np.zeros((h, w), np.float32)
        for row, y in enumerate(range(0, 900, 44)):
            cv2.line(m, (0, y), (w, y), 1.0, 2)
            off = 0 if row % 2 else 60
            for x in range(off, w, 120):
                cv2.line(m, (x, y), (x, y + 44), 1.0, 2)
        wall = wall * (1 - 0.35 * m[..., None])
        wall = wall * (1 - 0.12 * (E.noise(h, w, 30, 61, octaves=2)[..., None] - 0.5))
        # 地面
        wall[905:] = E.vgrad('#0E0B19', '#07060D')[905:]
        # 墙上灯牌：月牙 + 小星星（灯管）
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">'
               '<path d="M1520,180 A110,110 0 1 0 1620,330 A86,86 0 1 1 1520,180 Z"/>'
               '<path d="M1700,170 l12,30 l32,4 l-24,20 l8,32 l-28,-18 l-28,18 l8,-32 l-24,-20 l32,-4 Z"/>'
               '<path d="M330,230 q60,-40 120,0 q60,40 120,0" /><path d="M330,280 q60,-40 120,0 q60,40 120,0"/></svg>')
        sig = E.svg_rgba(svg)[..., 3]
        self.sign = sig
        cols = np.zeros((h, w, 3), np.float32)
        cols[:, :1000] = E.hexrgb('#4FE3FF')
        cols[:, 1000:] = E.hexrgb('#FFC94F')
        self.sign_col = cols
        self.wall = wall

    def pose(self, t):
        K = E.K
        p = E.pose(x=960, y=905, s=0.92)
        beat = 0.6
        b = math.sin(2 * math.pi * t / (2 * beat))           # 两拍一次换重心
        down = abs(math.sin(math.pi * t / beat))              # 每拍下沉
        groove = E.smooth(t / 0.5)
        p['dx'] = 34 * b * groove
        p['lean'] = 6 * b * groove
        p['sq'] = 1 - 0.045 * down * groove
        p['hop'] = 6 * (1 - down) * groove
        ph = t / beat
        # 手臂：前段交替摆；中段双臂打拍；末段举手慢摇
        aL = 30 + 40 * math.sin(math.pi * ph)
        aR = 30 - 40 * math.sin(math.pi * ph)
        mid = E.smooth((t - 1.2) / 0.3) * (1 - E.smooth((t - 2.4) / 0.3))
        aL = E.lerp(aL, 70 + 30 * math.sin(2 * math.pi * ph), mid)
        aR = E.lerp(aR, 70 + 30 * math.sin(2 * math.pi * ph), mid)
        end = E.smooth((t - 3.0) / 0.4)
        aL = E.lerp(aL, 130 + 10 * math.sin(2 * math.pi * t / 1.2), end)
        aR = E.lerp(aR, 120 + 10 * math.sin(2 * math.pi * t / 1.2 + 1), end)
        p['armL'], p['armR'] = aL, aR
        # 2.4–3.0 下沉摆肩：重心压低、左右快速晃肩
        dip = math.sin(math.pi * E.seg(t, 2.4, 3.0))
        p['sq'] -= 0.07 * dip
        p['lean'] += 7 * dip * math.sin(2 * math.pi * (t - 2.4) / 0.3)
        p['legs'] = (12 * max(0, b), 0, 0, 12 * max(0, -b))
        p['hair'] = -9 * b * groove - 5 * math.sin(2 * math.pi * t / beat)
        p['skirt'] = -4 * b * groove
        p['eye_mode'] = 'happy' if (t < 1.2 or 3.1 < t < 4.0) else 'open'
        p['eye_dx'] = 10 * b
        p['eye_dy'] = -10 if t > 3.0 else 0
        return p

    def frame(self, t, p=None, trans=False):
        p = dict(self.pose(t) if p is None else p)
        img = self.wall.copy()
        # 灯牌（缓慢呼吸，不闪烁）
        pulse = 0.9 + 0.1 * math.sin(t * 2.0)
        img = fx.glow_add(img, self.sign * pulse, self.sign_col * 0.9)
        img = img + self.sign[..., None] * 0.5
        flat = E.render_char(6, p, 'flat')
        la = E.line_alpha(6, p, sw=1.25, eye_ring=True)
        col = fx.palette_map(fx.neighbor_color(flat[..., :3], flat[..., 3], 6), NEON)
        # 身体：夜色剪影（保留服装色相）
        body = flat[..., :3] * 0.34 + 0.02
        img = E.over_rgb(img, body, flat[..., 3])
        # 灯管：辉光 + 白芯
        tube = la
        img = fx.glow_add(img, tube, col, radii=((2, 0.9), (8, 0.8), (22, 0.5)))
        img = img * (1 - tube[..., None] * 0.2) + (col * 0.55 + 0.45) * (tube[..., None] * 0.9)
        # 湿地面倒影
        ref = img[905 - 300:905][::-1]
        ref = E.blur(ref, 4)
        fade = np.linspace(0.45, 0, 175, dtype=np.float32)[:, None, None]
        img[905:1080] = img[905:1080] * (1 - fade) + ref[:175] * fade * 1.2
        return np.clip(img, 0, 1)
