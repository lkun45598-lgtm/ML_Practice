# 人工智能综合实训Ⅱ — 设计文档

日期：2026-05-30
分支：feature 工作在 `ML_Practice/` 独立 git 仓库中进行。

## 1. 背景与目标

华南农业大学《人工智能综合实训Ⅱ》课程项目。需完成两个独立任务，最终合成一份按学校毕业论文格式撰写的 Word 文档，并提交 ppt、word、python 源码（以附件提交、不打包）。

统一流程：**加载 → 查看 → 预处理 → 建立模型 → 评估模型 → 结论**。

**硬性约束**：任务②的 AlexNet 必须逐层手写（用 `nn.Conv2d` / `nn.Linear` 等基础算子手工搭建网络），**不得**调用 `torchvision.models.alexnet` 或任何预置 AlexNet。

## 2. 运行环境

- 机器：单机 8× RTX 4090（24GB），使用单卡即可。
- Python 环境：conda `pytorch312`（torch 2.7.1+cu118, torchvision 0.22.1, sklearn 1.8.0, pandas 3.0.2, cuda 可用）。
- 解释器路径：`/home/lz/miniconda3/envs/pytorch312/bin/python`。
- 网络：UCI、torchvision/AWS 镜像可达；无 Kaggle 凭证（故选用可自动下载的数据集）。

## 3. 目录结构

```
ML_Practice/
├── task1_ml_wine/              # 任务① 机器学习
│   ├── data/                   # 自动下载 winequality-white.csv
│   ├── wine_quality.py         # 完整流程脚本（加载/EDA/预处理/4模型/评估/结论）
│   └── outputs/                # 图表、指标、混淆矩阵
├── task2_alexnet_fmnist/       # 任务② 手写 AlexNet
│   ├── data/                   # torchvision 自动下载 FashionMNIST
│   ├── alexnet.py              # 逐层手写 AlexNet（nn.Module）
│   ├── train.py                # 训练 + 验证
│   ├── evaluate.py             # 测试集评估
│   └── outputs/                # 训练曲线、混淆矩阵、checkpoint、预测样例
├── report/                     # 学校格式 Word 论文（两项目合一）
└── docs/superpowers/specs/     # 本设计文档
```

## 4. 任务① 红酒质量（机器学习）

### 4.1 数据集
- UCI Wine Quality（white wine），4898 样本 × 11 特征 + quality（0–10 评分）。
- 来源：`https://archive.ics.uci.edu/static/public/186/wine+quality.zip` 或直接 CSV，下载到 `data/`。

### 4.2 加载与查看（EDA）
- 读取 CSV（分号分隔），打印形状、`describe()`、缺失值检查。
- 可视化：各特征分布直方图、quality 分布、特征相关性热力图。图存 `outputs/`。

### 4.3 预处理
- 将 quality 评分分箱为 **3 类**：≤5 → 0（差），=6 → 1（中），≥7 → 2（好）。
- 特征标准化 `StandardScaler`（在训练集 fit，避免泄漏）。
- 分层划分 train/test（如 80/20，`stratify`）。
- 类别不平衡：建模时用 `class_weight='balanced'`；在文档中讨论 SMOTE 等替代方案。

### 4.4 建模（≥2 个，实际 4 个）
- SVM（`SVC`，RBF 核）
- 决策树（`DecisionTreeClassifier`）
- 随机森林（`RandomForestClassifier`，集成学习）
- 逻辑回归（`LogisticRegression`，作为线性基线对比）
- 统一用分层交叉验证 + `GridSearchCV` 调关键超参。

### 4.5 评估
- 指标：accuracy、precision/recall/F1（macro）、每类指标（`classification_report`）。
- 图表：各模型混淆矩阵、模型对比柱状图、树模型特征重要性图。
- 结果指标写入 `outputs/`（图 + 文本/CSV）。

### 4.6 结论
- 四模型对比，分析最优模型及原因，讨论不平衡与可改进方向。

## 5. 任务② 手写 AlexNet（Fashion-MNIST）

### 5.1 数据集
- torchvision `FashionMNIST`：60000 训练 / 10000 测试，28×28 灰度，10 类。
- 从训练集切 10% 作验证集。
- transform：`Resize(224)` → `ToTensor` → `Normalize`（单通道均值方差）。

### 5.2 模型（逐层手写，alexnet.py）
经典 AlexNet 结构，输入 `1×224×224`：
- 特征提取（5 卷积块）：
  - Conv1: 1→96, k=11, s=4, p=2 → ReLU → (LRN) → MaxPool(k=3,s=2)
  - Conv2: 96→256, k=5, p=2 → ReLU → (LRN) → MaxPool(k=3,s=2)
  - Conv3: 256→384, k=3, p=1 → ReLU
  - Conv4: 384→384, k=3, p=1 → ReLU
  - Conv5: 384→256, k=3, p=1 → ReLU → MaxPool(k=3,s=2)
- 分类器（3 全连接）：
  - Dropout → Linear(256×6×6 → 4096) → ReLU
  - Dropout → Linear(4096 → 4096) → ReLU
  - Linear(4096 → 10)
- 用 `nn.Conv2d/nn.MaxPool2d/nn.Linear/nn.ReLU/nn.Dropout`(可选 `nn.LocalResponseNorm`) 在自定义 `nn.Module` 中逐层组装；不调用预置模型。

### 5.3 训练（train.py）
- 损失：交叉熵；优化器：SGD(momentum=0.9) 或 Adam（文档中说明选择）。
- 设备：CUDA 单卡；mini-batch（如 128）。
- 记录每个 epoch 的 train/val loss 与 acc，保存验证集最优 checkpoint 到 `outputs/`。
- 先小 epoch/子集冒烟测试，再完整训练。

### 5.4 评估（evaluate.py）
- 加载最优 checkpoint，在测试集计算 accuracy、precision/recall/F1、混淆矩阵。
- 可视化：训练曲线（loss/acc）、混淆矩阵、若干预测样例（图像+预测/真实标签）。

### 5.5 结论
- 性能分析、过拟合与正则（Dropout/数据增强）讨论、可改进方向。

## 6. 论文（report/）

按附件模板撰写（封面、原创性声明及授权、中文摘要/关键词、引言、相关方法、实验设计与结果、结论、参考文献）。两个项目合成**一个** Word 文档，中文撰写。

最终交付物：
- ppt（汇报用）
- word 文档（学校毕业论文格式）
- 各 `.py` 源码（以附件提交、不打包）
- 文件命名按学号后 3 位姓名（汇报阶段由用户提供学号/姓名后补）。

## 7. 测试与验证策略

- 每个脚本可独立 `python <script>.py` 跑通。
- 产出图表/指标文件落到各自 `outputs/`。
- 任务②先用小 epoch + 数据子集冒烟测试，确认管线无误后再完整训练。
- 代码全部中文注释。

## 8. 范围之外（YAGNI）

- 不做 Kaggle 数据集（无凭证）。
- 不做多卡分布式训练（单卡足够）。
- 不实现卷积底层算子（“逐层手写”指手工组装网络结构，使用框架基础算子即可）。
