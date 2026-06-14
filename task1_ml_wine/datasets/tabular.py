# -*- coding: utf-8 -*-
"""跨数据集对照的统一表格数据加载器。

把项目一从单一的白葡萄酒数据集，扩展到难度递增的多个结构化数据集，
用同一套传统机器学习模型对照，考察"什么决定模型性能"。

统一返回 (X: float ndarray, y: int ndarray, meta: dict)。缺失值在加载器内用中位数填充；
字符串标签做整数编码；Lending Club 仅取已结清贷款、剔除泄露列并分层抽样以保证可计算性。
"""
import os
import io
import zipfile
import numpy as np
import pandas as pd

from task1_ml_wine import DATA_DIR


def _meta(name, label_cn, X, y, class_names):
    counts = np.bincount(y)
    imb = float(counts.max() / max(counts.min(), 1))
    return {"name": name, "label": label_cn, "n_samples": int(X.shape[0]),
            "n_features": int(X.shape[1]), "n_classes": int(len(class_names)),
            "class_names": class_names, "class_counts": counts.tolist(),
            "imbalance_ratio": round(imb, 2),
            "minority_frac": round(float(counts.min() / counts.sum()), 4)}


def load_wine():
    """白葡萄酒质量：11 特征，质量分箱为 3 类(≤5 差 / =6 中 / ≥7 好)。"""
    df = pd.read_csv(os.path.join(DATA_DIR, "winequality-white.csv"), sep=";")
    q = df["quality"].to_numpy()
    y = np.where(q <= 5, 0, np.where(q == 6, 1, 2)).astype(int)
    X = df.drop(columns=["quality"]).to_numpy(dtype=float)
    return X, y, _meta("wine", "白葡萄酒 11维·3类", X, y, ["差", "中", "好"])


def load_ionosphere():
    """电离层雷达回波：34 特征，二分类(good/bad)。小样本、近线性可分。"""
    with zipfile.ZipFile(os.path.join(DATA_DIR, "ionosphere.zip")) as z:
        raw = z.read("ionosphere.data").decode("utf-8")
    df = pd.read_csv(io.StringIO(raw), header=None)
    y = (df.iloc[:, -1].map({"g": 1, "b": 0})).to_numpy(dtype=int)
    X = df.iloc[:, :-1].to_numpy(dtype=float)
    return X, y, _meta("ionosphere", "电离层 34维·2类", X, y, ["bad", "good"])


def load_ozone():
    """臭氧层超标检测(1 小时)：72 特征，二分类。极度不平衡(~3% 阳性)+缺失值。"""
    with zipfile.ZipFile(os.path.join(DATA_DIR, "Ozone Level Detection.zip")) as z:
        raw = z.read("onehr.data.csv").decode("utf-8")
    df = pd.read_csv(io.StringIO(raw), header=None, na_values="?")
    df = df.iloc[:, 1:]                      # 丢掉首列日期
    y = df.iloc[:, -1].to_numpy(dtype=int)
    # 保留 NaN，缺失值填充交给建模 Pipeline 中的 SimpleImputer，避免划分前用全量统计造成泄漏
    X = df.iloc[:, :-1].to_numpy(dtype=float)
    return X, y, _meta("ozone", "臭氧 72维·2类(极不平衡)", X, y, ["正常", "超标"])


def load_drybean():
    """干豆形态分类：16 特征，7 类。样本较大、特征干净。"""
    with zipfile.ZipFile(os.path.join(DATA_DIR, "DryBean Dataset.zip")) as z:
        raw = z.read("Dry_Bean_Dataset/Dry_Bean_Dataset.arff").decode("utf-8")
    rows, in_data = [], False
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.lower().startswith("@data"):
            in_data = True
            continue
        if in_data and not s.startswith("@"):
            rows.append(s.split(","))
    df = pd.DataFrame(rows)
    classes = sorted(df.iloc[:, -1].unique())
    cls_to_idx = {c: i for i, c in enumerate(classes)}
    y = df.iloc[:, -1].map(cls_to_idx).to_numpy(dtype=int)
    X = df.iloc[:, :-1].to_numpy(dtype=float)
    return X, y, _meta("drybean", "干豆 16维·7类", X, y, classes)


# Lending Club：仅用申请时可得的数值特征，避免用回款额等"事后泄露"列
_LC_FEATURES = ["loan_amnt", "int_rate", "installment", "annual_inc", "dti",
                "delinq_2yrs", "inq_last_6mths", "open_acc", "pub_rec",
                "revol_bal", "revol_util", "total_acc"]
# rich 模式额外纳入的申请时类别特征（grade 为 LC 自有风险评级，强信号）
_LC_CAT = ["term", "grade", "sub_grade", "emp_length", "home_ownership",
           "verification_status", "purpose"]


# 固定类别域：独热编码用此列表，避免“从全量数据得知所有类别”造成的泄漏
_LC_SUBGRADES = [f"{g}{i}" for g in "ABCDEFG" for i in range(1, 6)]
_LC_HOME = ["ANY", "MORTGAGE", "NONE", "OTHER", "OWN", "RENT"]
_LC_PURPOSE = ["car", "credit_card", "debt_consolidation", "educational",
               "home_improvement", "house", "major_purchase", "medical", "moving",
               "other", "renewable_energy", "small_business", "vacation", "wedding"]


def _lc_encode_categoricals(df):
    """把 Lending Club 的类别特征编码为数值/独热（均用固定域，无数据泄漏）。"""
    out = pd.DataFrame(index=df.index)
    out["term_months"] = df["term"].str.extract(r"(\d+)").astype(float)
    out["grade_ord"] = df["grade"].map({g: i for i, g in enumerate("ABCDEFG")})
    out["subgrade_ord"] = df["sub_grade"].map({s: i for i, s in enumerate(_LC_SUBGRADES)})
    emp_map = {"< 1 year": 0, "1 year": 1, "2 years": 2, "3 years": 3, "4 years": 4,
               "5 years": 5, "6 years": 6, "7 years": 7, "8 years": 8, "9 years": 9,
               "10+ years": 10}
    out["emp_len"] = df["emp_length"].map(emp_map)
    out["verif_ord"] = df["verification_status"].map(
        {"Not Verified": 0, "Source Verified": 1, "Verified": 2})
    # 用固定类别域做独热，列结构不依赖于具体样本集合
    home = pd.Categorical(df["home_ownership"].astype(str), categories=_LC_HOME)
    purp = pd.Categorical(df["purpose"].astype(str), categories=_LC_PURPOSE)
    oh = pd.concat([pd.get_dummies(home, prefix="home", dtype=float),
                    pd.get_dummies(purp, prefix="purpose", dtype=float)], axis=1)
    oh.index = df.index
    return pd.concat([out, oh], axis=1)


def load_lendingclub(subsample=30000, seed=42, rich=False):
    """贷款违约预测：从 1.19GB loan.csv 流式读取，仅取已结清贷款做二分类
    (Fully Paid=0 良 / Charged Off=1 违约)，剔除回款额等事后泄露列，分层抽样到 subsample 行。
    rich=True 时额外纳入 grade/期限/工龄等申请时类别特征。"""
    zip_path = os.path.join(DATA_DIR, "Lending Club Loan Data.zip")
    keep_status = {"Fully Paid": 0, "Charged Off": 1}
    usecols = _LC_FEATURES + ["loan_status"] + (_LC_CAT if rich else [])
    parts = []
    with zipfile.ZipFile(zip_path) as z:
        with z.open("loan.csv") as f:
            for chunk in pd.read_csv(f, chunksize=200000, usecols=usecols,
                                     low_memory=False):
                chunk = chunk[chunk["loan_status"].isin(keep_status)]
                if len(chunk):
                    parts.append(chunk)
    df = pd.concat(parts, ignore_index=True)
    y_all = df["loan_status"].map(keep_status).to_numpy(dtype=int)
    num = df[_LC_FEATURES].apply(pd.to_numeric, errors="coerce")
    if rich:
        feat = pd.concat([num, _lc_encode_categoricals(df)], axis=1)
        label = f"贷款违约 {feat.shape[1]}维·2类(含类别特征)"
    else:
        feat, label = num, "贷款违约 12维·2类(大规模)"
    # 保留 NaN，缺失值填充交给建模 Pipeline 的 SimpleImputer
    X_all = feat.to_numpy(dtype=float)
    if subsample and X_all.shape[0] > subsample:
        from sklearn.model_selection import train_test_split
        X_all, _, y_all, _ = train_test_split(
            X_all, y_all, train_size=subsample, stratify=y_all, random_state=seed)
    return X_all, y_all, _meta("lendingclub", label, X_all, y_all, ["良", "违约"])


LOADERS = {
    "ionosphere": load_ionosphere,
    "wine": load_wine,
    "ozone": load_ozone,
    "drybean": load_drybean,
    "lendingclub": load_lendingclub,
}


if __name__ == "__main__":
    import sys
    names = sys.argv[1:] or list(LOADERS)
    for n in names:
        X, y, meta = LOADERS[n]()
        print(f"[{n}] X={X.shape} y类别={np.bincount(y).tolist()} "
              f"不平衡比={meta['imbalance_ratio']} 少数类占比={meta['minority_frac']} "
              f"含NaN={bool(np.isnan(X).any())}")
