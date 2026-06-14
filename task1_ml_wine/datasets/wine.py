# -*- coding: utf-8 -*-
"""UCI 白葡萄酒质量数据集的下载与读取。"""
import os
import io
import zipfile
import urllib.request
import pandas as pd

from task1_ml_wine import DATA_DIR

CSV_PATH = os.path.join(DATA_DIR, "winequality-white.csv")


def download_data():
    """下载 UCI 白葡萄酒质量数据集到 data/。优先直链 CSV，失败则取官方 zip 解压。"""
    if os.path.exists(CSV_PATH):
        print(f"[数据] 已存在: {CSV_PATH}")
        return
    direct = ("https://archive.ics.uci.edu/ml/machine-learning-databases/"
              "wine-quality/winequality-white.csv")
    try:
        print("[数据] 尝试直链下载...")
        urllib.request.urlretrieve(direct, CSV_PATH)
    except Exception as e:
        print(f"[数据] 直链失败({e})，改用官方 zip...")
        zip_url = "https://archive.ics.uci.edu/static/public/186/wine+quality.zip"
        with urllib.request.urlopen(zip_url, timeout=60) as resp:
            zbytes = resp.read()
        with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
            with z.open("winequality-white.csv") as f, open(CSV_PATH, "wb") as out:
                out.write(f.read())
    print(f"[数据] 已保存: {CSV_PATH}")


def load_data():
    """读取分号分隔的 CSV，返回 DataFrame。"""
    df = pd.read_csv(CSV_PATH, sep=";")
    print(f"[数据] 形状: {df.shape}")
    return df
