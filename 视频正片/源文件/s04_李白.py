# -*- coding: utf-8 -*-
"""04《李白》—— 8-bit 像素游戏。
意象：Live House 的红幕变成一关横版游戏。Clawd 跟着拍子点头 → 下蹲蓄力 → 跳起顶砖块，金币弹出 →
落地压扁回弹 → 戴着手套左右两步踩点 → 双臂举起定格摆酷。动作节奏由慢到快再定住。
画法：整幅画面在 320×180 的低分辨率上绘制，角色按造型调色板量化并加 1 像素描边，最近邻放大 6 倍；一拍二。
"""
import math
import numpy as np
import cv2
import engine as E
from scene_base import Scene

LW, LH, SC = 240, 135, 8
FLOOR = 113
PAL = ['#7C1F2C', '#57121D', '#A33A4A', '#B9C3DA', '#8E97B0', '#D97757', '#B65C40', '#2B1F1C',
       '#5A4540', '#2E2320', '#F4E9D8', '#8FA6D8', '#E6C9B8']


def rgbs(lst):
    return np.array([E.hexrgb(c) for c in lst], np.float32)


class S04(Scene):
    key = '04'
    filename = '04_李白'
    style = '8-bit 像素游戏'
    no = 4
    core = 4.0
    step = 2

    def setup(self):
        bg = np.zeros((LH, LW, 3), np.float32)
        # 红幕：竖向褶皱三色
        cur = [E.hexrgb('#5C0F1C'), E.hexrgb('#8A1B2B'), E.hexrgb('#B3293A')]
        for x in range(LW):
            k = (x % 12)
            bg[:, x] = cur[0] if k < 2 else cur[2] if 5 <= k < 8 else cur[1]
        # 幕顶垂帘
        for x in range(LW):
            yb = 10 + (2 if (x // 6) % 2 else 0)
            bg[:yb, x] = E.hexrgb('#3E0A14')
            bg[yb - 2:yb, x] = E.hexrgb('#D6A23B')
        # 舞台地板
        bg[FLOOR:] = E.hexrgb('#4A2C1E')
        for y in range(FLOOR, LH, 5):
            bg[y] = E.hexrgb('#5E3A27')
        for x in range(0, LW, 17):
            bg[FLOOR:, x] = E.hexrgb('#3A2216')
        bg[FLOOR] = E.hexrgb('#D6A23B')
        # 两盏像素射灯光斑
        for cx in (40, 200):
            for y in range(FLOOR + 1, LH):
                hw = int(8 + (y - FLOOR) * 0.9)
                bg[y, max(0, cx - hw):cx + hw] = bg[y, max(0, cx - hw):cx + hw] * 0.6 + E.hexrgb('#F2C46A') * 0.4
        self.bg = bg
        self.pal = rgbs(PAL)

    def pose(self, t):
        K = E.K
        p = E.pose(x=960, y=904, s=0.80)
        beat = 0.5
        bob = abs(math.sin(math.pi * t / beat))
        pre = t < 0.5
        p['sq'] = 1 + (0.035 * bob if pre else 0)
        p['sq'] = K(t, [(0.5, p['sq']), (0.85, 0.84), (1.0, 1.12, 'out'), (1.35, 1.05), (1.55, 0.80, 'in'), (1.75, 1.08, 'out'), (1.95, 1.0)])
        p['hop'] = K(t, [(0.95, 0), (1.25, 150, 'out'), (1.55, 0, 'in')])
        p['armR'] = K(t, [(0.6, 0), (0.85, -20), (1.15, 140, 'out'), (1.5, 110), (1.8, 40)])
        p['armL'] = K(t, [(0.6, 0), (0.85, -20), (1.15, 60, 'out'), (1.5, 50), (1.8, 30)])
        # 两步踩点（快板）
        if 1.95 <= t < 2.95:
            ph = (t - 1.95) / 0.25
            side = 1 if int(ph) % 2 == 0 else -1
            k = math.sin(math.pi * (ph % 1))
            p['dx'] = 26 * side * k
            p['lean'] = 5 * side * k
            p['armL'] = 20 + 70 * (side > 0) * k
            p['armR'] = 20 + 70 * (side < 0) * k
            p['legs'] = (14 * k * (side > 0), 0, 0, 14 * k * (side < 0))
            p['sq'] = 1 - 0.05 * k
        if t >= 2.95:                                    # 举臂定格摆酷，随拍轻点头
            k = E.ease_back((t - 2.95) / 0.3)
            p['armL'] = 30 + 95 * k
            p['armR'] = 30 + 95 * k
            p['sq'] = K(t, [(2.95, 0.9), (3.2, 1.0)]) + 0.02 * abs(math.sin(math.pi * (t - 2.95) / beat))
            p['lean'] = -3 * E.smooth((t - 2.95) / 0.3)
        p['eye_dx'] = K(t, [(-0.4, 0), (0.3, 4), (1.6, 4), (2.0, 0)])
        p['eye_dy'] = K(t, [(-0.4, -6), (0.3, -16), (1.4, -16), (1.8, 0)])
        p['eye_mode'] = 'happy' if t > 3.05 else 'open'
        p['hair'] = K(t, [(0.95, 0), (1.1, 6), (1.3, -4), (1.6, 5), (1.9, 0)]) - 0.4 * p['lean']
        p['skirt'] = -0.5 * p['lean']
        return p

    def frame(self, t, p=None, trans=False):
        p = dict(self.pose(t) if p is None else p)
        img = self.bg.copy()
        # 砖块：被顶时上弹
        bump = 3 * math.sin(math.pi * E.seg(t, 1.22, 1.42)) if 1.22 < t < 1.42 else 0
        bx, by = 120 - 6, int(26 - bump)
        used = t > 1.25
        img[by:by + 12, bx:bx + 12] = E.hexrgb('#9C6B2E' if used else '#E8A93A')
        img[by:by + 12, bx] = img[by:by + 12, bx + 11] = img[by, bx:bx + 12] = img[by + 11, bx:bx + 12] = E.hexrgb('#2E2320')
        if not used:                                     # 砖块上的星形图标
            for (dx, dy) in [(5, 3), (6, 3), (4, 5), (5, 5), (6, 5), (7, 5), (5, 7), (6, 7), (4, 8), (7, 8)]:
                img[by + dy, bx + dx] = E.hexrgb('#FFF4C8')
        # 金币：弹出、旋转、落到右手
        if 1.25 < t < 2.2:
            k = (t - 1.25) / 0.95
            cx = 120 + 24 * k
            cy = 22 - 22 * math.sin(math.pi * min(1, k * 1.1)) + 40 * k
            wdt = max(1, int(abs(math.cos(t * 14)) * 4))
            yy, xx = np.mgrid[0:LH, 0:LW]
            m = ((xx - cx) / wdt) ** 2 + ((yy - cy) / 4.5) ** 2 <= 1
            img[m] = E.hexrgb('#FFD84A')
            img[(((xx - cx) / (wdt + 1)) ** 2 + ((yy - cy) / 5.5) ** 2 <= 1) & ~m] = E.hexrgb('#A8741C')
        if 2.0 < t < 2.4:                                # 收集闪光
            k = (t - 2.0) / 0.4
            for a in range(4):
                ang = a * math.pi / 2 + 0.6
                x = int(144 + math.cos(ang) * 6 * (1 + k * 2))
                y = int(62 + math.sin(ang) * 6 * (1 + k * 2))
                if 0 <= x < LW and 0 <= y < LH:
                    img[y, x] = E.hexrgb('#FFF4C8')
        # 角色：高分辨率渲染 → 缩小 → 调色板量化 → 1 像素描边
        ch = E.render_char(4, p, 'full')
        small = cv2.resize(ch, (LW, LH), interpolation=cv2.INTER_AREA)
        a = small[..., 3] > 0.45
        col = small[..., :3] / np.maximum(small[..., 3:], 1e-3)
        d = ((col[:, :, None, :] - self.pal[None, None]) ** 2).sum(-1)
        q = self.pal[np.argmin(d, axis=2)]
        ring = cv2.dilate(a.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~a
        img[ring] = E.hexrgb('#1A1014')
        img[a] = q[a]
        # 地面阴影（像素椭圆）
        big = cv2.resize(img, (LW * SC, LH * SC), interpolation=cv2.INTER_NEAREST)
        # 扫描线 + 轻微像素格
        big[::SC] *= 0.9
        return big
