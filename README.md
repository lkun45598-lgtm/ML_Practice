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
│   ├── wine_quality.py         # 完整管线：下载/EDA/预处理/四模型网格搜索/评估
│   └── outputs/                # EDA图、混淆矩阵、模型对比、特征重要性、metrics.csv
├── task2_alexnet_fmnist/       # 任务② 手写 AlexNet
│   ├── alexnet.py              # 逐层手写的 AlexNet（nn.Module）
│   ├── data.py                 # Fashion-MNIST 加载（Resize 224 + train/val/test）
│   ├── train.py                # 基础训练脚本
│   ├── experiments.py          # 主模型与对照/消融实验统一运行器
│   ├── evaluate.py             # 测试集评估、混淆矩阵、训练曲线、预测样例
│   └── outputs/                # 曲线图、混淆矩阵、样例图、history.json、test_metrics.json
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
├── report/                     # 两个项目合并版报告（保留备份）
│   ├── 毕业论文_人工智能实训.docx
│   ├── generate_report.py      # Word 生成脚本
│   ├── report.tex              # LaTeX 版（xelatex + ctex/fandol）
│   └── report.pdf              # LaTeX 编译产物
├── docs/superpowers/           # 设计文档与实施计划
└── requirements.txt
```

> 数据集与训练得到的模型 checkpoint（`*.pt`）已通过 `.gitignore` 排除，不在仓库中。
> 运行脚本时会自动重新下载数据并训练。

## 环境

- Python 3.12，建议用 conda 环境（开发环境为 `pytorch312`）
- GPU：训练任务②使用 CUDA（开发环境为单卡 RTX 4090，主模型 40 轮约半小时）

```bash
pip install -r requirements.txt
# 关键依赖：torch、torchvision、scikit-learn、pandas、matplotlib、seaborn、python-docx、thop
```

## 运行方式

### 任务① 红酒质量分类
```bash
python task1_ml_wine/wine_quality.py
```
自动下载 UCI 数据集，完成 EDA、预处理（质量评分分箱为 差/中/好 三类）、
对四个模型做 5 折交叉验证网格搜索，并在测试集评估，结果与图表输出到 `task1_ml_wine/outputs/`。

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

# 合并版报告仍可保留备份：
# python report/generate_report.py
# cd report && python make_flowchart.py && xelatex report.tex && xelatex report.tex
```

## 提交说明（重要）
最终在「教育在线」**以附件分别提交、不要打包成 zip**：
1. PPT（汇报用）
2. 任务一 Word 文档（学校毕业论文格式，独立封面与目录）
3. 任务二 Word 文档（学校毕业论文格式，独立封面与目录）
4. Python 源代码（各 `.py` 文件，作为附件）

由学号最小者 **蔡铭飞（202434610301）** 负责提交；文件按「学号后3位姓名_…」命名，
建议：`309雷正_301蔡铭飞_326冼嘉谦`。数据集与模型 checkpoint 不随仓库提交，运行脚本会自动下载/重新训练。

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
