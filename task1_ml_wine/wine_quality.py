# -*- coding: utf-8 -*-
"""任务① 红酒（白葡萄酒）质量多分类：加载→查看→预处理→建模→评估→结论。"""
import os
import io
import zipfile
import urllib.request
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.zh_font import set_chinese_font

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
OUT_DIR = os.path.join(HERE, "outputs")
CSV_PATH = os.path.join(DATA_DIR, "winequality-white.csv")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)


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


def eda(df):
    """探索性分析：打印统计、缺失值；绘制 quality 分布与相关性热力图。"""
    print("\n[EDA] 描述统计:\n", df.describe().T)
    print("\n[EDA] 缺失值合计:", int(df.isnull().sum().sum()))
    print("\n[EDA] quality 取值分布:\n", df["quality"].value_counts().sort_index())

    set_chinese_font()
    plt.figure(figsize=(6, 4))
    sns.countplot(x="quality", data=df, color="#4C72B0")
    plt.title("葡萄酒质量评分分布")
    plt.xlabel("质量评分"); plt.ylabel("样本数")
    plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, "eda_quality_dist.png"), dpi=150)
    plt.close()
    plt.figure(figsize=(10, 8))
    sns.heatmap(df.corr(), annot=True, fmt=".2f", cmap="coolwarm", square=True,
                cbar_kws={"shrink": .8}, annot_kws={"size": 7})
    plt.title("特征相关性热力图")
    plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, "eda_corr_heatmap.png"), dpi=150)
    plt.close()
    print(f"[EDA] 图已保存到 {OUT_DIR}")


from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

CLASS_NAMES = ["差(≤5)", "中(=6)", "好(≥7)"]


def make_labels(df):
    """将 0-10 的 quality 评分分箱为 3 类：≤5→0, =6→1, ≥7→2。"""
    def to_cls(q):
        if q <= 5:
            return 0
        elif q == 6:
            return 1
        return 2
    y = df["quality"].apply(to_cls).to_numpy()
    X = df.drop(columns=["quality"]).to_numpy()
    print("[预处理] 三分类标签分布:", np.bincount(y))
    return X, y


def preprocess(X, y, test_size=0.2, seed=42):
    """分层划分 + 标准化（仅在训练集 fit）。返回标准化后的数据与 scaler。"""
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=seed)
    scaler = StandardScaler().fit(X_tr)
    X_tr = scaler.transform(X_tr)
    X_te = scaler.transform(X_te)
    print(f"[预处理] 训练集 {X_tr.shape}，测试集 {X_te.shape}")
    return X_tr, X_te, y_tr, y_te, scaler


if __name__ == "__main__":
    download_data()
    df = load_data()
    eda(df)
    X, y = make_labels(df)
    X_tr, X_te, y_tr, y_te, scaler = preprocess(X, y)
    assert X_tr.shape[1] == 11 and len(set(y)) == 3
    print("[自检] 预处理通过")
