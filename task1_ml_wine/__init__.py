# -*- coding: utf-8 -*-
"""任务① 传统机器学习（白葡萄酒质量分类 + 跨数据集对照）。

统一的目录常量：DATA_DIR 存放数据集，OUT_DIR 存放运行产物（图表 / 指标）。
"""
import os

PKG_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PKG_DIR, "data")
OUT_DIR = os.path.join(PKG_DIR, "outputs")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)
