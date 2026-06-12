# 人工智能综合实训 II

华南农业大学《人工智能综合实训 II》课程项目。包含两个独立的机器学习项目，完整实践
**加载 → 查看 → 预处理 → 建模 → 评估 → 结论** 的流程：

| 任务 | 内容 | 数据集 | 最佳结果 |
|------|------|--------|----------|
| **任务①** | 传统机器学习多分类（SVM / 决策树 / 随机森林 / 逻辑回归） | UCI 白葡萄酒质量（4898×11，3 分类） | 随机森林 macro-F1 **0.734** |
| **任务②** | **逐层实现** AlexNet 图像分类（基于基础算子构建） | Fashion-MNIST（70000，10 分类） | 测试集准确率 **94.38%** |

## 目录结构

```
ML_Practice/
├── task1_ml_wine/              # 任务① 机器学习
│   ├── wine_quality.py         # 白葡萄酒主管线：下载/EDA/预处理/四模型网格搜索/评估
│   ├── data_tabular.py         # 五个结构化数据集统一加载器（缺失填充交给Pipeline）
│   ├── cross_dataset_tabular.py# 五数据集×四模型跨数据集对照
│   ├── cross_dataset_improve.py# 欠佳数据集改进尝试（补特征/SMOTE）
│   ├── gbdt_test.py            # 梯度提升 GBDT 第五模型对照
│   ├── ozone_temporal.py       # 臭氧时序特征创新 + 时序CV评估（识别"假提升"）
│   ├── credit_deepfeatures.py  # 贷款违约补全真实征信特征（信息侧上限检验）
│   ├── credit_monotonic.py     # 贷款违约单调约束 GBDT（信用评分领域先验）
│   └── outputs/                # EDA/混淆矩阵/模型对比/跨数据集图表/手绘示意图
├── task2_alexnet_fmnist/       # 任务② 手写 AlexNet
│   ├── alexnet.py              # 逐层手写的 AlexNet（含 small_kernel 开关）
│   ├── resnet_small.py simplecnn.py  # 架构对照模型
│   ├── data.py / data_image.py # 灰度(Fashion-MNIST)与彩色数据集加载
│   ├── train.py                # 旧版基础训练脚本（主入口为 experiments.py）
│   ├── experiments.py          # 主模型与对照/消融/跨数据集实验统一运行器（主入口）
│   ├── evaluate.py             # 测试集评估（--no-bn/--no-lrn/--small-kernel 匹配架构）
│   ├── cross_dataset_summary.py aggregate_experiments.py  # 结果聚合与绘图
│   └── outputs/                # 曲线/混淆矩阵/样例/手绘示意图/history.json/各 exp_*.json
├── common/zh_font.py           # matplotlib 中文字体设置（含数字/字母回退）
├── reports/                    # 两篇独立论文（当前提交口径）
│   ├── generate_split_reports.py
│   ├── task1_wine_quality/
│   │   ├── report.tex
│   │   ├── report.pdf
│   │   └── 任务一_白葡萄酒质量分类论文.docx
│   └── task2_alexnet_fmnist/
│       ├── report.tex
│       ├── report.pdf
│       └── 任务二_AlexNet服饰图像分类论文.docx
├── report/                     # 旧的两项目合并版报告（本地备份，已被 .gitignore 排除，不在仓库）
├── docs/superpowers/           # 设计文档与实施计划
└── requirements.txt
```

> 模型 checkpoint（`*.pt`）与各数据集均通过 `.gitignore` 排除，不在仓库中。
> **Fashion-MNIST 与白葡萄酒会在首次运行时自动下载**；其余数据集较大或来源不同，需手动放入对应
> `data/` 目录后才能运行跨数据集实验：
> - 任务①（放入 `task1_ml_wine/data/`）：`ionosphere.zip`、`Ozone Level Detection.zip`、
>   `DryBean Dataset.zip`、`Lending Club Loan Data.zip`
> - 任务②（放入 `task2_alexnet_fmnist/data/`）：flowers / garbage / catsdogs 三个数据集（解压到对应目录）

## 环境

- Python 3.12，建议用 conda 环境（开发环境为 `pytorch312`）
- GPU：训练任务②使用 CUDA（开发环境为单卡 RTX 4090，主模型 40 轮约半小时）

```bash
pip install -r requirements.txt
# 关键依赖：torch、torchvision、scikit-learn、imbalanced-learn、pandas、matplotlib、
#          seaborn、Pillow、python-docx、python-pptx、thop
```

## 运行方式

### 任务① 红酒质量分类
```bash
python task1_ml_wine/wine_quality.py
```
自动下载 UCI 数据集，完成 EDA、预处理（质量评分分箱为 差/中/好 三类）、
对四个模型做 5 折交叉验证网格搜索，并在测试集评估，结果与图表输出到 `task1_ml_wine/outputs/`。

跨数据集对照与改进实验（需先按上文把四个数据集放入 `task1_ml_wine/data/`）：
```bash
python task1_ml_wine/cross_dataset_tabular.py   # 五数据集×四模型对照
python task1_ml_wine/cross_dataset_improve.py   # 欠佳数据集改进尝试
python task1_ml_wine/gbdt_test.py               # GBDT 第五模型对照
python task1_ml_wine/ozone_temporal.py          # 臭氧时序特征创新 + 时序CV评估
python task1_ml_wine/credit_deepfeatures.py     # 贷款违约补全真实征信特征
python task1_ml_wine/credit_monotonic.py        # 贷款违约单调约束 GBDT
```

### 任务② 手写 AlexNet
```bash
# 1) 模型自检（打印前向输出形状与参数量）
python task2_alexnet_fmnist/alexnet.py

# 2) 训练主模型（首次运行自动下载 Fashion-MNIST）
python task2_alexnet_fmnist/experiments.py --model alexnet --bn --augment --cosine \
  --epochs 40 --batch-size 128 --lr 0.01 --seed 0 --tag main \
  --save-ckpt task2_alexnet_fmnist/outputs/alexnet_best.pt \
  --save-history task2_alexnet_fmnist/outputs/history.json
#   冒烟测试：python task2_alexnet_fmnist/experiments.py --model alexnet --bn --subset 256 --epochs 2 --tag smoke

# 3) 评估（加载最优 checkpoint，生成混淆矩阵/曲线/样例）
python task2_alexnet_fmnist/evaluate.py
```

### 对照实验（SimpleCNN 基线 / LRN 消融 / 数据增强）
```bash
cd task2_alexnet_fmnist
python experiments.py --model simplecnn --img-size 28 --seed 0 --epochs 10 --tag simplecnn_s0
python experiments.py --model alexnet --no-lrn --seed 0 --epochs 15 --tag alexnet_nolrn
python experiments.py --model alexnet --augment --seed 0 --epochs 15 --tag alexnet_aug
python aggregate_experiments.py           # 汇总并绘制对比图
```

### 生成报告
```bash
python reports/generate_split_reports.py  # 生成任务一、任务二两篇独立 Word

cd reports/task1_wine_quality && xelatex report.tex && xelatex report.tex
cd ../../reports/task2_alexnet_fmnist && xelatex report.tex && xelatex report.tex
```
> 报告引用的图片均已纳入各自 `outputs/` 目录（含手绘示意图），可从零克隆后直接编译。

## 提交说明（重要）
最终在「教育在线」**以附件分别提交、不要打包成 zip**：
1. PPT（汇报用）
2. 任务一 Word 文档（学校毕业论文格式，独立封面与目录）
3. 任务二 Word 文档（学校毕业论文格式，独立封面与目录）
4. Python 源代码（各 `.py` 文件，作为附件）

由学号最小者 **蔡铭飞（202434610301）** 负责提交；文件按「学号后3位姓名_…」命名，
建议：`309雷正_301蔡铭飞_326冼嘉谦`。数据集与模型 checkpoint 不随仓库提交；Fashion-MNIST 与白葡萄酒
会自动下载，其余数据集需按上文手动放入对应 `data/` 目录。

## 网络结构（手写 AlexNet）

主模型输入 `1×224×224`，约 58.3M 参数；卷积层使用 BatchNorm，LRN 作为对照实验保留：

- **特征提取（5 卷积块）**：Conv(1→96,11×11,s4)→BN→ReLU→MaxPool；Conv(96→256,5×5)→BN→ReLU→MaxPool；
  Conv(256→384,3×3)→BN→ReLU；Conv(384→384,3×3)→BN→ReLU；Conv(384→256,3×3)→BN→ReLU→MaxPool（输出 256×6×6）
- **分类器（3 全连接）**：Dropout→Linear(9216→4096)→ReLU；Dropout→Linear(4096→4096)→ReLU；Linear(4096→10)

> AlexNet 使用 `nn.Conv2d` / `nn.Linear` 等基础算子逐层构建，
> 不调用 `torchvision.models.alexnet` 或任何预置 AlexNet。

## 说明

- 所有脚本可独立运行，产物统一落到各自的 `outputs/` 目录。
- 绘图中文显示：`common/zh_font.py` 优先选用同时含中文、数字与拉丁字母的字体
  （如 AR PL SungtiL GB），避免数字被渲染成方块。
