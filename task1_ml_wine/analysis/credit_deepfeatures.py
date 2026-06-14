# -*- coding: utf-8 -*-
"""贷款违约的"信息侧"创新：把原始 145 列中被弃用的申请时征信特征用起来。

动机：基线仅用 12 个数值特征，而 loan.csv 实含约 145 列，其中数十个是【申请时即可获得的征信
行为特征】(逾期recency、卡使用率、账户年龄、严重逾期账户数、破产记录等)，与 int_rate 并不冗余，
却被基线丢弃。本实验在严格排除【放款后/结果泄漏列】的前提下纳入这些特征，直接检验贷款违约的
"天花板"究竟是数据本身的，还是此前只用 12 列自我设限造成的。

评估：分层 5 折交叉验证(报告各模型 CV 宏平均 F1)，对比 12 维基线 vs 完整征信特征。
输出：outputs/credit_deepfeatures_summary.json、outputs/credit_deepfeatures.png
"""
import os
import sys
import json
import zipfile
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from common.zh_font import set_chinese_font
from task1_ml_wine.models import build_models
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import HistGradientBoostingClassifier

from task1_ml_wine import OUT_DIR as OUT
from task1_ml_wine import DATA_DIR

BASE12 = ["loan_amnt", "int_rate", "installment", "annual_inc", "dti",
          "delinq_2yrs", "inq_last_6mths", "open_acc", "pub_rec",
          "revol_bal", "revol_util", "total_acc"]

# 申请时即可获得的征信行为特征(非泄漏)——基线未用、与 int_rate 不冗余
EXTRA_NUM = [
    "mths_since_last_delinq", "mths_since_last_record", "mths_since_last_major_derog",
    "collections_12_mths_ex_med", "acc_now_delinq", "tot_coll_amt", "tot_cur_bal",
    "total_rev_hi_lim", "acc_open_past_24mths", "avg_cur_bal", "bc_open_to_buy",
    "bc_util", "chargeoff_within_12_mths", "delinq_amnt", "mo_sin_old_il_acct",
    "mo_sin_old_rev_tl_op", "mo_sin_rcnt_rev_tl_op", "mo_sin_rcnt_tl", "mort_acc",
    "mths_since_recent_bc", "mths_since_recent_inq", "num_accts_ever_120_pd",
    "num_actv_bc_tl", "num_actv_rev_tl", "num_bc_sats", "num_bc_tl", "num_il_tl",
    "num_op_rev_tl", "num_rev_accts", "num_rev_tl_bal_gt_0", "num_sats",
    "num_tl_120dpd_2m", "num_tl_30dpd", "num_tl_90g_dpd_24m", "num_tl_op_past_12m",
    "pct_tl_nvr_dlq", "percent_bc_gt_75", "pub_rec_bankruptcies", "tax_liens",
    "tot_hi_cred_lim", "total_bal_ex_mort", "total_bc_limit", "total_il_high_credit_limit",
]
# 用于派生"信用历史长度"(申请时可知)：issue_d - earliest_cr_line
DATE_COLS = ["earliest_cr_line", "issue_d"]
KEEP_STATUS = {"Fully Paid": 0, "Charged Off": 1}


def load_rich(subsample=30000, seed=42):
    usecols = list(dict.fromkeys(BASE12 + EXTRA_NUM + DATE_COLS + ["loan_status"]))
    parts = []
    with zipfile.ZipFile(os.path.join(DATA_DIR, "Lending Club Loan Data.zip")) as z:
        with z.open("loan.csv") as f:
            for chunk in pd.read_csv(f, chunksize=200000, usecols=usecols, low_memory=False):
                chunk = chunk[chunk["loan_status"].isin(KEEP_STATUS)]
                if len(chunk):
                    parts.append(chunk)
    df = pd.concat(parts, ignore_index=True)
    y = df["loan_status"].map(KEEP_STATUS).to_numpy(dtype=int)
    num = df[BASE12 + EXTRA_NUM].apply(pd.to_numeric, errors="coerce")
    # 派生信用历史长度(月)：申请时可知，不泄漏
    cr = pd.to_datetime(df["earliest_cr_line"], format="%b-%Y", errors="coerce")
    iss = pd.to_datetime(df["issue_d"], format="%b-%Y", errors="coerce")
    num["credit_age_months"] = (iss - cr).dt.days / 30.0
    X = num.to_numpy(dtype=float)
    base_idx = list(range(len(BASE12)))
    if subsample and X.shape[0] > subsample:
        from sklearn.model_selection import train_test_split
        X, _, y, _ = train_test_split(X, y, train_size=subsample, stratify=y, random_state=seed)
    return X, y, base_idx, list(num.columns)


def models_with_gbdt():
    m = dict(build_models())
    m["GBDT"] = (HistGradientBoostingClassifier(random_state=42, class_weight="balanced",
                                                early_stopping=True),
                 {"clf__learning_rate": [0.1], "clf__max_iter": [300]})
    return m


def cv_f1(X, y):
    """各模型分层5折 CV 宏F1(取每模型的均值)，返回 {模型: (mean, std)} 与最优。"""
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    res = {}
    for name, (est, grid) in models_with_gbdt().items():
        # 用网格中第一组合即可(此处重点比信息量而非调参)，构造单一估计器
        est2 = est.set_params(**{k.replace("clf__", ""): v[0] for k, v in grid.items()}) \
            if grid else est
        pipe = Pipeline([("imputer", SimpleImputer(strategy="median")),
                         ("scaler", StandardScaler()), ("clf", est2)])
        s = cross_val_score(pipe, X, y, cv=skf, scoring="f1_macro", n_jobs=-1)
        res[name] = (round(float(s.mean()), 4), round(float(s.std()), 4))
        print(f"    {name:<7} CV宏F1 = {s.mean():.4f} ± {s.std():.4f}")
    best = max(res, key=lambda k: res[k][0])
    return res, best


def main():
    set_chinese_font()
    X, y, base_idx, names = load_rich()
    Xbase = X[:, base_idx]
    print(f"样本 {X.shape[0]}，违约率 {y.mean()*100:.1f}%；"
          f"基线 {len(base_idx)} 维 -> 完整 {X.shape[1]} 维(+{X.shape[1]-len(base_idx)})\n")

    print("[基线 12 维] 分层5折CV：")
    base_res, base_best = cv_f1(Xbase, y)
    print(f"\n[完整征信特征 {X.shape[1]} 维] 分层5折CV：")
    full_res, full_best = cv_f1(X, y)

    delta = round(full_res[full_best][0] - base_res[base_best][0], 4)
    summary = {
        "n_samples": int(X.shape[0]), "default_rate": round(float(y.mean()), 4),
        "n_base": len(base_idx), "n_full": X.shape[1],
        "base": {k: {"f1_mean": v[0], "f1_std": v[1]} for k, v in base_res.items()},
        "full": {k: {"f1_mean": v[0], "f1_std": v[1]} for k, v in full_res.items()},
        "base_best": {"model": base_best, "f1": base_res[base_best][0]},
        "full_best": {"model": full_best, "f1": full_res[full_best][0]},
        "delta_best_f1": delta,
        "feature_names": names,
    }
    json.dump(summary, open(os.path.join(OUT, "credit_deepfeatures_summary.json"), "w"),
              ensure_ascii=False, indent=2)

    # 对比图
    ms = list(base_res.keys())
    x = np.arange(len(ms)); w = 0.38
    plt.figure(figsize=(8.4, 4.8))
    plt.bar(x - w/2, [base_res[m][0] for m in ms], w, yerr=[base_res[m][1] for m in ms],
            capsize=4, label=f"基线 {len(base_idx)} 维", color="#9AA0A6")
    plt.bar(x + w/2, [full_res[m][0] for m in ms], w, yerr=[full_res[m][1] for m in ms],
            capsize=4, label=f"完整征信 {X.shape[1]} 维", color="#C44E52")
    plt.xticks(x, ms); plt.ylabel("分层5折 CV 宏平均 F1")
    plt.title("贷款违约：纳入被弃用的申请时征信特征前后对比")
    plt.legend(); plt.tight_layout()
    plt.savefig(os.path.join(OUT, "credit_deepfeatures.png"), dpi=150)
    plt.close()

    print("\n========== 结论 ==========")
    print(f"基线 {len(base_idx)} 维最优：{base_best} CV宏F1 = {base_res[base_best][0]}")
    print(f"完整 {X.shape[1]} 维最优：{full_best} CV宏F1 = {full_res[full_best][0]}")
    print(f"Δ = {delta:+.4f}  ->  ", "突破！信息侧确有余量" if delta >= 0.02
          else "仍未突破：贷款违约确属数据信息天花板")


if __name__ == "__main__":
    main()
