# -*- coding: utf-8 -*-
"""贷款违约的"任务级方法创新"实验：单调约束梯度提升(信用评分领域先验)。

动机：信用评分是受监管领域，业界要求模型满足【单调性】——利率越高、负债收入比越高、
历史逾期/查询/坏账越多 → 违约概率不得下降；年收入越高 → 违约概率不得上升。把这些领域先验
作为硬约束注入 GBDT(sklearn HistGradientBoosting 的 monotonic_cst)，可在不引入新数据的前提下
约束假设空间、提升泛化稳定性与可解释性(监管友好)。

对照：同一 GBDT，无约束 vs 单调约束。指标为测试集 acc/宏F1/平衡准确率。
输出并入 outputs/ozone_temporal_summary.json 同级的 credit_monotonic_summary.json。
"""
import os
import sys
import json
import numpy as np

from task1_ml_wine.datasets.tabular import load_lendingclub, _LC_FEATURES
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, balanced_accuracy_score

from task1_ml_wine import OUT_DIR as OUT

# 领域先验：+1 表示"该特征↑ → 违约概率↑"，-1 反之，0 不约束
_SIGN = {"int_rate": 1, "annual_inc": -1, "dti": 1, "delinq_2yrs": 1,
         "inq_last_6mths": 1, "pub_rec": 1, "revol_util": 1}
MONO_CST = [_SIGN.get(f, 0) for f in _LC_FEATURES]
GRID = {"learning_rate": [0.05, 0.1], "max_depth": [None, 6], "max_iter": [200, 400]}


def run(X, y, monotonic):
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    est = HistGradientBoostingClassifier(
        random_state=42, class_weight="balanced", early_stopping=True,
        monotonic_cst=MONO_CST if monotonic else None)
    gs = GridSearchCV(est, GRID, cv=5, scoring="f1_macro", n_jobs=-1)
    gs.fit(Xtr, ytr)
    yp = gs.predict(Xte)
    return {"acc": round(float(accuracy_score(yte, yp)), 4),
            "f1": round(float(f1_score(yte, yp, average="macro")), 4),
            "bacc": round(float(balanced_accuracy_score(yte, yp)), 4)}


def main():
    X, y, meta = load_lendingclub()            # base 12 维
    print(f"贷款违约 base：{X.shape[0]} 样本 × {X.shape[1]} 维，"
          f"违约率 {y.mean()*100:.1f}%")
    constrained = {f: s for f, s in zip(_LC_FEATURES, MONO_CST) if s}
    print(f"单调约束列：{constrained}\n")

    res = {}
    print("[GBDT] 无约束 ...")
    res["unconstrained"] = run(X, y, monotonic=False)
    print("   ", res["unconstrained"])
    print("[GBDT] 单调约束(领域先验) ...")
    res["monotonic"] = run(X, y, monotonic=True)
    print("   ", res["monotonic"])

    summary = {"dataset": "lendingclub", "n_features": int(X.shape[1]),
               "monotonic_columns": constrained, "results": res,
               "delta_f1": round(res["monotonic"]["f1"] - res["unconstrained"]["f1"], 4)}
    json.dump(summary, open(os.path.join(OUT, "credit_monotonic_summary.json"), "w"),
              ensure_ascii=False, indent=2)
    print("\n========== 结论 ==========")
    print(f"无约束 GBDT   宏F1 = {res['unconstrained']['f1']}")
    print(f"单调约束 GBDT 宏F1 = {res['monotonic']['f1']}  "
          f"(Δ = {summary['delta_f1']:+.4f})")
    print("意义：单调约束注入领域先验，主要价值在泛化稳定性与监管可解释性，F1 通常持平或小幅变动。")


if __name__ == "__main__":
    main()
