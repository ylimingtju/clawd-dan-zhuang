# -*- coding: utf-8 -*-
"""逐帧渲染独立片段。

  python3 render.py clip 01            渲染 01 片段（含首尾余量）→ ../01_珠玉.mp4
  python3 render.py clip all           渲染全部 13 段 + 片头片尾
  python3 render.py stills 01 0,1.5,3  渲染指定时刻（核心时间轴，秒）→ 检查拼图
"""
import os, sys, math, time
import numpy as np
from multiprocessing import Pool
from PIL import Image

import engine as E
import scenes

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CHECK = os.path.join(os.path.dirname(__file__), '检查')
_SC = {}


def get_scene(key):
    if key not in _SC:
        sc = scenes.SCENES[key]()
        sc.setup()
        _SC[key] = sc
    return _SC[key]


def frame_time(sc, i, with_handles=True):
    h = sc.handle if with_handles else 0.0
    t = i / E.FPS - h
    if sc.step > 1:                                   # 定格/一拍二：按 step 帧保持
        k = math.floor((i) / sc.step) * sc.step
        t = k / E.FPS - h
    return t


def render_one(args):
    key, t = args
    sc = get_scene(key)
    return E.to_u8(sc.frame(t)).tobytes()


def nframes(sc, with_handles=True):
    return int(round((sc.core + (2 * sc.handle if with_handles else 0)) * E.FPS))


def render_trans_one(args):
    import trans
    k, i = args
    tr = trans.TRANS[k]
    return E.to_u8(trans.frame(tr, i, get_scene(tr.a), get_scene(tr.b))).tobytes()


def render_trans(k, workers=8):
    import trans
    tr = trans.TRANS[k]
    import film
    path = film.trans_path(k)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    w = E.Writer(path)
    t0 = time.time()
    with Pool(workers) as pool:
        for b in pool.imap(render_trans_one, [(k, i) for i in range(tr.n)], chunksize=1):
            w.write(np.frombuffer(b, np.uint8).reshape(E.H, E.W, 3))
    w.close()
    print(f'转场 {k:02d} {tr.a}→{tr.b} {tr.name}: {tr.n} 帧, {time.time() - t0:.1f}s')
    return path


def render_clip(key, path=None, with_handles=True, workers=8):
    sc = scenes.SCENES[key]()
    n = nframes(sc, with_handles)
    times = [frame_time(sc, i, with_handles) for i in range(n)]
    path = path or os.path.join(OUT, sc.filename + '.mp4')
    w = E.Writer(path)
    t0 = time.time()
    with Pool(workers) as pool:
        for b in pool.imap(render_one, [(key, t) for t in times], chunksize=2):
            w.write(np.frombuffer(b, np.uint8).reshape(E.H, E.W, 3))
    w.close()
    print(f'{sc.filename}: {n} 帧, {time.time() - t0:.1f}s → {path}')
    return path


def stills(key, ts, out=None, cols=3):
    sc = get_scene(key)
    ims = [Image.fromarray(E.to_u8(sc.frame(t))) for t in ts]
    tw, th = 640, 360
    rows = math.ceil(len(ims) / cols)
    sheet = Image.new('RGB', (cols * tw, rows * th), 'black')
    for i, im in enumerate(ims):
        sheet.paste(im.resize((tw, th)), ((i % cols) * tw, (i // cols) * th))
    os.makedirs(CHECK, exist_ok=True)
    out = out or os.path.join(CHECK, f'stills_{key}.jpg')
    if len(ims) == 1:
        ims[0].save(out.replace('.jpg', '_full.png'))
        return
    sheet.save(out, quality=90)
    print(out)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'clip':
        keys = list(scenes.SCENES) if sys.argv[2] == 'all' else sys.argv[2].split(',')
        for k in keys:
            render_clip(k)
    elif cmd == 'work':
        # 片头片尾：带余量的工作版（供正片转场取帧），存入源文件/cache
        os.makedirs(os.path.join(os.path.dirname(__file__), 'cache'), exist_ok=True)
        for k in sys.argv[2].split(','):
            sc = scenes.SCENES[k]()
            render_clip(k, os.path.join(os.path.dirname(__file__), 'cache', sc.filename + '_work.mp4'))
    elif cmd == 'deliver_bookends':
        # 片头片尾成品：只含核心时长（1–2 秒）
        for k in ('00', '14'):
            render_clip(k, with_handles=False)
    elif cmd == 'tstills':
        # 转场检查帧：python3 render.py tstills 3 0.2,0.5,0.8
        import trans
        tr = trans.TRANS[int(sys.argv[2])]
        sa, sb = get_scene(tr.a), get_scene(tr.b)
        ims = [Image.fromarray(E.to_u8(trans.frame(tr, int(round(float(u) * (tr.n - 1))), sa, sb)))
               for u in sys.argv[3].split(',')]
        tw, th = 640, 360
        sheet = Image.new('RGB', (tw * min(3, len(ims)), th * math.ceil(len(ims) / 3)))
        for i, im in enumerate(ims):
            sheet.paste(im.resize((tw, th)), ((i % 3) * tw, (i // 3) * th))
        os.makedirs(CHECK, exist_ok=True)
        out = os.path.join(CHECK, f'tstills_{sys.argv[2]}.jpg')
        sheet.save(out, quality=88)
        print(out)
    elif cmd == 'trans':
        import trans
        os.makedirs(os.path.join(os.path.dirname(__file__), 'cache'), exist_ok=True)
        idx = range(len(trans.TRANS)) if sys.argv[2] == 'all' else [int(x) for x in sys.argv[2].split(',')]
        for k in idx:
            render_trans(k)
    elif cmd == 'stills':
        stills(sys.argv[2], [float(x) for x in sys.argv[3].split(',')])
