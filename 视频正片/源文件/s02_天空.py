# -*- coding: utf-8 -*-
"""02《天空》—— 水墨留白 · 云上飞行。
意象：水墨云海之上，几座远山从云里露出尖。Clawd 张开双臂像翅膀一样慢慢滑翔，粉色薄纱披肩在身后飘；
两只大雁从身后追上来、与她并排飞，她侧头看它们、轻轻侧身转个弯，然后继续向远处飞去。空灵、克制，不做特技。
画法：角色线条为毛笔线（粗细变化、轻微抖动、干笔飞白），色块为淡彩晕染（向纸色提亮、边缘积色、颗粒）；
云分远、中、近三层以不同速度向后移，远山最慢，形成纵深；整幅压在宣纸纹理上。
"""
import math
import numpy as np
import cv2
import engine as E
import fx
from scene_base import Scene

PAPER = '#F2EDE2'
INK = '#2B2A28'
SPAN = 6400                      # 云层贴图宽度：覆盖 t ∈ [-1.6, 5.8] 的全部移动距离
T0 = -1.6                        # 贴图起点对应的时间
SPEED = {'far': 26, 'sea': 120, 'mid': 170, 'near': 420}   # px/s，向左移动（她向右飞）


def stroke(img, pts, w, color, alpha=1.0):
    """一笔墨：沿折线画粗细渐变的线。"""
    m = np.zeros(img.shape[:2], np.float32)
    n = len(pts)
    for i in range(n - 1):
        t = i / (n - 1)
        ww = max(1, int(w * (0.35 + 0.65 * math.sin(math.pi * min(1, t * 1.15)))))
        cv2.line(m, tuple(map(int, pts[i])), tuple(map(int, pts[i + 1])), 1.0, ww, cv2.LINE_AA)
    return E.over_rgb(img, np.asarray(color, np.float32), E.blur(m, 0.8) * alpha)


def band_layer(top_fn, h, w, bottom=None, edge_ink=0.35, seed=0, body=0.0):
    """云层贴图（RGBA）：top_fn(x) 给出云顶高度；云顶处积墨，向下淡去成纸色。"""
    ys = np.arange(h, dtype=np.float32)[:, None]
    top = top_fn(np.arange(w, dtype=np.float32))[None, :]
    d = ys - top
    a = np.clip(d / 6, 0, 1)
    if bottom is not None:
        a *= np.clip((bottom - ys) / 60, 0, 1)
    gran = E.noise(h, w, 5, seed)
    ink = np.exp(-np.clip(d, 0, None) / 34) * edge_ink + body
    ink = ink * (0.8 + 0.4 * gran)
    col = E.hexrgb(PAPER)[None, None] * (1 - ink[..., None]) + E.hexrgb(INK)[None, None] * ink[..., None]
    return np.dstack([col, a]).astype(np.float32)


def blob_layer(blobs, h, w, seed, ink_edge=0.22, white=1.025, soft=16, alpha=1.0):
    """水墨晕染的云团（RGBA）：若干椭圆合成一团，柔边；内部留白（比纸略亮），边缘积一圈淡墨。"""
    sc = 4
    a = np.zeros((h // sc, w // sc), np.float32)
    for (cx, cy, rx, ry) in blobs:
        cv2.ellipse(a, (int(cx / sc), int(cy / sc)), (max(1, int(rx / sc)), max(1, int(ry / sc))), 0, 0, 360, 1.0, -1)
    a = cv2.GaussianBlur(a, (0, 0), soft / sc)
    a = cv2.resize(a, (w, h), interpolation=cv2.INTER_LINEAR)
    wob = E.noise(h, w, 22, seed)
    a = np.clip((a - 0.35 + 0.18 * (wob - 0.5)) * 3.2, 0, 1)
    edge = np.clip(1 - np.abs(a - 0.45) / 0.45, 0, 1) ** 2
    gran = E.noise(h, w, 4, seed + 1)
    ink = edge * ink_edge * (0.7 + 0.6 * gran)
    col = E.hexrgb(PAPER)[None, None] * white * (1 - ink[..., None]) + E.hexrgb(INK)[None, None] * ink[..., None]
    return np.dstack([np.clip(col, 0, 1), a * alpha]).astype(np.float32)


def cloud_blobs(rng, cx, cy, L, th):
    out = []
    n = int(L / 70) + 3
    for i in range(n):
        x = cx - L + 2 * L * (i + rng.uniform(0, 0.6)) / n
        k = 1 - ((x - cx) / L) ** 2
        r = th * (0.45 + 0.75 * max(0.0, k)) * rng.uniform(0.8, 1.2)
        out.append((x, cy - r * 0.35, r * 1.3, r * 0.75))
    return out


class S02(Scene):
    key = '02'
    filename = '02_天空'
    style = '水墨留白'
    no = 2
    core = 4.0

    def setup(self):
        h = 1080
        self.paper = fx.paper(1080, 1920, PAPER, seed=21, fiber=0.012, grain=0.025)
        self.sky = self.paper.copy()
        top = np.clip(1 - np.arange(h, dtype=np.float32) / 520, 0, 1)[:, None] ** 2
        self.sky = self.sky * (1 - 0.10 * top[..., None])                   # 天顶一抹淡墨
        rng = np.random.default_rng(202)
        n1 = lambda s, sd: E.noise(1, SPAN + 4, s, sd)[0][:SPAN]
        xs = np.arange(SPAN, dtype=np.float32)
        # 远山：几座从云海里露出的山尖
        far = np.zeros((h, SPAN, 4), np.float32)
        for k in range(14):
            cx, hh, ww = rng.uniform(0, SPAN), rng.uniform(140, 260), rng.uniform(160, 300)
            ridge = 830 - hh * np.clip(1 - np.abs(xs - cx) / ww, 0, 1) ** 1.4 + 10 * (n1(30, 300 + k)[:] - 0.5) * 2 * (np.abs(xs - cx) < ww)
            m = np.clip((np.arange(h, dtype=np.float32)[:, None] - ridge[None, :]) / 3, 0, 1)
            m *= np.clip(1 - (np.arange(h, dtype=np.float32)[:, None] - ridge[None, :]) / 140, 0, 1) ** 1.2
            far[..., 3] = np.maximum(far[..., 3], m * 0.24)
        far[..., :3] = E.hexrgb(INK)
        self.far = far
        # 云海（下方）
        self.sea = band_layer(lambda x: 860 - 70 * (n1(260, 211)[x.astype(int)] - 0.5) * 2 - 22 * (n1(60, 212)[x.astype(int)] - 0.5) * 2,
                              h, SPAN, edge_ink=0.20, seed=213)
        # 中层浮云：一团团水墨晕染的云（留白 + 边缘淡墨），分布在角色上下方
        blobs = []
        for k in range(18):
            cx = rng.uniform(0, SPAN)
            cy = rng.uniform(150, 290) if k % 2 == 0 else rng.uniform(720, 800)
            blobs += cloud_blobs(rng, cx, cy, rng.uniform(220, 420), rng.uniform(60, 100))
        self.mid = blob_layer(blobs, h, SPAN, 230, ink_edge=0.24)
        # 近景流云：只在画面上下边缘掠过，很淡，表现速度
        blobs = []
        for k in range(12):
            cx = rng.uniform(0, SPAN)
            cy = rng.uniform(-10, 60) if k % 2 == 0 else rng.uniform(1030, 1100)
            blobs += cloud_blobs(rng, cx, cy, rng.uniform(300, 560), rng.uniform(90, 140))
        self.near = blob_layer(blobs, h, SPAN, 250, ink_edge=0.14, soft=30, alpha=0.7)

    def layer(self, img, lay, speed, t):
        off = int(round(speed * (t - T0)))
        off = max(0, min(SPAN - 1920, off))
        return E.over(img, np.ascontiguousarray(lay[:, off:off + 1920]))

    def pose(self, t):
        K = E.K
        bank = math.sin(math.pi * E.seg(t, 2.1, 3.3)) if 2.1 < t < 3.3 else 0.0
        p = E.pose(x=960 + 40 * math.sin(t * 0.8), y=640 + 14 * math.sin(t * 2.1) - 46 * bank, s=0.78)
        flap = math.sin(2 * math.pi * t / 1.5)
        p['armL'] = 86 + 9 * flap
        p['armR'] = 86 + 9 * flap
        p['lean'] = 6 + 10 * bank + 1.5 * math.sin(t * 1.3)
        p['legs'] = (8, 10, 10, 8)
        p['skirt'] = -7 + 2 * math.sin(t * 2.4)
        p['hair'] = -5 + 1.5 * math.sin(t * 2.0)
        p['flare'] = 1.05 + 0.02 * math.sin(t * 1.7)
        p['eye_dx'] = K(t, [(-0.4, 0), (0.4, -12), (1.1, -12), (1.7, 14), (2.6, 14), (3.4, 6)])
        p['eye_dy'] = K(t, [(-0.4, 0), (0.4, -4), (1.7, -10), (2.6, -8), (3.4, 0)])
        p['eye_mode'] = 'happy' if 1.8 < t < 2.5 else 'open'
        p['eye_open'] = E.blink(t, [0.2, 3.7])
        return p

    def geese(self, img, t):
        """两只大雁：从左后方追上来，与她并排，再向前飞出画面。"""
        ink = E.hexrgb(INK)
        for k, (yy, ph, sc) in enumerate([(360, 0.0, 3.4), (450, 1.3, 2.9)]):
            x = K_g(t, k)
            y = yy + 8 * math.sin(t * 2 + ph)
            fl = math.sin(t * 6.5 + ph)
            wing = 22 * sc
            pts_l = [(x - wing, y - 7 * fl * sc), (x - wing * 0.5, y - 3 * sc), (x, y)]
            pts_r = [(x, y), (x + wing * 0.6, y - 4 * sc - 5 * fl * sc), (x + wing * 1.1, y - 7 * fl * sc)]
            img = stroke(img, pts_l, 5.5 * sc, ink, 0.88)
            img = stroke(img, pts_r, 5.5 * sc, ink, 0.88)
            img = stroke(img, [(x + wing * 0.2, y - 2), (x + wing * 0.9, y - 5)], 3 * sc, ink, 0.8)     # 头颈
        return img

    def frame(self, t, p=None, trans=False):
        p = dict(self.pose(t) if p is None else p)
        img = self.sky.copy()
        img = self.layer(img, self.far, SPEED['far'], t)
        img = self.layer(img, self.mid, SPEED['mid'], t)
        img = self.layer(img, self.sea, SPEED['sea'], t)
        img = self.geese(img, t)
        ox, oy = p['x'] - 960 + p['dx'] * p['s'], p['y'] - 640
        flat = E.render_char(2, p, 'flat')
        wash = fx.ink_wash(flat, ox, oy, E.hexrgb(PAPER), lift=0.22)
        img = E.over(img, wash, 0.94)
        a = fx.brush_lines(E.line_alpha(2, p, sw=1.5), ox, oy)
        img = E.over_rgb(img, E.hexrgb('#1C1A18'), E.blur(a, 2.0) * 0.18)
        img = E.over_rgb(img, E.hexrgb('#1C1A18'), a * 0.92)
        img = self.layer(img, self.near, SPEED['near'], t)
        return np.clip(img * (self.paper / np.maximum(self.paper.mean(), 1e-3)) ** 0.3, 0, 1)


def K_g(t, k):
    """雁的屏幕 x：从左后方追上来（t≈1.7 与她并排），再加速飞出右侧。"""
    return E.K(t, [(-1.6, -400 - 160 * k), (0.3, -220 - 160 * k), (1.7, 1300 + 170 * k, 'out'),
                   (2.8, 1380 + 170 * k), (4.4, 2300 + 170 * k, 'in'), (5.8, 3200)])
