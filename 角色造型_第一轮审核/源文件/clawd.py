# -*- coding: utf-8 -*-
"""Clawd 穿单依纯《歌手2025》13 套造型 —— 第一轮审核图生成脚本。

所有角色共用同一套身体几何（BODY / EYES / ARMS / LEGS），每套造型只定义服装图层。
输出 SVG（可编辑源文件），再由 render.py 用 Chrome 无头模式渲染为 1600×1600 PNG。
"""
import math

W = H = 1600
BG = '#ECE7E1'          # 统一浅暖灰背景
INK = '#2E2320'         # 统一描边色
SW = 5                  # 统一描边宽度

ORANGE = '#D97757'
EYE = '#1E1714'

# ---- 固定角色几何（全套共用，不随造型改变） ----
FX0, FX1, FY0, FY1 = 572, 972, 600, 990     # 正面
DX, DY = 56, -28                            # 侧面厚度（轻微三分之四视角，右侧为侧面）
GROUND = 1120                               # 腿底 / 地面
EYES = [(706, 722), (812, 722)]             # 眼睛中心
EYE_W, EYE_H = 30, 80
LEGS_X = [620, 690, 854, 924]               # 四条腿中心
LEG_W = 50
ARM_L, ARM_W = 128, 46
ARM_PIVOT = {'L': (580, 842), 'R': (1004, 826)}
ARM_ANGLE = {'L': 26, 'R': -26}

BODY_POLY = [(FX0, FY0), (FX0 + DX, FY0 + DY), (FX1 + DX, FY0 + DY),
             (FX1 + DX, FY1 + DY), (FX1, FY1), (FX0, FY1)]
SIDE_POLY = [(FX1, FY0), (FX1 + DX, FY0 + DY), (FX1 + DX, FY1 + DY), (FX1, FY1)]
TOP_POLY = [(FX0, FY0), (FX0 + DX, FY0 + DY), (FX1 + DX, FY0 + DY), (FX1, FY0)]


def pts(p):
    return 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in p) + ' Z'


def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(a[i] + (b[i] - a[i]) * t):02x}' for i in range(3))


def dark(c, t=0.22):
    return mix(c, '#1a0f14', t)


def light(c, t=0.3):
    return mix(c, '#ffffff', t)


class Doc:
    def __init__(self):
        self.defs = []
        self.n = 0
        self.out = []

    def uid(self, p='c'):
        self.n += 1
        return f'{p}{self.n}'

    def raw(self, s):
        self.out.append(s)

    def shape(self, d, fill, shade=None, off=(-30, -6), stroke=INK, sw=SW,
              opacity=1.0, clip=None, outline=None):
        """平涂 + 赛璐璐阴影（右下侧月牙阴影，统一光源来自左上）。"""
        g = []
        if shade is not None and shade is not False:
            sc = dark(fill) if shade is True else shade
            cid = self.uid()
            self.defs.append(f'<clipPath id="{cid}"><path d="{d}"/></clipPath>')
            g.append(f'<g clip-path="url(#{cid})"><path d="{d}" fill="{sc}"/>'
                     f'<path d="{d}" fill="{fill}" transform="translate({off[0]},{off[1]})"/></g>')
        else:
            g.append(f'<path d="{d}" fill="{fill}"/>')
        if stroke:
            g.append(f'<path d="{outline or d}" fill="none" stroke="{stroke}" stroke-width="{sw}" '
                     f'stroke-linejoin="round" stroke-linecap="round"/>')
        inner = ''.join(g)
        attrs = ''
        if opacity < 1:
            attrs += f' opacity="{opacity}"'
        if clip:
            attrs += f' clip-path="url(#{clip})"'
        self.out.append(f'<g{attrs}>{inner}</g>' if attrs else inner)

    def line(self, d, color=INK, sw=3, opacity=1.0, dash=None, cap='round'):
        extra = f' stroke-dasharray="{dash}"' if dash else ''
        op = f' opacity="{opacity}"' if opacity < 1 else ''
        self.out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" '
                        f'stroke-linecap="{cap}" stroke-linejoin="round"{extra}{op}/>')

    def circle(self, cx, cy, r, fill, stroke=INK, sw=SW, opacity=1.0):
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ''
        op = f' opacity="{opacity}"' if opacity < 1 else ''
        self.out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{st}{op}/>')

    def group_open(self, attrs=''):
        self.out.append(f'<g {attrs}>')

    def group_close(self):
        self.out.append('</g>')

    def svg(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
                f'viewBox="0 0 {W} {H}"><defs>{"".join(self.defs)}</defs>'
                + ''.join(self.out) + '</svg>')


# ---------------------------------------------------------------- 身体部件
def arm_path(side, length=ARM_L, start=0.0, width=ARM_W, extra_w=0):
    """返回手臂（或手臂上一段）的路径，局部坐标→全局。start/length 以沿手臂方向计。"""
    px, py = ARM_PIVOT[side]
    a = math.radians(ARM_ANGLE[side])
    w = width / 2 + extra_w
    r = min(w, 22)
    y0, y1 = start, length
    # 圆角矩形（局部坐标，沿 +y 方向）
    loc = (f'M{-w},{y0} L{w},{y0} L{w},{y1 - r} Q{w},{y1} {w - r},{y1} '
           f'L{-w + r},{y1} Q{-w},{y1} {-w},{y1 - r} Z')
    return loc, f'translate({px},{py}) rotate({ARM_ANGLE[side]})'


def arm_point(side, t, u=0.0):
    """手臂局部坐标 (u 横向, t 沿臂) → 全局坐标。"""
    px, py = ARM_PIVOT[side]
    a = math.radians(ARM_ANGLE[side])
    return (px + u * math.cos(a) - t * math.sin(a), py + u * math.sin(a) + t * math.cos(a))


def outside_clip(doc):
    """只保留身体轮廓以外的区域：手臂、手套画在这里，看起来从身体侧面长出。"""
    if not any('id="outside"' in d for d in doc.defs):
        doc.defs.append(f'<clipPath id="outside"><path clip-rule="evenodd" '
                        f'd="M0,0 L{W},0 L{W},{H} L0,{H} Z {pts(BODY_POLY)}"/></clipPath>')
    return 'outside'


def draw_arm(doc, side, fill=ORANGE, start=0, length=ARM_L, extra_w=0, stroke=INK, opacity=1.0):
    d, tr = arm_path(side, length, start, extra_w=extra_w)
    cid = doc.uid()
    sc = dark(fill)
    op = f' opacity="{opacity}"' if opacity < 1 else ''
    op += f' clip-path="url(#{outside_clip(doc)})"'
    doc.defs.append(f'<clipPath id="{cid}"><path d="{d}"/></clipPath>')
    doc.raw(f'<g{op}><g transform="{tr}"><g clip-path="url(#{cid})"><path d="{d}" fill="{sc}"/>'
            f'<path d="{d}" fill="{fill}" transform="translate(-12,0)"/></g>'
            + (f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{SW}" stroke-linejoin="round"/>' if stroke else '')
            + '</g></g>')


def leg_path(x, top=FY1 - 10, bottom=GROUND, w=LEG_W):
    r = 10
    return (f'M{x - w / 2},{top} L{x + w / 2},{top} L{x + w / 2},{bottom - r} '
            f'Q{x + w / 2},{bottom} {x + w / 2 - r},{bottom} L{x - w / 2 + r},{bottom} '
            f'Q{x - w / 2},{bottom} {x - w / 2},{bottom - r} Z')


def draw_legs(doc, sock=None, sock_top=None, shoe=None, shoe_h=26, platform=0):
    for x in LEGS_X:
        doc.shape(leg_path(x), ORANGE, shade=True, off=(-10, 0))
        if sock:
            doc.shape(leg_path(x, top=sock_top), sock, shade=True, off=(-10, 0))
        if shoe:
            top = GROUND - shoe_h
            d = (f'M{x - LEG_W / 2 - 3},{top} L{x + LEG_W / 2 + 3},{top} '
                 f'L{x + LEG_W / 2 + 4},{GROUND + platform} L{x - LEG_W / 2 - 4},{GROUND + platform} Z')
            doc.shape(d, shoe, shade=True, off=(-10, 0))


def body_clip(doc):
    cid = 'bodyclip'
    if not any('id="bodyclip"' in d for d in doc.defs):
        doc.defs.append(f'<clipPath id="{cid}"><path d="{pts(BODY_POLY)}"/></clipPath>')
    return cid


def draw_body(doc):
    doc.shape(pts(BODY_POLY), ORANGE)


def side_overlay(doc):
    # 侧面统一压暗（光源左上），顶面略提亮
    doc.raw(f'<path d="{pts(SIDE_POLY)}" fill="#2a1208" opacity="0.20"/>')
    doc.raw(f'<path d="{pts(TOP_POLY)}" fill="#ffffff" opacity="0.10"/>')


def body_outline(doc):
    doc.raw(f'<path d="{pts(BODY_POLY)}" fill="none" stroke="{INK}" stroke-width="{SW}" stroke-linejoin="round"/>')
    doc.line(f'M{FX1},{FY0} L{FX1},{FY1}', INK, 3)
    doc.line(f'M{FX0},{FY0} L{FX1},{FY0} L{FX1 + DX},{FY0 + DY}', INK, 3)


def draw_eyes(doc):
    for (x, y) in EYES:
        doc.raw(f'<rect x="{x - EYE_W / 2}" y="{y - EYE_H / 2}" width="{EYE_W}" height="{EYE_H}" '
                f'rx="{EYE_W / 2}" fill="{EYE}"/>')


def ground_shadow(doc, rx=330, cx=800):
    doc.raw(f'<ellipse cx="{cx}" cy="{GROUND + 4}" rx="{rx}" ry="30" fill="#5a4636" opacity="0.16"/>')


# ---------------------------------------------------------------- 发型部件
HAIR = '#2B1F1C'
HAIR_SH = '#1B1311'
HAIR_HI = '#5A4540'


def hair_cap(doc, color=HAIR, part=True, sleek=False):
    """覆盖头顶的发盖，发际线停在眼睛上方（眼睛顶端 y=682）。"""
    top = 554 if not sleek else 560
    hl = 646 if not sleek else 636
    d = (f'M558,700 C548,630 552,{top + 14} 610,{top + 2} C700,{top - 10} 900,{top - 10} 1000,{top - 2} '
         f'C1046,{top + 4} 1052,600 1046,650 L1040,690 '
         f'C1026,{hl + 8} 1000,{hl - 4} 970,{hl - 10} C920,{hl - 22} 850,{hl - 28} 796,{hl - 22} '
         f'C730,{hl - 30} 650,{hl - 18} 610,{hl - 2} C590,{hl + 8} 572,{hl + 28} 558,700 Z')
    doc.shape(d, color, shade=HAIR_SH, off=(-24, -8))
    if part:
        doc.line(f'M796,{hl - 24} C800,{hl - 44} 804,{top + 34} 806,{top + 22}', HAIR_HI, 4)
    doc.line(f'M646,{top + 26} C700,{top + 12} 760,{top + 8} 830,{top + 8}', HAIR_HI, 5, opacity=0.7)


def hair_long_back(doc, bottom=1000, spread=0, wavy=0, color=HAIR):
    """披在身后的长发（只在身体两侧露出）。"""
    L = 548 - spread
    R = 1060 + spread
    if wavy:
        # 波浪外轮廓
        segs_l = []
        y = 620
        x = L
        while y < bottom:
            segs_l.append(f'Q{x - wavy},{y + 30} {x},{y + 60}')
            y += 60
        left = ' '.join(segs_l)
        segs_r = []
        y = bottom
        while y > 620:
            segs_r.append(f'Q{R + wavy},{y - 30} {R},{y - 60}')
            y -= 60
        right = ' '.join(segs_r)
        d = (f'M{L + 30},580 Q{L - 10},590 {L},620 {left} '
             f'Q{(L + R) / 2},{bottom + 40} {R},{bottom} {right} Q{R + 4},590 {R - 40},572 Z')
    else:
        d = (f'M{L + 30},580 C{L},600 {L - 6},660 {L - 4},740 L{L - 8},{bottom - 10} '
             f'Q{L},{bottom + 8} {L + 40},{bottom} L{R - 40},{bottom - 20} '
             f'Q{R},{bottom - 24} {R + 4},{bottom - 40} L{R + 2},700 C{R},620 {R - 10},582 {R - 40},572 Z')
    doc.shape(d, color, shade=HAIR_SH, off=(-30, 0))


def hair_front_locks(doc, bottom=930, color=HAIR, wavy=0):
    """贴在脸两侧的前发：只落在身体轮廓内（左 572–628，右侧面 994–1030），不遮眼睛、不挡手臂。"""
    if wavy:
        dl = (f'M572,650 C604,642 628,668 630,708 Q{642 + wavy},770 622,830 Q{606 - wavy},880 618,{bottom - 40} '
              f'Q{626 + wavy},{bottom - 10} 604,{bottom} L572,{bottom - 4} Z')
        dr = (f'M992,606 C1012,600 1028,600 1028,620 L1028,{bottom - 16} L1004,{bottom - 22} '
              f'Q{990 - wavy},860 1000,790 Q{988 - wavy},730 996,680 Z')
    else:
        dl = (f'M572,650 C604,642 626,668 628,720 L626,{bottom - 20} Q620,{bottom + 4} 600,{bottom} L572,{bottom - 4} Z')
        dr = (f'M990,610 C1010,602 1028,600 1028,620 L1028,{bottom - 16} L1000,{bottom - 22} L998,680 Z')
    doc.shape(dl, color, shade=HAIR_SH, off=(-14, 0))
    doc.shape(dr, color, shade=HAIR_SH, off=(-10, 0))
    doc.line(f'M596,690 L598,{bottom - 40}', HAIR_HI, 3, opacity=0.6)
    doc.line(f'M1014,660 L1014,{bottom - 60}', HAIR_HI, 3, opacity=0.6)


def bun_top(doc, cx=800, cy=520, r=58):
    d = f'M{cx - r},{cy} A{r},{r * 0.92} 0 1 1 {cx + r},{cy} A{r},{r * 0.92} 0 1 1 {cx - r},{cy} Z'
    doc.shape(d, HAIR, shade=HAIR_SH, off=(-16, -6))
    doc.line(f'M{cx - r * 0.6},{cy - 10} Q{cx},{cy - r * 0.8} {cx + r * 0.6},{cy - 14}', HAIR_HI, 4, opacity=0.7)
    doc.line(f'M{cx - r * 0.5},{cy + 22} Q{cx},{cy + r * 0.4} {cx + r * 0.55},{cy + 14}', HAIR_SH, 4)


def low_bun_side(doc, cx=1062, cy=690, r=50):
    d = f'M{cx - r},{cy} A{r},{r} 0 1 1 {cx + r},{cy} A{r},{r} 0 1 1 {cx - r},{cy} Z'
    doc.shape(d, HAIR, shade=HAIR_SH, off=(-14, -4))
    doc.line(f'M{cx - r * 0.6},{cy} Q{cx},{cy - r * 0.6} {cx + r * 0.6},{cy - 4}', HAIR_HI, 4, opacity=0.6)


def tendrils(doc, color=HAIR):
    """耳侧几缕碎发（贴着发盖垂下，较短）。"""
    doc.line('M580,690 Q570,730 584,770 Q592,794 580,812', color, 6)
    doc.line('M1018,660 Q1030,700 1016,740 Q1008,764 1020,790', color, 6)


def arm_band(doc, side, t0, t1, fill, stroke=INK, sw=3, extra_w=1):
    """手臂上的一段（手镯、袖口等），只显示在身体外侧。"""
    px, py = ARM_PIVOT[side]
    w = ARM_W / 2 + extra_w
    d = f'M{-w},{t0} L{w},{t0} L{w},{t1} L{-w},{t1} Z'
    doc.raw(f'<g clip-path="url(#{outside_clip(doc)})"><g transform="translate({px},{py}) rotate({ARM_ANGLE[side]})">'
            f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"/></g></g>')


class Bez:
    """由 M/C/L 段组成的路径，可同时输出 SVG d 与沿线采样点（用于褶边轮廓）。"""
    def __init__(self, start):
        self.p0 = start
        self.segs = []

    def C(self, a, b, c):
        self.segs.append(('C', a, b, c)); return self

    def L(self, a):
        self.segs.append(('L', a)); return self

    def d(self, close=True):
        out = f'M{self.p0[0]},{self.p0[1]}'
        for s in self.segs:
            if s[0] == 'C':
                out += f' C{s[1][0]},{s[1][1]} {s[2][0]},{s[2][1]} {s[3][0]},{s[3][1]}'
            else:
                out += f' L{s[1][0]},{s[1][1]}'
        return out + (' Z' if close else '')

    def sample(self, spacing=20, segs=None):
        pts = []
        cur = self.p0
        for i, s in enumerate(self.segs):
            fine = []
            for k in range(1, 61):
                t = k / 60
                if s[0] == 'C':
                    a, b, c = s[1], s[2], s[3]
                    x = (1 - t) ** 3 * cur[0] + 3 * (1 - t) ** 2 * t * a[0] + 3 * (1 - t) * t * t * b[0] + t ** 3 * c[0]
                    y = (1 - t) ** 3 * cur[1] + 3 * (1 - t) ** 2 * t * a[1] + 3 * (1 - t) * t * t * b[1] + t ** 3 * c[1]
                else:
                    x = cur[0] + (s[1][0] - cur[0]) * t
                    y = cur[1] + (s[1][1] - cur[1]) * t
                fine.append((x, y))
            if segs is None or i in segs:
                acc = 0
                prev = cur
                for p in fine:
                    acc += math.hypot(p[0] - prev[0], p[1] - prev[1])
                    prev = p
                    if acc >= spacing:
                        pts.append(p)
                        acc = 0
            cur = s[3] if s[0] == 'C' else s[1]
        return pts


def ruffle_shape(doc, bez, fill, shade, r=14, spacing=20, segs=None, off=(-36, -6)):
    """褶边外轮廓：沿边放一串小圆（带描边），再把主体平涂盖上去，形成波浪边。"""
    for (x, y) in bez.sample(spacing, segs):
        doc.circle(f'{x:.1f}', f'{y:.1f}', r, fill, stroke=INK, sw=SW)
    d = bez.d()
    cid = doc.uid()
    doc.defs.append(f'<clipPath id="{cid}"><path d="{d}"/></clipPath>')
    doc.raw(f'<g clip-path="url(#{cid})"><path d="{d}" fill="{shade}"/>'
            f'<path d="{d}" fill="{fill}" transform="translate({off[0]},{off[1]})"/></g>')
    for (x, y) in bez.sample(spacing, segs):
        doc.circle(f'{x:.1f}', f'{y:.1f}', r - 3.5, fill, stroke=None)
    return cid
