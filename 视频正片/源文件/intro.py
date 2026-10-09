# -*- coding: utf-8 -*-
"""00 片头：素色底上，穿《珠玉》造型的 Clawd 从下方跳上来落地、挥手；标题「Clawd 蛋装」整体浮现；13 个造型色块依次弹出成一排，
最后 Clawd 望向第一块（珠玉的珍珠白），这块轻轻放大——正片由它扩成光圈进入《珠玉》。"""
import math
import numpy as np
import engine as E
import fx
import titles as T
from scene_base import Scene


class Intro(Scene):
    key = '00'
    filename = '00_片头'
    style = '素色设定稿'
    no = 1
    core = 1.6
    handle = 0.4

    def setup(self):
        self.text = T.text_layer()
        self.bg = E.solid(T.BG)

    def pose(self, t):
        K = E.K
        p = E.pose(x=960, y=860, s=0.62)
        p['hop'] = K(t, [(-0.4, -520), (0.0, -520), (0.28, 60, 'out'), (0.42, 0, 'in')])
        p['sq'] = K(t, [(0.3, 1.12), (0.42, 0.82), (0.58, 1.05, 'out'), (0.72, 1.0)])
        p['armR'] = K(t, [(0.5, 6), (0.65, 120, 'out'), (0.8, 96), (0.95, 128), (1.1, 100), (1.3, 30)])
        p['armL'] = K(t, [(0.3, 40), (0.5, 6)])
        p['eye_dx'] = K(t, [(0.9, 0), (1.25, -14)])
        p['eye_dy'] = K(t, [(0.9, 0), (1.25, 16)])
        p['eye_mode'] = 'happy' if 0.55 < t < 1.05 else 'open'
        p['lean'] = K(t, [(1.0, 0), (1.3, 3)])
        p['flare'] = K(t, [(0.3, 0.96), (0.45, 1.06, 'out'), (0.75, 1.0)])
        p['skirt'] = K(t, [(0.35, 0), (0.5, -3), (0.75, 2), (1.0, 0)])
        p['hair'] = K(t, [(0.3, 4), (0.5, -4), (0.75, 2), (1.0, 0)])
        return p

    def frame(self, t, p=None, trans=False):
        p = dict(self.pose(t) if p is None else p)
        img = self.bg.copy()
        k = E.ease_out((t - 0.12) / 0.32)
        if k > 0:
            txt = E.shifted(self.text, 0, 24 * (1 - k))
            img = E.over(img, txt, k)
        appear = lambda i: 0.0 if (trans and i == 0) else E.seg(t, 0.3 + i * 0.03, 0.5 + i * 0.03)
        pulse = 0.35 * E.smooth((t - 1.15) / 0.35)
        img = E.over(img, E.svg_rgba(T.chips_svg(appear, pulse)))
        if p['hop'] > -400:
            sh = fx.contact_shadow(1080, 1920, 960, 862, 240 * (1 - min(1, max(0, p['hop']) / 300)), 14, 0.25, 8)
            img = E.over_rgb(img, np.zeros(3, np.float32), sh)
            img = E.over(img, E.svg_rgba(E.char_svg(1, p)))
        return np.clip(img, 0, 1)
