# -*- coding: utf-8 -*-
"""各画风共用的重绘工具（numpy / OpenCV）。所有随机量都来自固定种子，逐帧可复现。"""
import math
import numpy as np
import cv2
import engine as E


def region_dist(rgb, alpha, thr=0.06):
    """到最近色块边界的距离（像素）。"""
    e = E.edges_of(rgb, alpha, thr)
    inside = (alpha > 0.5) & ~e
    return cv2.distanceTransform(inside.astype(np.uint8), cv2.DIST_L2, 5)


def volume(rgba, light=(-0.55, -0.65, 0.55), R=20, spec=0.55, shin=24, amb=0.58, ao=0.3):
    """柔光 3D：按色块边界生成圆润斜面高度场 → 法线 → 漫反射 + 高光 + 接缝暗角。"""
    rgb, a = rgba[..., :3], rgba[..., 3]
    d = region_dist(rgb, a)
    h = np.sqrt(np.clip(d / R, 0, 1))
    h = E.blur(h, 1.2)
    gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3)
    k = R * 0.18
    n = np.dstack([-gx * k, -gy * k, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    L = np.array(light, np.float32)
    L /= np.linalg.norm(L)
    L = np.array([L[0], L[1], L[2]])
    diff = np.clip((n * np.array([-L[0], -L[1], L[2]])).sum(-1), 0, 1)
    Hv = np.array([-L[0], -L[1], L[2] + 1.0])
    Hv /= np.linalg.norm(Hv)
    sp = np.clip((n * Hv).sum(-1), 0, 1) ** shin
    occl = 1 - ao * (1 - np.clip(d / 7, 0, 1))
    shade = (amb + (1 - amb) * 1.25 * diff) * occl
    out = rgb * shade[..., None] + spec * sp[..., None]
    return np.dstack([np.clip(out, 0, 1), a])


def soft_disc(img, cx, cy, r, color, alpha, sharp=0.6):
    """柔边圆（散景、光斑）。直接加在 img 上（局部窗口，速度快）。"""
    h, w = img.shape[:2]
    x0, x1 = int(max(0, cx - r - 2)), int(min(w, cx + r + 2))
    y0, y1 = int(max(0, cy - r - 2)), int(min(h, cy + r + 2))
    if x0 >= x1 or y0 >= y1:
        return img
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dd = np.hypot(xx - cx, yy - cy) / r
    m = np.clip((1 - dd) / (1 - sharp + 1e-6), 0, 1) * alpha
    img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - m[..., None]) + np.asarray(color, np.float32) * m[..., None]
    return img


def reflection(rgba, ground_y, fade=0.28, length=260, blur_r=3):
    """地面倒影：角色沿地面线翻转、渐隐、模糊。"""
    h = rgba.shape[0]
    g = int(ground_y)
    ref = np.zeros_like(rgba)
    src = rgba[max(0, g - length):g][::-1]
    ref[g:g + src.shape[0]] = src[:max(0, min(src.shape[0], h - g))]
    ref = E.blur(ref, blur_r)
    yy = np.arange(h, dtype=np.float32)[:, None]
    f = np.clip(1 - (yy - g) / length, 0, 1) * fade * (yy >= g)
    ref[..., 3] *= f
    return ref


def contact_shadow(h, w, cx, cy, rx, ry, strength=0.45, soft=18):
    m = np.zeros((h, w), np.float32)
    cv2.ellipse(m, (int(cx), int(cy)), (int(rx), int(ry)), 0, 0, 360, 1.0, -1)
    return E.blur(m, soft) * strength


# ------------------------------------------------------------------ 水墨
def paper(h, w, base='#F1ECE1', seed=7, fiber=0.05, grain=0.035):
    """宣纸：底色 + 纤维 + 颗粒。"""
    img = E.solid(base, h, w)
    n1 = E.noise(h, w, 2, seed)
    n2 = E.noise(h, w, 90, seed + 1, octaves=2)
    fib = cv2.resize(E.noise(h // 6, w // 2, 2, seed + 2), (w, h), interpolation=cv2.INTER_LINEAR)
    img *= (1 - grain * (n1 - 0.5) * 2 - 0.025 * (n2 - 0.5) * 2 - fiber * np.clip(fib - 0.62, 0, 1) * 3)[..., None]
    return img


def brush_lines(alpha, ox, oy, seed=3, wob=1.8, thick=0.55, dry=0.22):
    """把线条层的 alpha 变成毛笔线：粗细随机变化、轻微抖动、干笔飞白。纹理随角色平移。"""
    h, w = alpha.shape
    n = E.shifted(E.noise(h, w, 18, seed), ox, oy)
    a = alpha.copy()
    fat = cv2.dilate(a, np.ones((3, 3), np.uint8))
    fat2 = cv2.dilate(a, np.ones((5, 5), np.uint8))
    a = np.where(n > thick, np.maximum(a, fat), a)
    a = np.where(n > thick + 0.18, np.maximum(a, fat2), a)
    fx_ = (E.shifted(E.noise(h, w, 26, seed + 5), ox, oy) - 0.5) * 2 * wob
    fy_ = (E.shifted(E.noise(h, w, 26, seed + 9), ox, oy) - 0.5) * 2 * wob
    a = E.warp(a, fx_, fy_)
    streak = E.shifted(cv2.resize(E.noise(h // 8, w, 2, seed + 13), (w, h)), ox, oy)
    a = a * np.clip(1 - dry * (streak > 0.62) * 1.0, 0, 1)
    return np.clip(a, 0, 1)


def ink_wash(rgba, ox, oy, paper_rgb, seed=11, lift=0.42, edge=0.22, keep_dark=0.35):
    """淡彩晕染：颜色向纸色提亮、色块边缘积色、颗粒、边缘柔化。"""
    rgb, a = rgba[..., :3], rgba[..., 3]
    h, w = a.shape
    L = E.lum(rgb)[..., None]
    k = lift * np.clip((L - keep_dark) / (1 - keep_dark), 0, 1) + 0.12
    wash = rgb * (1 - k) + paper_rgb * k
    d = region_dist(rgb, a)
    pool = np.clip(1 - d / 5, 0, 1)
    wash = wash * (1 - edge * pool[..., None])
    gran = E.shifted(E.noise(h, w, 4, seed), ox, oy)
    wash = wash * (1 - 0.10 * (gran[..., None] - 0.5))
    fxw = (E.shifted(E.noise(h, w, 30, seed + 3), ox, oy) - 0.5) * 5
    fyw = (E.shifted(E.noise(h, w, 30, seed + 4), ox, oy) - 0.5) * 5
    out = np.dstack([wash, a])
    out = E.warp(out, fxw, fyw)
    out[..., 3] = E.blur(out[..., 3], 1.2)
    return out


# ------------------------------------------------------------------ 网点印刷（Riso）
_GRID = {}


def _grid(h, w):
    if (h, w) not in _GRID:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        _GRID[(h, w)] = (xx, yy)
    return _GRID[(h, w)]


def halftone_plate(val, cell, angle_deg, ox=0.0, oy=0.0):
    """单色印版：val(0..1 覆盖率) → 抗锯齿圆网点覆盖率。网格可随角色平移 (ox, oy)。"""
    h, w = val.shape
    xx, yy = _grid(h, w)
    a = math.radians(angle_deg)
    x, y = xx - ox, yy - oy
    u = (x * math.cos(a) + y * math.sin(a)) / cell
    v = (-x * math.sin(a) + y * math.cos(a)) / cell
    du, dv = u - np.floor(u) - 0.5, v - np.floor(v) - 0.5
    dist = np.sqrt(du * du + dv * dv) * cell
    r = cell * 0.72 * np.sqrt(np.clip(val, 0, 1))
    return np.clip(r - dist + 0.6, 0, 1)


RISO = {'pink': '#FF4FA0', 'blue': '#2E5AAC', 'yellow': '#FFD43A', 'black': '#1D1B22'}


def riso_separate(rgb, kmax=0.95):
    c, m, y = 1 - rgb[..., 0], 1 - rgb[..., 1], 1 - rgb[..., 2]
    k = np.minimum(np.minimum(c, m), y) * kmax
    return {'blue': np.clip(c - k, 0, 1) * 1.05, 'pink': np.clip(m - k, 0, 1), 'yellow': np.clip(y - k, 0, 1), 'black': k}


def riso_print(rgb, cell=8, ox=0.0, oy=0.0, reg=None, solid_black=None, kmax=0.95):
    """分色 → 各版网点 → 在纸上逐版叠印（乘色）。返回各版覆盖率合成后的颜色（不含纸色）。"""
    reg = reg or {'pink': (3, -2), 'blue': (-2, 2), 'yellow': (1, 3), 'black': (0, 0)}
    ang = {'pink': 75, 'blue': 15, 'yellow': 0, 'black': 45}
    plates = riso_separate(rgb, kmax)
    out = np.ones(rgb.shape, np.float32)
    for name in ('yellow', 'pink', 'blue', 'black'):
        cov = halftone_plate(plates[name], cell, ang[name], ox, oy)
        if name == 'black' and solid_black is not None:
            cov = np.maximum(cov, solid_black)
        dx, dy = reg[name]
        cov = E.shifted(cov, dx, dy)
        ink = E.hexrgb(RISO[name])
        out *= 1 - cov[..., None] * (1 - ink)
    return out


# ------------------------------------------------------------------ 撕纸拼贴
def torn_paper(rgba, ox, oy, seed=51, rim=5, rim_col='#F8F3E8', inner=True):
    """色块 → 撕纸片：边缘撕裂抖动、外圈白色纤维毛边、色块之间的纸边与投影、纸纹。"""
    h, w = rgba.shape[:2]
    nx = (E.shifted(E.noise(h, w, 5, seed), ox, oy) - 0.5) * 5
    ny = (E.shifted(E.noise(h, w, 5, seed + 1), ox, oy) - 0.5) * 5
    lay = E.warp(rgba, nx, ny)
    a = lay[..., 3]
    rgb = lay[..., :3]
    fib = E.shifted(E.noise(h, w, 3, seed + 2), ox, oy)
    grow = E.blur((a > 0.5).astype(np.float32), rim * 0.7)
    rimmask = np.clip((grow - 0.12 - 0.22 * fib) * 6, 0, 1) * (1 - a)
    out_rgb = rgb.copy()
    out_a = np.maximum(a, rimmask)
    paperc = E.hexrgb(rim_col) * (1 - 0.08 * fib[..., None])
    out_rgb = out_rgb * a[..., None] + paperc * (rimmask * (1 - a))[..., None]
    out_rgb = out_rgb / np.maximum(out_a[..., None], 1e-3)
    if inner:
        e = E.edges_of(rgb, a, 0.08) & (a > 0.5)
        e = cv2.dilate(e.astype(np.uint8), np.ones((2, 2), np.uint8)).astype(np.float32)
        sh = E.shifted(E.blur(e, 1.5), 2, 3)
        out_rgb = out_rgb * (1 - 0.28 * sh[..., None] * a[..., None])
        out_rgb = out_rgb * (1 - e[..., None] * 0.75) + paperc * (e[..., None] * 0.75)
    tex = E.shifted(E.noise(h, w, 2, seed + 3), ox, oy)
    tex2 = E.shifted(E.noise(h, w, 24, seed + 4, octaves=2), ox, oy)
    out_rgb = out_rgb * (1 - 0.06 * (tex[..., None] - 0.5) - 0.06 * (tex2[..., None] - 0.5))
    return np.dstack([np.clip(out_rgb, 0, 1), out_a])


def drop_shadow(dst, alpha, dx=8, dy=10, r=6, strength=0.35):
    sh = E.shifted(E.blur(alpha, r), dx, dy) * strength
    return dst * (1 - sh[..., None])


# ------------------------------------------------------------------ 霓虹
def neighbor_color(rgb, alpha, r=5):
    """线条处取邻近色块的颜色（模糊后按 alpha 归一）。"""
    num = E.blur(rgb * alpha[..., None], r)
    den = E.blur(alpha, r)[..., None]
    return num / np.maximum(den, 1e-3)


def neonize(col):
    """把颜色推成霓虹色：提高饱和与亮度。"""
    mx = col.max(-1, keepdims=True)
    mn = col.min(-1, keepdims=True)
    sat = (col - mn) / np.maximum(mx - mn, 1e-3)
    out = 0.25 + 0.75 * sat
    grey = (mx - mn) < 0.12
    return np.where(grey, np.array([0.85, 0.75, 1.0], np.float32), out)


def glow_add(img, mask, color_img, radii=((2, 1.0), (7, 0.7), (20, 0.45))):
    for r, k in radii:
        img = img + E.blur(mask[..., None] * color_img, r) * k
    return img


def palette_map(col, mapping):
    """按最近的源色把颜色映射到目标色（用于把服装色换成某种画风的专用色）。"""
    src = np.array([E.hexrgb(k) for k in mapping], np.float32)
    dst = np.array([E.hexrgb(v) for v in mapping.values()], np.float32)
    d = ((col[..., None, :] - src[None, None]) ** 2).sum(-1)
    return dst[np.argmin(d, axis=-1)]


# ------------------------------------------------------------------ 木刻（浮世绘）
def woodgrain(h, w, seed=71, ox=0.0, oy=0.0):
    g = cv2.resize(E.noise(h // 10 + 2, w // 2 + 2, 2, seed), (w + 20, h + 20), interpolation=cv2.INTER_CUBIC)[:h, :w]
    g2 = E.noise(h, w, 60, seed + 1, octaves=2)
    tex = 0.5 + 0.5 * np.sin((g * 18 + g2 * 6) * math.pi)
    return E.shifted(tex.astype(np.float32), ox, oy)


def carve_lines(alpha, ox, oy, seed=73, wob=1.0):
    h, w = alpha.shape
    fx_ = (E.shifted(E.noise(h, w, 12, seed), ox, oy) - 0.5) * 2 * wob
    fy_ = (E.shifted(E.noise(h, w, 12, seed + 1), ox, oy) - 0.5) * 2 * wob
    a = E.warp(alpha, fx_, fy_)
    return np.clip((a - 0.25) * 1.8, 0, 1)


# ------------------------------------------------------------------ 油画
def kuwahara(img, r=5):
    """Kuwahara 滤波：在四个象限中取方差最小者的均值 → 保边的油画色块。"""
    k = r + 1
    mean = cv2.blur(img, (k, k))
    sq = cv2.blur(img * img, (k, k))
    var = (sq - mean * mean).sum(-1)
    h, w = img.shape[:2]
    best_m = np.zeros_like(img)
    best_v = np.full((h, w), 1e9, np.float32)
    for dy, dx in [(-r // 2 - 1, -r // 2 - 1), (-r // 2 - 1, r // 2 + 1), (r // 2 + 1, -r // 2 - 1), (r // 2 + 1, r // 2 + 1)]:
        m = E.shifted(mean, dx, dy)
        v = E.shifted(var, dx, dy)
        sel = v < best_v
        best_v = np.where(sel, v, best_v)
        best_m = np.where(sel[..., None], m, best_m)
    return best_m


def stroke_texture(h, w, seed=81, angle=35, length=26):
    """方向性笔触纹理：噪声沿笔触方向做运动模糊。"""
    n = E.noise(h, w, 3, seed)
    ker = np.zeros((length, length), np.float32)
    c = length // 2
    a = math.radians(angle)
    cv2.line(ker, (int(c - math.cos(a) * c), int(c - math.sin(a) * c)), (int(c + math.cos(a) * c), int(c + math.sin(a) * c)), 1.0, 1)
    ker /= ker.sum()
    t = cv2.filter2D(n, -1, ker)
    t = (t - t.mean()) / (t.std() + 1e-6)
    return np.clip(0.5 + 0.18 * t, 0, 1).astype(np.float32)


def impasto(img, height, strength=6.0, light=(-0.6, -0.8)):
    gx = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3)
    shade = -(gx * light[0] + gy * light[1]) * strength
    return img * (1 + 0.35 * np.clip(shade, -1, 1)[..., None]) + 0.12 * np.clip(shade, 0, 1)[..., None] ** 2


def make_strokes(n, x0, y0, x1, y1, seed, lmin, lmax, wmin, wmax, angle_fn):
    rng = np.random.default_rng(seed)
    xs = rng.uniform(x0, x1, n)
    ys = rng.uniform(y0, y1, n)
    ls = rng.uniform(lmin, lmax, n)
    ws = rng.uniform(wmin, wmax, n)
    js = rng.uniform(-0.09, 0.09, n)
    hs = rng.uniform(0.3, 1.0, n)
    an = np.array([angle_fn(x, y) for x, y in zip(xs, ys)]) + rng.uniform(-0.25, 0.25, n)
    return np.stack([xs, ys, ls, ws, an, js, hs], 1).astype(np.float32)


def paint_strokes(src, canvas, height, strokes, ox=0.0, oy=0.0, mask=None):
    """逐笔绘制：每一笔从 src 取色（中心点），按固定明暗偏差画成粗线，同时写入高度图（用于浮雕）。"""
    h, w = src.shape[:2]
    for (x, y, L, wd, a, j, hv) in strokes:
        cx, cy = x + ox, y + oy
        ix, iy = int(cx), int(cy)
        if ix < 0 or iy < 0 or ix >= w or iy >= h:
            continue
        if mask is not None and mask[iy, ix] < 0.5:
            continue
        c = src[iy, ix] * (1 + j)
        dx, dy = math.cos(a) * L / 2, math.sin(a) * L / 2
        p0, p1 = (int(cx - dx), int(cy - dy)), (int(cx + dx), int(cy + dy))
        cv2.line(canvas, p0, p1, (float(c[0]), float(c[1]), float(c[2])), int(wd), cv2.LINE_AA)
        cv2.line(height, p0, p1, float(hv), int(wd), cv2.LINE_AA)
    return canvas, height


# ------------------------------------------------------------------ 彩色玻璃
def voronoi_cells_svg(x0, y0, x1, y1, n, seed, lead='#141018', lead_w=5):
    """设计坐标中的泰森多边形玻璃片（随角色姿势一起变换）。fill 为随机明暗，用于玻璃片之间的差异。"""
    from scipy.spatial import Voronoi
    rng = np.random.default_rng(seed)
    pts = np.stack([rng.uniform(x0, x1, n), rng.uniform(y0, y1, n)], 1)
    far = np.array([[x0 - 2000, y0 - 2000], [x1 + 2000, y0 - 2000], [x0 - 2000, y1 + 2000], [x1 + 2000, y1 + 2000]])
    vor = Voronoi(np.vstack([pts, far]))
    out = []
    for i in range(n):
        reg = vor.regions[vor.point_region[i]]
        if -1 in reg or not reg:
            continue
        poly = vor.vertices[reg]
        d = 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in poly) + ' Z'
        v = rng.uniform(-1, 1)
        fill = '#FFFFFF' if v > 0 else '#000000'
        out.append(f'<path d="{d}" fill="{fill}" fill-opacity="{abs(v) * 0.22:.3f}" stroke="{lead}" stroke-width="{lead_w}"/>')
    return ''.join(out)


# ------------------------------------------------------------------ 色粉笔
def pastel(rgba, ox, oy, seed=101, density=0.9, angle=60, whiten=0.12):
    """色粉：颜料只落在纸纹凸起处（颗粒），带斜向笔触与晕擦的软边。"""
    h, w = rgba.shape[:2]
    tooth = E.shifted(E.noise(h, w, 2, seed), ox, oy)
    streak = E.shifted(stroke_texture(h, w, seed + 1, angle=angle, length=22), ox, oy)
    fxw = (E.shifted(E.noise(h, w, 9, seed + 2), ox, oy) - 0.5) * 6
    fyw = (E.shifted(E.noise(h, w, 9, seed + 3), ox, oy) - 0.5) * 6
    lay = E.warp(rgba, fxw, fyw)
    a = E.blur(lay[..., 3], 1.6)
    cov = np.clip((tooth * 0.6 + streak * 0.8 - (1.05 - density)) * 3.0, 0, 1) * a
    col = lay[..., :3] * (1 - whiten) + whiten
    return np.dstack([col, cov])


# ------------------------------------------------------------------ 月份牌喷绘
def airbrush(rgba, soft=38, top_light=0.18):
    """喷枪柔光：色块中心亮、边缘暗的柔和渐变 + 自上而下的光。"""
    rgb, a = rgba[..., :3], rgba[..., 3]
    d = region_dist(rgb, a, 0.05)
    vol = np.sqrt(np.clip(d / soft, 0, 1))
    vol = E.blur(vol, 6)
    ys = np.where(a > 0.5)[0]
    y0, y1 = (ys.min(), ys.max()) if len(ys) else (0, 1080)
    yy = np.clip((np.arange(rgb.shape[0], dtype=np.float32) - y0) / max(1, y1 - y0), 0, 1)[:, None]
    shade = (0.78 + 0.3 * vol) * (1 + top_light * (0.5 - yy))
    out = rgb * shade[..., None] + 0.06 * vol[..., None]
    return np.dstack([np.clip(out, 0, 1), a])


def age_print(img, paper_tex, warm='#E9D3A6', amount=0.2, fade=0.1):
    """旧印刷品：偏暖褪色、对比降低、纸纹。"""
    out = img * (1 - amount) + img * E.hexrgb(warm) * amount * 1.1
    out = out * (1 - fade) + fade * 0.85
    return out * paper_tex


def rubbed(rgba):
    """擦笔水彩：炭粉擦出的灰调塑形（边缘深、中心浅、上亮下暗）+ 透明淡彩 + 整体柔化。"""
    rgb, a = rgba[..., :3], rgba[..., 3]
    d = region_dist(rgb, a, 0.05)
    vol = E.blur(np.sqrt(np.clip(d / 55, 0, 1)), 8)
    ys = np.where(a > 0.5)[0]
    y0, y1 = (ys.min(), ys.max()) if len(ys) else (0, 1080)
    yy = np.clip((np.arange(rgb.shape[0], dtype=np.float32) - y0) / max(1, y1 - y0), 0, 1)[:, None]
    charcoal = (0.62 + 0.42 * vol) * (1.06 - 0.16 * yy)
    tint = rgb * 0.82 + 0.18
    out = tint * charcoal[..., None]
    out = E.blur(out, 1.4)
    return np.dstack([np.clip(out, 0, 1), E.blur(a, 1.0)])


# ------------------------------------------------------------------ 蜡笔
def crayon_fill(rgba, ox, oy, seed=131, angle=28, gap=9.0, boil=0):
    """蜡笔排线填色：斜向排线（带抖动）× 蜡质颗粒；boil 切换笔迹（每几帧换一次）。"""
    h, w = rgba.shape[:2]
    xx, yy = _grid(h, w)
    a = math.radians(angle)
    wob = (E.shifted(E.noise(h, w, 40, seed + boil * 17), ox, oy) - 0.5) * 10
    u = ((xx - ox) * math.cos(a) + (yy - oy) * math.sin(a) + wob) / gap
    stripe = 0.5 + 0.5 * np.cos(u * 2 * math.pi)
    tooth = E.shifted(E.noise(h, w, 2, seed + 1 + boil), ox, oy)
    cov = np.clip((stripe * 0.75 + tooth * 0.55 - 0.42) * 2.6, 0, 1)
    cov = np.maximum(cov, 0.35 * tooth)
    dark = np.clip((0.45 - E.lum(rgba[..., :3])) / 0.3, 0, 1)        # 深色（头发等）涂得更密，保持原色
    cov = np.maximum(cov, dark * (0.82 + 0.18 * tooth))
    col = rgba[..., :3]
    mx = col.max(-1, keepdims=True)
    col = np.where(dark[..., None] > 0, col, np.clip((col - mx * 0.15) * 1.18 + 0.03, 0, 1))
    return np.dstack([col, cov * rgba[..., 3]])


def crayon_line(alpha, ox, oy, seed=133, boil=0, wob=2.2):
    h, w = alpha.shape
    fx_ = (E.shifted(E.noise(h, w, 14, seed + boil * 7), ox, oy) - 0.5) * 2 * wob
    fy_ = (E.shifted(E.noise(h, w, 14, seed + 1 + boil * 7), ox, oy) - 0.5) * 2 * wob
    a = E.warp(cv2.dilate(alpha, np.ones((3, 3), np.uint8)), fx_, fy_)
    tooth = E.shifted(E.noise(h, w, 2, seed + 2 + boil), ox, oy)
    return np.clip(a * (0.55 + 0.6 * tooth), 0, 1)
