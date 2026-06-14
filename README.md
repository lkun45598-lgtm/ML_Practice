# ML_Practice

两个独立的机器学习项目，完整实践 **加载 → 查看 → 预处理 → 建模 → 评估 → 结论** 的流程。
本分支仅包含项目源代码（不含报告、PPT 等生成脚本与文档）。

| 任务 | 内容 | 数据集 | 最佳结果 |
|------|------|--------|----------|
| **任务①** | 传统机器学习多分类（SVM / 决策树 / 随机森林 / 逻辑回归） | UCI 白葡萄酒质量（4898×11，3 分类） | 随机森林 macro-F1 **0.734** |
| **任务②** | 逐层手写 AlexNet 图像分类（基于 PyTorch 基础模块） | Fashion-MNIST（70000，10 分类） | 测试集准确率 **94.38%** |

## 目录结构

```
ML_Practice/
├── task1_ml_wine/                 # 任务① 传统机器学习
│   ├── wine_quality.py            # 白葡萄酒主管线：下载/EDA/预处理/四模型网格搜索/评估
│   ├── data_tabular.py            # 五个结构化数据集的统一加载器
│   ├── cross_dataset_tabular.py   # 五数据集 × 四模型跨数据集对照
│   ├── cross_dataset_improve.py   # 欠佳数据集改进尝试（补特征 / SMOTE）
│   ├── gbdt_test.py               # 梯度提升（GBDT）第五模型对照
│   ├── ozone_temporal.py          # 臭氧时序特征建模 + 时序交叉验证
│   ├── credit_deepfeatures.py     # 贷款违约补全真实征信特征（信息侧上限检验）
│   ├── credit_monotonic.py        # 贷款违约单调约束 GBDT（领域先验）
│   └── outputs/                   # 运行产物（图表 / 指标，自动生成）
├── task2_alexnet_fmnist/          # 任务② 手写 AlexNet
│   ├── alexnet.py                 # 逐层手写的 AlexNet（含 small_kernel 开关）
│   ├── resnet_small.py            # 手写小型 ResNet（架构对照）
│   ├── simplecnn.py               # 轻量基线 CNN（架构对照）
│   ├── data.py / data_image.py    # Fashion-MNIST（灰度）与彩色数据集加载器
│   ├── experiments.py             # 主入口：主模型 / 消融 / 跨数据集实验统一运行器
│   ├── train.py                   # 旧版最小训练脚本（演示保留）
│   ├── evaluate.py                # 测试集评估（混淆矩阵 / 曲线 / 样例）
│   ├── complexity.py              # 参数量与 FLOPs 复杂度对照
│   ├── gradcam.py                 # Grad-CAM 可解释性可视化
│   ├── aggregate_experiments.py   # 汇总实验结果并绘制对比图
│   ├── cross_dataset_summary.py   # 跨数据集对照结果聚合
│   ├── run_*.sh                   # 各组对照/消融实验的批量运行脚本
│   └── outputs/                   # 运行产物（曲线 / 混淆矩阵 / json，自动生成）
├── common/zh_font.py              # matplotlib 中文字体设置
├── requirements.txt
└── LICENSE
```

> 数据集与模型 checkpoint（`*.pt`）均由 `.gitignore` 排除，不在仓库中。
> Fashion-MNIST 与白葡萄酒在首次运行时自动下载；其余数据集需手动放入对应 `data/` 目录：
> - 任务①（放入 `task1_ml_wine/data/`）：`ionosphere`、`Ozone Level Detection`、
>   `DryBean Dataset`、`Lending Club Loan Data`
> - 任务②（放入 `task2_alexnet_fmnist/data/`）：flowers / garbage / catsdogs（解压到对应目录）

## 环境

- Python 3.12（建议使用 conda 环境）
- 任务② 训练需要 CUDA GPU（开发环境为单卡 RTX 4090，主模型 40 轮约半小时）

```bash
pip install -r requirements.txt
# 关键依赖：torch、torchvision、scikit-learn、imbalanced-learn、
#          pandas、matplotlib、seaborn、Pillow、thop
```

## 任务① 白葡萄酒质量分类

```bash
python task1_ml_wine/wine_quality.py
```

自动下载 UCI 数据集，完成 EDA、预处理（质量评分分箱为 差/中/好 三类）、对四个模型做
5 折交叉验证网格搜索并在测试集评估，图表与指标输出到 `task1_ml_wine/outputs/`。

跨数据集对照与改进实验（需先把四个数据集放入 `task1_ml_wine/data/`）：

```bash
python task1_ml_wine/cross_dataset_tabular.py   # 五数据集 × 四模型对照
python task1_ml_wine/cross_dataset_improve.py   # 欠佳数据集改进尝试
python task1_ml_wine/gbdt_test.py               # GBDT 第五模型对照
python task1_ml_wine/ozone_temporal.py          # 臭氧时序特征 + 时序交叉验证
python task1_ml_wine/credit_deepfeatures.py     # 贷款违约补全真实征信特征
python task1_ml_wine/credit_monotonic.py        # 贷款违约单调约束 GBDT
```

## 任务② 手写 AlexNet

```bash
# 1) 模型自检（打印前向输出形状与参数量）
python task2_alexnet_fmnist/alexnet.py

# 2) 训练主模型（首次运行自动下载 Fashion-MNIST）
python task2_alexnet_fmnist/experiments.py --model alexnet --bn --augment --cosine \
  --epochs 40 --batch-size 128 --lr 0.01 --seed 0 --tag main \
  --save-ckpt task2_alexnet_fmnist/outputs/alexnet_best.pt \
  --save-history task2_alexnet_fmnist/outputs/history.json
#   冒烟测试：python task2_alexnet_fmnist/experiments.py --model alexnet --bn --subset 256 --epochs 2 --tag smoke

# 3) 评估（加载最优 checkpoint，生成混淆矩阵 / 曲线 / 样例）
python task2_alexnet_fmnist/evaluate.py
```

对照实验（基线 / LRN 消融 / 数据增强）：

```bash
cd task2_alexnet_fmnist
python experiments.py --model simplecnn --img-size 28 --seed 0 --epochs 10 --tag simplecnn_s0
python experiments.py --model alexnet --no-lrn --seed 0 --epochs 15 --tag alexnet_nolrn
python experiments.py --model alexnet --augment --seed 0 --epochs 15 --tag alexnet_aug
python aggregate_experiments.py    # 汇总并绘制对比图
```

## 网络结构（手写 AlexNet）

主模型输入 `1×224×224`，约 58.3M 参数；卷积层使用 BatchNorm，LRN 作为对照实验保留：

- **特征提取（5 卷积块）**：Conv(1→96,11×11,s4)→BN→ReLU→MaxPool；Conv(96→256,5×5)→BN→ReLU→MaxPool；
  Conv(256→384,3×3)→BN→ReLU；Conv(384→384,3×3)→BN→ReLU；Conv(384→256,3×3)→BN→ReLU→MaxPool（输出 256×6×6）
- **分类器（3 全连接）**：Dropout→Linear(9216→4096)→ReLU；Dropout→Linear(4096→4096)→ReLU；Linear(4096→10)

> AlexNet 使用 `nn.Conv2d` / `nn.Linear` 等基础模块逐层构建网络结构，
> 不调用 `torchvision.models.alexnet` 或任何预置 AlexNet 模型。

## 说明

- 所有脚本可独立运行，产物统一写入各自的 `outputs/` 目录。
- 绘图中文显示由 `common/zh_font.py` 统一设置字体。
