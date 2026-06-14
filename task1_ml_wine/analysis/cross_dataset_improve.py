# -*- coding: utf-8 -*-
"""针对跨数据集对照中两个"效果不好"的数据集做对症处理，并量化改进。

诊断：
  - 贷款违约 F1 低 —— 之前只用 12 个数值特征，丢弃了 grade/期限/工龄等强信号类别特征 → 补特征
  - 臭氧 F1 低 —— 33:1 极端不平衡，仅靠 class_weight 不足 → 加 SMOTE 过采样
干豆/电离层/白葡萄酒本就较好，不在此处理。

输出：
  outputs/improve_summary.json / improve_metrics.csv
  outputs/improve_lendingclub.png  贷款违约 加类别特征前后(宏F1)
  outputs/improve_ozone.png        臭氧 类别权重 vs SMOTE(宏F1/平衡准确率)
"""
import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from common.zh_font import set_chinese_font
from task1_ml_wine.datasets.tabular import load_lendingclub, load_ozone

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, balanced_accuracy_score
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

from task1_ml_wine import OUT_DIR as OUT
MODELS = ["SVM", "决策树", "随机森林", "逻辑回归"]


def _estimators(class_weight="balanced"):
    return {
        "SVM": (SVC(class_weight=class_weight, random_state=42),
                {"clf__C": [1, 10], "clf__gamma": ["scale", 0.1]}),
        "决策树": (DecisionTreeClassifier(class_weight=class_weight, random_state=42),
                 {"clf__max_depth": [None, 10, 20], "clf__min_samples_leaf": [1, 5]}),
        "随机森林": (RandomForestClassifier(class_weight=class_weight, random_state=42, n_jobs=-1),
                 {"clf__n_estimators": [200, 400], "clf__max_depth": [None, 20]}),
        "逻辑回归": (LogisticRegression(class_weight=class_weight, max_iter=2000),
                 {"clf__C": [0.5, 1, 10]}),
    }


def _fit_eval(Xtr, ytr, Xte, yte, smote=False, class_weight="balanced"):
    out = {}
    for name, (est, grid) in _estimators(class_weight).items():
        steps = [("imputer", SimpleImputer(strategy="median")),
                 ("scaler", StandardScaler())]
        if smote:
            steps.append(("smote", SMOTE(random_state=42)))
        steps.append(("clf", est))
        pipe = ImbPipeline(steps) if smote else Pipeline(steps)
        gs = GridSearchCV(pipe, grid, cv=5, scoring="f1_macro", n_jobs=-1)
        gs.fit(Xtr, ytr)
        yp = gs.predict(Xte)
        out[name] = {"acc": round(float(accuracy_score(yte, yp)), 4),
                     "f1": round(float(f1_score(yte, yp, average="macro")), 4),
                     "bacc": round(float(balanced_accuracy_score(yte, yp)), 4)}
        print(f"    {name}: f1={out[name]['f1']:.4f} bacc={out[name]['bacc']:.4f}")
    return out


def split(X, y, seed=42):
    return train_test_split(X, y, test_size=0.2, stratify=y, random_state=seed)


def main():
    set_chinese_font()
    results = {}

    # ---- 贷款违约：补类别特征 ----
    print("\n===== 贷款违约：基线(12数值) vs 补类别特征 =====")
    Xb, yb, mb = load_lendingclub(rich=False)
    Xr, yr, mr = load_lendingclub(rich=True)
    print(f"  基线维度={Xb.shape[1]} 改进维度={Xr.shape[1]}")
    Xtr, Xte, ytr, yte = split(Xb, yb)
    print("  [基线]");  base_lc = _fit_eval(Xtr, ytr, Xte, yte)
    Xtr, Xte, ytr, yte = split(Xr, yr)
    print("  [补类别特征]"); imp_lc = _fit_eval(Xtr, ytr, Xte, yte)
    results["lendingclub"] = {"baseline": base_lc, "improved": imp_lc,
                              "dim_base": Xb.shape[1], "dim_improved": Xr.shape[1]}

    # ---- 臭氧：class_weight vs SMOTE ----
    print("\n===== 臭氧：类别权重(基线) vs SMOTE 过采样 =====")
    Xo, yo, mo = load_ozone()
    Xtr, Xte, ytr, yte = split(Xo, yo)
    print("  [基线: class_weight]"); base_oz = _fit_eval(Xtr, ytr, Xte, yte, smote=False)
    print("  [改进: SMOTE]"); imp_oz = _fit_eval(Xtr, ytr, Xte, yte, smote=True, class_weight=None)
    results["ozone"] = {"baseline": base_oz, "improved": imp_oz}

    json.dump(results, open(os.path.join(OUT, "improve_summary.json"), "w"),
              ensure_ascii=False, indent=2)
    # 扁平 CSV
    flat = []
    for ds, d in results.items():
        for variant in ("baseline", "improved"):
            for m in MODELS:
                flat.append({"数据集": ds, "配置": variant, "模型": m, **d[variant][m]})
    pd.DataFrame(flat).to_csv(os.path.join(OUT, "improve_metrics.csv"),
                              index=False, encoding="utf-8-sig")

    # 图：贷款违约 前后宏F1
    x = np.arange(len(MODELS)); w = 0.36
    plt.figure(figsize=(8, 4.6))
    b1 = plt.bar(x - w/2, [results["lendingclub"]["baseline"][m]["f1"] for m in MODELS], w,
                 label=f"基线({results['lendingclub']['dim_base']}维数值)", color="#4C72B0")
    b2 = plt.bar(x + w/2, [results["lendingclub"]["improved"][m]["f1"] for m in MODELS], w,
                 label=f"补类别特征({results['lendingclub']['dim_improved']}维)", color="#55A868")
    for bs in (b1, b2):
        for bi in bs:
            plt.text(bi.get_x()+bi.get_width()/2, bi.get_height()+0.008, f"{bi.get_height():.2f}",
                     ha="center", va="bottom", fontsize=8)
    plt.xticks(x, MODELS); plt.ylim(0, 1.0); plt.ylabel("宏平均 F1")
    plt.title("贷款违约：补充申请时类别特征后宏F1提升")
    plt.legend(); plt.grid(axis="y", alpha=0.3); plt.tight_layout()
    plt.savefig(os.path.join(OUT, "improve_lendingclub.png"), dpi=150); plt.close()

    # 图：臭氧 class_weight vs SMOTE（宏F1 + 平衡准确率）
    plt.figure(figsize=(8.5, 4.6))
    bf = [results["ozone"]["baseline"][m]["f1"] for m in MODELS]
    sf = [results["ozone"]["improved"][m]["f1"] for m in MODELS]
    b1 = plt.bar(x - w/2, bf, w, label="基线(class_weight) 宏F1", color="#4C72B0")
    b2 = plt.bar(x + w/2, sf, w, label="SMOTE 宏F1", color="#C44E52")
    for bs in (b1, b2):
        for bi in bs:
            plt.text(bi.get_x()+bi.get_width()/2, bi.get_height()+0.008, f"{bi.get_height():.2f}",
                     ha="center", va="bottom", fontsize=8)
    plt.xticks(x, MODELS); plt.ylim(0, 0.9); plt.ylabel("宏平均 F1")
    plt.title("臭氧(不平衡33:1)：SMOTE 过采样 vs 类别权重")
    plt.legend(); plt.grid(axis="y", alpha=0.3); plt.tight_layout()
    plt.savefig(os.path.join(OUT, "improve_ozone.png"), dpi=150); plt.close()

    # 控制台汇总
    print("\n===== 改进汇总(宏平均 F1) =====")
    for ds, d in results.items():
        print(f"[{ds}]")
        for m in MODELS:
            print(f"  {m:<8} 基线 {d['baseline'][m]['f1']:.4f} -> 改进 {d['improved'][m]['f1']:.4f} "
                  f"(Δ{(d['improved'][m]['f1']-d['baseline'][m]['f1'])*100:+.1f}pp)")
    print(f"\n[聚合] -> improve_summary.json / improve_metrics.csv / improve_lendingclub.png / improve_ozone.png")


if __name__ == "__main__":
    main()
