# -*- coding: utf-8 -*-
"""跨数据集模型对照实验：同一套 4 个传统机器学习模型(SVM/决策树/随机森林/逻辑回归)，
在难度递增的 5 个结构化数据集上对照，考察"什么决定模型性能"。

复用 wine_quality.build_models 的网格搜索 + 标准化 Pipeline 管线，保证方法与项目一一致。
每个(数据集×模型)记录测试集 准确率 / 宏平均 F1 / 平衡准确率，并与数据集特点(样本量、维度、
类别数、不平衡比)一起聚合，输出：
  outputs/cross_tab_summary.json / .csv
  outputs/cross_tab_f1.png        模型×数据集 宏平均F1 分组柱状
  outputs/cross_tab_imbalance.png 不平衡数据上 准确率 vs 宏F1 vs 平衡准确率
"""
import os
import sys
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from common.zh_font import set_chinese_font
from task1_ml_wine.datasets.tabular import LOADERS
from task1_ml_wine.models import build_models

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import (accuracy_score, f1_score, balanced_accuracy_score)

from task1_ml_wine import OUT_DIR as OUT

# 难度阶梯顺序(由易到难/由小到大)
ORDER = ["ionosphere", "wine", "lendingclub", "drybean", "ozone"]


def run_one(name, seed=42):
    X, y, meta = LOADERS[name]()
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y,
                                          random_state=seed)
    majority = float(np.bincount(yte).max() / len(yte))
    res = {"dataset": name, "label": meta["label"], "n_samples": meta["n_samples"],
           "n_features": meta["n_features"], "n_classes": meta["n_classes"],
           "imbalance_ratio": meta["imbalance_ratio"],
           "minority_frac": meta["minority_frac"],
           "majority_baseline": round(majority, 4), "models": {}}
    for mname, (est, grid) in build_models().items():
        t0 = time.time()
        pipe = Pipeline([("imputer", SimpleImputer(strategy="median")),
                         ("scaler", StandardScaler()), ("clf", est)])
        gs = GridSearchCV(pipe, grid, cv=5, scoring="f1_macro", n_jobs=-1)
        gs.fit(Xtr, ytr)
        yp = gs.predict(Xte)
        acc = accuracy_score(yte, yp)
        f1 = f1_score(yte, yp, average="macro")
        bacc = balanced_accuracy_score(yte, yp)
        res["models"][mname] = {"acc": round(float(acc), 4),
                                "f1": round(float(f1), 4),
                                "bacc": round(float(bacc), 4)}
        print(f"  [{name}/{mname}] acc={acc:.4f} f1={f1:.4f} bacc={bacc:.4f} "
              f"({time.time()-t0:.1f}s)")
    return res


def main():
    set_chinese_font()
    rows = []
    for name in ORDER:
        print(f"\n===== {name} =====")
        rows.append(run_one(name))

    json.dump({"rows": rows, "note": "4模型×5数据集；指标为测试集 acc/宏F1/平衡准确率"},
              open(os.path.join(OUT, "cross_tab_summary.json"), "w"),
              ensure_ascii=False, indent=2)

    # 扁平 CSV
    flat = []
    for r in rows:
        for m, v in r["models"].items():
            flat.append({"数据集": r["label"], "模型": m, **v,
                         "多数类基线": r["majority_baseline"]})
    pd.DataFrame(flat).to_csv(os.path.join(OUT, "cross_tab_metrics.csv"),
                              index=False, encoding="utf-8-sig")

    models = list(build_models().keys())
    labels = [r["label"] for r in rows]
    colors = {"SVM": "#C44E52", "决策树": "#8172B3", "随机森林": "#55A868", "逻辑回归": "#4C72B0"}

    # 图1：模型 × 数据集 宏平均F1 分组柱状
    x = np.arange(len(rows)); w = 0.2
    plt.figure(figsize=(11, 5.4))
    for i, m in enumerate(models):
        vals = [r["models"][m]["f1"] for r in rows]
        b = plt.bar(x + (i - 1.5) * w, vals, w, label=m, color=colors[m])
        for bi, v in zip(b, vals):
            plt.text(bi.get_x() + bi.get_width() / 2, v + 0.012, f"{v:.2f}",
                     ha="center", va="bottom", fontsize=7)
    plt.xticks(x, labels, fontsize=8.5)
    plt.ylim(0, 1.08); plt.ylabel("宏平均 F1")
    plt.title("同一套模型在五个数据集上的对照（宏平均 F1）")
    plt.legend(loc="lower left", ncol=4, fontsize=9); plt.grid(axis="y", alpha=0.3)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "cross_tab_f1.png"), dpi=150)
    plt.close()

    # 图2：不平衡的代价——随机森林在各数据集上 准确率 vs 宏F1 vs 平衡准确率
    rf_acc = [r["models"]["随机森林"]["acc"] for r in rows]
    rf_f1 = [r["models"]["随机森林"]["f1"] for r in rows]
    rf_bacc = [r["models"]["随机森林"]["bacc"] for r in rows]
    xx = np.arange(len(rows)); w2 = 0.26
    plt.figure(figsize=(11, 5.0))
    plt.bar(xx - w2, rf_acc, w2, label="准确率", color="#4C72B0")
    plt.bar(xx, rf_f1, w2, label="宏平均 F1", color="#55A868")
    plt.bar(xx + w2, rf_bacc, w2, label="平衡准确率", color="#C44E52")
    for j in range(len(rows)):
        for off, val in [(-w2, rf_acc[j]), (0, rf_f1[j]), (w2, rf_bacc[j])]:
            plt.text(xx[j] + off, val + 0.012, f"{val:.2f}", ha="center", va="bottom", fontsize=7)
    plt.xticks(xx, [f"{r['label']}\n不平衡比{r['imbalance_ratio']}" for r in rows], fontsize=8)
    plt.ylim(0, 1.08); plt.ylabel("分数")
    plt.title("不平衡的代价：随机森林的准确率 vs 宏F1 vs 平衡准确率")
    plt.legend(loc="lower left", ncol=3, fontsize=9); plt.grid(axis="y", alpha=0.3)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "cross_tab_imbalance.png"), dpi=150)
    plt.close()

    # 控制台汇总表
    print("\n===== 跨数据集对照（宏平均 F1）=====")
    hdr = f"{'数据集':<26}" + "".join(f"{m:>10}" for m in models) + f"{'最优模型':>12}"
    print(hdr)
    for r in rows:
        f1s = {m: r["models"][m]["f1"] for m in models}
        best = max(f1s, key=f1s.get)
        line = f"{r['label']:<26}" + "".join(f"{f1s[m]:>10.4f}" for m in models) + f"{best:>12}"
        print(line)
    print(f"\n[聚合] -> cross_tab_summary.json / cross_tab_metrics.csv / cross_tab_f1.png / cross_tab_imbalance.png")


if __name__ == "__main__":
    main()
