# -*- coding: utf-8 -*-
"""完整正片：片头核心段 → 转场 → 01 核心段 → 转场 → … → 13 核心段 → 转场 → 片尾核心段。

每首歌的核心段（有效展示时长）取自各段独立 MP4（跳过首尾剪辑余量）；转场是 Clawd 一个人从上一段走进下一段的独立动画
（trans.py，渲染在 cache/转场_XX.mp4），首帧接上一段最后一帧，末帧接下一段第一帧，所以直接首尾相接即可，不做叠化。

  python3 film.py            → ../Clawd_单依纯13套造型_无声正片.mp4
"""
import os, subprocess
import numpy as np
import engine as E
import scenes
import trans

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, '..'))
FILM = os.path.join(OUT, 'Clawd_单依纯13套造型_无声正片.mp4')
CACHE = os.path.join(HERE, 'cache')


def trans_path(i):
    tr = trans.TRANS[i]
    return os.path.join(OUT, '转场', f'转场{i:02d}_{tr.a}到{tr.b}_{tr.name}.mp4')


def segments():
    """返回按播放顺序排列的段落列表：歌曲 / 片头片尾核心段（kind='core'）与转场（kind='trans'），带起止时间。"""
    out = []
    t = 0.0
    keys = [k for k, _, _ in scenes.ORDER]
    for idx, key in enumerate(keys):
        sc = scenes.SCENES[key]
        src = os.path.join(CACHE, sc.filename + '_work.mp4') if key in ('00', '14') else os.path.join(OUT, sc.filename + '.mp4')
        n = int(round(sc.core * E.FPS))
        out.append(dict(kind='core', key=key, name=sc.filename, core=sc.core, handle=sc.handle, src=src,
                        skip=int(round(sc.handle * E.FPS)), frames=n, start=t))
        t += n / E.FPS
        if idx < len(trans.TRANS):
            tr = trans.TRANS[idx]
            out.append(dict(kind='trans', key=f'{tr.a}→{tr.b}', name=tr.name, src=trans_path(idx),
                            skip=0, frames=tr.n, start=t, core=tr.n / E.FPS))
            t += tr.n / E.FPS
    return out, t


def decode(path, skip, count):
    p = subprocess.Popen([E.FFMPEG, '-loglevel', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    sz = E.W * E.H * 3
    i = got = 0
    last = None
    while got < count:
        b = p.stdout.read(sz)
        if len(b) < sz:
            break
        if i >= skip:
            last = b
            got += 1
            yield b
        i += 1
    p.stdout.close()
    p.kill()
    while got < count:                 # 源文件意外短缺时补最后一帧（不应发生；verify 会检查总帧数）
        got += 1
        yield last


def build(path=FILM):
    segs, total = segments()
    w = E.Writer(path, crf=16)
    nf = 0
    for s in segs:
        for b in decode(s['src'], s['skip'], s['frames']):
            w.p.stdin.write(b)
            nf += 1
    w.close()
    print('正片', path, f'{total:.2f}s', nf, '帧')
    return segs, total


if __name__ == '__main__':
    build()
