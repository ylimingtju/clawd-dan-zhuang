# -*- coding: utf-8 -*-
"""视频引擎：姿势绑定 → SVG → 位图；缓动与关键帧；噪声纹理；合成；逐帧并行渲染与 H.264 编码。

借鉴（方法，未复制代码）：
- Claude-Mascot-Style-Gallery（MIT）：同一个 Clawd 模型 + 多个重绘器（平涂、栅格化、排线、网点、抖动墨线）。
- opus-5.5-musical-cartoon：画面是时间 t 的纯函数、时间点表驱动节奏、预备—动作—回弹、
  纹理用固定种子一次生成以免线条“沸腾”、用检查拼图回查。
"""
import io, math, os, subprocess
import numpy as np
import cv2
from PIL import Image
import resvg_py
import imageio_ffmpeg

import clawd
import looks

W, H, FPS = 1920, 1080, 30
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

LOOKS = {0: looks.Base()}
for _c in looks.Look.__subclasses__():
    if _c.no:
        LOOKS[_c.no] = _c()

# ------------------------------------------------------------------ 数学与缓动
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def seg(t, a, b):
    return clamp((t - a) / (b - a)) if b != a else float(t >= b)


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in(x):
    x = clamp(x)
    return x ** 3


def ease_back(x, s=1.7):
    x = clamp(x) - 1
    return 1 + x * x * ((s + 1) * x + s)


EASES = {'io': smooth, 'out': ease_out, 'in': ease_in, 'back': ease_back, 'lin': clamp}


def K(t, keys):
    """关键帧：keys=[(t0,v0),(t1,v1,'out'),...]；第三项为进入该关键帧所用缓动。"""
    if t <= keys[0][0]:
        return keys[0][1]
    for i in range(1, len(keys)):
        t1 = keys[i][0]
        if t <= t1:
            t0, v0 = keys[i - 1][0], keys[i - 1][1]
            e = EASES[keys[i][2] if len(keys[i]) > 2 else 'io']
            return lerp(v0, keys[i][1], e((t - t0) / (t1 - t0)))
    return keys[-1][1]


# ------------------------------------------------------------------ 姿势
POSE0 = dict(x=960.0, y=900.0, s=0.95, dx=0.0, hop=0.0, lean=0.0, sq=1.0, turn=1.0,
             armL=0.0, armR=0.0, eye_dx=0.0, eye_dy=0.0, eye_open=1.0, eye_mode='open',
             legs=(0, 0, 0, 0), hair=0.0, skirt=0.0, flare=1.0, hat=0.0, hat_lift=0.0, rot=0.0)


def pose(**kw):
    p = dict(POSE0)
    p.update(kw)
    return p


def blink(t, times, dur=0.14):
    """在给定时刻眨眼，返回睁眼程度。"""
    o = 1.0
    for b in times:
        k = seg(t, b, b + dur)
        if 0 < k < 1:
            o = min(o, abs(1 - 2 * k))
    return o


ROT_CY = 860          # 平面内旋转（翻滚、侧手翻）的支点：角色身体中心（设计坐标）


def tf_str(p):
    sx = p['turn'] / math.sqrt(max(0.3, p['sq']))
    return (f"translate({p['x']:.2f},{p['y']:.2f}) scale({p['s']:.4f}) "
            f"translate({p['dx']:.2f},{-p['hop']:.2f}) rotate({p['lean']:.3f}) "
            f"scale({sx:.4f},{p['sq']:.4f}) translate(-800,-{clawd.GROUND}) "
            f"translate(800,{ROT_CY}) rotate({p.get('rot', 0.0):.3f}) translate(-800,-{ROT_CY})")


def tf_matrix(p):
    """与 tf_str 一致的 3×3 矩阵（设计坐标 → 屏幕坐标），用于把道具挂到手臂末端等。"""
    def T(x, y): return np.array([[1, 0, x], [0, 1, y], [0, 0, 1.0]])
    def S(a, b): return np.array([[a, 0, 0], [0, b, 0], [0, 0, 1.0]])
    def R(d):
        c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])
    sx = p['turn'] / math.sqrt(max(0.3, p['sq']))
    return (T(p['x'], p['y']) @ S(p['s'], p['s']) @ T(p['dx'], -p['hop']) @ R(p['lean']) @ S(sx, p['sq']) @ T(-800, -clawd.GROUND)
            @ T(800, ROT_CY) @ R(p.get('rot', 0.0)) @ T(-800, -ROT_CY))


def to_screen(p, pt):
    v = tf_matrix(p) @ np.array([pt[0], pt[1], 1.0])
    return float(v[0]), float(v[1])


def apply_pose_state(p):
    clawd.ARM_ANGLE['L'] = 26 + p['armL']
    clawd.ARM_ANGLE['R'] = -(26 + p['armR'])
    es = clawd.EYE_STATE
    es['dx'], es['dy'], es['open'], es['mode'] = p['eye_dx'], p['eye_dy'], p['eye_open'], p['eye_mode']
    for i in range(4):
        clawd.LEG_LIFT[i] = p['legs'][i]
    clawd.HAT['tilt'] = p['hat']
    clawd.HAT['lift'] = p['hat_lift']


def arm_tip(p, side, t=None):
    apply_pose_state(p)
    return to_screen(p, clawd.arm_point(side, clawd.ARM_L - 14 if t is None else t))


def char_svg(no, p, mode='full', sw=1.0, extra=None, seam=0.0, eye_ring=False):
    apply_pose_state(p)
    return LOOKS[no].render_pose(tf_str(p), {'hair': p['hair'], 'skirt': p['skirt'], 'flare': p['flare']},
                                 mode=mode, sw=sw, extra=extra, seam=seam, eye_ring=eye_ring)


def svg_rgba(svg, w=W, h=H):
    png = resvg_py.svg_to_bytes(svg_string=svg, skip_system_fonts=True)
    im = Image.open(io.BytesIO(bytes(png))).convert('RGBA')
    if im.size != (w, h):
        im = im.resize((w, h))
    return np.asarray(im, dtype=np.float32) / 255.0


def render_char(no, p, mode='full', sw=1.0, extra=None, seam=0.0, eye_ring=False):
    return svg_rgba(char_svg(no, p, mode, sw, extra, seam, eye_ring))


# ------------------------------------------------------------------ 颜色与合成
def hexrgb(c):
    c = c.lstrip('#')
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32) / 255.0


def over(dst, src_rgba, opacity=1.0):
    a = src_rgba[..., 3:4] * opacity
    return dst * (1 - a) + src_rgba[..., :3] * a


def over_rgb(dst, rgb, alpha):
    a = alpha[..., None] if alpha.ndim == 2 else alpha
    return dst * (1 - a) + rgb * a


def solid(c, h=H, w=W):
    return np.ones((h, w, 3), np.float32) * hexrgb(c)


def vgrad(c0, c1, h=H, w=W, gamma=1.0):
    t = (np.linspace(0, 1, h, dtype=np.float32) ** gamma)[:, None, None]
    return np.broadcast_to(hexrgb(c0) * (1 - t) + hexrgb(c1) * t, (h, w, 3)).copy()


def radial(cx, cy, r, h=H, w=W):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return np.clip(1 - np.hypot(xx - cx, yy - cy) / r, 0, 1)


def blur(a, r):
    if r <= 0:
        return a
    k = int(r * 3) | 1
    return cv2.GaussianBlur(a, (k, k), r)


def lum(rgb):
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def to_u8(rgb):
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)


# ------------------------------------------------------------------ 噪声（固定种子，可复现）
_NCACHE = {}


def noise(h, w, scale, seed, octaves=1):
    """平滑值噪声 0..1，scale 为特征尺寸（像素）。"""
    key = (h, w, scale, seed, octaves)
    if key in _NCACHE:
        return _NCACHE[key]
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot, sc = 1.0, 0.0, scale
    for _ in range(octaves):
        gh, gw = max(2, int(h / sc) + 3), max(2, int(w / sc) + 3)
        g = rng.random((gh, gw)).astype(np.float32)
        up = cv2.resize(g, (int(gw * sc), int(gh * sc)), interpolation=cv2.INTER_CUBIC)[:h, :w]
        out += up * amp
        tot += amp
        amp *= 0.5
        sc = max(2, sc / 2)
    out = np.clip(out / tot, 0, 1)
    _NCACHE[key] = out
    return out


def shifted(tex, ox, oy):
    """把整幅纹理平移（随角色移动，避免纹理在角色身上游动）。"""
    M = np.float32([[1, 0, ox], [0, 1, oy]])
    return cv2.warpAffine(tex, M, (tex.shape[1], tex.shape[0]), borderMode=cv2.BORDER_REFLECT)


def warp(img, fx, fy):
    h, w = img.shape[:2]
    xx, yy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(img, xx + fx, yy + fy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def edges_of(rgb, alpha, thr=0.06):
    """色块之间与外轮廓的边界（布尔）。"""
    c = rgb * alpha[..., None]
    gx = np.abs(np.diff(c, axis=1, append=c[:, -1:])).sum(-1)
    gy = np.abs(np.diff(c, axis=0, append=c[-1:])).sum(-1)
    e = (gx + gy) > thr
    a = alpha > 0.5
    ae = (np.abs(np.diff(a.astype(np.int8), axis=1, append=a[:, -1:].astype(np.int8))) +
          np.abs(np.diff(a.astype(np.int8), axis=0, append=a[-1:].astype(np.int8)))) > 0
    return e | ae


# ------------------------------------------------------------------ 文字（PIL，保证中文准确）
FONT_SANS = '/System/Library/Fonts/Hiragino Sans GB.ttc'
FONT_SONG = '/System/Library/Fonts/Supplemental/Songti.ttc'


# ------------------------------------------------------------------ 编码
class Writer:
    def __init__(self, path, crf=14, w=W, h=H):
        cmd = [FFMPEG, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}',
               '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf),
               '-vf', 'scale=out_color_matrix=bt709:out_range=tv', '-pix_fmt', 'yuv420p',
               '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
               '-movflags', '+faststart', path]
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def write(self, u8):
        self.p.stdin.write(u8.tobytes())

    def close(self):
        self.p.stdin.close()
        if self.p.wait() != 0:
            raise RuntimeError('ffmpeg failed')


def read_frames(path, start=0, count=None, w=W, h=H):
    """解码 MP4 指定帧段 → uint8 帧列表。"""
    cmd = [FFMPEG, '-loglevel', 'error', '-i', path, '-vf', f'select=gte(n\\,{start})',
           '-vsync', '0', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    if count:
        cmd[-1:-1] = ['-frames:v', str(count)]
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
    n = len(out) // (w * h * 3)
    return [np.frombuffer(out[i * w * h * 3:(i + 1) * w * h * 3], np.uint8).reshape(h, w, 3) for i in range(n)]


def line_alpha(no, p, sw=1.0, extra=None, eye_ring=False):
    """有遮挡关系的线条层（含眼睛）：0..1。"""
    m = render_char(no, p, 'linemask', sw=sw, extra=extra, eye_ring=eye_ring)
    return np.clip(lum(m[..., :3]) * m[..., 3], 0, 1)


def render_char_eyes_apart(no, p, mode='flatshade', seam=0.0):
    """分别返回：不含眼睛的角色层，以及眼睛遮罩（0..1）。用于让眼睛不参与某些画风的立体处理。"""
    with_eyes = render_char(no, p, mode, seam=seam)
    clawd.RSTATE['no_eyes'] = True
    try:
        no_eyes = render_char(no, p, mode, seam=seam)
    finally:
        clawd.RSTATE['no_eyes'] = False
    m = np.clip(np.abs(with_eyes[..., :3] - no_eyes[..., :3]).sum(-1) * 2.5, 0, 1) * with_eyes[..., 3]
    return no_eyes, m
