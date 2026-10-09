# -*- coding: utf-8 -*-
"""14 片尾：回到片头的素色底。穿着《有趣》造型的 Clawd 回头望一眼、挥手，然后笑着站定；
同一套标题与 13 色块重新出现，与片头呼应；末尾保留约 0.5 秒稳定画面。"""
import math
import numpy as np
import cv2
import engine as E
import fx
import titles as T
from scene_base import Scene


def brighten_orange(rgba):
    """把身体的橙色提亮一档（D97757 → 约 F18764），在浅色底上不显黑；只作用于橙色系像素。"""
    rgb = rgba[..., :3]
    hsv = cv2.cvtColor(np.ascontiguousarray(rgb), cv2.COLOR_RGB2HSV)
    h, s_ = hsv[..., 0], hsv[..., 1]
    m = ((h > 4) & (h < 30) & (s_ > 0.35)).astype(np.float32)
    m = cv2.GaussianBlur(m, (0, 0), 0.8)
    out = rgba.copy()
    out[..., :3] = rgb * (1 - m[..., None]) + np.clip(rgb * 1.08 + 0.025, 0, 1) * m[..., None]
    return out


class Outro(Scene):
    key = '14'
    filename = '14_片尾'
    style = '素色设定稿'
    no = 13
    core = 1.8
    handle = 0.4

    def setup(self):
        self.text = T.text_layer()
        self.bg = E.solid(T.BG)

    def pose(self, t):
        K = E.K
        p = E.pose(x=960, y=860, s=0.62)
        p['eye_dx'] = K(t, [(-0.4, -16), (0.35, -16), (0.6, 0)])
        p['eye_dy'] = K(t, [(-0.4, 0), (0.35, 0), (0.6, 0)])
        p['lean'] = K(t, [(-0.4, -5), (0.35, -4), (0.6, 0)])
        p['armR'] = K(t, [(-0.4, 10), (0.4, 10), (0.55, 118, 'out'), (0.7, 92), (0.85, 120), (1.0, 96), (1.2, 40), (1.35, 34)])
        p['armL'] = K(t, [(-0.4, 8), (1.0, 8), (1.2, 34)])
        p['sq'] = K(t, [(1.0, 1.0), (1.12, 0.94), (1.28, 1.02), (1.4, 1.0)])
        p['eye_mode'] = 'happy' if t > 0.6 else 'open'
        p['hair'] = K(t, [(-0.4, -5), (0.4, -4), (0.7, 3), (1.0, 0)])
        return p

    def frame(self, t, p=None, trans=False):
        p = dict(self.pose(t) if p is None else p)
        img = self.bg.copy()
        k = E.ease_out((t - 0.25) / 0.35)
        if k > 0:
            img = E.over(img, E.shifted(self.text, 0, 24 * (1 - k)), k)
        appear = lambda i: E.seg(t, 0.35 + (12 - i) * 0.025, 0.55 + (12 - i) * 0.025)
        img = E.over(img, E.svg_rgba(T.chips_svg(appear)))
        img = E.over_rgb(img, np.zeros(3, np.float32), fx.contact_shadow(1080, 1920, 960, 862, 190, 14, 0.25, 8))
        img = E.over(img, brighten_orange(E.svg_rgba(E.char_svg(13, p))))
        return np.clip(img, 0, 1)
