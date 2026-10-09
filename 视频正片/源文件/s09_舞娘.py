# -*- coding: utf-8 -*-
"""09《舞娘》—— 彩色玻璃花窗。
意象：幽暗的大殿里，背后一扇玫瑰花窗。Clawd 裹着披风下蹲蓄力 → 猛地张开双臂，褶皱披风像花一样炸开 →
左右换重心踏步，双臂一高一低交替，披风与拖尾跟着甩动 → 深蹲收拢 → 起身高举双臂，彩色光柱一下子亮起 →
披风慢慢落下，她闭上眼，在热闹的光里安静地站着。（不做翻面旋转：二维角色无法真实地 3D 转身。）
画法：真实花窗的做法——人物的脸、身体、头发、内搭长裙都是“一整块彩绘玻璃”，铅条只沿造型结构线和轮廓走，背光透亮、带辉光；
只有羽毛披风切成约 40 片沿披风方向放射的长条玻璃（明暗各异），像一片片羽毛。
场景：夜里的哥特式大殿——尖拱石柱、点满蜡烛的两侧烛台、两座燃烧的火盆（火苗与火星上升）、缭绕的香烟，
背后的玫瑰花窗与彩色光柱、地面上的彩色光斑；整体暗色调，火光与花窗是仅有的光源。
"""
import math
import numpy as np
import cv2
import engine as E
import fx
from scene_base import Scene


CAPE_COLS = ['#B3174F', '#7E0E37', '#DE5486']
BRAZIERS = [(330, 640), (1590, 640)]          # 火盆碗口中心


def cape_shards():
    """披风的长条玻璃（设计坐标）：以领口为中心按角度 × 半径分 10 × 4 = 40 片，顶点轻微抖动，像一片片羽毛。"""
    rng = np.random.default_rng(941)
    cx, cy = 780, 790
    angs = np.linspace(math.radians(-8), math.radians(188), 11)
    rads = [0, 130, 270, 440, 720]
    jit = {}

    def v(i, j):
        if (i, j) not in jit:
            jit[(i, j)] = (rng.uniform(-0.06, 0.06), rng.uniform(-18, 18) if j not in (0, len(rads) - 1) else 0)
        da, dr = jit[(i, j)]
        a, r = angs[i] + (da if 0 < i < len(angs) - 1 else 0), rads[j] + dr
        return cx + r * math.cos(a), cy + r * math.sin(a)
    out = []
    for i in range(len(angs) - 1):
        for j in range(len(rads) - 1):
            pts = [v(i, j), v(i, j + 1), v(i + 1, j + 1), v(i + 1, j)]
            d = 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in pts) + ' Z'
            t = rng.uniform(-1, 1)
            out.append(f'<path d="{d}" fill="{'#FFFFFF' if t > 0 else '#000000'}" fill-opacity="{abs(t) * 0.5:.3f}" '
                       f'stroke="#FF0000" stroke-width="9" stroke-linejoin="round"/>')
    return ''.join(out)


def flame_svg(x, y, h, w, t, ph, col='#FFB347', core='#FFF1C4'):
    sway = 0.18 * math.sin(t * 9 + ph) + 0.1 * math.sin(t * 23 + ph * 2)
    hh = h * (1 + 0.12 * math.sin(t * 13 + ph) + 0.06 * math.sin(t * 31 + ph))
    tx = x + sway * hh * 0.6
    outer = (f'M{x - w},{y} C{x - w},{y - hh * 0.45} {tx - w * 0.2},{y - hh * 0.7} {tx},{y - hh} '
             f'C{tx + w * 0.2},{y - hh * 0.7} {x + w},{y - hh * 0.45} {x + w},{y} Q{x},{y + w * 0.5} {x - w},{y} Z')
    ic = 0.55
    inner = (f'M{x - w * ic},{y} C{x - w * ic},{y - hh * 0.3} {tx - w * 0.1},{y - hh * 0.45} {E.lerp(x, tx, 0.7)},{y - hh * 0.62} '
             f'C{tx + w * 0.1},{y - hh * 0.45} {x + w * ic},{y - hh * 0.3} {x + w * ic},{y} Z')
    return f'<path d="{outer}" fill="{col}"/><path d="{inner}" fill="{core}"/>'


class S09(Scene):
    key = '09'
    filename = '09_舞娘'
    style = '彩色玻璃花窗'
    no = 9
    core = 4.6

    def setup(self):
        h, w = 1080, 1920
        bg = E.vgrad('#0B0A16', '#141026')
        # 玫瑰窗
        cx, cy, R = 960, 215, 190
        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080"><g stroke="#08070D" stroke-width="7">']
        cols = ['#B3174F', '#2F5FB8', '#E0A62E', '#2E8C6A', '#7A2E9E', '#D7563A']
        rng = np.random.default_rng(909)
        for ring, (r0, r1, n) in enumerate([(0, 46, 6), (46, 112, 12), (112, 190, 18)]):
            for k in range(n):
                a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
                p = [(cx + r0 * math.cos(a0), cy + r0 * math.sin(a0)), (cx + r1 * math.cos(a0), cy + r1 * math.sin(a0)),
                     (cx + r1 * math.cos(a1), cy + r1 * math.sin(a1)), (cx + r0 * math.cos(a1), cy + r0 * math.sin(a1))]
                d = 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in p) + ' Z'
                svg.append(f'<path d="{d}" fill="{cols[(k + ring) % len(cols)]}"/>')
        svg.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke-width="14"/></g></svg>')
        rose = E.svg_rgba(''.join(svg))
        rose[..., :3] *= 0.75
        self.rose = rose
        self.cells = cape_shards()
        self.flecks = [(rng.uniform(0, w), rng.uniform(0, h), rng.uniform(3, 7), rng.integers(0, 6)) for _ in range(40)]
        self.cols = [E.hexrgb(c) for c in cols]
        bg = self.cathedral(bg)
        self.mottle = E.noise(h, w, 7, 931)
        self.smoke = E.noise(h, w, 90, 932, octaves=3)
        rng2 = np.random.default_rng(933)
        self.candles = [(x, 905 - rng2.uniform(0, 26), rng2.uniform(36, 70), rng2.uniform(0, 6.28))
                        for x in list(np.linspace(150, 470, 7)) + list(np.linspace(1450, 1770, 7))]
        self.sparks = [(rng2.uniform(-40, 40), rng2.uniform(0, 1), rng2.uniform(0.8, 1.6), rng2.integers(0, 2)) for _ in range(28)]
        self.bg = bg

    def cathedral(self, bg):
        """静态部分：尖拱石柱、地面石砖透视线、台阶、烛台、火盆（不含火焰）。"""
        h, w = 1080, 1920
        sv = ['<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">']
        # 远处两侧的尖拱窗（深蓝夜空 + 竖向窗棂）
        for ax in (520, 1400):
            sv.append(f'<path d="M{ax - 70},640 L{ax - 70},330 Q{ax - 70},230 {ax},190 Q{ax + 70},230 {ax + 70},330 L{ax + 70},640 Z" fill="#1A2350"/>')
            sv.append(f'<path d="M{ax},200 L{ax},640 M{ax - 70},420 L{ax + 70},420" stroke="#07060C" stroke-width="8"/>')
            sv.append(f'<path d="M{ax - 70},640 L{ax - 70},330 Q{ax - 70},230 {ax},190 Q{ax + 70},230 {ax + 70},330 L{ax + 70},640 Z" fill="none" stroke="#07060C" stroke-width="12"/>')
        # 石柱与尖拱
        for px in (150, 830, 1090, 1770):
            pass
        for px in (230, 1690):
            sv.append(f'<rect x="{px - 46}" y="120" width="92" height="790" fill="#100D1C"/>')
            sv.append(f'<rect x="{px - 46}" y="120" width="10" height="790" fill="#241C38"/>')
            sv.append(f'<rect x="{px - 62}" y="880" width="124" height="30" fill="#0C0A16"/>')
        sv.append('<path d="M-20,0 L-20,170 Q480,-60 960,40 Q1440,-60 1940,170 L1940,0 Z" fill="#0A0814"/>')
        # 台阶（舞台后方三级矮阶）
        for k, (y, c) in enumerate([(860, '#15111F'), (878, '#1A1526'), (894, '#1E182C')]):
            sv.append(f'<rect x="560" y="{y}" width="800" height="20" fill="{c}"/>')
        # 地面石砖：透视线
        for k in range(-12, 13):
            x2 = 960 + k * 260
            sv.append(f'<path d="M{960 + k * 70},905 L{x2},1080" stroke="#0E0B17" stroke-width="3"/>')
        for y in (930, 965, 1015, 1075):
            sv.append(f'<path d="M0,{y} L1920,{y}" stroke="#0E0B17" stroke-width="3"/>')
        # 烛台（每侧一条低架）
        sv.append('<rect x="120" y="905" width="380" height="14" fill="#2A1E16"/><rect x="1420" y="905" width="380" height="14" fill="#2A1E16"/>')
        # 火盆：三脚架 + 铁碗
        for (bx, by) in BRAZIERS:
            sv.append(f'<path d="M{bx - 50},{by + 20} L{bx - 80},905 M{bx + 50},{by + 20} L{bx + 80},905 M{bx},{by + 20} L{bx},905" stroke="#1B1414" stroke-width="12"/>')
            sv.append(f'<path d="M{bx - 90},{by} L{bx + 90},{by} Q{bx + 80},{by + 50} {bx},{by + 52} Q{bx - 80},{by + 50} {bx - 90},{by} Z" fill="#231A18" stroke="#3A2A22" stroke-width="5"/>')
        sv.append('</svg>')
        lay = E.svg_rgba(''.join(sv))
        bg = E.over(bg, lay)
        bg[905:] = bg[905:] * 0.9 + E.vgrad('#130F1E', '#0A0812')[905:] * 0.1
        return bg

    def fire(self, img, t):
        """火盆火焰、蜡烛火苗、上升的火星、暖光照明（全部由 t 决定，可复现）。"""
        sv = ['<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">']
        for k, (bx, by) in enumerate(BRAZIERS):
            for j, (dx, hh, ww) in enumerate([(-38, 150, 34), (34, 165, 36), (0, 210, 44), (-14, 120, 26), (22, 130, 26)]):
                sv.append(flame_svg(bx + dx, by + 6, hh, ww, t, k * 3.1 + j * 1.7,
                                    col='#E8582A' if j < 2 else '#FF9A3C', core='#FFE08A'))
        for (x, y, hgt, ph) in self.candles:
            sv.append(f'<rect x="{x - 9}" y="{y - hgt}" width="18" height="{hgt}" fill="#E9DFC8"/>')
            sv.append(f'<rect x="{x - 9}" y="{y - hgt}" width="5" height="{hgt}" fill="#FFF6E2"/>')
            sv.append(flame_svg(x, y - hgt - 2, 26, 7, t, ph, col='#FFB347', core='#FFF6D0'))
        sv.append('</svg>')
        fl = E.svg_rgba(''.join(sv))
        flick = 1 + 0.08 * math.sin(t * 11) + 0.05 * math.sin(t * 27)
        # 暖光：火盆周围与地面光池
        for (bx, by) in BRAZIERS:
            g = E.radial(bx, by - 40, 520) ** 2 * 0.42 * flick
            img = img + g[..., None] * E.hexrgb('#FF8A3A')
        cl = (E.radial(310, 880, 300) ** 2 + E.radial(1610, 880, 300) ** 2) * 0.25 * flick
        img = img + cl[..., None] * E.hexrgb('#FFB357')
        img = E.over(img, fl)
        img = fx.glow_add(img, fl[..., 3], fl[..., :3], radii=((8, 0.35), (26, 0.3)))
        # 火星：从火盆向上飘，逐渐变暗
        for (dx, ph, sp, side) in self.sparks:
            bx, by = BRAZIERS[side]
            q = (ph + t * 0.5 * sp) % 1.0
            x = bx + dx + 30 * math.sin(q * 9 + dx)
            y = by - 60 - q * 420
            fx.soft_disc(img, x, y, 3.5, E.hexrgb('#FFC46B'), 0.9 * (1 - q), 0.4)
        return img

    def pose(self, t):
        K = E.K
        p = E.pose(x=960, y=905, s=0.86)
        # 1 裹披风蓄力 → 2 炸开 → 3 左右踏步 → 4 深蹲收拢 → 5 起身高举 → 6 静立
        p['sq'] = K(t, [(-0.4, 1.0), (0.35, 1.0), (0.7, 0.86), (0.9, 1.08, 'out'), (1.15, 1.0),
                        (2.35, 1.0), (2.65, 0.86), (2.95, 1.07, 'out'), (3.25, 1.0)]) + 0.008 * math.sin(t * 3)
        p['hop'] = K(t, [(0.82, 0), (1.0, 26, 'out'), (1.2, 0, 'in'), (2.85, 0), (3.02, 18, 'out'), (3.2, 0, 'in')])
        arms = K(t, [(-0.4, -8), (0.7, -16), (1.0, 112, 'back'), (1.2, 100), (2.35, 96), (2.65, -12), (2.95, 118, 'back'),
                     (3.6, 110), (4.4, 46), (5.0, 40)])
        p['flare'] = K(t, [(-0.4, 0.96), (0.7, 0.9), (1.0, 1.36, 'back'), (1.25, 1.24), (2.35, 1.2), (2.65, 0.96),
                           (3.0, 1.3, 'back'), (3.6, 1.14), (5.0, 1.03)])
        # 踏步段（1.2–2.35）：每 0.38 s 换一次重心，手臂一高一低交替，披风迟后甩动
        step = E.smooth((t - 1.15) / 0.15) * (1 - E.smooth((t - 2.3) / 0.15))
        ph = (t - 1.2) / 0.38
        b = math.sin(math.pi * ph)
        p['dx'] = 34 * b * step
        p['lean'] = 7 * b * step + K(t, [(2.95, 0), (3.3, -2), (4.0, 1), (4.6, 0)])
        p['armL'] = arms + 34 * b * step
        p['armR'] = arms - 34 * b * step
        p['legs'] = (14 * max(0, b) * step, 0, 0, 14 * max(0, -b) * step)
        lag = math.sin(math.pi * (ph - 0.35))
        p['skirt'] = -9 * lag * step + K(t, [(0.85, 0), (1.05, -6), (1.3, 3), (1.5, 0), (2.95, 0), (3.15, 5), (3.45, -3), (3.8, 0)])
        p['hair'] = -8 * lag * step + K(t, [(0.85, 0), (1.0, 8), (1.25, -4), (1.5, 0), (2.95, 0), (3.1, 7), (3.4, -3), (3.7, 0)])
        p['eye_mode'] = 'closed' if (t < 0.75 or t > 3.9) else ('happy' if 3.0 < t < 3.6 else 'open')
        p['eye_dx'] = 10 * b * step
        p['eye_dy'] = K(t, [(2.95, 0), (3.15, -14), (3.7, -10), (3.95, 4)])
        return p

    def frame(self, t, p=None, trans=False):
        p = dict(self.pose(t) if p is None else p)
        img = self.bg.copy()
        burst = 0.35 * E.smooth((t - 0.9) / 0.3) * (1 - E.smooth((t - 2.4) / 0.3)) + E.smooth((t - 2.95) / 0.3) * (1 - 0.45 * E.smooth((t - 3.8) / 1.0))
        # 光柱：从玫瑰窗斜射下来，缓慢转动
        rays = np.zeros((1080, 1920, 3), np.float32)
        yy, xx = np.mgrid[0:1080, 0:1920].astype(np.float32)
        ang = np.arctan2(yy - 215, xx - 960)
        for k, col in enumerate(self.cols):
            a0 = 0.6 + k * 0.35 + 0.05 * t
            band = np.exp(-((np.angle(np.exp(1j * (ang - a0)))) / 0.05) ** 2) * (yy > 215)
            rays += band[..., None] * col
        img = img + rays * (0.10 + 0.25 * burst) * np.clip((yy - 215) / 500, 0, 1)[..., None]
        img = E.over(img, self.rose)
        img = fx.glow_add(img, self.rose[..., 3] * (0.5 + 0.5 * burst), self.rose[..., :3], radii=((10, 0.25), (40, 0.25)))
        # 香烟：缓缓上升的薄雾（火光照得发暖）
        sm = E.shifted(self.smoke, 10 * math.sin(t * 0.4), -40 * (t + 0.4))
        band = np.clip((np.arange(1080, dtype=np.float32) - 200) / 500, 0, 1)[:, None]
        img = img + (sm * band * 0.10)[..., None] * E.hexrgb('#9C8AB8')
        img = self.fire(img, t)
        # 漂浮的彩色光点
        for (x, y, r, ci) in self.flecks:
            yy_ = (y - 30 * (t + 0.4)) % 1080
            fx.soft_disc(img, x + 12 * math.sin(t + x), yy_, r, self.cols[ci], 0.2 + 0.35 * burst, 0.2)
        # 角色：整块彩绘玻璃；只有披风切成长条玻璃
        flat = E.render_char(9, p, 'flat')
        a = flat[..., 3]
        col = flat[..., :3]
        cape = np.zeros(a.shape, np.float32)
        for c in CAPE_COLS:
            cape = np.maximum(cape, (np.abs(col - E.hexrgb(c)).sum(-1) < 0.16).astype(np.float32))
        cape = cv2.morphologyEx(cape, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) * (a > 0.5)
        sh = E.svg_rgba(f'<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080"><g transform="{E.tf_str(p)}">{self.cells}</g></svg>')
        red = (sh[..., 0] > 0.5) & (sh[..., 1] < 0.3) & (sh[..., 3] > 0.3)          # 红色描边 = 披风铅条
        shard_lead = red.astype(np.float32) * cape
        tint = np.where(red, 0.5, sh[..., :3].mean(-1)) * sh[..., 3] + 0.5 * (1 - sh[..., 3])
        col = np.where(cape[..., None] > 0.5, E.hexrgb('#B3174F'), col)          # 披风长条内部纯色，去掉原来的细褶纹
        glass = col * 1.04 + 0.03
        ox = p['x'] - 960
        mot = E.shifted(self.mottle, ox, p['y'] - 905)
        glass = glass * (1 + 0.06 * (mot[..., None] - 0.5))                         # 手工玻璃的轻微斑驳
        glass = glass * (1 + 1.1 * (tint[..., None] - 0.5) * cape[..., None])         # 披风长条之间明暗各异
        la = E.line_alpha(9, p, sw=1.6)
        struct = np.clip((la - 0.62) / 0.25, 0, 1)                                   # 只保留结构线（去掉披风上的细褶纹）
        lead = np.maximum(struct, shard_lead) * a
        lit = glass * (1 - lead[..., None]) + E.hexrgb('#120E18') * lead[..., None]
        img = E.over_rgb(img, lit, a)
        img = fx.glow_add(img, a * (1 - lead) * (0.35 + 0.55 * burst), glass, radii=((6, 0.10), (24, 0.10)))
        # 地面彩色光斑
        pool = E.blur(cv2.resize(self.rose[..., :3] * self.rose[..., 3:], (480, 270))[5:110], 6)
        pool = cv2.resize(pool, (1920, 175))
        img[905:] = img[905:] + pool * (0.18 + 0.3 * burst)
        return np.clip(img, 0, 1)
