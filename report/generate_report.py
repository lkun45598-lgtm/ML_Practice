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
    h = doc.add_heading("人工智能综合实训Ⅱ 实训报告", level=0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_heading(doc, "摘要", 1)
    doc.add_paragraph("本报告完成两个机器学习项目：白葡萄酒质量多分类与基于手写 AlexNet 的"
                      "Fashion-MNIST 图像分类……（正式撰写时补充背景、方法、结果与结论概述）")
    doc.add_paragraph("关键词：机器学习；支持向量机；随机森林；卷积神经网络；AlexNet")
    add_heading(doc, "1 引言", 1)
    doc.add_paragraph("（此处撰写研究背景：机器学习与图像分类的意义、应用现状、AlexNet 历史地位等。）")
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
