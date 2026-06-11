# -*- coding: utf-8 -*-
"""最后一搏：在两个"效果不好"的数据集上加入梯度提升(HistGradientBoosting)作第 5 个模型，
看更强的模型能否突破 4 个基础模型的上限。结果并入 improve_summary.json。"""
import os
import sys
import json
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_tabular import load_lendingclub, load_ozone
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import f1_score, balanced_accuracy_score, accuracy_score

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
GRID = {"learning_rate": [0.05, 0.1], "max_depth": [None, 6],
        "max_iter": [200, 400]}


def run(X, y, class_weight=None):
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    est = HistGradientBoostingClassifier(random_state=42, class_weight=class_weight,
                                         early_stopping=True)
    gs = GridSearchCV(est, GRID, cv=5, scoring="f1_macro", n_jobs=-1)
    gs.fit(Xtr, ytr)
    yp = gs.predict(Xte)
    return {"acc": round(float(accuracy_score(yte, yp)), 4),
            "f1": round(float(f1_score(yte, yp, average="macro")), 4),
            "bacc": round(float(balanced_accuracy_score(yte, yp)), 4)}


def main():
    res = {}
    print("[GBDT] 贷款违约(补类别特征 37 维)...")
    Xr, yr, _ = load_lendingclub(rich=True)
    res["lendingclub"] = run(Xr, yr)
    print("   ", res["lendingclub"])
    print("[GBDT] 臭氧(class_weight=balanced)...")
    Xo, yo, _ = load_ozone()
    res["ozone"] = run(Xo, yo, class_weight="balanced")
    print("   ", res["ozone"])

    # 并入 improve_summary.json
    path = os.path.join(OUT, "improve_summary.json")
    summary = json.load(open(path))
    for ds in res:
        summary[ds]["gbdt"] = res[ds]
    json.dump(summary, open(path, "w"), ensure_ascii=False, indent=2)
    print("\n[GBDT] 已并入 improve_summary.json")
    print(f"贷款违约: 4模型最优≈0.5843(LR) -> GBDT {res['lendingclub']['f1']}")
    print(f"臭氧:     4模型最优≈0.5806(DT)  -> GBDT {res['ozone']['f1']}")


if __name__ == "__main__":
    main()
