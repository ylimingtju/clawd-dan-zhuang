# -*- coding: utf-8 -*-
"""08《梦一场》—— 油画厚涂。
意象：左边浮着一幅暖金色的回忆小画（亮着灯的桌边、两只杯子）。Clawd 望着它慢慢伸手，画就开始融化，
颜料往下流、被夜蓝吞没；她收回手抱住自己、闭上眼，再睁眼、转向前方，迈出一步——回忆与现实之间的变化。
画法：整幅画面先合成，再做 Kuwahara 油画色块化 + 方向性笔触浮雕（角色身上的笔触纹理随角色移动）+ 画布纹；一拍二。
"""
import math
import numpy as np
import cv2
import engine as E
import fx
from scene_base import Scene


class S08(Scene):
    key = '08'
    filename = '08_梦一场'
    style = '油画厚涂'
    no = 8
    core = 4.0
    step = 2

    def setup(self):
        h, w = 1080, 1920
        bg = E.vgrad('#1B2440', '#2A3558', gamma=0.8)
        # 窗外夜色：大块冷色笔触区域
        n = E.noise(h, w, 140, 82, octaves=3)
        bg = bg * (0.85 + 0.3 * n[..., None])
        bg[905:] = E.vgrad('#2B2A3A', '#17161F')[905:]
        self.bg = bg
        flow = E.noise(h, w, 260, 86)
        self.st_bg = fx.make_strokes(6500, -20, -20, w + 20, h + 20, 87, 34, 60, 10, 17,
                                     lambda x, y: 0.4 + 1.6 * flow[int(min(h - 1, max(0, y))), int(min(w - 1, max(0, x)))])
        # 角色笔触在角色局部坐标（以站位为原点）中固定，随角色平移
        self.st_ch = fx.make_strokes(4200, -330, -560, 330, 30, 88, 14, 26, 6, 10, lambda x, y: 1.35)
        self.st_mem = fx.make_strokes(2600, 170, 150, 630, 900, 89, 10, 18, 5, 8, lambda x, y: 0.2)
        canvas = np.zeros((h, w), np.float32)
        yy, xx = np.mgrid[0:h, 0:w]
        canvas = (0.5 + 0.25 * np.sin(xx * 1.9) * np.sin(yy * 1.9)).astype(np.float32)
        self.canvas = canvas
        mem = E.svg_rgba('<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">'
                         '<path d="M180,620 L180,330 C180,220 290,160 400,160 C510,160 620,220 620,330 L620,620 Z" fill="#E7A74D"/>'
                         '<path d="M180,470 C300,440 500,450 620,480 L620,620 L180,620 Z" fill="#B8642F"/>'
                         '<ellipse cx="400" cy="300" rx="120" ry="90" fill="#FFD989"/>'
                         '<rect x="300" y="470" width="200" height="22" fill="#5B2E1A"/>'
                         '<rect x="320" y="492" width="14" height="80" fill="#5B2E1A"/><rect x="466" y="492" width="14" height="80" fill="#5B2E1A"/>'
                         '<path d="M350,470 l6,-34 h26 l6,34 Z" fill="#F4EBDD"/><path d="M420,470 l6,-34 h26 l6,34 Z" fill="#F4EBDD"/>'
                         '<path d="M180,620 L180,330 C180,220 290,160 400,160 C510,160 620,220 620,330 L620,620 Z" fill="none" stroke="#C7913E" stroke-width="16"/>'
                         '</svg>')
        self.mem = mem
        self.drip = E.noise(1, w, 14, 85)[0]

    def pose(self, t):
        K = E.K
        p = E.pose(x=1180, y=905, s=0.92)
        p['armL'] = K(t, [(-0.4, 4), (0.4, 10), (1.5, 62), (2.1, 58), (2.6, -6), (3.2, -10), (3.8, 6), (4.4, 10)])
        p['armR'] = K(t, [(-0.4, 4), (2.2, 8), (2.7, -8), (3.2, -10), (3.8, 6), (4.4, 10)])
        p['eye_dx'] = K(t, [(-0.4, -14), (2.2, -16), (2.6, -8), (3.3, 0), (3.6, 12), (4.4, 10)])
        p['eye_dy'] = K(t, [(-0.4, -4), (1.6, -6), (2.4, 8), (3.3, 0), (3.6, -4)])
        p['eye_mode'] = 'closed' if 2.65 < t < 3.25 else 'open'
        p['eye_open'] = K(t, [(1.8, 1.0), (2.5, 0.6), (2.65, 0.6), (3.3, 0.9)])
        p['lean'] = K(t, [(-0.4, -2), (1.5, -6), (2.1, -6), (2.7, 2), (3.3, 3), (3.7, -2), (4.4, 0)])
        p['sq'] = K(t, [(2.4, 1.0), (2.8, 0.95), (3.3, 0.96), (3.55, 1.03), (3.8, 1.0)])
        p['dx'] = K(t, [(3.4, 0), (4.0, 36), (4.4, 40)])
        p['hop'] = K(t, [(3.5, 0), (3.7, 10, 'out'), (3.9, 0, 'in')])
        p['legs'] = (0, 0, K(t, [(3.5, 0), (3.7, 14), (3.9, 0)]), 0)
        p['skirt'] = K(t, [(-0.4, 0), (1.5, -3), (2.7, 2), (3.4, 0), (3.8, -4), (4.4, 0)])
        return p

    def frame(self, t, p=None, trans=False):
        p = dict(self.pose(t) if p is None else p)
        img = self.bg.copy()
        # 回忆小画：融化下流、褪成夜蓝
        melt = E.smooth((t - 1.6) / 1.6)
        mem = self.mem.copy()
        if melt > 0:
            yy = np.arange(1080, dtype=np.float32)[:, None]
            dy = -melt * (40 + 260 * self.drip[None, :]) * np.clip((yy - 160) / 460, 0, 1)
            mem = E.warp(mem, np.zeros_like(dy) + 0 * yy, dy * np.ones((1, 1920), np.float32))
            mem[..., :3] = mem[..., :3] * (1 - 0.6 * melt) + E.hexrgb('#2C3A66') * 0.6 * melt
            mem[..., 3] *= 1 - 0.55 * melt
        img = E.over(img, mem)
        # 暖光照在角色身上（随回忆消失变冷）
        warm = (1 - melt) * E.radial(400, 400, 1300) ** 2
        img = img + E.hexrgb('#E7A74D') * 0.10 * warm[..., None]
        ch = E.render_char(8, p, 'flatshade')
        tint = ch[..., :3] * (1 + 0.25 * warm[..., None] * np.array([1.0, 0.7, 0.3], np.float32))
        img = E.over_rgb(img, tint, ch[..., 3])
        # 油画化：底层色块化 → 背景大笔触 → 角色小笔触（笔位随角色移动）→ 浮雕 → 暗色轮廓
        base = fx.kuwahara(img, 5)
        canvas = base.copy()
        height = np.zeros((1080, 1920), np.float32)
        fx.paint_strokes(base, canvas, height, self.st_bg, mask=1 - (mem[..., 3] > 0.3))
        fx.paint_strokes(base, canvas, height, self.st_mem, mask=mem[..., 3] > 0.3)
        cx = p['x'] + p['dx'] * p['s']
        cmask = cv2.dilate(ch[..., 3], np.ones((5, 5), np.uint8))
        fx.paint_strokes(base, canvas, height, self.st_ch, ox=cx, oy=p['y'], mask=cmask)
        paint = fx.impasto(canvas, E.blur(height, 1.2), strength=3.2)
        la = E.line_alpha(8, p, sw=1.2)
        paint = E.over_rgb(paint, E.hexrgb('#141320'), E.blur(la, 0.8) * 0.75)
        paint = paint * (0.95 + 0.07 * self.canvas[..., None])
        return np.clip(paint, 0, 1)
