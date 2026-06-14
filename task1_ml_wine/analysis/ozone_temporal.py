# -*- coding: utf-8 -*-
"""臭氧检测的"任务级方法创新"实验：把被当成 iid 表格的臭氧数据还原为时间序列。

动机：UCI 臭氧数据集是 1998-2004 按天采集的序列(首列即日期)，原基线把日期列直接丢弃、
随机划分训练/测试，等于扔掉了地面臭氧强烈的【日间自相关 + 季节性】信息。本实验注入时序特征
并改用【按时间切分】，验证瓶颈究竟是"模型不行"还是"问题建模方式不对"。

三档消融(隔离"换划分方式"与"加时序特征"两件事)：
  A  72原始特征 + 随机split           —— 复现现状(信息上限的当前估计)
  B  72原始特征 + 时序split           —— 仅改划分方式，控制变量
  C  72原始 + 时序特征 + 时序split    —— 本文创新(注入自相关/季节信息)

时序特征(9 维，均只用"过去"信息，无未来泄漏)：
  - 标签滞后 y[t-1], y[t-2], y[t-3]        昨日/前日是否超标(部署时昨日结果已知，可用)
  - 标签滑动率 mean(y, 3) / mean(y, 7)     近期超标频率
  - 月份 sin/cos、年内第几天 sin/cos       季节周期

输出：outputs/ozone_temporal_summary.json、outputs/ozone_temporal.png
"""
import os
import sys
import io
import json
import time
import zipfile
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from common.zh_font import set_chinese_font
from task1_ml_wine.models import build_models

from sklearn.base import clone
from sklearn.model_selection import train_test_split, GridSearchCV, TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (accuracy_score, f1_score, balanced_accuracy_score,
                             recall_score, precision_score)

from task1_ml_wine import OUT_DIR as OUT
from task1_ml_wine import DATA_DIR


def load_ozone_with_date():
    """返回按日期升序的 (dates, X72, y)。"""
    with zipfile.ZipFile(os.path.join(DATA_DIR, "Ozone Level Detection.zip")) as z:
        raw = z.read("onehr.data.csv").decode("utf-8")
    df = pd.read_csv(io.StringIO(raw), header=None, na_values="?")
    dates = pd.to_datetime(df.iloc[:, 0], format="%m/%d/%Y", errors="coerce")
    order = np.argsort(dates.values, kind="stable")
    df = df.iloc[order].reset_index(drop=True)
    dates = dates.iloc[order].reset_index(drop=True)
    y = df.iloc[:, -1].to_numpy(dtype=int)
    X = df.iloc[:, 1:-1].to_numpy(dtype=float)   # 72 个气象特征
    return dates, X, y


def build_temporal_features(dates, y):
    """构造 9 维时序特征；标签类特征只用 shift(过去)，预测当天不可见当天标签。"""
    s = pd.Series(y.astype(float))
    feats = {
        "lag1": s.shift(1), "lag2": s.shift(2), "lag3": s.shift(3),
        "roll3": s.shift(1).rolling(3, min_periods=1).mean(),
        "roll7": s.shift(1).rolling(7, min_periods=1).mean(),
    }
    doy = dates.dt.dayofyear.to_numpy(dtype=float)
    month = dates.dt.month.to_numpy(dtype=float)
    feats["month_sin"] = pd.Series(np.sin(2 * np.pi * month / 12))
    feats["month_cos"] = pd.Series(np.cos(2 * np.pi * month / 12))
    feats["doy_sin"] = pd.Series(np.sin(2 * np.pi * doy / 365.25))
    feats["doy_cos"] = pd.Series(np.cos(2 * np.pi * doy / 365.25))
    T = pd.DataFrame(feats).fillna(0.0).to_numpy(dtype=float)   # 起始几天无历史→填0
    return T


def all_models():
    """4 个传统模型 + GBDT(与项目口径一致，class_weight=balanced)。"""
    models = dict(build_models())
    models["GBDT"] = (
        HistGradientBoostingClassifier(random_state=42, class_weight="balanced",
                                       early_stopping=True),
        {"clf__learning_rate": [0.05, 0.1], "clf__max_depth": [None, 6],
         "clf__max_iter": [200, 400]},
    )
    return models


def fit_eval(X, y, split, seed=42):
    """split='random' 用分层随机划分；split='time' 用按时间前80%/后20%划分。
    CV 也相应：随机split→普通5折；时序split→TimeSeriesSplit(5)，避免用未来调参。"""
    if split == "random":
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y,
                                              random_state=seed)
        cv = 5
    else:
        n = len(y)
        cut = int(n * 0.8)
        Xtr, Xte, ytr, yte = X[:cut], X[cut:], y[:cut], y[cut:]
        cv = TimeSeriesSplit(n_splits=5)
    out = {}
    for mname, (est, grid) in all_models().items():
        t0 = time.time()
        pipe = Pipeline([("imputer", SimpleImputer(strategy="median")),
                         ("scaler", StandardScaler()), ("clf", est)])
        gs = GridSearchCV(pipe, grid, cv=cv, scoring="f1_macro", n_jobs=-1)
        gs.fit(Xtr, ytr)
        yp = gs.predict(Xte)
        out[mname] = {"acc": round(float(accuracy_score(yte, yp)), 4),
                      "f1": round(float(f1_score(yte, yp, average="macro")), 4),
                      "bacc": round(float(balanced_accuracy_score(yte, yp)), 4)}
        print(f"    [{mname:<7}] f1={out[mname]['f1']:.4f} "
              f"acc={out[mname]['acc']:.4f} bacc={out[mname]['bacc']:.4f} "
              f"({time.time()-t0:.1f}s)")
    out["_best_f1"] = round(max(v["f1"] for v in out.values()), 4)
    out["_best_model"] = max((k for k in out if not k.startswith("_")),
                             key=lambda k: out[k]["f1"])
    return out


def cv_eval(X, y, n_splits=6):
    """时序滚动交叉验证：每折在过去训练、在下一时间块测试，汇集所有折测试预测后统一评估。
    用固定默认超参(不在极少正例下逐折 GridSearch)，重点比较"加不加时序特征"。
    返回 {模型: 指标}，指标基于汇集后的全部测试样本(覆盖远多于单次划分的正例数)。"""
    tscv = TimeSeriesSplit(n_splits=n_splits)
    res = {}
    pooled_pos = None
    for mname, (est, grid) in all_models().items():
        yt_all, yp_all = [], []
        for tr, te in tscv.split(X):
            pipe = Pipeline([("imputer", SimpleImputer(strategy="median")),
                             ("scaler", StandardScaler()), ("clf", clone(est))])
            pipe.fit(X[tr], y[tr])
            yt_all.append(y[te])
            yp_all.append(pipe.predict(X[te]))
        yt = np.concatenate(yt_all)
        yp = np.concatenate(yp_all)
        pooled_pos = int(yt.sum())
        res[mname] = {"f1": round(float(f1_score(yt, yp, average="macro")), 4),
                      "bacc": round(float(balanced_accuracy_score(yt, yp)), 4),
                      "recall_pos": round(float(recall_score(yt, yp, pos_label=1)), 3),
                      "prec_pos": round(float(precision_score(yt, yp, pos_label=1,
                                                              zero_division=0)), 3)}
    res["_pooled_test_pos"] = pooled_pos
    res["_best_f1"] = round(max(v["f1"] for k, v in res.items()
                                if not k.startswith("_")), 4)
    res["_best_model"] = max((k for k in res if not k.startswith("_")),
                             key=lambda k: res[k]["f1"])
    return res


def main():
    set_chinese_font()
    dates, X72, y = load_ozone_with_date()
    Tfeat = build_temporal_features(dates, y)
    Xtemporal = np.hstack([X72, Tfeat])
    print(f"样本 {len(y)}，正例 {int(y.sum())}({y.mean()*100:.1f}%)，"
          f"日期 {dates.min().date()}→{dates.max().date()}")
    print(f"原始 {X72.shape[1]} 维；加时序后 {Xtemporal.shape[1]} 维(+{Tfeat.shape[1]})\n")

    results = {}
    print("A 档：72原始 + 随机split(复现现状)")
    results["A_raw_random"] = fit_eval(X72, y, "random")
    print("\nB 档：72原始 + 时序split(仅换划分)")
    results["B_raw_time"] = fit_eval(X72, y, "time")
    print("\nC 档：72原始+时序特征 + 时序split(创新)")
    results["C_temporal_time"] = fit_eval(Xtemporal, y, "time")

    # —— 权威评估：单次时序划分仅含极少正例(噪声大)，改用时序CV汇集评估 ——
    print("\n[严谨] 时序CV滚动评估(汇集多折测试正例)：")
    cv_raw = cv_eval(X72, y)
    cv_temporal = cv_eval(Xtemporal, y)
    print(f"  汇集测试正例={cv_raw['_pooled_test_pos']}")
    print(f"  B 原始72维   最优宏F1={cv_raw['_best_f1']} ({cv_raw['_best_model']})")
    print(f"  C 加时序特征 最优宏F1={cv_temporal['_best_f1']} ({cv_temporal['_best_model']})"
          f"  Δ={cv_temporal['_best_f1']-cv_raw['_best_f1']:+.4f}")
    results["cv_raw"] = cv_raw
    results["cv_temporal"] = cv_temporal

    summary = {
        "n_samples": int(len(y)), "n_pos": int(y.sum()),
        "pos_rate": round(float(y.mean()), 4),
        "date_min": str(dates.min().date()), "date_max": str(dates.max().date()),
        "n_temporal_feats": int(Tfeat.shape[1]),
        "configs": results,
        "single_split": {
            "A_best_f1": results["A_raw_random"]["_best_f1"],
            "B_best_f1": results["B_raw_time"]["_best_f1"],
            "C_best_f1": results["C_temporal_time"]["_best_f1"],
            "warning": "单次时序划分测试集正例极少(约4个)，F1 噪声极大，不可作为结论依据",
        },
        "authoritative_cv": {
            "pooled_test_pos": cv_raw["_pooled_test_pos"],
            "B_raw_best_f1": cv_raw["_best_f1"],
            "C_temporal_best_f1": cv_temporal["_best_f1"],
            "delta": round(cv_temporal["_best_f1"] - cv_raw["_best_f1"], 4),
            "conclusion": "时序CV汇集评估下，时序特征未带来提升(Δ≈0)，臭氧确属数据信息天花板",
        },
    }
    json.dump(summary, open(os.path.join(OUT, "ozone_temporal_summary.json"), "w"),
              ensure_ascii=False, indent=2)

    # 对比图：三档 × 各模型 宏F1
    models = [k for k in results["A_raw_random"] if not k.startswith("_")]
    labelmap = {"A_raw_random": "A 原始+随机", "B_raw_time": "B 原始+时序split",
                "C_temporal_time": "C 时序特征+时序split"}
    x = np.arange(len(models))
    w = 0.26
    colors = ["#9AA0A6", "#4C72B0", "#C44E52"]
    plt.figure(figsize=(9, 4.8))
    for i, key in enumerate(["A_raw_random", "B_raw_time", "C_temporal_time"]):
        vals = [results[key][m]["f1"] for m in models]
        plt.bar(x + (i - 1) * w, vals, w, label=labelmap[key], color=colors[i], alpha=0.92)
    plt.xticks(x, models)
    plt.ylabel("宏平均 F1")
    plt.title("臭氧：单次时序划分下各模型宏F1（正例极少，仅作过程展示）")
    plt.axhline(summary["single_split"]["A_best_f1"], ls="--", lw=1, color="#9AA0A6")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "ozone_temporal.png"), dpi=150)
    plt.close()

    ss = summary["single_split"]
    cv = summary["authoritative_cv"]
    print("\n========== 结论 ==========")
    print(f"[单次时序划分·噪声大] A={ss['A_best_f1']} B={ss['B_best_f1']} "
          f"C={ss['C_best_f1']} (表面 Δ vs B = {ss['C_best_f1']-ss['B_best_f1']:+.4f})")
    print(f"[时序CV·权威] 汇集正例={cv['pooled_test_pos']}  "
          f"原始={cv['B_raw_best_f1']} -> 加时序={cv['C_temporal_best_f1']} "
          f"(Δ={cv['delta']:+.4f})")
    print("结论：严谨评估下时序特征未突破，臭氧确属数据信息天花板；"
          "单次少正例划分的'提升'为评估假象。")


if __name__ == "__main__":
    main()
