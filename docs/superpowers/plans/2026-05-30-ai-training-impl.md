# 人工智能综合实训Ⅱ 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成两个机器学习项目——红酒质量多分类（4个传统ML模型对比）与逐层手写 AlexNet 在 Fashion-MNIST 上的图像分类——并产出图表、指标与一份学校格式的 Word 论文。

**Architecture:** 两个互相独立的子项目目录，各自包含可独立运行的脚本，产出落到各自 `outputs/`。任务①为单脚本完整管线；任务②拆分为模型定义/训练/评估三个模块。最后汇总结果撰写论文。

**Tech Stack:** Python 3.12（conda `pytorch312`），sklearn 1.8、pandas、matplotlib、seaborn；PyTorch 2.7 + CUDA（单卡 RTX 4090）；torchvision 仅用于数据集下载与变换（**不**用其预置 AlexNet）。

**统一约定：**
- 解释器：`PY=/home/lz/miniconda3/envs/pytorch312/bin/python`
- 工作目录：`/data1/user/lz/ML_Practice`
- 所有代码中文注释；中文绘图需设置中文字体回退（见 Task 1 步骤）。
- 提交用本地仓库身份：`git -c user.name="lkun45598" -c user.email="lkun45598@local" commit ...`

---

## Phase 0 — 脚手架

### Task 0: 创建目录结构与依赖检查

**Files:**
- Create: `task1_ml_wine/`, `task2_alexnet_fmnist/`, `report/`（目录）
- Create: `requirements.txt`
- Create: `common/zh_font.py`

- [ ] **Step 1: 创建目录**

```bash
cd /data1/user/lz/ML_Practice
mkdir -p task1_ml_wine/data task1_ml_wine/outputs \
         task2_alexnet_fmnist/data task2_alexnet_fmnist/outputs \
         report common
```

- [ ] **Step 2: 写依赖清单**

Create `requirements.txt`:
```
torch>=2.5
torchvision>=0.20
scikit-learn>=1.7
pandas>=2.0
numpy
matplotlib
seaborn
```

- [ ] **Step 3: 写中文字体辅助模块**

Create `common/zh_font.py`:
```python
"""matplotlib 中文显示设置：尝试常见中文字体，找不到则回退并提示。"""
import matplotlib
import matplotlib.font_manager as fm


def set_chinese_font():
    """设置 matplotlib 支持中文，返回所用字体名（找不到返回 None）。"""
    candidates = ["WenQuanYi Zen Hei", "WenQuanYi Micro Hei", "Noto Sans CJK SC",
                  "Source Han Sans SC", "SimHei", "Microsoft YaHei", "Droid Sans Fallback"]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            matplotlib.rcParams["font.sans-serif"] = [name]
            matplotlib.rcParams["axes.unicode_minus"] = False
            return name
    # 回退：仍设负号正常，标题尽量用英文避免乱码
    matplotlib.rcParams["axes.unicode_minus"] = False
    print("[警告] 未找到中文字体，图中中文可能显示为方块。")
    return None
```

- [ ] **Step 4: 验证环境**

Run:
```bash
PY=/home/lz/miniconda3/envs/pytorch312/bin/python
$PY -c "import torch,torchvision,sklearn,pandas,matplotlib,seaborn,numpy; print('torch',torch.__version__,'cuda',torch.cuda.is_available()); print('sklearn',sklearn.__version__)"
$PY -c "from common.zh_font import set_chinese_font; print('font:', set_chinese_font())"
```
Expected: 打印 torch 版本且 `cuda True`；font 行打印字体名或警告。若缺 seaborn：`$PY -m pip install seaborn`。

- [ ] **Step 5: 提交**

```bash
git add requirements.txt common/zh_font.py .gitignore
git -c user.name="lkun45598" -c user.email="lkun45598@local" commit -m "chore: 项目脚手架与中文字体辅助"
```

---

## Phase 1 — 任务① 红酒质量机器学习

单脚本 `task1_ml_wine/wine_quality.py`，分步骤逐渐充实；每步跑通后提交。

### Task 1: 数据下载与加载/EDA

**Files:**
- Create: `task1_ml_wine/wine_quality.py`

- [ ] **Step 1: 写下载+加载+EDA 代码**

Create `task1_ml_wine/wine_quality.py`:
```python
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
    # quality 分布
    plt.figure(figsize=(6, 4))
    sns.countplot(x="quality", data=df, color="#4C72B0")
    plt.title("葡萄酒质量评分分布")
    plt.xlabel("质量评分"); plt.ylabel("样本数")
    plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, "eda_quality_dist.png"), dpi=150)
    plt.close()
    # 相关性热力图
    plt.figure(figsize=(10, 8))
    sns.heatmap(df.corr(), annot=True, fmt=".2f", cmap="coolwarm", square=True,
                cbar_kws={"shrink": .8}, annot_kws={"size": 7})
    plt.title("特征相关性热力图")
    plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, "eda_corr_heatmap.png"), dpi=150)
    plt.close()
    print(f"[EDA] 图已保存到 {OUT_DIR}")


if __name__ == "__main__":
    download_data()
    df = load_data()
    eda(df)
```

- [ ] **Step 2: 运行验证**

Run:
```bash
cd /data1/user/lz/ML_Practice
/home/lz/miniconda3/envs/pytorch312/bin/python task1_ml_wine/wine_quality.py
```
Expected: 打印形状 `(4898, 12)`，缺失值 0，quality 分布；`task1_ml_wine/outputs/` 出现 `eda_quality_dist.png` 与 `eda_corr_heatmap.png`。

- [ ] **Step 3: 提交**

```bash
git add task1_ml_wine/wine_quality.py
git -c user.name="lkun45598" -c user.email="lkun45598@local" commit -m "feat(task1): 红酒数据下载/加载/EDA"
```

### Task 2: 预处理（分箱、标准化、划分）

**Files:**
- Modify: `task1_ml_wine/wine_quality.py`

- [ ] **Step 1: 追加预处理函数**

在 `wine_quality.py` 的 `eda` 之后、`__main__` 之前插入：
```python
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
```

- [ ] **Step 2: 在 `__main__` 中调用并自检**

把 `__main__` 改为：
```python
if __name__ == "__main__":
    download_data()
    df = load_data()
    eda(df)
    X, y = make_labels(df)
    X_tr, X_te, y_tr, y_te, scaler = preprocess(X, y)
    assert X_tr.shape[1] == 11 and len(set(y)) == 3
    print("[自检] 预处理通过")
```

- [ ] **Step 3: 运行验证**

Run: `/home/lz/miniconda3/envs/pytorch312/bin/python task1_ml_wine/wine_quality.py`
Expected: 打印三分类标签分布（三个非零计数）、训练/测试形状、`[自检] 预处理通过`。

- [ ] **Step 4: 提交**

```bash
git add task1_ml_wine/wine_quality.py
git -c user.name="lkun45598" -c user.email="lkun45598@local" commit -m "feat(task1): 标签分箱与标准化预处理"
```

### Task 3: 四模型训练与调参

**Files:**
- Modify: `task1_ml_wine/wine_quality.py`

- [ ] **Step 1: 追加建模函数**

在 `preprocess` 之后插入：
```python
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV


def build_models():
    """返回 {模型名: (estimator, 参数网格)}，统一类别加权处理不平衡。"""
    return {
        "SVM": (
            SVC(class_weight="balanced", probability=False),
            {"C": [1, 10], "gamma": ["scale", 0.1], "kernel": ["rbf"]},
        ),
        "决策树": (
            DecisionTreeClassifier(class_weight="balanced", random_state=42),
            {"max_depth": [None, 10, 20], "min_samples_leaf": [1, 5]},
        ),
        "随机森林": (
            RandomForestClassifier(class_weight="balanced", random_state=42, n_jobs=-1),
            {"n_estimators": [200, 400], "max_depth": [None, 20]},
        ),
        "逻辑回归": (
            LogisticRegression(class_weight="balanced", max_iter=2000, multi_class="auto"),
            {"C": [0.5, 1, 10]},
        ),
    }


def train_models(X_tr, y_tr):
    """对每个模型做 5 折网格搜索，返回 {名: 最优estimator}。"""
    fitted = {}
    for name, (est, grid) in build_models().items():
        print(f"\n[训练] {name} 网格搜索中...")
        gs = GridSearchCV(est, grid, cv=5, scoring="f1_macro", n_jobs=-1)
        gs.fit(X_tr, y_tr)
        print(f"[训练] {name} 最优参数: {gs.best_params_}  CV f1_macro={gs.best_score_:.4f}")
        fitted[name] = gs.best_estimator_
    return fitted
```

- [ ] **Step 2: 在 `__main__` 调用**

在 `print("[自检] 预处理通过")` 之后追加：
```python
    models = train_models(X_tr, y_tr)
    print("[自检] 训练完成，模型数:", len(models))
```

- [ ] **Step 3: 运行验证**

Run: `/home/lz/miniconda3/envs/pytorch312/bin/python task1_ml_wine/wine_quality.py`
Expected: 四个模型各打印最优参数与 CV 分数；末尾 `模型数: 4`。（耗时约 1-3 分钟）

- [ ] **Step 4: 提交**

```bash
git add task1_ml_wine/wine_quality.py
git -c user.name="lkun45598" -c user.email="lkun45598@local" commit -m "feat(task1): 四模型网格搜索训练"
```

### Task 4: 评估、可视化与结论

**Files:**
- Modify: `task1_ml_wine/wine_quality.py`

- [ ] **Step 1: 追加评估函数**

在 `train_models` 之后插入：
```python
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
        # 混淆矩阵
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

    # 模型对比柱状图
    plt.figure(figsize=(8, 5))
    m = metrics.set_index("模型")[["准确率", "精确率", "召回率", "F1"]]
    m.plot(kind="bar", ax=plt.gca())
    plt.title("各模型测试集指标对比"); plt.ylabel("分数"); plt.xticks(rotation=0)
    plt.ylim(0, 1); plt.legend(loc="lower right"); plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "model_compare.png"), dpi=150); plt.close()

    # 随机森林特征重要性
    if "随机森林" in models:
        rf = models["随机森林"]
        cols = pd.read_csv(CSV_PATH, sep=";").drop(columns=["quality"]).columns
        imp = pd.Series(rf.feature_importances_, index=cols).sort_values()
        plt.figure(figsize=(7, 5))
        imp.plot(kind="barh", color="#55A868")
        plt.title("随机森林特征重要性"); plt.tight_layout()
        plt.savefig(os.path.join(OUT_DIR, "rf_feature_importance.png"), dpi=150); plt.close()

    best = metrics.loc[metrics["F1"].idxmax(), "模型"]
    print(f"\n[结论] 按 macro-F1，最优模型为: {best}")
    return metrics
```

- [ ] **Step 2: 在 `__main__` 调用**

把 `print("[自检] 训练完成...")` 行之后改为：
```python
    metrics = evaluate_models(models, X_te, y_te)
    assert os.path.exists(os.path.join(OUT_DIR, "metrics.csv"))
    print("[完成] 任务① 全流程结束")
```

- [ ] **Step 3: 运行验证**

Run: `/home/lz/miniconda3/envs/pytorch312/bin/python task1_ml_wine/wine_quality.py`
Expected: 每模型 classification_report；指标汇总表；`outputs/` 下出现 `metrics.csv`、`model_compare.png`、`cm_*.png`、`rf_feature_importance.png`；末尾打印最优模型与 `[完成]`。

- [ ] **Step 4: 提交**

```bash
git add task1_ml_wine/wine_quality.py
git -c user.name="lkun45598" -c user.email="lkun45598@local" commit -m "feat(task1): 评估/可视化/结论，任务①完成"
```

---

## Phase 2 — 任务② 逐层手写 AlexNet

### Task 5: 逐层手写 AlexNet 模型

**Files:**
- Create: `task2_alexnet_fmnist/alexnet.py`

- [ ] **Step 1: 写模型（逐层定义，不调用预置 AlexNet）**

Create `task2_alexnet_fmnist/alexnet.py`:
```python
# -*- coding: utf-8 -*-
"""逐层手写的 AlexNet（输入 1x224x224）。仅用基础算子搭建，不调用 torchvision 预置模型。"""
import torch
import torch.nn as nn


class AlexNet(nn.Module):
    """经典 AlexNet 结构，按论文逐层手工组装。

    输入: (N, in_channels, 224, 224)
    输出: (N, num_classes)
    """

    def __init__(self, num_classes=10, in_channels=1, use_lrn=True):
        super().__init__()
        # ---- 特征提取：5 个卷积块 ----
        layers = []
        # Conv1: 1->96, 11x11, stride4, pad2 -> 96x55x55
        layers += [nn.Conv2d(in_channels, 96, kernel_size=11, stride=4, padding=2),
                   nn.ReLU(inplace=True)]
        if use_lrn:
            layers += [nn.LocalResponseNorm(size=5, alpha=1e-4, beta=0.75, k=2)]
        layers += [nn.MaxPool2d(kernel_size=3, stride=2)]            # -> 96x27x27
        # Conv2: 96->256, 5x5, pad2 -> 256x27x27
        layers += [nn.Conv2d(96, 256, kernel_size=5, padding=2),
                   nn.ReLU(inplace=True)]
        if use_lrn:
            layers += [nn.LocalResponseNorm(size=5, alpha=1e-4, beta=0.75, k=2)]
        layers += [nn.MaxPool2d(kernel_size=3, stride=2)]            # -> 256x13x13
        # Conv3: 256->384, 3x3, pad1
        layers += [nn.Conv2d(256, 384, kernel_size=3, padding=1),
                   nn.ReLU(inplace=True)]
        # Conv4: 384->384, 3x3, pad1
        layers += [nn.Conv2d(384, 384, kernel_size=3, padding=1),
                   nn.ReLU(inplace=True)]
        # Conv5: 384->256, 3x3, pad1 -> pool -> 256x6x6
        layers += [nn.Conv2d(384, 256, kernel_size=3, padding=1),
                   nn.ReLU(inplace=True),
                   nn.MaxPool2d(kernel_size=3, stride=2)]            # -> 256x6x6
        self.features = nn.Sequential(*layers)

        # ---- 分类器：3 个全连接 ----
        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(256 * 6 * 6, 4096), nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(4096, 4096), nn.ReLU(inplace=True),
            nn.Linear(4096, num_classes),
        )

    def forward(self, x):
        x = self.features(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x


if __name__ == "__main__":
    # 自检：前向输出形状应为 (2, 10)
    net = AlexNet(num_classes=10, in_channels=1)
    dummy = torch.randn(2, 1, 224, 224)
    out = net(dummy)
    n_param = sum(p.numel() for p in net.parameters())
    print("输出形状:", tuple(out.shape), "参数量:", f"{n_param/1e6:.1f}M")
    assert out.shape == (2, 10)
    print("[自检] AlexNet 前向通过")
```

- [ ] **Step 2: 运行验证**

Run: `/home/lz/miniconda3/envs/pytorch312/bin/python task2_alexnet_fmnist/alexnet.py`
Expected: 打印 `输出形状: (2, 10)`、参数量（约 58.3M）、`[自检] AlexNet 前向通过`。

- [ ] **Step 3: 提交**

```bash
git add task2_alexnet_fmnist/alexnet.py
git -c user.name="lkun45598" -c user.email="lkun45598@local" commit -m "feat(task2): 逐层手写 AlexNet 模型"
```

### Task 6: 数据加载模块

**Files:**
- Create: `task2_alexnet_fmnist/data.py`

- [ ] **Step 1: 写数据模块**

Create `task2_alexnet_fmnist/data.py`:
```python
# -*- coding: utf-8 -*-
"""Fashion-MNIST 数据加载：下载、变换(Resize224)、train/val/test 三划分。"""
import os
import torch
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")

CLASS_NAMES = ["T恤", "裤子", "套衫", "连衣裙", "外套",
               "凉鞋", "衬衫", "运动鞋", "包", "短靴"]

# Fashion-MNIST 单通道均值/方差
_MEAN, _STD = (0.2860,), (0.3530,)


def _transform():
    return transforms.Compose([
        transforms.Resize(224),
        transforms.ToTensor(),
        transforms.Normalize(_MEAN, _STD),
    ])


def get_loaders(batch_size=128, val_ratio=0.1, num_workers=4, subset=None, seed=42):
    """返回 (train_loader, val_loader, test_loader)。
    subset: 若给整数，仅取该数量训练样本用于冒烟测试。"""
    tf = _transform()
    full_train = datasets.FashionMNIST(DATA_DIR, train=True, download=True, transform=tf)
    test_set = datasets.FashionMNIST(DATA_DIR, train=False, download=True, transform=tf)

    if subset is not None:
        full_train = torch.utils.data.Subset(full_train, range(subset))
        test_set = torch.utils.data.Subset(test_set, range(min(subset, len(test_set))))

    n_val = int(len(full_train) * val_ratio)
    n_train = len(full_train) - n_val
    g = torch.Generator().manual_seed(seed)
    train_set, val_set = random_split(full_train, [n_train, n_val], generator=g)

    mk = lambda ds, sh: DataLoader(ds, batch_size=batch_size, shuffle=sh,
                                   num_workers=num_workers, pin_memory=True)
    return mk(train_set, True), mk(val_set, False), mk(test_set, False)


if __name__ == "__main__":
    tr, va, te = get_loaders(batch_size=8, subset=64)
    xb, yb = next(iter(tr))
    print("batch:", tuple(xb.shape), "标签样例:", yb[:8].tolist())
    assert xb.shape[1:] == (1, 224, 224)
    print("[自检] 数据加载通过；train/val/test 批数:", len(tr), len(va), len(te))
```

- [ ] **Step 2: 运行验证**

Run: `/home/lz/miniconda3/envs/pytorch312/bin/python task2_alexnet_fmnist/data.py`
Expected: 首次会下载 FashionMNIST；打印 `batch: (8, 1, 224, 224)`、`[自检] 数据加载通过`。

- [ ] **Step 3: 提交**

```bash
git add task2_alexnet_fmnist/data.py
git -c user.name="lkun45598" -c user.email="lkun45598@local" commit -m "feat(task2): Fashion-MNIST 数据加载模块"
```

### Task 7: 训练脚本（含冒烟测试）

**Files:**
- Create: `task2_alexnet_fmnist/train.py`

- [ ] **Step 1: 写训练脚本**

Create `task2_alexnet_fmnist/train.py`:
```python
# -*- coding: utf-8 -*-
"""训练手写 AlexNet：训练/验证循环，记录曲线，保存最优 checkpoint。"""
import os
import json
import argparse
import torch
import torch.nn as nn

from alexnet import AlexNet
from data import get_loaders

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "outputs")
os.makedirs(OUT_DIR, exist_ok=True)


def run_epoch(model, loader, criterion, optimizer, device, train=True):
    """跑一个 epoch，返回 (平均loss, 准确率)。train=False 时不更新参数。"""
    model.train(train)
    total, correct, loss_sum = 0, 0, 0.0
    torch.set_grad_enabled(train)
    for xb, yb in loader:
        xb, yb = xb.to(device), yb.to(device)
        if train:
            optimizer.zero_grad()
        out = model(xb)
        loss = criterion(out, yb)
        if train:
            loss.backward(); optimizer.step()
        loss_sum += loss.item() * xb.size(0)
        correct += (out.argmax(1) == yb).sum().item()
        total += xb.size(0)
    return loss_sum / total, correct / total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--batch-size", type=int, default=128)
    ap.add_argument("--lr", type=float, default=0.01)
    ap.add_argument("--subset", type=int, default=None, help="冒烟测试用样本数")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    device = torch.device(args.device)
    print(f"[训练] 设备={device} epochs={args.epochs} subset={args.subset}")
    train_loader, val_loader, _ = get_loaders(
        batch_size=args.batch_size, subset=args.subset)

    model = AlexNet(num_classes=10, in_channels=1).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.SGD(model.parameters(), lr=args.lr, momentum=0.9,
                                weight_decay=5e-4)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.1)

    history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}
    best_val = 0.0
    for ep in range(1, args.epochs + 1):
        tr_loss, tr_acc = run_epoch(model, train_loader, criterion, optimizer, device, True)
        va_loss, va_acc = run_epoch(model, val_loader, criterion, optimizer, device, False)
        scheduler.step()
        history["train_loss"].append(tr_loss); history["train_acc"].append(tr_acc)
        history["val_loss"].append(va_loss); history["val_acc"].append(va_acc)
        print(f"[epoch {ep:2d}] train loss={tr_loss:.4f} acc={tr_acc:.4f} | "
              f"val loss={va_loss:.4f} acc={va_acc:.4f}")
        if va_acc > best_val:
            best_val = va_acc
            torch.save(model.state_dict(), os.path.join(OUT_DIR, "alexnet_best.pt"))
            print(f"        ↳ 保存最优模型 (val_acc={va_acc:.4f})")

    with open(os.path.join(OUT_DIR, "history.json"), "w") as f:
        json.dump(history, f)
    print(f"[训练] 完成，最优 val_acc={best_val:.4f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 冒烟测试（小子集 2 epoch）**

Run:
```bash
cd /data1/user/lz/ML_Practice/task2_alexnet_fmnist
/home/lz/miniconda3/envs/pytorch312/bin/python train.py --subset 256 --epochs 2 --batch-size 64
```
Expected: 2 个 epoch 正常打印；`outputs/` 出现 `alexnet_best.pt` 与 `history.json`。无报错即通过。

- [ ] **Step 3: 提交**

```bash
cd /data1/user/lz/ML_Practice
git add task2_alexnet_fmnist/train.py
git -c user.name="lkun45598" -c user.email="lkun45598@local" commit -m "feat(task2): 训练脚本与冒烟测试"
```

### Task 8: 完整训练

**Files:**
- Modify: `task2_alexnet_fmnist/outputs/`（产物）

- [ ] **Step 1: 完整训练**

Run（后台运行，约十几分钟；可先用 1 张卡）：
```bash
cd /data1/user/lz/ML_Practice/task2_alexnet_fmnist
CUDA_VISIBLE_DEVICES=0 /home/lz/miniconda3/envs/pytorch312/bin/python train.py --epochs 15 --batch-size 128 --lr 0.01 2>&1 | tee outputs/train_log.txt
```
Expected: 15 个 epoch；val_acc 收敛到约 0.90+；保存 `alexnet_best.pt`、`history.json`、`train_log.txt`。

- [ ] **Step 2: 检查产物**

Run: `ls -lh outputs/alexnet_best.pt outputs/history.json`
Expected: 两文件均存在，checkpoint 约 200MB+。

- [ ] **Step 3: 提交日志（不提交大 checkpoint，已被 .gitignore）**

```bash
cd /data1/user/lz/ML_Practice
git add task2_alexnet_fmnist/outputs/history.json task2_alexnet_fmnist/outputs/train_log.txt
git -c user.name="lkun45598" -c user.email="lkun45598@local" commit -m "chore(task2): 完整训练日志与曲线数据"
```

### Task 9: 评估与可视化

**Files:**
- Create: `task2_alexnet_fmnist/evaluate.py`

- [ ] **Step 1: 写评估脚本**

Create `task2_alexnet_fmnist/evaluate.py`:
```python
# -*- coding: utf-8 -*-
"""评估手写 AlexNet：测试集指标、混淆矩阵、训练曲线、预测样例可视化。"""
import os
import json
import sys
import numpy as np
import torch
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (accuracy_score, precision_recall_fscore_support,
                             confusion_matrix, classification_report)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.zh_font import set_chinese_font
from alexnet import AlexNet
from data import get_loaders, CLASS_NAMES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "outputs")
CKPT = os.path.join(OUT_DIR, "alexnet_best.pt")


def plot_curves():
    """从 history.json 画训练/验证 loss 与 acc 曲线。"""
    with open(os.path.join(OUT_DIR, "history.json")) as f:
        h = json.load(f)
    epochs = range(1, len(h["train_loss"]) + 1)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].plot(epochs, h["train_loss"], label="训练"); ax[0].plot(epochs, h["val_loss"], label="验证")
    ax[0].set_title("损失曲线"); ax[0].set_xlabel("epoch"); ax[0].set_ylabel("loss"); ax[0].legend()
    ax[1].plot(epochs, h["train_acc"], label="训练"); ax[1].plot(epochs, h["val_acc"], label="验证")
    ax[1].set_title("准确率曲线"); ax[1].set_xlabel("epoch"); ax[1].set_ylabel("acc"); ax[1].legend()
    plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, "curves.png"), dpi=150); plt.close()


@torch.no_grad()
def evaluate(device):
    """在测试集预测，返回 (y_true, y_pred, 部分图像)。"""
    _, _, test_loader = get_loaders(batch_size=256)
    model = AlexNet(num_classes=10, in_channels=1).to(device)
    model.load_state_dict(torch.load(CKPT, map_location=device))
    model.eval()
    ys, ps, sample_imgs, sample_meta = [], [], None, None
    for xb, yb in test_loader:
        out = model(xb.to(device))
        pred = out.argmax(1).cpu()
        if sample_imgs is None:
            sample_imgs = xb[:12].cpu()
            sample_meta = (yb[:12].tolist(), pred[:12].tolist())
        ys.append(yb); ps.append(pred)
    return torch.cat(ys).numpy(), torch.cat(ps).numpy(), sample_imgs, sample_meta


def plot_samples(imgs, meta):
    """画 12 张预测样例（标题: 真/预测）。"""
    y_true, y_pred = meta
    plt.figure(figsize=(10, 6))
    for i in range(min(12, len(imgs))):
        plt.subplot(3, 4, i + 1)
        plt.imshow(imgs[i, 0], cmap="gray")
        c = "green" if y_true[i] == y_pred[i] else "red"
        plt.title(f"真:{CLASS_NAMES[y_true[i]]}\n预:{CLASS_NAMES[y_pred[i]]}", color=c, fontsize=8)
        plt.axis("off")
    plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, "samples.png"), dpi=150); plt.close()


def main():
    set_chinese_font()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    plot_curves()
    y_true, y_pred, imgs, meta = evaluate(device)
    acc = accuracy_score(y_true, y_pred)
    p, r, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="macro")
    print(f"[评估] 测试集 acc={acc:.4f} 精确率={p:.4f} 召回率={r:.4f} F1={f1:.4f}")
    print(classification_report(y_true, y_pred, target_names=CLASS_NAMES))

    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(8, 7))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES)
    plt.title("AlexNet 测试集混淆矩阵"); plt.xlabel("预测"); plt.ylabel("真实")
    plt.xticks(rotation=45, ha="right"); plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "confusion_matrix.png"), dpi=150); plt.close()

    plot_samples(imgs, meta)
    with open(os.path.join(OUT_DIR, "test_metrics.json"), "w") as f:
        json.dump({"acc": acc, "precision": p, "recall": r, "f1": f1}, f)
    print(f"[评估] 图与指标已保存到 {OUT_DIR}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行验证**

Run:
```bash
cd /data1/user/lz/ML_Practice/task2_alexnet_fmnist
/home/lz/miniconda3/envs/pytorch312/bin/python evaluate.py
```
Expected: 打印测试集 acc/precision/recall/F1 与 classification_report；`outputs/` 出现 `curves.png`、`confusion_matrix.png`、`samples.png`、`test_metrics.json`。

- [ ] **Step 3: 提交**

```bash
cd /data1/user/lz/ML_Practice
git add task2_alexnet_fmnist/evaluate.py task2_alexnet_fmnist/outputs/test_metrics.json
git -c user.name="lkun45598" -c user.email="lkun45598@local" commit -m "feat(task2): 评估/可视化，任务②完成"
```

---

## Phase 3 — 论文与汇总

### Task 10: 撰写学校格式 Word 论文

**Files:**
- Create: `report/generate_report.py`
- Create: `report/毕业论文_人工智能实训.docx`（产物）

- [ ] **Step 1: 阅读学校模板要点**

Run（提取格式规范文字，确认章节结构与格式要求）：
```bash
cd /data1/user/lz/ML_Practice
/home/lz/miniconda3/envs/pytorch312/bin/python -m pip install python-docx >/dev/null 2>&1
ls "附件3.华南农业大学本科毕业论文（设计）撰写规范（华南农办〔2024〕56号）"
```
Expected: 列出 .doc/.pdf 模板文件。人工浏览 PDF 确认章节顺序：封面 / 原创性声明 / 中文摘要+关键词 / 英文摘要 / 目录 / 引言 / 正文（方法、实验、结果）/ 结论 / 参考文献。

- [ ] **Step 2: 写文档生成脚本**

Create `report/generate_report.py`，用 `python-docx` 按模板章节生成论文骨架，嵌入两个任务的指标表与 `outputs/` 图片。脚本结构：
```python
# -*- coding: utf-8 -*-
"""用 python-docx 生成学校格式的实训论文（两个项目合一）。"""
import os, json
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T1 = os.path.join(ROOT, "task1_ml_wine", "outputs")
T2 = os.path.join(ROOT, "task2_alexnet_fmnist", "outputs")


def add_heading(doc, text, level):
    doc.add_heading(text, level=level)


def add_image(doc, path, width=5.5):
    if os.path.exists(path):
        doc.add_picture(path, width=Inches(width))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


def build():
    doc = Document()
    # 标题
    h = doc.add_heading("人工智能综合实训Ⅱ 实训报告", level=0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # 摘要
    add_heading(doc, "摘要", 1)
    doc.add_paragraph("本报告完成两个机器学习项目：白葡萄酒质量多分类与基于手写 AlexNet 的"
                      "Fashion-MNIST 图像分类……（正式撰写时补充背景、方法、结果与结论概述）")
    doc.add_paragraph("关键词：机器学习；支持向量机；随机森林；卷积神经网络；AlexNet")
    # 引言（研究背景）
    add_heading(doc, "1 引言", 1)
    doc.add_paragraph("（此处撰写研究背景：机器学习与图像分类的意义、应用现状、AlexNet 历史地位等。）")
    # 任务①
    add_heading(doc, "2 项目一：红酒质量分类", 1)
    add_heading(doc, "2.1 数据集与预处理", 2)
    doc.add_paragraph("UCI 白葡萄酒数据集，4898 样本、11 特征；质量评分分箱为差/中/好三类……")
    add_image(doc, os.path.join(T1, "eda_quality_dist.png"))
    add_image(doc, os.path.join(T1, "eda_corr_heatmap.png"))
    add_heading(doc, "2.2 模型与结果", 2)
    if os.path.exists(os.path.join(T1, "metrics.csv")):
        import csv
        with open(os.path.join(T1, "metrics.csv"), encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        table = doc.add_table(rows=1, cols=len(rows[0])); table.style = "Light Grid Accent 1"
        for j, c in enumerate(rows[0]):
            table.rows[0].cells[j].text = c
        for r in rows[1:]:
            cells = table.add_row().cells
            for j, c in enumerate(r):
                cells[j].text = c if j == 0 else f"{float(c):.3f}"
    add_image(doc, os.path.join(T1, "model_compare.png"))
    add_image(doc, os.path.join(T1, "rf_feature_importance.png"))
    # 任务②
    add_heading(doc, "3 项目二：手写 AlexNet 图像分类", 1)
    add_heading(doc, "3.1 网络结构", 2)
    doc.add_paragraph("逐层手写 AlexNet：5 个卷积块 + 3 个全连接，输入 1×224×224，输出 10 类……")
    add_heading(doc, "3.2 训练与评估", 2)
    if os.path.exists(os.path.join(T2, "test_metrics.json")):
        m = json.load(open(os.path.join(T2, "test_metrics.json")))
        doc.add_paragraph(f"测试集准确率 {m['acc']:.4f}，macro-F1 {m['f1']:.4f}。")
    add_image(doc, os.path.join(T2, "curves.png"))
    add_image(doc, os.path.join(T2, "confusion_matrix.png"))
    add_image(doc, os.path.join(T2, "samples.png"))
    # 结论
    add_heading(doc, "4 结论", 1)
    doc.add_paragraph("（总结两个项目的结果、对比分析与改进方向。）")
    add_heading(doc, "参考文献", 1)
    doc.add_paragraph("[1] Krizhevsky A, et al. ImageNet Classification with Deep "
                      "Convolutional Neural Networks. NeurIPS, 2012.")

    out = os.path.join(os.path.dirname(__file__), "毕业论文_人工智能实训.docx")
    doc.save(out)
    print("[论文] 已生成:", out)


if __name__ == "__main__":
    build()
```

- [ ] **Step 3: 运行生成**

Run: `/home/lz/miniconda3/envs/pytorch312/bin/python report/generate_report.py`
Expected: 生成 `report/毕业论文_人工智能实训.docx`，包含两个任务的表格与图片。

- [ ] **Step 4: 提交**

```bash
git add report/generate_report.py report/毕业论文_人工智能实训.docx
git -c user.name="lkun45598" -c user.email="lkun45598@local" commit -m "feat(report): 生成学校格式论文骨架"
```

- [ ] **Step 5: 人工完善**

提示用户：用 Word 打开 `.docx`，对照学校模板调整封面/页眉/字体字号/行距，补写摘要、引言背景、结论与分工说明，并填入学号姓名命名文件。

---

## 自检（计划对照 spec）

- spec §4（任务①）→ Task 1-4 全覆盖（加载/EDA/预处理/4模型/评估/结论）。✓
- spec §5（任务②手写 AlexNet）→ Task 5-9（模型/数据/训练/完整训练/评估）；§5.2 逐层手写在 Task 5 用基础算子组装，未调用预置模型。✓
- spec §6（论文）→ Task 10；引言/背景明确为学术内容占位待人工补全。✓
- spec §7（测试策略：可独立运行、冒烟测试、产物落 outputs、中文注释）→ 各 Task 含 run 验证与冒烟步骤。✓
- 类型一致性：`AlexNet(num_classes, in_channels)`、`get_loaders(...)→(train,val,test)`、`CLASS_NAMES`、`outputs/` 文件名在 train/evaluate/report 间一致。✓
- 无占位符：各 step 含完整可运行代码与预期输出。✓
