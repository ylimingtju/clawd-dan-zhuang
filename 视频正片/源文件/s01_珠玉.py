# -*- coding: utf-8 -*-
"""01《珠玉》—— 柔光 3D 瓷感。
意象：从低头沉静到抬眼张开双臂、向前一步；光从一束窄光慢慢铺开成整片晨光，镜头缓慢拉远，空间由窄变阔。
画法：角色按色块生成圆润斜面高度场，做漫反射 + 高光 + 接缝暗角（无描边）；背景为景深虚化的影棚、上升的散景光点、镜面地板倒影。
"""
import math
import numpy as np
import engine as E
import fx
from scene_base import Scene


class S01(Scene):
    key = '01'
    filename = '01_珠玉'
    style = '柔光 3D 瓷感'
    no = 1
    core = 4.4

    def setup(self):
        rng = np.random.default_rng(101)
        self.bokeh = [(rng.uniform(0, 1920), rng.uniform(0, 1080), rng.uniform(8, 34), rng.uniform(14, 40),
                       rng.uniform(0.10, 0.32), rng.integers(0, 3)) for _ in range(38)]
        self.base = E.vgrad('#070F24', '#16264D', gamma=1.2)
        self.floor = E.vgrad('#16264D', '#0B152E')

    def pose(self, t):
        K, sm = E.K, E.smooth
        p = E.pose()
        p['s'] = K(t, [(-0.4, 1.10), (4.8, 0.90)])
        p['x'] = 960 + K(t, [(2.5, 0), (3.4, 46, 'io')])
        p['y'] = 905
        p['eye_dy'] = K(t, [(-0.4, 16), (0.7, 16), (1.5, -8), (2.6, -12), (3.4, -6)])
        p['eye_dx'] = K(t, [(2.4, 0), (3.2, 12), (4.2, 6)])
        p['eye_open'] = K(t, [(-0.4, 0.55), (0.8, 0.55), (1.4, 1.0)]) * E.blink(t, [3.9])
        p['sq'] = K(t, [(-0.4, 0.985), (0.8, 0.965), (1.25, 1.035, 'out'), (1.7, 1.0), (2.9, 0.975), (3.15, 1.02), (3.5, 1.0)])
        p['hop'] = K(t, [(2.85, 0), (3.12, 14, 'out'), (3.42, 0, 'in')])
        p['lean'] = K(t, [(-0.4, 3), (0.9, 4), (1.6, -1), (2.8, -3), (3.4, 1.5), (4.2, 0)])
        arm = K(t, [(-0.4, -14), (1.0, -14), (2.3, 78, 'back'), (3.5, 64), (4.8, 52)])
        p['armL'] = arm + 2 * math.sin(t * 2.1)
        p['armR'] = arm + 2 * math.sin(t * 2.1 + 0.8)
        p['flare'] = K(t, [(-0.4, 0.93), (1.2, 0.93), (2.4, 1.12, 'back'), (3.6, 1.07)])
        p['skirt'] = 2.2 * math.sin(t * 1.7 + 0.4) + K(t, [(2.8, 0), (3.2, -3), (3.8, 0)])
        p['hair'] = 2.5 * math.sin(t * 1.5) + K(t, [(1.3, 0), (2.2, -3), (3.2, 2)])
        p['legs'] = (0, K(t, [(2.85, 0), (3.05, 10), (3.3, 0)]), 0, 0)
        return p

    def frame(self, t, p=None, trans=False):
        p = dict(self.pose(t) if p is None else p)
        img = self.base.copy()
        # 光由窄变宽、由暗变亮
        open_k = E.smooth((t + 0.4) / 4.2)
        r = E.lerp(330, 1500, open_k)
        g = E.radial(960, 470, r) ** 1.6
        img = img + (E.hexrgb('#CADBF2') * (0.25 + 0.55 * open_k))[None, None] * g[..., None]
        beam = np.clip(1 - np.abs(np.arange(1920, dtype=np.float32) - 960) / E.lerp(160, 760, open_k), 0, 1) ** 2
        img = img + 0.10 * (0.5 + 0.5 * open_k) * beam[None, :, None] * np.linspace(1, 0.2, 1080, dtype=np.float32)[:, None, None]
        # 地板
        fl = np.zeros((1080, 1920), np.float32)
        fl[905:] = 1
        img = img * (1 - 0.35 * fl[..., None]) + self.floor * 0.35 * fl[..., None]
        # 散景（缓慢上升 = 时间流逝）
        for (x, y, rad, sp, al, c) in self.bokeh:
            yy = (y - sp * (t + 0.4)) % 1180 - 50
            col = [E.hexrgb('#DCE9FF'), E.hexrgb('#F4E6C8'), E.hexrgb('#BFD3F5')][c]
            if abs(x - 960) < 420 and 200 < yy < 900:
                al *= 0.35                                  # 不挡住服装
            fx.soft_disc(img, x, yy, rad, col, al * (0.5 + 0.5 * open_k), sharp=0.15)
        # 眼睛不参与斜面隆起：先对“无眼”的角色做体积光照，再把眼睛作为平贴的深色釉面画回去
        body, eye = E.render_char_eyes_apart(1, p, 'flatshade', seam=0.22)
        ch = fx.volume(body, R=22, amb=0.70, spec=0.30, shin=30)
        ch[..., :3] = ch[..., :3] * (1 - eye[..., None]) + E.hexrgb('#1E1714') * eye[..., None]
        if p['eye_open'] > 0.3 and p['eye_mode'] == 'open':
            for (ex, ey) in [(706, 722), (812, 722)]:
                sx, sy = E.to_screen(p, (ex + p['eye_dx'] - 5, ey + p['eye_dy'] - 22 * p['eye_open']))
                fx.soft_disc(ch, sx, sy, 4.5 * p['s'], np.array([1, 1, 1, 1], np.float32), 0.7, sharp=0.5)
        img = E.over_rgb(img, np.zeros(3, np.float32), fx.contact_shadow(1080, 1920, p['x'] - 10, 905 + 4, 330 * p['s'], 26 * p['s'], 0.55))
        img = E.over(img, fx.reflection(ch, 905 + 2, fade=0.22))
        img = E.over(img, ch)
        # 轻微暗角
        img *= (0.82 + 0.18 * E.radial(960, 540, 1300) ** 0.6)[..., None]
        return np.clip(img, 0, 1)
