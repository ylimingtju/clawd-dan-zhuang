# -*- coding: utf-8 -*-
"""13 套造型的服装图层。坐标系与身体几何见 clawd.py。"""
import math
from clawd import *


SCALE = 1.25
GROUND_Y = 1215


def hem(x0, x1, y_base, rise=0, jag=0, step=26, cx=772, width=150, tilt=0):
    """下摆点串：前中可提起 rise，jag 为羽状锯齿，tilt 为左右高低差（右端相对左端）。"""
    out = []
    n = max(2, int(abs(x1 - x0) / step))
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        y = y_base - rise * math.exp(-((x - cx) / width) ** 2) + tilt * (x - 772) / 400
        if jag and i % 2:
            y -= jag
        out.append(f'L{x:.1f},{y:.1f}')
    return ' '.join(out)


def zigzag(x0, x1, y_a, y_b, step=28):
    """从 x0 到 x1 的锯齿/羽状下摆点串（x0 > x1 时反向）。"""
    out = []
    n = max(2, int(abs(x1 - x0) / step))
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        y = y_a if i % 2 == 0 else y_b
        out.append(f'L{x:.1f},{y:.1f}')
    return ' '.join(out)


def scallop(x0, x1, y, r=14, up=False):
    """一串小圆弧（花边/褶皱边）。"""
    out = []
    n = max(1, int(abs(x1 - x0) / (2 * r)))
    step = (x1 - x0) / n
    for i in range(n):
        xa = x0 + step * (i + 1)
        out.append(f'A{abs(step) / 2:.1f},{r} 0 0 {1 if not up else 0} {xa:.1f},{y:.1f}')
    return ' '.join(out)


class Look:
    no = 0
    title = ''
    shadow_rx = 330
    shadow_cx = 800
    skirt_pivot = 980          # 裙摆摆动/展开的支点高度（设计坐标）

    def back(self, d): pass
    def legs(self, d): draw_legs(d)
    def arms(self, d):
        draw_arm(d, 'L')
        draw_arm(d, 'R')
    def locks(self, d): pass
    def bodice(self, d): pass
    def skirt(self, d): pass
    def front(self, d): pass

    def render_pose(self, tf, sway, mode='full', sw=1.0, extra=None, w=1920, h=1080, seam=0.0, eye_ring=False):
        """视频用：tf 为整体变换字符串；sway={'hair','skirt','flare'}；不画背景与地面阴影。"""
        RSTATE['mode'] = mode
        RSTATE['sw'] = sw
        RSTATE['seam'] = seam
        RSTATE['eye_ring'] = eye_ring
        d = Doc()
        d.group_open(f'transform="{tf}"')
        hp = sway.get('hair', 0.0)
        d.group_open(f'transform="translate(800,600) skewX({hp:.3f}) translate(-800,-600)"')
        self.back(d)
        d.group_close()
        self.legs(d)
        draw_body(d)
        cid = body_clip(d)
        d.group_open(f'clip-path="url(#{cid})"')
        self.bodice(d)
        d.group_close()
        side_overlay(d)
        body_outline(d)
        d.group_open(f'transform="translate(800,640) skewX({hp * 0.4:.3f}) translate(-800,-640)"')
        self.locks(d)
        d.group_close()
        self.arms(d)
        py = self.skirt_pivot
        d.group_open(f'transform="translate(800,{py}) skewX({sway.get("skirt", 0.0):.3f}) '
                     f'scale({sway.get("flare", 1.0):.4f},1) translate(-800,-{py})"')
        self.skirt(d)
        d.group_close()
        self.front(d)
        draw_eyes(d)
        if extra:
            extra(d)
        d.group_close()
        RSTATE['mode'] = 'full'
        RSTATE['sw'] = 1.0
        RSTATE['seam'] = 0.0
        return d.svg(w, h)

    def render(self):
        d = Doc()
        d.raw(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
        # 全套统一的角色显示尺度与位置
        d.group_open(f'transform="translate(800,{GROUND_Y}) scale({SCALE}) translate(-800,-{GROUND})"')
        ground_shadow(d, self.shadow_rx, self.shadow_cx)
        self.back(d)
        self.legs(d)
        draw_body(d)
        cid = body_clip(d)
        d.group_open(f'clip-path="url(#{cid})"')
        self.bodice(d)
        d.group_close()
        side_overlay(d)
        body_outline(d)
        self.locks(d)
        self.arms(d)
        self.skirt(d)
        self.front(d)
        draw_eyes(d)
        d.group_close()
        return d.svg()


# =============================================================== 00 基础角色
class Base(Look):
    no = 0
    title = 'Clawd 基础角色'


# =============================================================== 01 珠玉
class L01(Look):
    no = 1
    title = '珠玉'
    WHITE = '#F6F3EC'
    SH = '#D8D4CB'
    PL = '#C9C3B8'
    shadow_rx = 400

    def back(self, d):
        hair_long_back(d, bottom=990, wavy=16)

    def bodice(self, d):
        # 不对称一字肩：左侧（她的右肩）带盖肩，右侧露肩
        d.shape('M556,806 C640,796 724,834 786,856 C846,836 910,808 1044,798 L1044,1000 L556,1000 Z',
                self.WHITE, shade=self.SH, off=(-40, 0))
        # 蕾丝底层（躯干中央可见）
        d.shape('M700,880 C760,872 830,880 880,900 L900,990 L690,990 Z', '#ECE8DF', stroke=None)
        for (x, y) in [(722, 912), (770, 900), (822, 918), (860, 948), (742, 958), (800, 962), (706, 975)]:
            d.circle(x, y, 9, 'none', stroke=self.PL, sw=2)
            d.circle(x, y, 3, self.PL, stroke=None)

    def _ribbon(self, d, path, w=30):
        d.line(path, INK, w + 8)
        d.line(path, self.WHITE, w)
        d.line(path, self.PL, 2.5)

    def locks(self, d):
        hair_front_locks(d, bottom=910, wavy=12)

    def skirt(self, d):
        # 鱼尾：臀下收束 → 下摆展开，右后方拖尾
        hem_ = hem(1236, 470, 1126, rise=26, jag=16, step=24, width=120)
        sk = (f'M560,936 C640,926 960,924 1040,936 C1040,970 1018,996 1004,1018 '
              f'C1040,1058 1110,1088 1180,1104 C1212,1110 1232,1118 1240,1124 {hem_} '
              f'C510,1094 566,1062 596,1018 C574,994 560,968 560,936 Z')
        d.shape(sk, self.WHITE, shade=self.SH, off=(-46, 0))
        # 立体褶：从收束处放射到下摆
        for i in range(15):
            t = i / 14
            xb = 490 + t * 720
            xt = 610 + t * 380
            d.line(f'M{xt:.0f},1022 Q{(xt * 0.6 + xb * 0.4):.0f},1060 {xb:.0f},1108', self.PL, 2.5)
        # 收束处一圈扭转褶带
        self._ribbon(d, 'M584,1010 C680,1000 760,1030 860,1016 C930,1006 980,1010 1012,1022', 18)

    def legs(self, d):
        draw_legs(d)

    def front(self, d):
        hair_cap(d)
        # 左肩立体褶皱盖袖
        d.shape('M608,804 C574,786 536,806 528,852 C546,878 584,874 612,848 Z', self.WHITE,
                shade=self.SH, off=(-14, 0))
        d.line('M594,808 C568,816 550,836 546,860', self.PL, 2.5)
        # 主 S 形褶带：沿领口 → 斜穿躯干 → 卷入右胯
        self._ribbon(d, 'M604,808 C670,800 734,842 788,858 C846,870 904,816 962,808', 30)
        self._ribbon(d, 'M962,808 C1000,850 930,872 850,890 C760,910 660,930 600,990', 26)
        self._ribbon(d, 'M700,860 C780,900 900,890 990,920', 20)
        # 右胯螺旋褶饰
        cx, cy = 1014, 940
        d.shape(f'M{cx - 50},{cy} A50,46 0 1 1 {cx + 50},{cy} A50,46 0 1 1 {cx - 50},{cy} Z',
                self.WHITE, shade=self.SH, off=(-14, -4))
        d.line(f'M{cx - 34},{cy + 6} A34,30 0 1 1 {cx + 28},{cy + 18}', self.PL, 3)
        d.line(f'M{cx - 16},{cy + 4} A18,16 0 1 1 {cx + 14},{cy + 10}', self.PL, 3)
        # 白色花簇耳饰（简化）
        for (x, y) in [(594, 762), (1010, 748)]:
            for (ox, oy) in [(0, 0), (-9, 12), (9, 12), (0, 24)]:
                d.circle(x + ox, y + oy, 8, '#FFFFFF', stroke=INK, sw=2.5)


def skirt_shape(d, TL, TR, rest, fill, shade=True, off=(-44, 0), opacity=1.0, top_stroke=False):
    """裙身：TL→TR 为腰线（默认不描边，与上身连成一体），rest 从 TR 绕到 TL。"""
    fd = f'M{TL[0]},{TL[1]} L{TR[0]},{TR[1]} {rest} Z'
    ol = None if top_stroke else f'M{TR[0]},{TR[1]} {rest}'
    d.shape(fd, fill, shade=shade, off=off, opacity=opacity, outline=ol)


def earring_drop(d, x, y, color, n=2, r=7):
    d.line(f'M{x},{y} L{x},{y + 10}', INK, 2.5)
    for i in range(n):
        d.circle(x, y + 16 + i * 16, r, color, stroke=INK, sw=2.5)


# =============================================================== 02 天空
class L02(Look):
    no = 2
    title = '天空'
    PINK = '#EBCFDC'
    SH = '#D1ABBF'
    EDGE = '#A57A90'

    def bodice(self, d):
        d.shape('M556,792 C680,804 880,800 1044,780 L1044,1000 L556,1000 Z', self.PINK, shade=self.SH, off=(-40, 0))
        for x in range(610, 1000, 46):
            d.line(f'M{x},{820} Q{x + 10},900 {x - 4},990', self.SH, 2.5)

    def skirt(self, d):
        rest = f'C1052,1010 1066,1060 1078,1110 {hem(1078, 500, 1112, rise=22, step=40)} C516,1050 540,1010 560,980'
        skirt_shape(d, (560, 980), (1028, 974), rest, self.PINK, shade=self.SH)
        # 层叠半透明薄纱片
        d.shape('M600,990 C640,1040 600,1090 560,1116 L760,1112 C730,1060 700,1020 690,990 Z',
                light(self.PINK, 0.35), stroke=self.EDGE, sw=3, opacity=0.75)
        d.shape('M840,990 C880,1040 900,1080 960,1114 L1072,1110 C1050,1060 1020,1010 1000,985 Z',
                light(self.PINK, 0.35), stroke=self.EDGE, sw=3, opacity=0.75)
        for x in (700, 790, 880, 960):
            d.line(f'M{x},1000 Q{x + 14},1060 {x + 6},1104', self.SH, 2.5)

    def front(self, d):
        hair_cap(d, sleek=True, part=False)
        bun_top(d, 806, 516, 56)
        # 斗篷式薄纱：从双肩垂下，半透明，可透出手臂
        cape = light(self.PINK, 0.25)
        d.shape('M640,788 C580,792 512,846 480,930 C462,990 470,1036 492,1060 '
                'C520,1020 560,990 610,972 C650,958 676,930 680,900 Z', cape, stroke=self.EDGE, sw=3.5, opacity=0.62)
        d.shape('M930,782 C1004,780 1080,838 1112,920 C1132,980 1126,1030 1108,1056 '
                'C1078,1016 1036,986 990,968 C956,952 936,926 930,896 Z', cape, stroke=self.EDGE, sw=3.5, opacity=0.62)
        d.line('M500,980 C540,960 600,950 650,930', self.EDGE, 2.5, opacity=0.8)
        d.line('M1100,980 C1060,960 1000,950 960,930', self.EDGE, 2.5, opacity=0.8)
        # 前中层叠荷叶褶
        for i, y in enumerate(range(800, 960, 32)):
            w = 46 + i * 4
            d.shape(f'M{780 - w},{y} C{780 - w / 2},{y - 12} {780 + w / 2},{y - 12} {780 + w},{y} '
                    f'C{780 + w * 0.6},{y + 30} {780 - w * 0.6},{y + 30} {780 - w},{y} Z',
                    light(self.PINK, 0.15), shade=self.SH, off=(-10, -4), stroke=self.EDGE, sw=3, opacity=0.92)
        # 水晶垂坠耳饰
        earring_drop(d, 594, 764, '#EAF2F7', n=3, r=7)
        earring_drop(d, 1010, 750, '#EAF2F7', n=3, r=7)


# =============================================================== 03 爱情
class L03(Look):
    no = 3
    title = '爱情'
    BLK = '#24242C'
    SH = '#141419'
    HI = '#5A5A6C'
    GOLD = '#D9AE4E'

    def back(self, d):
        low_bun_side(d, 1064, 700, 46)

    def bodice(self, d):
        d.shape('M556,788 C660,790 720,806 780,806 C850,806 920,790 1044,776 L1044,1000 L556,1000 Z',
                self.BLK, shade=self.SH, off=(-40, 0))
        d.line('M690,792 C730,812 830,812 872,790', self.HI, 3)           # 圆领口缝
        d.line('M600,800 L600,860', self.HI, 3)                             # 垫肩线
        d.line('M944,790 L944,850', self.HI, 3)
        # 腰部两侧镂空（露出身体）+ 细金链
        d.shape('M576,920 C630,890 720,892 774,928 C720,950 630,950 576,920 Z', ORANGE, sw=4)
        d.shape('M774,928 C840,890 960,886 1044,906 C980,944 850,950 774,928 Z', ORANGE, sw=4)
        d.line('M576,922 C660,930 720,930 774,928 C850,928 960,916 1044,908', self.GOLD, 5)

    def arms(self, d):
        for s in ('L', 'R'):
            draw_arm(d, s)
            draw_arm(d, s, fill=self.BLK, length=ARM_L - 20)
            arm_band(d, s, ARM_L - 30, ARM_L - 20, self.BLK, stroke=self.HI, sw=2)

    def skirt(self, d):
        rest = (f'C1030,1030 1022,1060 1030,1084 C1040,1100 1060,1108 1076,1114 '
                f'{hem(1076, 486, 1116, rise=22, step=40)} C504,1104 540,1080 552,1050 C562,1024 568,1000 570,980')
        skirt_shape(d, (570, 980), (1028, 970), rest, self.BLK, shade=self.SH)
        d.line('M562,990 C560,1030 548,1070 506,1104', self.HI, 3)          # 左侧轮廓光
        d.line('M790,1000 L796,1100', self.HI, 2.5, opacity=0.8)

    def front(self, d):
        hair_cap(d, part=True)
        tendrils(d)
        for (x, y) in [(594, 772), (1010, 758)]:
            d.circle(x, y, 15, 'none', stroke=self.GOLD, sw=5)
            d.raw(f'<path d="M{x - 9},{y + 18} q9,-10 9,2 q0,-12 9,-2 q0,10 -9,16 q-9,-6 -9,-16 Z" '
                  f'fill="{self.GOLD}" stroke="{INK}" stroke-width="2"/>')


# =============================================================== 04 李白
class L04(Look):
    no = 4
    title = '李白'
    WINE = '#7C1F2C'
    SH = '#57121D'
    HI = '#A33A4A'
    GLOVE = '#B9C3DA'

    def locks(self, d):
        hair_front_locks(d, bottom=1000)

    def back(self, d):
        hair_long_back(d, bottom=1020)

    def bodice(self, d):
        # 无袖挖肩上衣（肩部露出身体）
        d.shape('M640,806 C660,800 676,792 680,776 L876,776 C880,792 896,800 930,806 C960,840 990,858 1044,866 '
                'L1044,1000 L556,1000 L556,872 C600,862 628,838 640,806 Z', self.WINE, shade=self.SH, off=(-40, 0))
        d.line('M684,804 C740,812 820,812 874,802', self.HI, 3)   # 立领缝线
        # 斜襟：左领口斜向右腰，带一条叠襟阴影
        d.shape('M678,806 L708,806 C800,850 900,880 1044,900 L1044,914 C900,898 790,866 678,820 Z',
                self.SH, stroke=None)
        d.line('M708,806 C800,850 900,880 1044,900', INK, 3.5)
        # 腰头
        d.shape('M556,930 L1044,914 L1044,946 L556,962 Z', self.WINE, shade=self.SH, off=(-30, 0))

    def arms(self, d):
        for s in ('L', 'R'):
            draw_arm(d, s)
            draw_arm(d, s, fill=self.GLOVE, start=22)

    def skirt(self, d):
        # 阔腿裤：两条宽裤管，裤脚落地前露出脚尖
        d.shape(f'M570,975 L780,975 L786,1100 L514,1100 C530,1060 556,1010 570,975 Z', self.WINE,
                shade=self.SH, off=(-30, 0), outline='M780,975 L786,1100 L514,1100 C530,1060 556,1010 570,975')
        d.shape(f'M780,975 L1032,962 C1046,1010 1062,1060 1076,1100 L794,1100 Z', self.WINE,
                shade=self.SH, off=(-30, 0), outline='M1032,962 C1046,1010 1062,1060 1076,1100 L794,1100 L780,975')
        d.line('M650,990 L640,1096', self.HI, 2.5)
        d.line('M930,985 L950,1096', self.HI, 2.5)
        # 胯部两侧尖角翻片
        d.shape('M600,940 L742,960 L648,1050 L526,1004 Z', self.WINE, shade=self.SH, off=(-16, -6))
        d.shape('M836,956 L1036,926 L1104,1000 L956,1046 Z', self.WINE, shade=self.SH, off=(-16, -6))
        d.line('M610,952 L644,1036', self.HI, 2.5)
        d.line('M1020,940 L960,1032', self.HI, 2.5)

    def front(self, d):
        hair_cap(d, part=True)
        d.circle(1012, 752, 8, '#8FA6D8', stroke=INK, sw=2.5)   # 小耳钉（简化）
        d.circle(598, 762, 8, '#8FA6D8', stroke=INK, sw=2.5)


# =============================================================== 05 Dear Friend
class L05(Look):
    no = 5
    title = 'Dear Friend'
    YEL = '#F2E3A2'
    SH = '#D9C47E'
    LACE = '#FFFDF4'

    def locks(self, d):
        hair_front_locks(d, bottom=990)

    def back(self, d):
        hair_long_back(d, bottom=1010)

    def bodice(self, d):
        d.shape('M556,806 C620,804 664,800 676,780 L884,774 C896,794 940,796 1044,790 L1044,1000 L556,1000 Z',
                self.YEL, shade=self.SH, off=(-40, 0))
        d.line('M680,806 C740,814 830,812 880,800', self.SH, 3)   # 高领缝线
        for x in range(612, 1010, 22):
            d.line(f'M{x},{818} L{x + 4},{990}', self.SH, 2.2)

    def arms(self, d):
        draw_arm(d, 'L')
        draw_arm(d, 'R')

    def skirt(self, d):
        rest = f'C1070,1010 1108,1070 1130,1112 {hem(1130, 444, 1114, rise=22, step=40)} C468,1060 520,1010 560,980'
        skirt_shape(d, (560, 980), (1028, 972), rest, self.YEL, shade=self.SH)
        for (x0, x1) in [(640, 560), (720, 700), (800, 820), (900, 960), (980, 1070)]:
            d.line(f'M{x0},990 Q{(x0 + x1) / 2 + 6},1050 {x1},1106', self.SH, 2.5)
        # 轻薄下摆层
        d.line(f'M470,1086 C640,1074 900,1074 1110,1088', light(self.SH, 0.2), 3)

    def front(self, d):
        hair_cap(d, part=True)
        # 领口花边
        d.raw(f'<path d="M678,780 {scallop(678, 884, 776, r=8, up=True)}" fill="{self.LACE}" stroke="{INK}" stroke-width="2.5"/>')
        # 短泡泡袖 + 花边袖口
        for s in ('L', 'R'):
            cx, cy = arm_point(s, 22)
            ex, ey = arm_point(s, 58)
            d.shape(f'M{cx - 48},{cy - 8} C{cx - 50},{cy - 50} {cx + 50},{cy - 50} {cx + 48},{cy - 8} '
                    f'C{ex + 40},{ey} {ex - 40},{ey + 4} {cx - 48},{cy - 8} Z', self.YEL, shade=self.SH, off=(-12, -4))
            d.line(f'M{ex - 36},{ey - 2} Q{ex},{ey + 12} {ex + 36},{ey - 4}', self.LACE, 7)
            d.line(f'M{ex - 36},{ey - 2} Q{ex},{ey + 12} {ex + 36},{ey - 4}', INK, 2, dash='3 6')
        # 金色耳骨夹（简化）
        d.line('M596,756 q-10,14 0,28', '#D2A84E', 6)
        d.line('M1014,744 q-10,14 0,28', '#D2A84E', 6)


# =============================================================== 06 一个人跳舞
class L06(Look):
    no = 6
    title = '一个人跳舞'
    DEN = '#2D3448'
    SH = '#1C2132'
    ST = '#9AA5BF'
    GOLD = '#D9B25C'

    def back(self, d):
        hair_long_back(d, bottom=1050, spread=40, wavy=26)

    def locks(self, d):
        hair_front_locks(d, bottom=990, wavy=18)

    def bodice(self, d):
        d.shape('M556,800 L654,800 C660,872 700,898 778,898 C856,898 894,868 902,794 L1044,782 '
                'L1044,1000 L556,1000 Z', self.DEN, shade=self.SH, off=(-40, 0))
        d.line('M640,806 C648,884 696,912 778,912 C866,912 908,880 916,800', self.ST, 2.5, dash='7 6')
        d.line('M610,830 C640,900 660,960 650,1000', self.ST, 2.5, dash='7 6')
        d.line('M950,820 C930,900 920,960 930,1000', self.ST, 2.5, dash='7 6')

    def arms(self, d):
        for s in ('L', 'R'):
            draw_arm(d, s)
            arm_band(d, s, 84, 106, self.GOLD, sw=3)

    def skirt(self, d):
        rest = (f'C1046,1010 1056,1060 1064,1098 L800,1098 L784,1050 L768,1098 L500,1098 '
                f'C518,1050 544,1006 562,980')
        skirt_shape(d, (562, 980), (1028, 972), rest, self.DEN, shade=self.SH)
        d.line('M640,1000 C630,1040 610,1070 600,1092', self.ST, 2.5, dash='7 6')
        d.line('M940,996 C950,1040 962,1070 970,1092', self.ST, 2.5, dash='7 6')
        # 前中通长金色拉链
        d.line('M778,898 L784,1050', INK, 10)
        d.line('M778,898 L784,1050', self.GOLD, 6)
        for y in range(906, 1046, 10):
            d.line(f'M{775 + (y - 898) * 0.04},{y} l8,0', '#A9842F', 2)
        d.shape('M770,900 L788,900 L790,930 L772,930 Z', self.GOLD, sw=3)

    def front(self, d):
        hair_cap(d, part=True)
        # 蓬松卷发：头顶与两侧的卷曲轮廓
        for (x, y) in [(560, 640), (556, 720), (1050, 610), (1066, 690)]:
            d.line(f'M{x},{y} q-16,20 0,40 q16,20 0,40', HAIR_HI, 3, opacity=0.7)
        d.circle(598, 772, 9, self.GOLD, stroke=INK, sw=2.5)
        d.circle(1012, 756, 9, self.GOLD, stroke=INK, sw=2.5)


# =============================================================== 07 思念是一种病
class L07(Look):
    no = 7
    title = '思念是一种病'
    BLUE = '#2C3EB2'
    SH = '#1B2780'
    HI = '#5B6EDB'
    shadow_rx = 400

    def back(self, d):
        low_bun_side(d, 1064, 706, 44)

    def bodice(self, d):
        # 单肩：左腋下斜向右肩
        d.shape('M556,878 C650,866 820,834 936,794 L1044,770 L1044,1000 L556,1000 Z',
                self.BLUE, shade=self.SH, off=(-40, 0))
        for i, y in enumerate(range(900, 1000, 18)):
            d.line(f'M{580 + i * 4},{y} Q780,{y - 22 + i * 2} 1040,{y - 30}', self.HI, 2.5)

    def arms(self, d):
        for s, sign in (('L', -1), ('R', 1)):
            draw_arm(d, s, fill=self.BLUE)
            # 手套上臂垂下的长垂片
            p1 = arm_point(s, 16, 22 * sign)
            p2 = arm_point(s, 70, 24 * sign)
            bx = p2[0] + sign * 26
            d.shape(f'M{p1[0]:.0f},{p1[1]:.0f} C{bx + sign * 6:.0f},{p1[1] + 80:.0f} {bx:.0f},1000 {bx - sign * 6:.0f},1070 '
                    f'L{bx - sign * 36:.0f},1062 C{bx - sign * 26:.0f},1000 {p2[0]:.0f},{p2[1] + 30:.0f} {p2[0]:.0f},{p2[1]:.0f} Z',
                    self.BLUE, shade=self.SH, off=(-10, 0))

    def skirt(self, d):
        rest = (f'C1028,1010 1018,1040 1016,1060 C1060,1080 1140,1100 1236,1120 '
                f'{hem(1236, 474, 1124, rise=22, step=40)} C520,1100 560,1080 574,1060 C566,1030 568,1006 572,980')
        skirt_shape(d, (572, 980), (1028, 966), rest, self.BLUE, shade=self.SH)
        for i, y in enumerate(range(996, 1060, 16)):
            d.line(f'M{578},{y} Q790,{y - 16} 1024,{y - 24}', self.HI, 2.5)
        d.line('M574,1062 C680,1052 900,1050 1016,1060', INK, 3)       # 鱼尾分界
        for (x0, x1) in [(640, 560), (740, 720), (840, 880), (940, 1060)]:
            d.line(f'M{x0},1068 Q{(x0 + x1) / 2},1090 {x1},1116', self.SH, 3)

    def front(self, d):
        # 夸张大斜帽：扁平宽檐圆盘，向右下倾斜约 24°
        hair_cap(d, sleek=True, part=False)
        cx, cy, a = 866, 604 - HAT['lift'], 22 + HAT['tilt']
        d.raw(f'<g transform="translate({cx},{cy}) rotate({a})">')
        d.shape('M-262,0 A262,64 0 1 0 262,0 A262,64 0 1 0 -262,0 Z', self.BLUE, shade=self.SH, off=(0, -16))
        d.shape('M-232,-6 A232,48 0 1 0 232,-6 A232,48 0 1 0 -232,-6 Z', self.HI, stroke=None, opacity=0.35)
        d.shape('M-70,-8 C-70,-58 70,-58 70,-8 A70,20 0 0 1 -70,-8 Z', self.BLUE, shade=self.SH, off=(-14, 0))
        d.raw('</g>')
        # 深色大耳饰
        for (x, y) in [(596, 770), (1010, 756)]:
            for (ox, oy) in [(0, 0), (-8, 14), (8, 14), (0, 28)]:
                d.circle(x + ox, y + oy, 8, '#2A2F55', stroke=INK, sw=2.5)

    def legs(self, d):
        draw_legs(d)


# =============================================================== 08 梦一场
class L08(Look):
    no = 8
    title = '梦一场'
    BLK = '#23232B'
    BSH = '#141419'
    BHI = '#5A5A6C'
    NAVY = '#25336A'
    NSH = '#172146'
    NHI = '#40569E'

    def back(self, d):
        low_bun_side(d, 1064, 690, 44)

    def bodice(self, d):
        d.shape('M556,846 L1044,828 L1044,1000 L556,1000 Z', self.BLK, shade=self.BSH, off=(-40, 0))
        d.line('M560,852 L1044,834', self.BHI, 3)
        for x in (640, 710, 850, 930):
            d.line(f'M{x},{850 - (x - 556) * 0.04} Q{x + (12 if x < 780 else -12)},920 {x},990', self.BHI, 2.5)

    def legs(self, d):
        draw_legs(d, shoe='#1A1A1F', shoe_h=34, platform=6)

    def skirt(self, d):
        # 深蓝蓬裙：腰下收碎褶 → 鼓起 → 下摆内收
        d.shape('M566,960 L1034,944 C1056,972 1090,1010 1094,1050 C1098,1092 1050,1102 980,1102 '
                'L600,1104 C530,1104 486,1090 490,1050 C494,1010 536,982 566,960 Z',
                self.NAVY, shade=self.NSH, off=(-50, -6))
        for x in range(600, 1040, 40):
            d.line(f'M{x},{962 - (x - 566) * 0.034} Q{x + (x - 800) * 0.25},1010 {x + (x - 800) * 0.35},1060', self.NHI, 2.5)
        d.line('M500,1060 C520,1092 600,1098 700,1098', self.NHI, 3, opacity=0.8)

    def front(self, d):
        hair_cap(d, part=True)
        tendrils(d)
        earring_drop(d, 594, 762, '#D6DBE2', n=2, r=8)
        earring_drop(d, 1010, 748, '#D6DBE2', n=2, r=8)


# =============================================================== 09 舞娘
class L09(Look):
    no = 9
    skirt_pivot = 800
    title = '舞娘'
    CAPE = '#B3174F'
    SH = '#7E0E37'
    HI = '#DE5486'
    INNER = '#5E1828'
    ISH = '#43101C'
    GOLD = '#D2A443'
    shadow_rx = 480

    def arms(self, d):
        pass                    # 视频版：手臂画在披风之前（front 里），举臂时可见

    def _tiers(self, d, cid, x0, x1, y0, y1, step=24):
        """内部层叠褶皱：一排排小弧，深浅交替。"""
        for k, y in enumerate(range(y0, y1, step)):
            xa = x0 + (k % 2) * 9
            d.raw(f'<path d="M{xa},{y} {scallop(xa, x1, y, r=10)}" fill="none" stroke="{self.SH}" '
                  f'stroke-width="3" clip-path="url(#{cid})"/>')
            d.raw(f'<path d="M{xa},{y - 4} {scallop(xa, x1, y - 4, r=10)}" fill="none" stroke="{self.HI}" '
                  f'stroke-width="1.6" opacity="0.7" clip-path="url(#{cid})"/>')

    def back(self, d):
        hair_long_back(d, bottom=960, wavy=20)
        # 拖地的褶边长条（披风尾），向两侧铺开
        strips = [
            Bez((560, 1000)).C((520, 1060), (430, 1100), (300, 1112)).C((290, 1124), (300, 1134), (316, 1136))
                .C((450, 1134), (560, 1110), (620, 1060)).L((620, 1000)),
            Bez((640, 1010)).C((610, 1070), (540, 1120), (440, 1132)).C((440, 1142), (452, 1148), (470, 1148))
                .C((570, 1144), (650, 1110), (690, 1060)).L((690, 1010)),
            Bez((1040, 1000)).C((1090, 1060), (1180, 1096), (1300, 1110)).C((1312, 1122), (1302, 1134), (1286, 1136))
                .C((1150, 1132), (1050, 1110), (980, 1060)).L((980, 1000)),
            Bez((960, 1010)).C((990, 1070), (1060, 1120), (1170, 1134)).C((1172, 1144), (1160, 1150), (1140, 1150))
                .C((1040, 1144), (950, 1110), (910, 1060)).L((910, 1010)),
        ]
        for b in strips:
            cid = ruffle_shape(d, b, self.CAPE, self.SH, r=11, spacing=16, off=(-20, -6))
            self._tiers(d, cid, 280, 1320, 1010, 1150, step=18)

    def bodice(self, d):
        d.shape('M556,792 L1044,780 L1044,1000 L556,1000 Z', self.INNER, shade=self.ISH, off=(-40, 0))

    def skirt(self, d):
        rest = f'L1000,1110 {hem(1000, 570, 1112, rise=20, step=40)} L568,1000'
        skirt_shape(d, (568, 1000), (980, 990), rest, self.INNER, shade=self.ISH)
        d.line('M760,1000 L752,1100', self.ISH, 3)
        d.line('M820,1000 L828,1100', self.ISH, 3)
        # 夸张的褶皱披风：大圆肩 + 落地，前中开口露出内层酒红长裙
        L = (Bez((700, 790)).C((640, 760), (520, 750), (472, 806)).C((424, 864), (436, 948), (480, 996))
             .C((462, 1046), (458, 1092), (466, 1124)).L((688, 1124)).C((676, 1040), (676, 900), (700, 790)))
        R = (Bez((862, 784)).C((934, 752), (1076, 748), (1126, 806)).C((1172, 862), (1160, 946), (1116, 994))
             .C((1132, 1044), (1140, 1092), (1146, 1126)).L((884, 1126)).C((880, 1040), (876, 900), (862, 784)))
        for b, x0, x1 in ((L, 430, 700), (R, 860, 1180)):
            cid = ruffle_shape(d, b, self.CAPE, self.SH, r=15, spacing=21, segs=[0, 1, 2], off=(-40, -6))
            self._tiers(d, cid, x0, x1, 800, 1130, step=24)
        # 开口边缘的竖向荷叶褶
        for path in ('M700,790 C676,900 676,1040 688,1124', 'M862,784 C876,900 880,1040 884,1126'):
            d.line(path, INK, 26)
            d.line(path, self.CAPE, 19)
            d.line(path, self.SH, 3, dash='5 8')
        # 高耸的褶边领
        collar = Bez((690, 800)).C((690, 770), (720, 764), (780, 766)).C((840, 764), (872, 770), (872, 796)).L((690, 800))
        ruffle_shape(d, collar, self.CAPE, self.SH, r=11, spacing=16, segs=[0, 1], off=(-10, -4))

    def front(self, d):
        draw_arm(d, 'L')
        draw_arm(d, 'R')
        hair_cap(d, part=False)
        hair_front_locks(d, bottom=790, wavy=14)
        # 内层领口系带蝴蝶结
        d.shape('M780,812 C744,790 712,800 716,830 C720,852 754,846 780,824 Z', self.INNER, shade=self.ISH, off=(-8, 0))
        d.shape('M786,812 C822,790 852,800 846,830 C842,852 810,846 786,824 Z', self.INNER, shade=self.ISH, off=(-8, 0))
        d.shape('M772,818 L792,818 L812,940 L794,946 L782,866 L770,950 L752,944 Z', self.INNER, shade=self.ISH, off=(-6, 0))
        d.circle(782, 818, 12, self.INNER, stroke=INK, sw=4)
        # 金色弹簧大圈耳饰
        for (x, y) in [(600, 770), (1010, 756)]:
            d.circle(x, y, 22, 'none', stroke=INK, sw=10)
            d.circle(x, y, 22, 'none', stroke=self.GOLD, sw=6)
            d.circle(x, y, 22, 'none', stroke='#A8822C', sw=2, opacity=0.8)


# =============================================================== 10 开始懂了
class L10(Look):
    no = 10
    title = '开始懂了'
    WHITE = '#F7F5F0'
    SH = '#D8D4CA'
    TRIM = '#1F1F26'

    def locks(self, d):
        hair_front_locks(d, bottom=1000)

    def back(self, d):
        hair_long_back(d, bottom=1060)

    def bodice(self, d):
        d.shape('M556,800 L690,794 L774,934 L862,788 L1044,778 L1044,1000 L556,1000 Z',
                self.WHITE, shade=self.SH, off=(-40, 0))
        # 黑色亮片领缘（深 V）
        d.line('M690,794 L774,934 L862,788', INK, 26)
        d.line('M690,794 L774,934 L862,788', self.TRIM, 19)
        d.line('M690,794 L774,934 L862,788', '#A4A6B4', 4, dash='1 9')
        for x in (646, 662, 900, 916):
            d.line(f'M{x},{820} l-8,14 l8,14 l-8,14 l8,14 l-8,14 l8,14 l-8,14 l8,14 l-8,14 l8,14', self.SH, 2.5)

    def arms(self, d):
        for s in ('L', 'R'):
            draw_arm(d, s)
            arm_band(d, s, 92, 100, '#CDD2DA', sw=2)
            arm_band(d, s, 103, 110, '#CDD2DA', sw=2)

    def skirt(self, d):
        # 长裙：胯部两侧垂坠鼓起（并入裙身外轮廓），再落成长摆
        rest = (f'C1078,996 1104,1030 1088,1062 C1100,1080 1108,1096 1112,1112 '
                f'{hem(1112, 458, 1114, rise=22, step=40)} '
                f'C464,1096 474,1080 490,1064 C470,1030 500,994 560,980')
        skirt_shape(d, (560, 980), (1028, 972), rest, self.WHITE, shade=self.SH)
        # 鼓包的垂坠弧线
        d.line('M500,1060 C540,1084 610,1080 650,1040', INK, 3)
        d.line('M520,1030 C560,1050 600,1046 630,1020', self.SH, 3)
        d.line('M1086,1058 C1040,1080 980,1074 950,1034', INK, 3)
        d.line('M1066,1026 C1030,1046 996,1040 972,1016', self.SH, 3)
        for (x0, x1) in [(640, 560), (710, 670), (780, 780), (850, 880), (920, 990)]:
            d.line(f'M{x0},1050 Q{(x0 + x1) / 2 + 8},1084 {x1},1108', self.SH, 3)

    def front(self, d):
        hair_cap(d, part=True)


# =============================================================== 11 君
class L11(Look):
    no = 11
    title = '君'
    WHITE = '#F8F7F3'
    SH = '#D2D6DC'
    HI = '#FFFFFF'
    RED = '#CC322C'
    RSH = '#8C1C1A'
    GREEN = '#55703A'

    def locks(self, d):
        hair_front_locks(d, bottom=990)

    def back(self, d):
        hair_long_back(d, bottom=1010)

    def legs(self, d):
        draw_legs(d, sock='#F6F5F1', sock_top=980, shoe='#D8D4CC', shoe_h=30, platform=8)
        for x in LEGS_X:
            d.line(f'M{x - 24},{GROUND - 40} L{x + 24},{GROUND - 40}', '#ECEAE6', 6)
            d.line(f'M{x - 24},{GROUND - 40} L{x + 24},{GROUND - 40}', INK, 2)

    def bodice(self, d):
        d.shape('M556,842 C700,850 860,838 1044,824 L1044,1000 L556,1000 Z', self.WHITE, shade=self.SH, off=(-40, 0))
        for (a, b) in [((600, 860), (700, 990)), ((700, 856), (760, 940)), ((930, 846), (880, 990))]:
            d.line(f'M{a[0]},{a[1]} Q{(a[0] + b[0]) / 2 + 20},{(a[1] + b[1]) / 2} {b[0]},{b[1]}', self.SH, 3)

    def skirt(self, d):
        # 高低不对称下摆：右前短（露白袜），左后长
        rest = ('C1060,1004 1080,1032 1096,1056 C1010,1062 930,1066 860,1072 '
                'C760,1080 620,1096 470,1104 C496,1060 530,1010 562,980')
        skirt_shape(d, (562, 980), (1028, 970), rest, self.WHITE, shade=self.SH)
        d.line('M600,1000 C580,1040 540,1080 500,1100', self.SH, 3)
        d.line('M700,1000 C700,1040 680,1070 660,1090', self.SH, 3)
        d.line('M960,990 C990,1020 1020,1040 1050,1058', self.SH, 3)
        d.line('M530,1060 C620,1040 700,1046 760,1060', self.HI, 4, opacity=0.9)

    def front(self, d):
        hair_cap(d, part=True)
        # 绿色花茎与叶
        d.line('M862,904 C840,940 800,980 770,1030', INK, 12)
        d.line('M862,904 C840,940 800,980 770,1030', self.GREEN, 7)
        for (x, y, r) in [(820, 960, -30), (790, 1000, 30), (846, 930, 20)]:
            d.raw(f'<path d="M{x},{y} q-30,-14 -46,0 q24,16 46,0 Z" fill="{self.GREEN}" stroke="{INK}" '
                  f'stroke-width="3" transform="rotate({r} {x} {y})"/>')
        # 醒目的红色胸花（右胸前）
        cx, cy = 872, 872
        for k in range(7):
            ang = k * 2 * math.pi / 7
            px, py = cx + 30 * math.cos(ang), cy + 26 * math.sin(ang)
            d.circle(f'{px:.1f}', f'{py:.1f}', 24, self.RED, stroke=INK, sw=3.5)
        d.circle(cx, cy, 24, '#B12A26', stroke=INK, sw=3)
        d.circle(cx - 4, cy - 2, 10, '#5E1412', stroke=None)
        for k in range(5):
            ang = k * 2 * math.pi / 5 + 0.4
            d.line(f'M{cx + 14 * math.cos(ang):.1f},{cy + 14 * math.sin(ang):.1f} '
                   f'Q{cx + 30 * math.cos(ang + 0.3):.1f},{cy + 30 * math.sin(ang + 0.3):.1f} '
                   f'{cx + 42 * math.cos(ang):.1f},{cy + 40 * math.sin(ang):.1f}', self.RSH, 3)
        d.circle(1012, 756, 8, '#3A2A2A', stroke=INK, sw=2.5)


# =============================================================== 12 落叶归根
class L12(Look):
    no = 12
    title = '落叶归根'
    BLK = '#1E1E25'
    SH = '#121216'
    TOP = '#383845'
    HI = '#6A6A7E'
    GLOVE = '#2B2B33'

    def locks(self, d):
        hair_front_locks(d, bottom=960, wavy=10)

    def back(self, d):
        hair_long_back(d, bottom=1000, wavy=12)

    def legs(self, d):
        draw_legs(d, sock='#4A3F44', sock_top=980, shoe='#16161A', shoe_h=26)

    def bodice(self, d):
        d.shape('M556,874 C580,838 640,822 690,830 C740,838 766,862 774,876 C792,852 830,828 900,822 '
                'C962,818 1010,832 1044,852 L1044,1000 L556,1000 Z', self.BLK, shade=self.SH, off=(-40, 0))
        d.line('M562,878 C584,846 640,832 690,840 C736,848 762,868 774,884 C794,862 832,838 900,832 '
               'C960,828 1004,840 1040,860', self.HI, 4, dash='2 7')
        self._sparkle(d, 580, 1040, 880, 1000, 46)

    def _sparkle(self, d, x0, x1, y0, y1, n, seed=7):
        import random
        rnd = random.Random(seed)
        for _ in range(n):
            x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
            d.circle(f'{x:.0f}', f'{y:.0f}', rnd.choice([2, 2.5, 3]), rnd.choice(['#6E6E82', '#8A8AA0', '#C9CAD6']), stroke=None)

    def arms(self, d):
        for s in ('L', 'R'):
            draw_arm(d, s)
            draw_arm(d, s, fill=self.GLOVE, start=18, opacity=0.88)
            arm_band(d, s, 82, 94, '#D5DAE2', sw=2.5)

    def skirt(self, d):
        # 修身长柱裙，左前开衩
        rest = (f'C1030,1030 1024,1080 1020,1110 L640,1110 L620,1060 L604,1110 L566,1110 '
                f'C568,1060 570,1020 568,980')
        skirt_shape(d, (568, 980), (1028, 968), rest, self.BLK, shade=self.SH)
        self._sparkle(d, 590, 1010, 1000, 1100, 50, seed=11)
        d.line('M570,990 C570,1040 568,1080 566,1106', self.HI, 3)
        # 右胯不对称雕塑翼片：硬挺的扇形面，上沿提亮、折痕放射，避免黑成一片
        d.shape('M884,926 C980,926 1110,946 1200,986 C1150,1010 1080,1050 1030,1096 C1010,1040 960,980 884,926 Z',
                self.BLK, shade=self.SH, off=(-24, 0))
        d.shape('M884,926 C980,926 1110,946 1200,986 C1120,980 1000,972 940,950 Z', self.TOP, stroke=INK, sw=3.5)
        for (x1, y1) in [(1150, 1010), (1100, 1040), (1060, 1066)]:
            d.line(f'M936,950 Q{(936 + x1) / 2},{(950 + y1) / 2 - 18} {x1},{y1}', self.HI, 2.5)
        d.line('M890,930 C990,932 1110,952 1194,988', self.HI, 3)
        self._sparkle(d, 960, 1150, 990, 1050, 18, seed=5)

    def front(self, d):
        hair_cap(d, part=False)
        # 钻石项链 + 绿宝石吊坠（简化）
        d.line('M684,800 Q730,846 774,852 Q820,846 866,796', '#E3E7EE', 5)
        d.line('M684,800 Q730,846 774,852 Q820,846 866,796', INK, 1.5, dash='2 6')
        d.raw(f'<path d="M774,852 l-9,12 l9,16 l9,-16 Z" fill="#2F9E68" stroke="{INK}" stroke-width="2.5"/>')
        earring_drop(d, 594, 764, '#2F9E68', n=2, r=7)
        earring_drop(d, 1010, 750, '#2F9E68', n=2, r=7)


# =============================================================== 13 有趣
class L13(Look):
    no = 13
    title = '有趣'
    GB = '#BFCCD7'
    SH = '#97A9B8'
    HI = '#DCE5EC'
    GOLD = '#D7AA45'

    def back(self, d):
        # 长辫：从脑后右侧垂到膝下
        pts_ = [(1050 + 8 * math.sin(i * 0.5), 640 + i * 38) for i in range(10)]
        for i, (x, y) in enumerate(pts_):
            rot = 24 if i % 2 else -24
            d.raw(f'<g transform="translate({x:.0f},{y:.0f}) rotate({rot})">')
            d.shape('M-20,-26 C-24,0 -16,22 0,28 C16,22 24,0 20,-26 C10,-32 -10,-32 -20,-26 Z',
                    HAIR, shade=HAIR_SH, off=(-6, 0), sw=3.5)
            d.raw('</g>')
        d.shape('M1046,1006 l-16,34 l12,-6 l6,10 l8,-10 l12,4 Z', HAIR, sw=3)

    def bodice(self, d):
        # 挂脖挖肩：高立领，两侧袖窿深挖
        d.shape('M648,808 C666,802 684,792 688,774 L866,774 C870,792 888,802 906,808 C934,848 980,874 1044,882 '
                'L1044,1000 L556,1000 L556,892 C600,884 632,852 648,808 Z', self.GB, shade=self.SH, off=(-40, 0))
        d.line('M692,806 C740,814 820,814 864,804', self.SH, 3)   # 立领缝线
        for x in range(700, 900, 30):
            d.line(f'M{x},{820} Q{x + 6},860 {x - 4},900', self.SH, 2.5)
        # 腰部抽褶椭圆镂空
        d.shape('M676,932 C700,902 900,898 936,930 C900,962 712,966 676,932 Z', ORANGE, sw=4)
        for i in range(14):
            t = i / 13
            x = 690 + t * 236
            d.line(f'M{x:.0f},{916 - 10 * math.sin(t * math.pi):.0f} l0,-10', self.SH, 2.5)
            d.line(f'M{x:.0f},{948 + 10 * math.sin(t * math.pi):.0f} l0,10', self.SH, 2.5)

    def skirt(self, d):
        rest = (f'C1060,1010 1080,1064 1092,1110 {hem(1092, 480, 1114, rise=22, step=40, tilt=-10)} '
                f'C500,1060 530,1010 562,980')
        skirt_shape(d, (562, 980), (1028, 970), rest, self.GB, shade=self.SH)
        for (x0, x1) in [(640, 540), (720, 660), (800, 800), (880, 930), (960, 1050)]:
            d.line(f'M{x0},1000 Q{(x0 + x1) / 2 + 10},1060 {x1},1106', self.SH, 3)
        d.line('M600,990 C700,1030 860,1040 1000,1090', self.HI, 4)        # 斜向垂褶

    def front(self, d):
        hair_cap(d, sleek=True, part=True)
        for (x, y) in [(592, 774), (1006, 760)]:
            # 银白色细圈大耳环（按审核意见：银白、更细、更大）
            hp = f'M{x + 16},{y - 12} A40,47 0 1 0 {x + 22},{y + 58}'
            d.raw(f'<path d="{hp}" fill="none" stroke="{INK}" stroke-width="9" stroke-linecap="round"/>')
            d.raw(f'<path d="{hp}" fill="none" stroke="#E6EAF0" stroke-width="5" stroke-linecap="round"/>')
            d.raw(f'<path d="M{x - 14},{y + 6} A32,38 0 0 0 {x - 6},{y + 46}" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round"/>')
