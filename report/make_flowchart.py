# -*- coding: utf-8 -*-
"""生成研究流程图（六步机器学习流程），输出 report/flowchart.png。"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.zh_font import set_chinese_font

set_chinese_font()
HERE = os.path.dirname(os.path.abspath(__file__))

# 六个主流程步骤：标题 + 框内说明
steps = [
    ("1. 数据加载", "获取数据集，核对规模与字段", "#4C72B0"),
    ("2. 数据查看", "描述统计与可视化分析", "#4C72B0"),
    ("3. 数据预处理", "标签构造·标准化·划分·均衡", "#55A868"),
    ("4. 模型建立", "选择算法/网络结构，调参寻优", "#C44E52"),
    ("5. 模型评估", "多指标量化 + 混淆矩阵分析", "#C44E52"),
    ("6. 结论分析", "对比模型优劣，提出改进方案", "#937860"),
]

fig, ax = plt.subplots(figsize=(8.5, 11))
ax.set_xlim(0, 10)

# ---- 版面参数 ----
CX = 5.0            # 主流程列中心 x
BOX_W, BOX_H = 5.6, 1.05
PITCH = 1.65        # 相邻步骤中心间距
BOTTOM = 0.6
n = len(steps)
# 自底向上计算各步骤中心 y（step1 在最上）
centers = [BOTTOM + BOX_H / 2 + (n - 1 - i) * PITCH for i in range(n)]
SRC_Y = centers[0] + 1.85          # 数据源行
ax.set_ylim(0, SRC_Y + 0.9)
ax.axis("off")

# ---- 顶部两个数据源 ----
sources = [(2.7, "项目一：白葡萄酒质量数据", "（4898×11，3 分类）", "#8E7CC3"),
           (7.3, "项目二：Fashion-MNIST 图像", "（70000，10 分类）", "#6FA8DC")]
SRC_W, SRC_H = 4.0, 1.0
for cx, t1, t2, color in sources:
    ax.add_patch(FancyBboxPatch((cx - SRC_W / 2, SRC_Y - SRC_H / 2), SRC_W, SRC_H,
                 boxstyle="round,pad=0.02,rounding_size=0.12",
                 linewidth=1.4, edgecolor="#3b3b3b", facecolor=color, alpha=0.9))
    ax.text(cx, SRC_Y + 0.16, t1, ha="center", va="center", fontsize=11, color="white",
            fontweight="bold")
    ax.text(cx, SRC_Y - 0.18, t2, ha="center", va="center", fontsize=9.5, color="white")
    # 数据源 -> 步骤1
    ax.add_patch(FancyArrowPatch((cx, SRC_Y - SRC_H / 2), (CX, centers[0] + BOX_H / 2),
                 arrowstyle="-|>", mutation_scale=18, linewidth=1.6, color="#555",
                 connectionstyle="arc3,rad=0"))

# ---- 主流程步骤框 ----
for i, (title, desc, color) in enumerate(steps):
    cy = centers[i]
    ax.add_patch(FancyBboxPatch((CX - BOX_W / 2, cy - BOX_H / 2), BOX_W, BOX_H,
                 boxstyle="round,pad=0.02,rounding_size=0.14",
                 linewidth=1.8, edgecolor="#222", facecolor=color, alpha=0.93))
    ax.text(CX, cy + 0.2, title, ha="center", va="center", fontsize=15,
            color="white", fontweight="bold")
    ax.text(CX, cy - 0.24, desc, ha="center", va="center", fontsize=10.5, color="white")
    # 步骤之间的竖向箭头
    if i < n - 1:
        ax.add_patch(FancyArrowPatch((CX, cy - BOX_H / 2), (CX, centers[i + 1] + BOX_H / 2),
                     arrowstyle="-|>", mutation_scale=22, linewidth=2.2, color="#333"))

plt.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
out = os.path.join(HERE, "flowchart.png")
plt.savefig(out, dpi=160, bbox_inches="tight")
plt.close()
print("[流程图] 已生成:", out)
