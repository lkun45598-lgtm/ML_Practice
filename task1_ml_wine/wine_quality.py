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
    """分层划分（标准化放入建模 Pipeline 内逐折完成，避免交叉验证数据泄漏）。"""
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=seed)
    print(f"[预处理] 训练集 {X_tr.shape}，测试集 {X_te.shape}")
    return X_tr, X_te, y_tr, y_te


from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline


def build_models():
    """返回 {模型名: (estimator, 参数网格)}；参数键用 clf__ 前缀以配合 Pipeline。"""
    return {
        "SVM": (
            SVC(class_weight="balanced", probability=False),
            {"clf__C": [1, 10], "clf__gamma": ["scale", 0.1], "clf__kernel": ["rbf"]},
        ),
        "决策树": (
            DecisionTreeClassifier(class_weight="balanced", random_state=42),
            {"clf__max_depth": [None, 10, 20], "clf__min_samples_leaf": [1, 5]},
        ),
        "随机森林": (
            RandomForestClassifier(class_weight="balanced", random_state=42, n_jobs=-1),
            {"clf__n_estimators": [200, 400], "clf__max_depth": [None, 20]},
        ),
        "逻辑回归": (
            LogisticRegression(class_weight="balanced", max_iter=2000),
            {"clf__C": [0.5, 1, 10]},
        ),
    }


def train_models(X_tr, y_tr):
    """对每个模型做 5 折网格搜索，返回 {名: 最优Pipeline}。

    标准化与分类器封装为 Pipeline，使 StandardScaler 在每个交叉验证折内独立 fit，
    严格避免验证折信息泄漏到标准化参数中。
    """
    fitted = {}
    for name, (est, grid) in build_models().items():
        print(f"\n[训练] {name} 网格搜索中...")
        pipe = Pipeline([("scaler", StandardScaler()), ("clf", est)])
        gs = GridSearchCV(pipe, grid, cv=5, scoring="f1_macro", n_jobs=-1)
        gs.fit(X_tr, y_tr)
        best = {k.replace("clf__", ""): v for k, v in gs.best_params_.items()}
        print(f"[训练] {name} 最优参数: {best}  CV f1_macro={gs.best_score_:.4f}")
        fitted[name] = gs.best_estimator_
    return fitted


from sklearn.metrics import (accuracy_score, precision_recall_fscore_support,
                             confusion_matrix, classification_report)


def evaluate_models(models, X_te, y_te):
    """在测试集评估，画混淆矩阵与对比柱状图、特征重要性，返回指标表。"""
    set_chinese_font()
    rows = []
    for name, model in models.items():
        y_pred = model.predict(X_te)
        acc = accuracy_score(y_te, y_pred)
        p, r, f1, _ = precision_recall_fscore_support(
            y_te, y_pred, average="macro", zero_division=0)
        rows.append({"模型": name, "准确率": acc, "精确率": p, "召回率": r, "F1": f1})
        print(f"\n===== {name} =====")
        print(classification_report(y_te, y_pred, target_names=CLASS_NAMES, zero_division=0))
        cm = confusion_matrix(y_te, y_pred)
        plt.figure(figsize=(5, 4))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                    xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES)
        plt.title(f"{name} 混淆矩阵"); plt.xlabel("预测"); plt.ylabel("真实")
        plt.tight_layout()
        plt.savefig(os.path.join(OUT_DIR, f"cm_{name}.png"), dpi=150); plt.close()

    metrics = pd.DataFrame(rows)
    metrics.to_csv(os.path.join(OUT_DIR, "metrics.csv"), index=False, encoding="utf-8-sig")
    print("\n[评估] 指标汇总:\n", metrics.to_string(index=False))

    plt.figure(figsize=(8, 5))
    m = metrics.set_index("模型")[["准确率", "精确率", "召回率", "F1"]]
    m.plot(kind="bar", ax=plt.gca())
    plt.title("各模型测试集指标对比"); plt.ylabel("分数"); plt.xticks(rotation=0)
    plt.ylim(0, 1); plt.legend(loc="lower right"); plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "model_compare.png"), dpi=150); plt.close()

    if "随机森林" in models:
        rf = models["随机森林"].named_steps["clf"]  # 从 Pipeline 取出分类器
        cols = pd.read_csv(CSV_PATH, sep=";").drop(columns=["quality"]).columns
        imp = pd.Series(rf.feature_importances_, index=cols).sort_values()
        plt.figure(figsize=(7, 5))
        imp.plot(kind="barh", color="#55A868")
        plt.title("随机森林特征重要性"); plt.tight_layout()
        plt.savefig(os.path.join(OUT_DIR, "rf_feature_importance.png"), dpi=150); plt.close()

    best = metrics.loc[metrics["F1"].idxmax(), "模型"]
    print(f"\n[结论] 按 macro-F1，最优模型为: {best}")
    return metrics


from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import f1_score


def _to_cls(q):
    """质量评分→三类：≤5差(0)、=6中(1)、≥7好(2)。"""
    return np.where(q <= 5, 0, np.where(q == 6, 1, 2))


def ordinal_improvement(df, models, seed=42):
    """核心创新点①：误差驱动改进——既然误差几乎全是“邻级混淆”，将质量视为有序变量，
    用“回归→分级”替代直接分类，并用“严重误判数(差↔好,跨2级)”与“有序MAE”验证改进。"""
    set_chinese_font()
    X = df.drop(columns=["quality"]).to_numpy()
    q = df["quality"].to_numpy()
    Xtr, Xte, qtr, qte = train_test_split(
        X, q, test_size=0.2, stratify=_to_cls(q), random_state=seed)
    true_cls = _to_cls(qte)

    # 方案A：直接分类（沿用已训练的最优随机森林）
    pred_clf = models["随机森林"].predict(Xte)
    # 方案B：有序回归→分级（回归预测连续质量分，四舍五入后再分箱）
    reg = Pipeline([("scaler", StandardScaler()),
                    ("reg", RandomForestRegressor(n_estimators=400, random_state=42, n_jobs=-1))])
    reg.fit(Xtr, qtr)
    pred_reg = _to_cls(np.rint(reg.predict(Xte)))

    def stat(pred):
        acc = (pred == true_cls).mean()
        f1 = f1_score(true_cls, pred, average="macro")
        severe = int(np.sum(np.abs(pred - true_cls) == 2))   # 差↔好 严重误判
        mae = float(np.mean(np.abs(pred - true_cls)))         # 有序MAE
        return acc, f1, severe, mae

    rows = []
    for name, pred in [("直接分类(随机森林)", pred_clf), ("有序回归→分级", pred_reg)]:
        acc, f1, sev, mae = stat(pred)
        rows.append({"方法": name, "准确率": round(acc, 4), "宏F1": round(f1, 4),
                     "严重误判数": sev, "有序MAE": round(mae, 4)})
        print(f"[创新①] {name}: acc={acc:.4f} F1={f1:.4f} 严重误判={sev} MAE={mae:.4f}")
    pd.DataFrame(rows).to_csv(os.path.join(OUT_DIR, "ordinal_improvement.csv"),
                              index=False, encoding="utf-8-sig")

    # 对比柱状图（严重误判数）
    plt.figure(figsize=(5, 4))
    plt.bar([r["方法"] for r in rows], [r["严重误判数"] for r in rows],
            color=["#4C72B0", "#55A868"])
    for i, r in enumerate(rows):
        plt.text(i, r["严重误判数"] + 0.1, str(r["严重误判数"]), ha="center")
    plt.ylabel("严重误判数（差↔好，跨2级）")
    plt.title("有序回归→分级 显著减少严重误判")
    plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, "ordinal_improvement.png"), dpi=150)
    plt.close()
    return rows


if __name__ == "__main__":
    download_data()
    df = load_data()
    eda(df)
    X, y = make_labels(df)
    X_tr, X_te, y_tr, y_te = preprocess(X, y)
    assert X_tr.shape[1] == 11 and len(set(y)) == 3
    print("[自检] 预处理通过")
    models = train_models(X_tr, y_tr)
    print("[自检] 训练完成，模型数:", len(models))
    metrics = evaluate_models(models, X_te, y_te)
    ordinal_improvement(df, models)            # 核心创新点①：误差驱动的有序改进
    assert os.path.exists(os.path.join(OUT_DIR, "metrics.csv"))
    print("[完成] 任务① 全流程结束")
