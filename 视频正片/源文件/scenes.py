# -*- coding: utf-8 -*-
"""片段注册表（按演出顺序）。"""
import importlib

ORDER = [('00', 'intro', 'Intro'), ('01', 's01_珠玉', 'S01'), ('02', 's02_天空', 'S02'),
         ('03', 's03_爱情', 'S03'), ('04', 's04_李白', 'S04'), ('05', 's05_DearFriend', 'S05'),
         ('06', 's06_一个人跳舞', 'S06'), ('07', 's07_思念是一种病', 'S07'), ('08', 's08_梦一场', 'S08'),
         ('09', 's09_舞娘', 'S09'), ('10', 's10_开始懂了', 'S10'), ('11', 's11_君', 'S11'),
         ('12', 's12_落叶归根', 'S12'), ('13', 's13_有趣', 'S13'), ('14', 'outro', 'Outro')]
SCENES = {}
for key, mod, cls in ORDER:
    try:
        SCENES[key] = getattr(importlib.import_module(mod), cls)
    except ModuleNotFoundError:
        pass
