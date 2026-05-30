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

# 六个主流程步骤及右侧说明
steps = [
    ("数据加载", "从 UCI / torchvision 获取数据，核对规模与字段"),
    ("数据查看", "描述统计与可视化：分布、相关性、样例"),
    ("数据预处理", "标签构造 / 标准化 / 分层划分 / 不平衡处理"),
    ("模型建立", "选择算法或网络结构，调参确定最优配置"),
    ("模型评估", "准确率/精确率/召回率/F1、混淆矩阵、曲线"),
    ("结论分析", "对比模型优劣，归纳结论与改进方案"),
]

n = len(steps)
fig, ax = plt.subplots(figsize=(9, 8.6))
ax.set_xlim(0, 10)
ax.set_ylim(0, n * 1.5 + 1.4)
ax.axis("off")

# 顶部两个数据来源（并入主流程）
src_y = n * 1.5 + 0.55
for cx, label, color in [(2.2, "项目一：白葡萄酒质量数据\n(4898×11, 3 分类)", "#8E7CC3"),
                         (6.6, "项目二：Fashion-MNIST 图像\n(70000, 10 分类)", "#6FA8DC")]:
    box = FancyBboxPatch((cx - 1.7, src_y - 0.45), 3.4, 0.9,
                         boxstyle="round,pad=0.05,rounding_size=0.12",
                         linewidth=1.4, edgecolor="#444", facecolor=color, alpha=0.85)
    ax.add_patch(box)
    ax.text(cx, src_y, label, ha="center", va="center", fontsize=10.5, color="white")

box_cx = 3.3       # 主流程框中心 x
box_w, box_h = 3.6, 0.95
colors = ["#4C72B0", "#4C72B0", "#55A868", "#C44E52", "#C44E52", "#937860"]

centers = []
for i, (title, _) in enumerate(steps):
    cy = (n - i) * 1.5 - 0.4
    centers.append(cy)
    box = FancyBboxPatch((box_cx - box_w / 2, cy - box_h / 2), box_w, box_h,
                         boxstyle="round,pad=0.05,rounding_size=0.12",
                         linewidth=1.6, edgecolor="#222", facecolor=colors[i], alpha=0.92)
    ax.add_patch(box)
    ax.text(box_cx, cy, f"{i+1}. {title}", ha="center", va="center",
            fontsize=14, color="white", fontweight="bold")
    # 右侧说明
    ax.text(box_cx + box_w / 2 + 0.3, cy, steps[i][1], ha="left", va="center",
            fontsize=10, color="#333")

# 两个数据源 -> 第一个步骤
for cx in (2.2, 6.6):
    ax.add_patch(FancyArrowPatch((cx, src_y - 0.45), (box_cx, centers[0] + box_h / 2),
                 arrowstyle="-|>", mutation_scale=16, linewidth=1.4, color="#666",
                 connectionstyle="arc3,rad=0.0"))

# 步骤之间的竖向箭头
for i in range(n - 1):
    ax.add_patch(FancyArrowPatch((box_cx, centers[i] - box_h / 2),
                                 (box_cx, centers[i + 1] + box_h / 2),
                                 arrowstyle="-|>", mutation_scale=20,
                                 linewidth=2.0, color="#333"))

plt.tight_layout()
out = os.path.join(HERE, "flowchart.png")
plt.savefig(out, dpi=160, bbox_inches="tight")
plt.close()
print("[流程图] 已生成:", out)
