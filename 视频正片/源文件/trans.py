# -*- coding: utf-8 -*-
"""转场：14 个“小事件”，每个都借用前后两首歌里的一个元素，把同一个 Clawd 送进下一个世界，并在事件中换装换画风。

共同做法
- 每帧按同一个屏幕姿势分别渲染 A 场景（A 的造型与画风）和 B 场景（B 的造型与画风），两者可以各自缩放、平移；
  再用这个事件特有的遮罩（珍珠球面、云层、印刷滚筒、水管遮挡、剪刀轮廓、灯管、浪头、笔触、门缝、碎玻璃、画框、影子、
  落叶旋风、纸团）决定哪里属于新世界。画面里始终只有一个 Clawd。
- 道具（水管、剪刀、门、浪……）按所在世界的画风绘制；“角色在道具前面”时，道具层在角色处挖空。
- 第一帧 = 上一段最后一帧，最后一帧 = 下一段第一帧；所有随机量为固定种子，渲染可复现。

  python3 render.py trans all          渲染全部转场 → ../转场/
  python3 render.py tstills 3 0.2,0.5  检查某个转场的若干时刻
"""
import math
import numpy as np
import cv2
import engine as E
import fx
import titles as TT

W, H = E.W, E.H
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
K = E.K
ID = (1.0, 0.0, 0.0)
NUM = ('x', 'y', 's', 'hop', 'lean', 'sq', 'turn', 'armL', 'armR', 'eye_dx', 'eye_dy', 'eye_open',
       'hair', 'skirt', 'flare', 'hat', 'hat_lift', 'rot')
_MEMO = {}


def ss(x):
    x = min(1.0, max(0.0, x))
    return x * x * x * (x * (6 * x - 15) + 10)


def seg(u, a, b):
    return min(1.0, max(0.0, (u - a) / (b - a)))


def arc(u, a, b):
    return math.sin(math.pi * seg(u, a, b)) if a < u < b else 0.0


def soft(sd, aa=1.5):
    return np.clip(sd / aa + 0.5, 0, 1)


# ------------------------------------------------------------------ 姿势
def flat(p):
    q = dict(E.POSE0)
    q.update(p)
    q['x'] = p['x'] + p.get('dx', 0.0) * p['s']
    q['dx'] = 0.0
    q['rot'] = p.get('rot', 0.0)
    return q


def blend(a, b, w):
    q = dict(a)
    for k in NUM:
        q[k] = E.lerp(a.get(k, 0.0), b.get(k, 0.0), w)
    q['legs'] = tuple(E.lerp(x, y, w) for x, y in zip(a['legs'], b['legs']))
    q['eye_mode'] = a['eye_mode'] if w < 0.5 else b['eye_mode']
    return q


def gait(ph, lift=16, bob=8, arm=24, arm0=16):
    sn = math.sin(math.pi * ph)
    k = abs(sn)
    a = 1.0 if sn >= 0 else 0.0
    return dict(hop=bob * k, legs=(lift * k * a, lift * k * (1 - a), lift * k * a, lift * k * (1 - a)),
                armL=arm0 + arm * sn, armR=arm0 - arm * sn, sq=1 - 0.03 * k)


def to_world(p, xf):
    k, ox, oy = xf
    q = dict(p)
    q['x'] = (p['x'] - ox) / k
    q['y'] = (p['y'] - oy) / k
    q['s'] = p['s'] / k
    return q


def warp_world(img, xf):
    k, ox, oy = xf
    if k == 1.0 and ox == 0 and oy == 0:
        return img
    M = np.float32([[k, 0, ox], [0, k, oy]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def zoom_xf(z, cx, cy):
    return (z, cx - z * cx, cy - z * cy)


class C:
    """一帧的上下文。"""
    def __init__(self, tr, i, sa, sb):
        self.tr, self.sa, self.sb = tr, sa, sb
        self.n, self.T = tr.n, tr.T
        self.tau = i / E.FPS
        self.u = self.tau / tr.T
        self.pa = flat(sa.pose(sa.core))
        self.pb = flat(sb.pose(0.0))

    @property
    def ta(self):
        return self.sa.core + self.tau

    @property
    def tb(self):
        return self.tau - self.T

    def pose(self, over, win=(0.0, 1.0), edge=0.1, u=None):
        u = self.u if u is None else u
        base = blend(self.pa, self.pb, ss(seg(u, *win)))
        env = ss(u / edge) * ss((1 - u) / edge)
        p = dict(base)
        for k, v in over.items():
            if k == 'legs':
                p['legs'] = tuple(E.lerp(a, b, env) for a, b in zip(base['legs'], v))
            elif k == 'eye_mode':
                if env > 0.5:
                    p['eye_mode'] = v
            else:
                p[k] = E.lerp(base[k], v, env)
        return p

    def A(self, p, xf=ID, t=None):
        return warp_world(self.sa.frame(self.ta if t is None else t, to_world(p, xf), trans=True), xf)

    def B(self, p, xf=ID, t=None):
        return warp_world(self.sb.frame(self.tb if t is None else t, to_world(p, xf), trans=True), xf)

    def ca(self, p, dil=5):
        a = np.maximum(E.render_char(self.sa.no, p, 'flat')[..., 3], E.render_char(self.sb.no, p, 'flat')[..., 3])
        return cv2.dilate(a, np.ones((dil, dil), np.uint8)) if dil else a


def mix(A, B, m):
    return A * (1 - m[..., None]) + B * m[..., None]


def over_behind(img, lay, ca):
    """道具层画在背景上、但在角色后面（角色处挖空）。"""
    a = lay[..., 3] * (1 - ca)
    return img * (1 - a[..., None]) + lay[..., :3] * a[..., None]


def svg(body):
    return E.svg_rgba(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">{body}</svg>')


def pixelate(lay, b=8):
    sm = cv2.resize(lay, (W // b, H // b), interpolation=cv2.INTER_AREA)
    sm[..., 3] = (sm[..., 3] > 0.5).astype(np.float32)
    sm[..., :3] = np.round(sm[..., :3] * 5) / 5
    return cv2.resize(sm, (W, H), interpolation=cv2.INTER_NEAREST)


def riso_layer(lay):
    out = lay.copy()
    dark = (E.lum(lay[..., :3]) < 0.2).astype(np.float32) * lay[..., 3]
    out[..., :3] = fx.riso_print(lay[..., :3], cell=7, solid_black=dark)
    return out


def bg_blur(img, ca, v, axis):
    L = int(min(120, abs(v) * 0.55))
    if L < 3:
        return img
    bl = cv2.blur(img, (L, 1)) if axis == 'x' else cv2.blur(img, (1, L))
    m = E.blur(ca, 3)[..., None]
    return bl * (1 - m) + img * m


# ================================================================== 00 片头 → 珠玉：色块化成珍珠，把她包进新世界
def t_pearl(c):
    u = c.u
    p = c.pose({'armL': K(u, [(0, 6), (0.12, 50), (0.3, 64), (0.5, 20)]), 'eye_dx': K(u, [(0, 0), (0.1, -12), (0.3, 0)]),
                'eye_dy': K(u, [(0, 0), (0.1, 14), (0.3, 4), (0.45, 0)]), 'eye_mode': 'open',
                'sq': K(u, [(0.25, 1.0), (0.34, 0.95), (0.44, 1.03), (0.55, 1.0)])}, win=(0.3, 0.92))
    cx, cy = E.to_screen(p, (800, 820))
    A = c.A(p)
    if u < 0.3:                                         # 第一枚色块飞起来，在她胸前变圆
        q = ss(u / 0.3)
        x0, y0 = TT.chip_x(0), TT.CHIP_Y
        x = E.lerp(x0, cx, q)
        y = E.lerp(y0, cy, q) - 160 * math.sin(math.pi * q)
        sz = E.lerp(TT.CHIP, 52, q)
        rx = E.lerp(10, sz / 2, q)
        lay = svg(f'<rect x="{x - sz / 2:.1f}" y="{y - sz / 2:.1f}" width="{sz:.1f}" height="{sz:.1f}" rx="{rx:.1f}" '
                  f'fill="#F6F3EC" stroke="#2E2320" stroke-width="3"/>')
        img = E.over(A, lay)
        img = img + E.radial(x, y, 120 * q + 30)[..., None] ** 2 * 0.35 * q
        return np.clip(img, 0, 1)
    R = K(u, [(0.3, 26), (0.56, 300, 'io'), (1.0, 2600, 'in')])
    B = c.B(p)
    d = np.hypot(XX - cx, YY - cy)
    rr = np.clip(d / R, 0, 1)
    f = 0.80 + 0.20 * rr ** 2                           # 球面折射：中心放大
    mx, my = (cx + (XX - cx) * f).astype(np.float32), (cy + (YY - cy) * f).astype(np.float32)
    Bref = cv2.remap(B, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    fade = 1 - seg(u, 0.62, 0.86)
    inner = mix(B, Bref, np.full(d.shape, fade, np.float32) * (rr < 1))
    shade = 1 - 0.35 * fade * rr ** 4
    ang = np.arctan2(YY - cy, XX - cx)
    irid = (rr ** 6 * 0.22 * fade)[..., None] * np.dstack([0.5 + 0.5 * np.sin(ang * 2), 0.5 + 0.5 * np.sin(ang * 2 + 2), 0.5 + 0.5 * np.sin(ang * 2 + 4)])
    inner = inner * shade[..., None] + irid
    m = soft(R - d, 2.5)
    img = mix(A, inner, m)
    ring = np.exp(-((R - d) / 4) ** 2) * 0.6 * fade
    img = img + ring[..., None]
    fx.soft_disc(img, cx - 0.36 * R, cy - 0.42 * R, 0.16 * R, np.ones(3, np.float32), 0.55 * fade, 0.3)
    return np.clip(img, 0, 1)


# ================================================================== 01 珠玉 → 天空：光柱托起，冲破水墨云海
def t_takeoff(c):
    u = c.u
    p = c.pose({'sq': K(u, [(0, 1.0), (0.12, 0.86), (0.2, 1.12, 'out'), (0.4, 1.02), (0.8, 1.0)]),
                'hop': K(u, [(0.14, 0), (0.42, 240, 'out'), (0.9, 0, 'io')]),
                'armL': K(u, [(0, 55), (0.12, 14), (0.24, 150, 'out'), (0.6, 140), (0.88, 86)]),
                'armR': K(u, [(0, 55), (0.12, 14), (0.24, 150, 'out'), (0.6, 140), (0.88, 86)]),
                'legs': (12, 12, 12, 12), 'flare': K(u, [(0.2, 1.0), (0.4, 1.15), (0.9, 1.05)]),
                'eye_dy': -16, 'eye_dx': 0, 'eye_mode': 'open', 'lean': 2 * math.sin(u * 8)}, win=(0.0, 1.0))
    c_ = ss(seg(u, 0.16, 0.95))
    xa, xb = (1.0, 0.0, H * c_), (1.0, 0.0, -H * (1 - c_))
    A, B = c.A(p, xa), c.B(p, xb)
    seam = H * c_
    wav = 40 * (E.noise(1, W + 4, 140, 501)[0][:W] - 0.5) * 2 + 14 * np.sin(np.arange(W) / 53)
    amp = math.sin(math.pi * seg(u, 0.16, 0.95)) ** 0.5
    sd = (seam + amp * wav[None, :]) - YY              # >0：在云层之上 = 新世界
    m = soft(sd, 6)
    img = mix(A, B, m)
    if amp > 0.01:                                      # 云层：穿过时遮住她，换装发生在云里
        gran = E.shifted(E.noise(H, W, 30, 502, octaves=2), 0, seam)
        dens = np.clip(1 - np.abs(sd) / 230 + 0.35 * (gran - 0.5), 0, 1) ** 0.8 * amp
        ink = np.exp(-np.clip(sd + 150, 0, None) / 40) * 0.25 * (sd > -150)
        col = E.hexrgb('#F7F3EA')[None, None] * (1 - ink[..., None]) + E.hexrgb('#2B2A28')[None, None] * ink[..., None]
        img = mix(img, col, np.clip(dens * 1.15, 0, 0.97))
    v = H * (ss(seg(u, 0.16, 0.95)) - ss(seg(u - 1 / c.n, 0.16, 0.95)))
    return np.clip(bg_blur(img, c.ca(p), v, 'y'), 0, 1)


# ================================================================== 02 天空 → 爱情：四色套印，一版一版印出新世界
PLATES = ['yellow', 'pink', 'blue', 'black']
ANG = {'pink': 75, 'blue': 15, 'yellow': 0, 'black': 45}


def t_print(c):
    u = c.u
    land = seg(u, 0.55, 0.78)
    p = c.pose({'x': K(u, [(0, c.pa['x']), (0.75, c.pb['x'], 'io')]), 'y': K(u, [(0, c.pa['y']), (0.72, c.pb['y'], 'io')]),
                's': K(u, [(0, c.pa['s']), (0.72, c.pb['s'], 'io')]),
                'armL': K(u, [(0, 78), (0.5, 92), (0.72, 40), (0.85, 10)]), 'armR': K(u, [(0, 78), (0.5, 92), (0.72, 40), (0.85, 10)]),
                'legs': (8, 10, 10, 8) if u < 0.66 else (0, 0, 0, 0), 'lean': K(u, [(0, 5), (0.6, -3), (0.75, 0)]),
                'sq': K(u, [(0.66, 1.0), (0.74, 0.86), (0.84, 1.03), (0.92, 1.0)]),
                'skirt': K(u, [(0, -7), (0.6, 4), (0.8, 0)]), 'eye_dy': 10, 'eye_dx': -4, 'eye_mode': 'open'}, win=(0.6, 1.0))
    A, B = c.A(p), c.B(p)
    if 'paper03' not in _MEMO:
        _MEMO['paper03'] = fx.paper(H, W, '#F5EFE4', seed=33, fiber=0.01, grain=0.03)
    paper = _MEMO['paper03']
    plates = fx.riso_separate(B, 0.62)
    img = A
    acc = paper.copy()
    for j, name in enumerate(PLATES):
        a0 = 0.10 + 0.14 * j
        yf = K(u, [(a0, -140), (a0 + 0.42, H + 160, 'io')])
        cov = fx.halftone_plate(plates[name], 7, ANG[name])
        acc = acc * (1 - cov[..., None] * (1 - E.hexrgb(fx.RISO[name])))
        layer = B if j == 3 else acc
        m = soft(yf - YY, 3)
        img = mix(img, layer, m)
        if -80 < yf < H + 80:                           # 滚筒
            ink = E.hexrgb(fx.RISO[name])
            prof = np.clip(1 - np.abs(YY - yf) / 26, 0, 1)
            shadeline = 0.55 + 0.45 * np.cos((YY - yf) / 26 * math.pi / 2)
            roll = (ink * 0.55 + 0.15)[None, None] * shadeline[..., None]
            img = mix(img, roll, (prof > 0).astype(np.float32))
            img = img * (1 - 0.3 * np.clip(1 - (YY - yf - 26) / 30, 0, 1) * (YY > yf + 26))[..., None]
    return np.clip(img, 0, 1)


# ================================================================== 03 爱情 → 李白：钻进绿水管，从像素舞台的水管里蹦出来
PIPE_X = 1250


def pipe_svg(top, ground):
    bw, rw, rh = 470, 540, 74
    x0, r0 = PIPE_X - bw / 2, PIPE_X - rw / 2
    return (f'<rect x="{x0}" y="{top + rh - 4}" width="{bw}" height="{ground - top - rh + 40}" fill="#2E9A41" stroke="#14301A" stroke-width="7"/>'
            f'<rect x="{x0 + 40}" y="{top + rh}" width="60" height="{ground - top - rh + 36}" fill="#8EE07A"/>'
            f'<rect x="{x0 + bw - 110}" y="{top + rh}" width="70" height="{ground - top - rh + 36}" fill="#1F6B2A"/>'
            f'<rect x="{r0}" y="{top}" width="{rw}" height="{rh}" rx="8" fill="#3DAE4F" stroke="#14301A" stroke-width="7"/>'
            f'<rect x="{r0 + 34}" y="{top + 8}" width="60" height="{rh - 16}" fill="#9BEA86"/>'
            f'<rect x="{r0 + rw - 100}" y="{top + 8}" width="64" height="{rh - 16}" fill="#22772F"/>')


def t_pipe(c):
    u = c.u
    top_a = K(u, [(0.04, 900), (0.24, 650, 'out')])
    top_b = K(u, [(0.8, 654), (0.96, 920, 'in')])
    yA = c.pa['y']
    y = K(u, [(0.2, yA), (0.42, top_a, 'io'), (0.45, top_a), (0.54, top_a + 600, 'in'), (0.56, top_b + 600),
              (0.66, top_b, 'out'), (0.86, c.pb['y'], 'io')])
    x = K(u, [(0.2, c.pa['x']), (0.42, PIPE_X, 'io'), (0.66, PIPE_X), (0.86, c.pb['x'], 'io')])
    p = c.pose({'x': x, 'y': y, 'hop': 160 * arc(u, 0.2, 0.42) + 190 * arc(u, 0.64, 0.86),
                'sq': K(u, [(0.14, 1.0), (0.2, 0.84), (0.26, 1.1, 'out'), (0.42, 0.9), (0.46, 1.0), (0.62, 1.12), (0.7, 1.0),
                            (0.86, 0.82), (0.95, 1.03)]),
                'armL': K(u, [(0.18, 30), (0.3, 120), (0.44, 150), (0.66, 150), (0.86, 70)]),
                'armR': K(u, [(0.18, 30), (0.3, 120), (0.44, 150), (0.66, 150), (0.86, 70)]),
                'legs': (14, 14, 14, 14) if 0.22 < u < 0.86 else (0, 0, 0, 0),
                'eye_mode': 'happy' if 0.3 < u < 0.86 else 'open', 'eye_dx': 8}, win=(0.6, 1.0))
    hidden = dict(p, x=-6000)
    if u < 0.55:
        img = c.A(p)
        if u > 0.42:                                              # 沉到地面以下的部分不可见
            img = mix(img, c.A(hidden), (YY > 935).astype(np.float32))
        lay = riso_layer(svg(pipe_svg(top_a, 900)))
        cover = (YY > top_a + 2).astype(np.float32)             # 管口以下的身体被水管挡住
        img = E.over(img, lay * np.dstack([np.ones((H, W, 3), np.float32), cover * 0 + 1]))
        return np.clip(img, 0, 1)
    img = c.B(p)
    if u < 0.68:
        img = mix(img, c.B(hidden), (YY > 940).astype(np.float32))
    lay = pixelate(svg(pipe_svg(top_b, 904)), 8)
    cover = (YY > top_b + 2).astype(np.float32)
    ca = c.ca(p) * (1 - cover)                                    # 管口以上的身体在水管前面
    img = over_behind(img, lay, ca)
    if 0.55 < u < 0.68:                                           # 冒出来时的像素星星
        k = seg(u, 0.55, 0.68)
        for j in range(6):
            a = j * math.pi / 3 + 0.3
            r = 60 + 160 * k
            px, py = PIPE_X + r * math.cos(a), top_b - 20 + 0.6 * r * math.sin(a) - 60 * k
            img[int(py) - 8:int(py) + 8, int(px) - 8:int(px) + 8] = E.hexrgb('#FFF4C8') * (1 - k) + img[int(py) - 8:int(py) + 8, int(px) - 8:int(px) + 8] * k
    return np.clip(img, 0, 1)


# ================================================================== 04 李白 → Dear Friend：剪刀剪下她，像素舞台被整张揭起
def cut_contour(c):
    key = ('cut', c.tr.a)
    if key not in _MEMO:
        a = np.maximum(E.render_char(c.sa.no, c.pa, 'flat')[..., 3], E.render_char(c.sb.no, c.pb, 'flat')[..., 3])
        m = cv2.dilate((a > 0.3).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (52, 52)))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61)))
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cont = max(cs, key=cv2.contourArea)[:, 0, :].astype(np.float32)
        k = int(np.argmax(cont[:, 1] - 0.3 * cont[:, 0]))        # 从左下方开始剪
        cont = np.roll(cont, -k, axis=0)
        cont = cv2.GaussianBlur(cont[None], (1, 21), 0)[0] if len(cont) > 30 else cont
        fill = np.zeros((H, W), np.float32)
        cv2.fillPoly(fill, [cont.astype(np.int32)], 1.0)
        _MEMO[key] = (cont, E.blur(fill, 1.0))
    return _MEMO[key]


def scissors_svg(x, y, ang, op):
    a = math.degrees(ang)
    return (f'<g transform="translate({x:.1f},{y:.1f}) rotate({a:.1f})">'
            f'<g transform="rotate({-op:.1f})"><path d="M0,0 L70,-8 L74,0 Z" fill="#C9CED6" stroke="#2E2320" stroke-width="3"/>'
            f'<circle cx="-30" cy="-12" r="15" fill="none" stroke="#E8453C" stroke-width="9"/></g>'
            f'<g transform="rotate({op:.1f})"><path d="M0,0 L70,8 L74,0 Z" fill="#AEB4BE" stroke="#2E2320" stroke-width="3"/>'
            f'<circle cx="-30" cy="12" r="15" fill="none" stroke="#E8453C" stroke-width="9"/></g>'
            f'<circle r="5" fill="#2E2320"/></g>')


def t_scissors(c):
    u = c.u
    p = c.pose({'hop': 30 * arc(u, 0.46, 0.6), 'eye_mode': 'open', 'eye_dx': K(u, [(0, 0), (0.1, -14), (0.25, 14), (0.42, 0)]),
                'eye_dy': K(u, [(0, 0), (0.1, 12), (0.25, -10), (0.42, 0)])}, win=(0.5, 0.9))
    cont, fill = cut_contour(c)
    A = c.A(p)
    q = ss(seg(u, 0.04, 0.44))
    img = A
    if u >= 0.47:
        B = c.B(p)
        s = K(u, [(0.5, W + H + 60), (0.92, -260, 'io')])
        diag = XX + YY
        peeled = soft(diag - s, 2)
        flap = ((diag < s) & (diag > s - 220 * math.sin(math.pi * seg(u, 0.5, 0.92)))).astype(np.float32)
        img = mix(A, B, peeled)
        img = img * (1 - 0.35 * np.clip(1 - (diag - s) / 60, 0, 1) * (diag >= s))[..., None]
        back = E.hexrgb('#EDE6D8')[None, None] * (0.75 + 0.25 * np.clip((s - diag) / 220, 0, 1))[..., None]
        img = mix(img, back, flap)
        # 剪下来的她：纸色留边 + 新造型，略微抬起并投影
        lift = math.sin(math.pi * seg(u, 0.47, 0.62)) * 6 + 4 * (1 - seg(u, 0.9, 1.0))
        fade = 1 - seg(u, 0.9, 1.0)
        ab = cv2.dilate(E.render_char(c.sb.no, p, 'flat')[..., 3], np.ones((3, 3), np.uint8))
        cut = mix(np.ones((H, W, 3), np.float32) * E.hexrgb('#F8F3E8'), B, ab)
        sh = E.shifted(E.blur(fill, 8), 10, 14) * 0.35 * fade
        img = img * (1 - sh[..., None])
        a_cut = np.maximum(fill * fade, ab * fill)
        img = mix(img, E.shifted(cut, -lift * 0.6, -lift), E.shifted(a_cut, -lift * 0.6, -lift))
        return np.clip(img, 0, 1)
    # 剪的过程：虚线剪痕 + 剪刀
    n = len(cont)
    kk = int(q * (n - 1))
    if kk > 2:
        m = np.zeros((H, W), np.float32)
        pts = cont[:kk].astype(np.int32)
        for j in range(0, kk - 12, 24):
            cv2.polylines(m, [pts[j:j + 12]], False, 1.0, 4, cv2.LINE_AA)
        img = E.over_rgb(img, E.hexrgb('#1A1014'), m)
    if 0.02 < u < 0.46:
        x, y = cont[min(kk, n - 1)]
        x2, y2 = cont[min(kk + 6, n - 1)]
        op = 16 * abs(math.sin(u * 70))
        img = E.over(img, svg(scissors_svg(x, y, math.atan2(y2 - y, x2 - x), op)))
    return np.clip(img, 0, 1)


# ================================================================== 05 Dear Friend → 一个人跳舞：拉灯绳，关灯，霓虹一根根亮起
def t_switch(c):
    u = c.u
    p = c.pose({'armR': K(u, [(0, 62), (0.16, 120), (0.28, 130), (0.36, 96), (0.44, 100)]),
                'armL': K(u, [(0, 62), (0.2, 30)]), 'sq': K(u, [(0.28, 1.0), (0.34, 0.92), (0.42, 1.0)]),
                'eye_dx': K(u, [(0, 0), (0.12, 12), (0.4, 8)]), 'eye_dy': K(u, [(0, 0), (0.12, -16), (0.36, -10), (0.45, 0)]),
                'eye_mode': 'open'}, win=(0.42, 0.62))
    tip = E.arm_tip(p, 'R')
    if u < 0.5:
        img = c.A(p)
        drop = ss(u / 0.18)
        if u < 0.24:
            tx, ty = tip[0] + 20, E.lerp(-60, tip[1] - 16, drop)
        else:
            tx, ty = tip[0], tip[1] - 10
        lay = svg(f'<path d="M{tx:.1f},-20 L{tx:.1f},{ty - 24:.1f}" stroke="#7A5A3A" stroke-width="5"/>'
                  f'<path d="M{tx - 16:.1f},{ty - 26:.1f} L{tx + 16:.1f},{ty - 26:.1f} L{tx + 22:.1f},{ty + 12:.1f} L{tx - 22:.1f},{ty + 12:.1f} Z" fill="#F2C94C"/>')
        lay = fx.torn_paper(lay, 0, 0, seed=551, rim=4, inner=False)
        img = fx.drop_shadow(img, lay[..., 3], 6, 8, 5, 0.3)
        img = E.over(img, lay)
        dim = 1 - 0.86 * ss(seg(u, 0.38, 0.45))
        return np.clip(img * dim, 0, 1)
    B = c.B(p)
    key = 'neoncells'
    if key not in _MEMO:
        nz = E.noise(H, W, 170, 561, octaves=2)
        nz = (nz - nz.min()) / (nz.max() - nz.min() + 1e-6)
        _MEMO[key] = (0.48 + 0.18 * XX / W + 0.12 * nz).astype(np.float32)
    t_on = _MEMO[key].copy()
    cam = c.ca(p, 15)
    t_on = np.where(cam > 0.5, np.minimum(t_on, 0.0) + 0.8, t_on)
    on = np.clip((u - t_on) / 0.07, 0, 1)
    flick = 1.0
    for (tc, depth) in ((0.58, 0.3), (0.72, 0.25)):        # 灯管启动时整体闪几下
        flick *= 1 - depth * math.exp(-((u - tc) / 0.012) ** 2)
    dark = B * 0.2 + 0.015
    img = dark + (B - dark) * (on * flick)[..., None]
    return np.clip(img * (0.3 + 0.7 * ss(seg(u, 0.44, 0.52))) + B * 0 , 0, 1)


# ================================================================== 06 一个人跳舞 → 思念：浮世绘巨浪拍进来，她踩上浪头被送进海里
SLOPE = 0.42


def face_x(X, y):
    return X + SLOPE * (905 - y)


def wave_svg(X, ph):
    """浮世绘卷浪：斜坡浪面 → 高耸浪尖 → 向前卷的浪舌与白色浪爪，背面缓降。"""
    face = [(face_x(X, y), y) for y in (1100, 905, 760, 620, 480, 360)]
    crest = [(X + 230, 230), (X + 300, 150), (X + 210, 105), (X + 80, 120), (X - 40, 170), (X - 110, 250), (X - 120, 320)]
    back = [(X + 520, 160), (X + 760, 260), (X + 900, 420), (X + 960, 640), (X + 960, 1100)]
    pts = face + crest[::-1][:0] + [(X + 150, 300), (X + 230, 230)] + crest[1:2] + back
    body = 'M' + ' L'.join(f'{x:.0f},{y:.0f}' for x, y in pts) + ' Z'
    out = [f'<defs><clipPath id="wb"><path d="{body}"/></clipPath></defs>',
           f'<path d="{body}" fill="#23408E"/><g clip-path="url(#wb)">']
    out.append(f'<path d="M{face_x(X, 1100):.0f},1100 L{face_x(X, 300):.0f},300 L{face_x(X, 300) + 160:.0f},300 L{face_x(X, 1100) + 160:.0f},1100 Z" '
               f'fill="#4A6CC0" opacity="0.55"/>')                       # 浪面晕色（靠前更亮）
    for k_, o in enumerate(range(24, 860, 34)):
        col = ('#6E8BD4', '#3B5BA8', '#16152A')[k_ % 3]
        wd = (6, 8, 3)[k_ % 3]
        d = 'M' + ' L'.join(f'{face_x(X, y) + o * (1 + (905 - y) / 1600):.0f},{y + 0.06 * o:.0f}' for y in range(1100, 200, -50))
        out.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{wd}" stroke-linecap="round" opacity="0.85"/>')
    out.append(f'</g><path d="{body}" fill="none" stroke="#16152A" stroke-width="8" stroke-linejoin="round"/>')
    for j in range(9):                                   # 浪面飞起的泡沫
        y = 820 - 70 * j
        out.append(f'<circle cx="{face_x(X, y) - 8:.0f}" cy="{y}" r="{7 + (j % 3) * 3}" fill="#F3ECDD" stroke="#16152A" stroke-width="3"/>')
    lip = 'M' + ' L'.join(f'{x:.0f},{y:.0f}' for x, y in [(X + 150, 300)] + crest) + f' Q{X - 60},{360} {X + 40},{330} Q{X + 110},{310} {X + 150},{300} Z'
    out.append(f'<path d="{lip}" fill="#F3ECDD" stroke="#16152A" stroke-width="7" stroke-linejoin="round"/>')
    for j in range(7):                                   # 浪爪
        bx, by = X - 110 + 34 * j, 320 - 22 * j + 6 * math.sin(ph + j)
        out.append(f'<path d="M{bx:.0f},{by:.0f} q-22,26 0,44 q-6,-18 14,-24 q-4,16 12,22 q-2,-20 10,-30 Z" fill="#F3ECDD" stroke="#16152A" stroke-width="4"/>')
    for j in range(16):                                  # 飞沫
        a = j * 0.9 + ph
        r = 6 + 4 * (j % 3)
        out.append(f'<circle cx="{X + 40 + 140 * math.cos(a):.0f}" cy="{120 - 60 * abs(math.sin(a * 1.3)) - 10 * (j % 4):.0f}" r="{r}" '
                   f'fill="#F3ECDD" stroke="#16152A" stroke-width="3"/>')
    return ''.join(out)


def t_wave(c):
    u = c.u
    x = K(u, [(0.28, c.pa['x']), (0.42, 900, 'io'), (0.62, 760), (0.86, c.pb['x'], 'io')])
    yfeet = K(u, [(0.28, c.pa['y']), (0.42, 640, 'out'), (0.62, 640), (0.86, c.pb['y'], 'in')])
    # 浪：先从右边涌来，她跳上浪面后浪托着她走，最后浪从她脚下加速通过
    X_ride = x - SLOPE * (905 - yfeet) + 10
    X = K(u, [(0, 2300), (0.3, c.pa['x'] + 260, 'out')]) if u < 0.3 else \
        (E.lerp(c.pa['x'] + 260, X_ride, ss(seg(u, 0.3, 0.42))) if u < 0.42 else
         (X_ride if u < 0.62 else E.lerp(X_ride, -1300, E.ease_in(seg(u, 0.62, 0.95)))))
    p = c.pose({'x': x, 'y': yfeet, 'hop': 120 * arc(u, 0.28, 0.42),
                'lean': K(u, [(0.26, 0), (0.42, -14), (0.62, -10), (0.8, 4), (0.9, 0)]),
                'armL': K(u, [(0.2, 120), (0.36, 80), (0.62, 95), (0.82, 60)]), 'armR': K(u, [(0.2, 110), (0.36, 30), (0.62, 45), (0.82, 40)]),
                'sq': K(u, [(0.2, 1.0), (0.27, 0.86), (0.33, 1.08), (0.42, 0.92), (0.62, 0.94), (0.86, 0.84), (0.95, 1.02)]),
                'legs': (0, 12, 0, 12), 'hat': -8, 'eye_mode': 'happy' if 0.4 < u < 0.86 else 'open', 'eye_dx': -14}, win=(0.6, 1.0))
    A, B = c.A(p), c.B(p)
    ca = c.ca(p)
    m = soft(XX - (face_x(X, YY) + 30), 3)                       # 浪面之后就是新世界
    m = np.maximum(m, ca * ss(seg(u, 0.38, 0.44)))                # 她踩上浪面时换成浮世绘造型
    img = mix(A, B, m)
    img = over_behind(img, svg(wave_svg(X, u * 9)), ca)
    sp = arc(u, 0.36, 0.5)                                        # 落上浪面时炸开的浪花遮住换装
    if sp > 0:
        fx_, fy_ = E.to_screen(p, (800, 1080))
        body = ''.join(f'<circle cx="{fx_ + (40 + 220 * sp) * math.cos(a):.0f}" cy="{fy_ - 120 - (60 + 260 * sp) * abs(math.sin(a)):.0f}" '
                       f'r="{(26 + 26 * (j % 3)) * (0.6 + 0.6 * sp):.0f}" fill="#F3ECDD" stroke="#16152A" stroke-width="4"/>'
                       for j, a in enumerate(np.linspace(0.2, math.pi - 0.2, 13)))
        img = E.over(img, svg(body), min(1.0, sp / 0.15))
    return np.clip(img, 0, 1)


# ================================================================== 07 思念 → 梦一场：打哈欠、闭眼，画笔一笔笔把世界涂成油画
def strokes_list():
    if 'strokes' not in _MEMO:
        rng = np.random.default_rng(711)
        out = []
        for k in range(170):
            x, y = rng.uniform(-80, W + 80), rng.uniform(-60, H + 60)
            rank = 0.65 * (x / W) + 0.35 * rng.uniform()
            out.append((x, y, rng.uniform(-0.6, 0.6) + 0.25, rng.uniform(320, 560), rng.uniform(110, 170), 0.3 + 0.48 * rank))
        _MEMO['strokes'] = out
        _MEMO['bristle'] = fx.stroke_texture(H, W, 712, angle=20, length=40)
    return _MEMO['strokes']


def t_dream(c):
    u = c.u
    p = c.pose({'armL': K(u, [(0, 19), (0.12, 135, 'out'), (0.26, 130), (0.38, 0), (0.86, 4)]),
                'armR': K(u, [(0, 30), (0.12, 135, 'out'), (0.26, 130), (0.38, 0), (0.86, 4)]),
                'sq': K(u, [(0, 1.0), (0.12, 1.05), (0.3, 1.0), (0.42, 0.88), (0.85, 0.9), (0.95, 1.0)]),
                'hop': 46 * arc(u, 0.36, 0.92), 'x': K(u, [(0.34, c.pa['x']), (0.88, c.pb['x'], 'io')]),
                'y': K(u, [(0.34, c.pa['y']), (0.88, c.pb['y'], 'io')]), 'lean': 5 * math.sin(u * 6),
                'eye_mode': 'closed' if 0.1 < u < 0.9 else 'open', 'hat': 8 * arc(u, 0.0, 0.3)}, win=(0.34, 0.92))
    A, B = c.A(p), c.B(p)
    m = np.zeros((H, W), np.float32)
    for (x, y, a, L, w, t0) in strokes_list():
        g = seg(u, t0, t0 + 0.07)
        if g <= 0:
            continue
        dx, dy = math.cos(a) * L / 2 * g, math.sin(a) * L / 2 * g
        x0, y0 = x - math.cos(a) * L / 2, y - math.sin(a) * L / 2
        cv2.line(m, (int(x0), int(y0)), (int(x0 + 2 * dx), int(y0 + 2 * dy)), 1.0, int(w), cv2.LINE_AA)
    br = _MEMO['bristle']
    m = np.clip(E.blur(m, 2) * (0.75 + 0.5 * br) - 0.15 * (1 - E.blur(m, 6)), 0, 1)
    m = np.maximum(m, ss(seg(u, 0.88, 1.0)))
    img = mix(A, B, m)
    edge = np.clip(1 - np.abs(m - 0.5) * 2, 0, 1)
    img = img * (1 - 0.18 * edge[..., None])
    return np.clip(img, 0, 1)


# ================================================================== 08 梦一场 → 舞娘：推开大殿的门，镜头跟她走进去
def door_svg(a_deg, alpha):
    ca = math.cos(math.radians(a_deg))
    lw = 260 * ca
    leaf = lambda x0, w: (f'<rect x="{x0:.1f}" y="445" width="{w:.1f}" height="460" fill="#4A2C1C" stroke="#1A1210" stroke-width="6"/>'
                          f'<rect x="{x0 + w * 0.12:.1f}" y="480" width="{w * 0.76:.1f}" height="170" fill="#5A3622" stroke="#1A1210" stroke-width="4"/>'
                          f'<rect x="{x0 + w * 0.12:.1f}" y="690" width="{w * 0.76:.1f}" height="170" fill="#5A3622" stroke="#1A1210" stroke-width="4"/>'
                          + ''.join(f'<circle cx="{x0 + w * f:.1f}" cy="{yy}" r="6" fill="#1A1210"/>' for f in (0.2, 0.8) for yy in (470, 670, 880)))
    frame = ('<path d="M660,905 L660,445 Q660,300 960,230 Q1260,300 1260,445 L1260,905 L1220,905 L1220,445 '
             'Q1220,330 960,272 Q700,330 700,445 L700,905 Z" fill="#2A1A12" stroke="#120C0A" stroke-width="6"/>')
    arch = ('<path d="M700,445 Q700,330 960,272 Q1220,330 1220,445 Z" fill="#3A2318" stroke="#1A1210" stroke-width="5"/>'
            if a_deg < 1 else '')
    return f'<g opacity="{alpha:.3f}">{frame}{arch}{leaf(700, lw)}{leaf(1220 - lw, lw)}</g>'


def door_opening(a_deg):
    lw = 260 * math.cos(math.radians(a_deg))
    m = svg(f'<path d="M{700 + lw:.1f},905 L{700 + lw:.1f},445 Q700,330 960,272 Q1220,330 {1220 - lw:.1f},445 L{1220 - lw:.1f},905 Z" fill="#fff"/>')
    return m[..., 3] if a_deg > 0.5 else np.zeros((H, W), np.float32)


def t_door(c):
    u = c.u
    walk = u < 0.36
    g = gait(seg(u, 0.0, 0.36) * 3, 16, 8, 24, 14) if walk else gait(seg(u, 0.58, 1.0) * 3, 14, 7, 20, 14)
    over = dict(g)
    over.update({'x': K(u, [(0, c.pa['x']), (0.36, 960, 'io')]), 'y': 905, 'eye_mode': 'open', 'eye_dx': K(u, [(0, -10), (0.36, 0)]),
                 'eye_dy': K(u, [(0.36, 0), (0.45, -8), (0.6, 0)])})
    if 0.36 <= u < 0.58:
        over.update({'armL': K(u, [(0.36, 14), (0.44, 118, 'out'), (0.58, 100)]), 'armR': K(u, [(0.36, 14), (0.44, 118, 'out'), (0.58, 100)]),
                     'sq': K(u, [(0.36, 1.0), (0.42, 0.92), (0.5, 1.04), (0.58, 1.0)]), 'hop': 0, 'legs': (0, 0, 0, 0)})
    p = c.pose(over, win=(0.55, 1.0))
    ang = 82 * ss(seg(u, 0.4, 0.6))
    Z = 1 + 4.6 * E.ease_in(seg(u, 0.55, 1.0))
    xa = zoom_xf(Z, 960, 600)
    kB = E.lerp(0.62, 1.0, ss(seg(u, 0.5, 1.0)))
    cb = (960, E.lerp(600, 540, ss(seg(u, 0.8, 1.0))))
    xb = (kB, cb[0] - kB * 960, cb[1] - kB * 540)
    A, B = c.A(p, xa), c.B(p, xb)
    dalpha = ss(u / 0.18)
    door = warp_world(svg(door_svg(ang, dalpha)), xa)
    if 'doortex' not in _MEMO:
        _MEMO['doortex'] = fx.stroke_texture(H, W, 811, angle=80, length=24)
    door[..., :3] = fx.impasto(door[..., :3], _MEMO['doortex'], strength=4.0)
    opening = warp_world(np.dstack([np.zeros((H, W, 3), np.float32), door_opening(ang)]), xa)[..., 3] * dalpha
    opening = np.maximum(opening, ss(seg(u, 0.93, 1.0)))
    ca = c.ca(p)
    img = over_behind(A, door, ca * (1 - opening))
    img = mix(img, B, opening)
    glow = E.blur(opening, 40) * 0.5 * ss(seg(u, 0.42, 0.6)) * (1 - seg(u, 0.85, 1.0))
    img = img + glow[..., None] * E.hexrgb('#FFB357')
    return np.clip(img, 0, 1)


# ================================================================== 09 舞娘 → 开始懂了：花窗碎落，露出粉笔世界
def shards(c, hx, hy):
    if 'shards' not in _MEMO:
        from scipy.spatial import cKDTree
        rng = np.random.default_rng(911)
        pts = np.concatenate([np.stack([rng.normal(hx, 260, 50), rng.normal(hy, 220, 50)], 1),
                              np.stack([rng.uniform(0, W, 80), rng.uniform(0, H, 80)], 1)])
        tree = cKDTree(pts)
        sx, sy = np.meshgrid(np.arange(0, W, 2), np.arange(0, H, 2))
        _, lab = tree.query(np.stack([sx.ravel(), sy.ravel()], 1))
        lab = cv2.resize(lab.reshape(sx.shape).astype(np.float32), (W, H), interpolation=cv2.INTER_NEAREST).astype(np.int32)
        cells = []
        for i in range(len(pts)):
            ys, xs = np.nonzero(lab == i)
            if len(xs) == 0:
                continue
            x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
            cx, cy = xs.mean(), ys.mean()
            dist = math.hypot(cx - hx, cy - hy)
            cells.append(dict(i=i, box=(x0, y0, x1, y1), c=(cx, cy), rel=0.28 + 0.3 * min(1, dist / 1300) + rng.uniform(0, 0.05),
                              vx=(cx - hx) * 0.5 + rng.uniform(-120, 120), vy=-rng.uniform(80, 320), w=rng.uniform(-240, 240)))
        e = (np.abs(np.diff(lab, axis=1, append=lab[:, -1:])) + np.abs(np.diff(lab, axis=0, append=lab[-1:]))) > 0
        lead = cv2.dilate(e.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
        _MEMO['shards'] = (lab, cells, lead)
    return _MEMO['shards']


def t_shatter(c):
    u = c.u
    p = c.pose({'armL': K(u, [(0, 44), (0.2, 140, 'out'), (0.4, 130)]), 'armR': K(u, [(0, 44), (0.2, 140, 'out'), (0.4, 130)]),
                'eye_mode': 'closed' if u < 0.4 else 'open', 'eye_dy': K(u, [(0.4, -12), (0.7, -6)]),
                'sq': K(u, [(0.14, 1.0), (0.2, 1.05), (0.3, 1.0)]), 'flare': K(u, [(0, 1.03), (0.2, 1.2), (0.4, 1.1)])}, win=(0.4, 0.92))
    hx, hy = E.to_screen(c.pa, (800, 800))
    lab, cells, lead = shards(c, hx, hy)
    if u < 0.27:
        img = c.A(p)
        k = ss(seg(u, 0.16, 0.27))
        img = img * (1 - 0.9 * k * lead[..., None]) + k * E.blur(lead, 6)[..., None] * E.hexrgb('#FFE6B0') * 0.6
        return np.clip(img, 0, 1)
    if 'shatterA' not in _MEMO:
        pf = c.pose({'armL': 140, 'armR': 140, 'eye_mode': 'closed', 'flare': 1.2}, win=(0.4, 0.92), u=0.27)
        Af = c.A(pf, t=c.sa.core + 0.27 * c.T)
        _MEMO['shatterA'] = Af * (1 - 0.9 * lead[..., None]) + E.blur(lead, 6)[..., None] * E.hexrgb('#FFE6B0') * 0.6
    Af = _MEMO['shatterA']
    img = c.B(p)
    rel = np.zeros(len(cells) + 200)
    still = np.zeros((H, W), bool)
    for cl in cells:
        if u < cl['rel']:
            still |= (lab == cl['i'])
    img = np.where(still[..., None], Af, img)
    for cl in cells:
        if u < cl['rel']:
            continue
        dt = (u - cl['rel']) * c.T
        tx = cl['vx'] * dt
        ty = cl['vy'] * dt + 0.5 * 4600 * dt * dt
        if ty > H + 200:
            continue
        x0, y0, x1, y1 = cl['box']
        pad = 40
        x0p, y0p, x1p, y1p = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad)
        crop = Af[y0p:y1p, x0p:x1p]
        msk = (lab[y0p:y1p, x0p:x1p] == cl['i']).astype(np.float32)
        ccx, ccy = cl['c'][0] - x0p, cl['c'][1] - y0p
        M = cv2.getRotationMatrix2D((ccx, ccy), cl['w'] * dt, 1.0)
        M[0, 2] += x0p + tx
        M[1, 2] += y0p + ty
        piece = cv2.warpAffine(crop, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
        pm = cv2.warpAffine(msk, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
        edge = np.clip(pm - cv2.erode(pm, np.ones((5, 5), np.uint8)), 0, 1)
        piece = piece * (1 - edge[..., None]) + E.hexrgb('#120E18') * edge[..., None]
        img = mix(img, piece * (1 - 0.3 * min(1, dt)), pm * (1 - ss(seg(u, 0.8, 0.97))))
    return np.clip(img, 0, 1)


# ================================================================== 10 开始懂了 → 君：镜头后拉，原来是墙上的画，她从画框里跨出来
def t_frame_out(c):
    """三段：① 镜头后拉，粉笔画缩成墙上的一幅画，她在画里下蹲蓄力；② 一个连续的跳跃弧线从画框下沿跳出来，
    越过画框边时身体逐步换成新造型，离开画框后才随透视变大；③ 落地压扁回弹。画里画外只有一个她。"""
    u = c.u
    q = ss(seg(u, 0.0, 0.38))
    k = E.lerp(1.0, 0.36, q)
    cx, cy = E.lerp(960, 560, q), E.lerp(540, 360, q)
    xa = (k, cx - k * 960, cy - k * 540)
    kf, cxf, cyf = 0.36, 560, 360
    x_in = cxf - kf * 960 + kf * c.pa['x']
    y_in = cyf - kf * 540 + kf * c.pa['y']
    s_in = c.pa['s'] * kf
    jump = seg(u, 0.4, 0.82)
    e = E.smooth(jump)
    if u < 0.42:
        x, y, s_ = xa[1] + k * c.pa['x'], xa[2] + k * c.pa['y'], c.pa['s'] * k
    else:
        x = E.lerp(x_in, c.pb['x'], e)
        y = E.lerp(y_in, c.pb['y'], E.smooth(seg(u, 0.46, 0.82)))
        s_ = E.lerp(s_in, c.pb['s'], E.smooth(seg(u, 0.46, 0.88)))
    p = c.pose({'x': x, 'y': y, 's': s_, 'hop': 200 * s_ / 0.9 * math.sin(math.pi * jump) if 0 < jump < 1 else 0.0,
                'sq': K(u, [(0.3, 1.0), (0.37, 0.88), (0.43, 1.08, 'out'), (0.6, 1.0), (0.82, 1.0), (0.87, 0.86), (0.95, 1.03), (1.0, 1.0)]),
                'armL': K(u, [(0.3, 6), (0.4, -10), (0.48, 125, 'out'), (0.74, 110), (0.86, 50)]),
                'armR': K(u, [(0.3, 6), (0.4, -10), (0.48, 125, 'out'), (0.74, 110), (0.86, 50)]),
                'legs': (18, 18, 18, 18) if 0.42 < u < 0.82 else (0, 0, 0, 0),
                'lean': K(u, [(0.42, 0), (0.55, 6), (0.78, -2), (0.92, 0)]),
                'eye_mode': 'happy' if 0.44 < u < 0.86 else 'open', 'eye_dx': 8, 'eye_dy': K(u, [(0.42, 0), (0.6, 8), (0.8, 0)])},
               win=(0.6, 1.0))
    A = c.A(p, xa)
    B = c.B(p)
    Bbg = c.B(dict(p, x=-6000))
    out_bg = mix(Bbg, B, np.full((H, W), ss(seg(u, 0.78, 0.9)), np.float32))      # 落地后她的影子才出现在地板上
    x0, y0, x1, y1 = xa[1], xa[2], xa[1] + k * W, xa[2] + k * H
    dout = np.maximum(np.maximum(x0 - XX, XX - x1), np.maximum(y0 - YY, YY - y1))
    m = soft(dout, 1.5)
    ca = c.ca(p)
    img = mix(A, out_bg, m)
    cb = E.render_char(c.sb.no, p, 'flat')[..., 3]
    out_char = np.clip(cb * np.maximum(m, ss(seg(u, 0.62, 0.7))), 0, 1)            # 越过画框的部分是新造型；完全出来后整个换掉
    img = mix(img, B, out_char)
    fa = ss(seg(u, 0.06, 0.24))
    if fa > 0:
        th = 30
        band = ((dout > 0) & (dout < th)).astype(np.float32)
        gold = np.dstack([np.full((H, W), 0.80, np.float32), np.full((H, W), 0.62, np.float32), np.full((H, W), 0.34, np.float32)])
        gold = gold * (0.75 + 0.35 * np.clip(1 - dout / th, 0, 1))[..., None]
        sh = E.shifted(E.blur(((dout < th)).astype(np.float32), 18), 10, 16) * 0.35 * (dout >= th)
        lay = np.dstack([gold, band * fa])
        img = img * (1 - (sh * fa * (1 - ca))[..., None])
        img = over_behind(img, lay, ca * (u > 0.44))
    return np.clip(img, 0, 1)


# ================================================================== 11 君 → 落叶归根：走向一盏灯，墙上的影子越拉越大，影子里就是皮影世界
LAMP = (2250, 1060)                 # 画外右侧低处的一盏灯，把她的影子投向左边的墙


def t_shadow(c):
    u = c.u
    g = gait(seg(u, 0.05, 0.7) * 4, 12, 7, 16, 14)
    over = dict(g)
    over.update({'x': K(u, [(0.05, c.pa['x']), (0.72, c.pb['x'], 'io')]), 'y': K(u, [(0.05, c.pa['y']), (0.72, c.pb['y'], 'io')]),
                 's': K(u, [(0.05, c.pa['s']), (0.72, c.pb['s'], 'io')]), 'eye_dx': -14, 'eye_dy': 6, 'eye_mode': 'open'})
    p = c.pose(over, win=(0.6, 1.0))
    A, B = c.A(p), c.B(p)
    la = ss(u / 0.12)
    lamp = None
    sil = E.render_char(c.sa.no, p, 'flat')[..., 3]
    f = K(u, [(0.0, 1.3), (0.58, 1.0, 'io'), (0.66, 1.0), (1.0, 11.0, 'in')])      # 墙上的影子先滑过来与她重合，再胀满世界
    M = np.float32([[f, 0, LAMP[0] * (1 - f)], [0, f, LAMP[1] * (1 - f)]])
    shadow = cv2.warpAffine(sil, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
    shadow = E.blur(shadow, 2 + 0.8 * f)
    m = np.clip((shadow - 0.4) * 3, 0, 1) * la                                          # 墙上的影子 = 新世界的窗口
    sild = cv2.dilate(sil, np.ones((9, 9), np.uint8))
    me = sild * ss(seg(u, 0.5, 0.62))                                                  # 影子与她重合时，她融进影子
    end = ss(seg(u, 0.86, 1.0))
    Bbg = c.B(dict(p, x=-6000))                                                        # 影子里只有新世界的背景，不出现第二个她
    Ad = A * (1 - 0.6 * ss(seg(u, 0.4, 0.55)) * sil[..., None])                         # 先变成剪影
    pen = np.clip(shadow * 2.2, 0, 1) * (1 - m) * 0.45 * la * (1 - sild)
    img = mix(Ad * (1 - pen[..., None]), Bbg, m * (1 - sild))                          # 影子在墙上、在她身后
    img = mix(img, B, np.maximum(me, end))
    img = img + (E.radial(1980, 900, 900) ** 2 * 0.4 * la)[..., None] * E.hexrgb('#FFC86A')
    return np.clip(img, 0, 1)


# ================================================================== 12 落叶归根 → 有趣：一阵风卷起落叶围着她转，叶子散开时已在作业纸上
def leaves(c):
    if 'leaves' not in _MEMO:
        rng = np.random.default_rng(1211)
        _MEMO['leaves'] = [(rng.uniform(0, 2 * math.pi), rng.uniform(0.1, 1.0), rng.uniform(16, 34), rng.integers(0, 4),
                            rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.8, 1.25)) for _ in range(120)]
    return _MEMO['leaves']


LEAF_COLS = ['#C2502A', '#E08A2E', '#8E3A1E', '#F2B33A']


def t_whirl(c):
    u = c.u
    p = c.pose({'armL': K(u, [(0, 8), (0.12, 125), (0.5, 120), (0.7, 70)]), 'armR': K(u, [(0, 60), (0.12, 125), (0.5, 120), (0.7, 70)]),
                'hair': 8 * math.sin(u * 20), 'skirt': 5 * math.sin(u * 17), 'hop': 20 * arc(u, 0.55, 0.8),
                'eye_mode': 'closed' if 0.12 < u < 0.55 else 'happy', 'lean': 3 * math.sin(u * 14)}, win=(0.3, 0.9))
    cx, cy = E.to_screen(p, (800, 830))
    A, B = c.A(p), c.B(p)
    R = K(u, [(0.22, 0), (1.0, 2400, 'in')])
    th = np.arctan2(YY - cy, XX - cx)
    d = np.hypot(XX - cx, YY - cy)
    Reff = R * (1 + 0.2 * np.sin(3 * th - 12 * u)) + 40 * (R > 0)
    m = soft(Reff - d, 4) * (R > 0)
    m = np.maximum(m, ss(seg(u, 0.9, 1.0)))
    img = mix(A, B, m)
    body = []
    gather = ss(seg(u, 0.0, 0.3))
    for (a0, r0, sz, ci, sx, sy, sp) in leaves(c):
        ang = a0 + sp * u * 2 * math.pi * 1.8
        rr = max(R, 180) * (0.75 + 0.5 * r0) + 60 * r0
        tx, ty = cx + rr * math.cos(ang), cy + 0.62 * rr * math.sin(ang)
        x, y = E.lerp(sx, tx, gather), E.lerp(sy, ty, gather)
        if not (-60 < x < W + 60 and -60 < y < H + 60):
            continue
        rot = math.degrees(ang) + 90
        body.append(f'<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.1f})"><path d="M{-sz},0 Q0,{-sz * 0.6} {sz},0 Q0,{sz * 0.6} {-sz},0 Z" '
                    f'fill="{LEAF_COLS[ci]}" stroke="#3A1E10" stroke-width="2.5"/><path d="M{-sz},0 L{sz},0" stroke="#3A1E10" stroke-width="1.5"/></g>')
    fade = 1 - ss(seg(u, 0.88, 1.0))
    if body:
        img = E.over(img, svg(''.join(body)), fade)
    return np.clip(img, 0, 1)


# ================================================================== 13 有趣 → 片尾：作业纸揉成纸团，她颠两下，一脚踢飞
BALL0 = (1360, 470)


def crumple(A, C, R, k, seed=1311):
    """把 A 压缩进以 C 为中心、半径约 R 的皱纸团；k = R / 原尺寸。"""
    if 'crn' not in _MEMO:
        _MEMO['crn'] = (E.noise(H, W, 260, seed, octaves=2), E.noise(H, W, 260, seed + 1, octaves=2), E.noise(H, W, 70, seed + 2, octaves=2))
    nx, ny, cr = _MEMO['crn']
    wr = 1 - k
    amp = 220 * math.sin(math.pi * min(1.0, wr * 1.1)) / k
    sxm = C[0] + (XX - C[0]) / k + (nx - 0.5) * amp
    sym = C[1] + (YY - C[1]) / k + (ny - 0.5) * amp
    img = cv2.remap(A, sxm.astype(np.float32), sym.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                    borderValue=(0.9, 0.88, 0.84))
    crease = np.abs(cr - 0.5) * 2
    img = img * (1 - 0.18 * wr * np.clip(1 - crease * 7, 0, 1))[..., None] * (1 - 0.12 * wr * (cr[..., None] - 0.5))
    th = np.arctan2(YY - C[1], XX - C[0])
    Rb = R * (1 + 0.14 * wr * np.sin(7 * th) + 0.08 * wr * np.sin(13 * th + 1))
    d = np.hypot(XX - C[0], YY - C[1])
    m = soft(Rb - d, 2)
    shade = 1 - 0.35 * wr * np.clip(d / np.maximum(Rb, 1), 0, 1) ** 3
    return img * shade[..., None], m


def t_crumple(c):
    u = c.u
    head_bump = arc(u, 0.5, 0.6)
    kick = arc(u, 0.7, 0.82)
    p = c.pose({'x': 960, 'y': K(u, [(0, c.pa['y']), (0.45, c.pb['y'], 'io')]), 's': K(u, [(0, c.pa['s']), (0.45, c.pb['s'], 'io')]),
                'sq': 1 - 0.08 * head_bump - 0.06 * kick, 'legs': (0, 0, 34 * kick, 0), 'lean': -6 * kick + K(u, [(0.85, 0), (0.95, -4)]),
                'armL': K(u, [(0, 65), (0.4, 90), (0.7, 40), (0.85, 70), (0.95, 20)]), 'armR': K(u, [(0, 65), (0.4, 90), (0.7, 40), (0.85, 70), (0.95, 20)]),
                'eye_mode': 'happy' if 0.82 < u < 0.92 else 'open',
                'eye_dx': K(u, [(0, 0), (0.2, 16), (0.45, 4), (0.62, 0), (0.75, 6), (0.9, 18), (0.97, -16)]),
                'eye_dy': K(u, [(0, 0), (0.2, -14), (0.5, -18), (0.62, -16), (0.72, 14), (0.82, -16), (0.97, 0)])}, win=(0.0, 1.0))
    B = c.B(p)
    head = E.to_screen(p, (800, 540))
    foot = E.to_screen(p, (854, 1080))
    q = ss(seg(u, 0.04, 0.42))
    R = E.lerp(2300, 210, q)
    kk = R / 2300
    if u < 0.42:
        A = c.A(p)
        ball, m = crumple(A, BALL0, max(R * 0.45, 90) if q > 0.6 else R * 0.45 + 1200 * (1 - q) ** 3, kk)
        img = mix(B, ball, m)
        sh = E.shifted(E.blur(m, 20), 14, 22) * 0.3 * (1 - m) * q
        return np.clip(img * (1 - sh[..., None]) + 0, 0, 1) if True else img
    if 'ballspr' not in _MEMO:
        pf = c.pose({'x': 960}, u=0.42)
        Af = c.A(pf, t=c.sa.core + 0.42 * c.T)
        ball, m = crumple(Af, BALL0, 94, 210 / 2300)
        x0, y0 = BALL0[0] - 130, BALL0[1] - 130
        _MEMO['ballspr'] = (np.dstack([ball, m])[y0:y0 + 260, x0:x0 + 260].copy())
    spr = _MEMO['ballspr']
    bx = K(u, [(0.42, BALL0[0]), (0.56, head[0] + 10, 'in'), (0.66, 1060), (0.72, foot[0] + 40, 'in'), (0.97, 2200, 'out')])
    by = K(u, [(0.42, BALL0[1]), (0.56, head[1] - 60, 'in'), (0.63, head[1] - 300, 'out'), (0.72, foot[1] - 90, 'in'),
               (0.97, -260, 'out')])
    rot = 900 * u
    M = cv2.getRotationMatrix2D((130, 130), rot, 0.85)
    M[0, 2] += bx - 130
    M[1, 2] += by - 130
    lay = cv2.warpAffine(spr, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
    img = E.over(B, lay)
    return np.clip(img, 0, 1)


# ------------------------------------------------------------------ 转场表
class Tr:
    def __init__(self, a, b, fn, T, name):
        self.a, self.b, self.fn, self.T, self.name = a, b, fn, T, name

    @property
    def n(self):
        return int(round(self.T * E.FPS))


TRANS = [
    Tr('00', '01', t_pearl, 1.3, '色块化成珍珠'),
    Tr('01', '02', t_takeoff, 1.4, '起飞冲破云海'),
    Tr('02', '03', t_print, 1.4, '四色套印'),
    Tr('03', '04', t_pipe, 1.4, '钻水管'),
    Tr('04', '05', t_scissors, 1.5, '剪下来揭起舞台'),
    Tr('05', '06', t_switch, 1.4, '拉灯绳关灯'),
    Tr('06', '07', t_wave, 1.4, '踩浪冲浪'),
    Tr('07', '08', t_dream, 1.5, '闭眼入梦'),
    Tr('08', '09', t_door, 1.5, '推开大殿的门'),
    Tr('09', '10', t_shatter, 1.4, '花窗碎落'),
    Tr('10', '11', t_frame_out, 1.8, '从画框里跨出来'),
    Tr('11', '12', t_shadow, 1.5, '走进影子'),
    Tr('12', '13', t_whirl, 1.3, '落叶旋风'),
    Tr('13', '14', t_crumple, 1.6, '揉纸团踢飞'),
]


def frame(tr, i, sa, sb):
    return np.clip(tr.fn(C(tr, i, sa, sb)), 0, 1).astype(np.float32)
