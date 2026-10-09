# -*- coding: utf-8 -*-
import engine as E


class Scene:
    key = '00'
    filename = ''
    no = 0              # 对应造型编号
    core = 4.0          # 有效展示时长（秒）
    handle = 0.4        # 首尾剪辑余量（秒）
    step = 1            # 1=逐帧 30fps；2=一拍二；3=一拍三

    def setup(self):
        pass

    def frame(self, t, p=None, trans=False):
        raise NotImplementedError
