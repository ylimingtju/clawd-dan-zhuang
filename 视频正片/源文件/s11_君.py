# -*- coding: utf-8 -*-
"""11《君》—— 月份牌喷绘（旧印刷品）。
意象：老式房间，墙纸、小圆桌和一台留声机。Clawd 走到桌边，抬手把唱臂放到唱片上，唱片转起来，
音符从喇叭里飘出；她退半步，闭上眼，胸前的红花跟着慢慢摇——熟悉的旋律把时间连在一起。
画法：角色是柔和的喷枪渐变塑形（中心亮、边缘暗、上亮下暗），细棕线勾边；整体偏暖褪色、对比降低、带纸纹与暗角，像一张旧月份牌。
"""
import math
import numpy as np
import cv2
import engine as E
import fx
from scene_base import Scene


class S11(Scene):
    key = '11'
    filename = '11_君'
    style = '月份牌擦笔水彩'
    no = 11
    core = 4.0

    def setup(self):
        h, w = 1080, 1920
        wall = E.vgrad('#CFE0D6', '#AFC7BE')
        # 墙纸小花纹
        pat = '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">'
        for j, y in enumerate(range(40, 900, 110)):
            for x in range(40 + (55 if j % 2 else 0), 1920, 110):
                pat += (f'<g transform="translate({x},{y})" fill="#E8C7B8" opacity="0.7">'
                        f'<circle cx="0" cy="-9" r="7"/><circle cx="9" cy="0" r="7"/><circle cx="0" cy="9" r="7"/><circle cx="-9" cy="0" r="7"/>'
                        f'<circle cx="0" cy="0" r="5" fill="#D99A8C"/></g>')
        pat += '</svg>'
        p = E.svg_rgba(pat)
        wall = E.over(wall, p)
        # 墙裙与地板
        wall[760:905] = E.vgrad('#C9A487', '#B88F72')[760:905]
        wall[758:766] = E.hexrgb('#8C6248')
        wall[905:] = E.vgrad('#9A6A4C', '#7C523A')[905:]
        # 小圆桌与留声机底座（静态部分）
        st = E.svg_rgba('<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">'
                        '<ellipse cx="1430" cy="930" rx="150" ry="16" fill="#000" opacity="0.18"/>'
                        '<rect x="1418" y="720" width="24" height="200" fill="#7A4A35"/>'
                        '<path d="M1340,920 L1520,920 L1500,930 L1360,930 Z" fill="#6A3D2B"/>'
                        '<ellipse cx="1430" cy="716" rx="170" ry="26" fill="#A8607A"/>'
                        '<path d="M1260,716 L1600,716 L1600,742 C1500,770 1360,770 1260,742 Z" fill="#8E4A63"/>'
                        '<rect x="1340" y="636" width="180" height="70" rx="8" fill="#8A5634"/>'
                        '<rect x="1340" y="636" width="180" height="14" rx="6" fill="#A86E44"/></svg>')
        st[..., :3] = fx.airbrush(st, soft=30)[..., :3]
        self.bg = E.over(wall, st)
        self.paper = fx.paper(h, w, '#F3E7CF', seed=121, fiber=0.01, grain=0.03) / E.hexrgb('#F3E7CF').mean()
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        self.vign = (1 - 0.32 * np.clip(np.hypot((xx - 960) / 1100, (yy - 540) / 760) - 0.45, 0, 1))[..., None]
        # 月份牌边框：米色留边 + 双细线 + 圆角
        fr = E.svg_rgba('<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">'
                        '<path fill-rule="evenodd" fill="#EFE2C6" d="M0,0 H1920 V1080 H0 Z M46,46 H1874 V1034 H46 Z"/>'
                        '<rect x="46" y="46" width="1828" height="988" rx="26" fill="none" stroke="#EFE2C6" stroke-width="30"/>'
                        '<rect x="30" y="30" width="1860" height="1020" rx="34" fill="none" stroke="#9A5B47" stroke-width="3"/>'
                        '<rect x="22" y="22" width="1876" height="1036" rx="38" fill="none" stroke="#9A5B47" stroke-width="1.5"/></svg>')
        fr[..., :3] *= self.paper
        self.frame_m = fr

    def pose(self, t):
        K = E.K
        p = E.pose(x=K(t, [(-0.4, 900), (0.6, 1010), (1.8, 1030), (2.3, 980)]), y=905, s=0.9)
        walk = E.seg(t, -0.4, 0.6)
        if 0 < walk < 1:
            ph = walk * 2
            p['legs'] = (10 * max(0, math.sin(math.pi * ph * 2)), 0, 0, 10 * max(0, -math.sin(math.pi * ph * 2)))
            p['hop'] = 5 * abs(math.sin(math.pi * ph * 2))
        p['armR'] = K(t, [(-0.4, 8), (0.6, 10), (1.0, 66), (1.4, 58), (1.6, 60), (2.0, 14), (2.5, 10)])
        p['armL'] = K(t, [(-0.4, 8), (2.2, 8), (2.7, 24), (4.4, 22)])
        sway = math.sin(2 * math.pi * (t - 2.3) / 1.5) * E.smooth((t - 2.3) / 0.5)
        p['lean'] = K(t, [(0.6, 0), (1.0, -3), (1.6, -3), (2.1, 0)]) + 3.5 * sway
        p['dx'] = 10 * sway
        p['eye_dx'] = K(t, [(-0.4, 10), (0.6, 14), (1.6, 16), (2.1, 0)])
        p['eye_dy'] = K(t, [(-0.4, 0), (0.8, 4), (1.6, 6), (2.1, 0)])
        p['eye_mode'] = 'happy' if t > 2.3 else 'open'
        p['eye_open'] = E.blink(t, [0.3])
        p['skirt'] = -2.5 * sway + 1.5 * math.sin(t * 2.0)
        p['hair'] = -2 * sway
        return p

    def frame(self, t, p=None, trans=False):
        p = dict(self.pose(t) if p is None else p)
        img = self.bg.copy()
        # 唱片与唱臂、喇叭
        play = E.smooth((t - 1.35) / 0.3)
        rot = 360 * 0.55 * max(0.0, t - 1.35) * play
        arm_a = E.K(t, [(-0.4, -38), (1.0, -38), (1.35, -6)])
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">'
               '<ellipse cx="1430" cy="632" rx="80" ry="18" fill="#2A1E1E"/>'
               f'<g transform="translate(1430,632) scale(1,0.22) rotate({rot:.1f})">'
               '<circle r="70" fill="none" stroke="#4A3A3A" stroke-width="3"/><circle r="48" fill="none" stroke="#4A3A3A" stroke-width="3"/>'
               '<circle r="20" fill="#C8463F"/><path d="M0,-70 L0,-25" stroke="#6A5A5A" stroke-width="6"/></g>'
               f'<g transform="translate(1500,612) rotate({arm_a:.1f})"><path d="M0,0 L-60,24" stroke="#C9A65A" stroke-width="7" stroke-linecap="round"/></g>'
               '<path d="M1400,640 C1385,580 1360,520 1335,478" stroke="#B88B4A" stroke-width="12" fill="none"/>'
               '<path d="M1326,486 L1344,470 L1302,262 C1250,230 1170,290 1158,352 Z" fill="#E2A9B2"/>'
               '<g transform="translate(1232,308) rotate(-38)"><ellipse rx="96" ry="58" fill="#E9B8BF"/>'
               '<ellipse rx="70" ry="40" fill="#A8616C"/><ellipse rx="30" ry="17" fill="#6E3540"/></g>'
               '<path d="M1336,478 L1250,330" stroke="#C98A94" stroke-width="5" fill="none"/></svg>')
        g = E.svg_rgba(svg)
        g = fx.airbrush(g, soft=24)
        img = E.over(img, g)
        # 音符：从喇叭口飘出
        if play > 0:
            notes = '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" fill="#7A3E4E">'
            for k in range(5):
                tt = (t - 1.45 - k * 0.42)
                if tt <= 0:
                    continue
                x = 1250 - 120 * tt + 20 * math.sin(tt * 3 + k)
                y = 300 - 70 * tt
                al = max(0.0, min(1.0, tt * 3)) * max(0.0, 1 - tt / 2.6)
                notes += (f'<g transform="translate({x:.1f},{y:.1f}) rotate({-12 + 10 * math.sin(tt * 2 + k):.1f})" opacity="{al:.2f}">'
                          f'<ellipse cx="0" cy="0" rx="13" ry="10" transform="rotate(-20)"/><rect x="9" y="-52" width="5" height="52"/>'
                          + (f'<path d="M14,-52 q18,6 16,26" stroke="#7A3E4E" stroke-width="5" fill="none"/>' if k % 2 == 0 else '') + '</g>')
            notes += '</svg>'
            img = E.over(img, E.svg_rgba(notes))
        # 眼睛不参与炭粉塑形（否则眼眶边缘被压暗，像黑眼圈）：先塑形无眼角色，再画回眼睛
        body, eye = E.render_char_eyes_apart(11, p, 'flat')
        ch = fx.rubbed(body)
        ch[..., :3] = ch[..., :3] * (1 - eye[..., None]) + E.hexrgb('#2A1D19') * eye[..., None]
        img = E.over_rgb(img, np.zeros(3, np.float32), fx.contact_shadow(1080, 1920, p['x'] + p['dx'], 908, 300 * p['s'], 22, 0.3, 14))
        img = E.over_rgb(img, ch[..., :3], ch[..., 3])
        E_ = __import__('clawd')
        E_.RSTATE['no_eyes'] = True
        la = E.line_alpha(11, p, sw=0.8)
        E_.RSTATE['no_eyes'] = False
        img = E.over_rgb(img, E.hexrgb('#6A4A3A'), E.blur(la, 1.0) * 0.35)
        # 柔焦辉光（Orton）
        img = img * 0.8 + E.blur(np.clip(img * 1.15, 0, 1), 9) * 0.2
        img = fx.age_print(img, self.paper, amount=0.24, fade=0.08) * self.vign
        img = img * (1 - self.frame_m[..., 3:]) + self.frame_m[..., :3] * self.frame_m[..., 3:]
        return np.clip(img, 0, 1)
