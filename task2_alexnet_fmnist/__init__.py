# -*- coding: utf-8 -*-
"""任务② 手写 AlexNet 图像分类（Fashion-MNIST + 跨数据集架构对照）。

统一的目录常量：DATA_DIR 存放数据集，OUT_DIR 存放运行产物（曲线 / 混淆矩阵 / json）。
"""
import os

PKG_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PKG_DIR, "data")
OUT_DIR = os.path.join(PKG_DIR, "outputs")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)
