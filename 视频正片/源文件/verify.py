# -*- coding: utf-8 -*-
"""验收：逐个解码导出的 MP4，检查规格、时长、音轨、黑帧、闪烁；从正片抽帧生成关键帧总览与无标签画风检查图。

  python3 verify.py
"""
import os, re, subprocess, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import engine as E
import scenes
import film

OUT = film.OUT
CHECK = os.path.join(film.HERE, '检查')


def probe(path):
    r = subprocess.run([E.FFMPEG, '-hide_banner', '-i', path], capture_output=True, text=True)
    info = r.stderr
    v = re.search(r'Video: (\w+).*?, (\w+)\(.*?(\d{3,4})x(\d{3,4}).*?, ([\d.]+) fps', info)
    audio = 'Audio:' in info
    return dict(codec=v.group(1) if v else None, pix=v.group(2) if v else None,
                w=int(v.group(3)) if v else 0, h=int(v.group(4)) if v else 0,
                fps=float(v.group(5)) if v else 0, audio=audio)


def scan(path, step=1):
    """完整解码：帧数、每帧平均亮度（低分辨率）。"""
    p = subprocess.Popen([E.FFMPEG, '-loglevel', 'error', '-i', path, '-vf', 'scale=192:108', '-f', 'rawvideo',
                          '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    n, means, frames = 0, [], []
    sz = 192 * 108 * 3
    while True:
        b = p.stdout.read(sz)
        if len(b) < sz:
            break
        a = np.frombuffer(b, np.uint8).reshape(108, 192, 3).astype(np.float32)
        means.append(a.mean())
        frames.append(a)
        n += 1
    p.wait()
    diffs = [float(np.abs(frames[i] - frames[i - 1]).mean()) for i in range(1, len(frames))]
    return n, np.array(means), np.array(diffs)


def grab(path, t):
    out = subprocess.run([E.FFMPEG, '-loglevel', 'error', '-ss', f'{t:.3f}', '-i', path, '-frames:v', '1',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    return Image.frombuffer('RGB', (E.W, E.H), out[:E.W * E.H * 3])


def main():
    os.makedirs(CHECK, exist_ok=True)
    files = []
    for key, mod, cls in scenes.ORDER:
        files.append((key, os.path.join(OUT, scenes.SCENES[key].filename + '.mp4')))
    for i in range(len(film.trans.TRANS)):
        files.append(('trans', film.trans_path(i)))
    files.append(('film', film.FILM))
    report = []
    for key, path in files:
        pr = probe(path)
        n, means, diffs = scan(path)
        dur = n / 30
        black = int((means < 6).sum())
        # 闪烁：相邻帧差异的离群值（排除转场与正常动作，取远超中位数的尖峰）
        med = float(np.median(diffs)) if len(diffs) else 0
        spikes = [i + 1 for i, d in enumerate(diffs) if d > max(18, med * 6)]
        report.append(dict(file=os.path.basename(path), **pr, frames=n, seconds=round(dur, 3), black_frames=black,
                           diff_median=round(med, 2), diff_max=round(float(diffs.max()) if len(diffs) else 0, 2), spikes=spikes))
        print(report[-1])
    with open(os.path.join(CHECK, 'verify_report.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    # 关键帧总览（从最终正片抽取）：片头、13 套、片尾
    segs, total = film.segments()
    allsegs = segs
    segs = [x for x in segs if x['kind'] == 'core']
    picks = []
    for s in segs:
        if s['key'] == '00':
            t = s['start'] + 0.95
        elif s['key'] == '14':
            t = total - 0.3
        else:
            t = s['start'] + s['core'] / 2
        picks.append((s, t))
    tw, th = 576, 324
    font = ImageFont.truetype(E.FONT_SANS, 26, index=2)
    small = ImageFont.truetype(E.FONT_SANS, 20, index=0)
    cols, rows = 5, 3
    sheet = Image.new('RGB', (cols * tw + (cols + 1) * 16, rows * (th + 46) + 16 + 70), '#F4F1EC')
    d = ImageDraw.Draw(sheet)
    d.text((16, 18), 'Clawd × 单依纯《歌手2025》无声正片 · 关键帧总览（取自最终 MP4）', font=font, fill='#2E2320')
    styles = {s.key: s.style for s in [scenes.SCENES[k] for k in scenes.SCENES] if hasattr(s, 'style')}
    plain = []
    for i, (s, t) in enumerate(picks):
        im = grab(film.FILM, t)
        x = 16 + (i % cols) * (tw + 16)
        y = 70 + (i // cols) * (th + 46)
        sheet.paste(im.resize((tw, th)), (x, y))
        name = s['name'].split('_', 1)[1]
        label = f"{s['key']} {name}"
        st = getattr(scenes.SCENES[s['key']], 'style', '')
        d.text((x, y + th + 8), label + (f'  ·  {st}' if st else '') + f'   ({t:.1f}s)', font=small, fill='#2E2320')
        if s['key'] not in ('00', '14'):
            plain.append(im)
    sheet.save(os.path.join(OUT, '关键帧总览.png'))
    # 画风检查：每段中间一帧，不带歌名
    g = Image.new('RGB', (5 * 480 + 6 * 10, 3 * 270 + 4 * 10), '#111111')
    for i, im in enumerate(plain):
        g.paste(im.resize((480, 270)), (10 + (i % 5) * 490, 10 + (i // 5) * 280))
    g.save(os.path.join(OUT, '画风检查_13格无标签.png'))
    print('sheets saved')





def trans_sheet():
    """每个转场取 6 个时刻，检查 Clawd 跨越边界时的换装与画风。"""
    segs, total = film.segments()
    tr = [x for x in segs if x['kind'] == 'trans']
    tw, th = 320, 180
    font = ImageFont.truetype(E.FONT_SANS, 19, index=0)
    for part in range(2):
        sub = tr[part * 7:(part + 1) * 7]
        sheet = Image.new('RGB', (190 + 6 * tw, len(sub) * (th + 4)), '#222')
        d = ImageDraw.Draw(sheet)
        for r, s in enumerate(sub):
            d.text((6, r * (th + 4) + 70), f"{s['key']}\n{s['name']}", font=font, fill='white')
            for c, q in enumerate((0.0, 0.2, 0.4, 0.55, 0.7, 0.97)):
                im = grab(film.FILM, s['start'] + q * s['core'])
                sheet.paste(im.resize((tw, th)), (190 + c * tw, r * (th + 4)))
        sheet.save(os.path.join(CHECK, f'转场检查_{part + 1}.jpg'), quality=85)


if __name__ == '__main__':
    main()
    trans_sheet()
