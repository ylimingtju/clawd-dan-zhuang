# -*- coding: utf-8 -*-
"""渲染：python3 render.py <输出目录> [编号...]  —— 生成 SVG 源文件并用 Chrome 无头模式转 PNG。"""
import os, sys, subprocess
import looks

CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


def all_looks():
    out = []
    for name in dir(looks):
        obj = getattr(looks, name)
        if isinstance(obj, type) and issubclass(obj, looks.Look) and obj is not looks.Look:
            out.append(obj())
    return sorted(out, key=lambda l: l.no)


def to_png(svg_path, png_path, size=(1600, 1600)):
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars',
                    f'--screenshot={png_path}', f'--window-size={size[0]},{size[1]}',
                    'file://' + os.path.abspath(svg_path)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == '__main__':
    out_dir = sys.argv[1]
    only = set(int(x) for x in sys.argv[2:])
    src_dir = os.path.join(out_dir, '源文件')
    svg_dir = os.path.join(src_dir, 'svg')
    os.makedirs(svg_dir, exist_ok=True)
    for lk in all_looks():
        if only and lk.no not in only:
            continue
        stem = f'{lk.no:02d}_{lk.title}'
        sp = os.path.join(svg_dir, stem + '.svg')
        with open(sp, 'w', encoding='utf-8') as f:
            f.write(lk.render())
        # 基础角色只作比例参考，放在源文件夹，不与 00_总览 混淆
        png_dir = src_dir if lk.no == 0 else out_dir
        to_png(sp, os.path.join(png_dir, ('Clawd_基础角色' if lk.no == 0 else stem) + '.png'))
        print('ok', stem)
