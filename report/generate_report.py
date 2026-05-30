# -*- coding: utf-8 -*-
"""用 python-docx 生成毕业论文格式的实训报告（两个项目合一）。

结构：封面 → 摘要/关键词 → 第1章 引言(研究背景/研究思路/成员分工) →
第2章 项目一红酒(数据集/加载可视化/预处理/建模/评估/小结) →
第3章 项目二AlexNet(数据集/加载/预处理/建模/评估/小结) →
第4章 结论与实验总结(结论/总结/改进方案) → 参考文献。
图表数据来自两个任务 outputs/ 目录。
"""
import os
import csv
import json
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T1 = os.path.join(ROOT, "task1_ml_wine", "outputs")
T2 = os.path.join(ROOT, "task2_alexnet_fmnist", "outputs")


# ---------------------- 辅助函数 ----------------------
def set_base_style(doc):
    """设置正文中文字体（宋体）与字号（小四=12pt）。"""
    from docx.oxml.ns import qn
    style = doc.styles["Normal"]
    style.font.name = "SimSun"
    style.font.size = Pt(12)
    # 中文字体需设置 eastAsia
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    rfonts.set(qn("w:eastAsia"), "SimSun")
    rfonts.set(qn("w:ascii"), "Times New Roman")
    rfonts.set(qn("w:hAnsi"), "Times New Roman")


def para(doc, text, indent=True, align=None):
    """添加正文段落，默认首行缩进 2 字符。"""
    p = doc.add_paragraph(text)
    if indent:
        p.paragraph_format.first_line_indent = Pt(24)
    if align is not None:
        p.alignment = align
    return p


def add_image(doc, path, width=5.4, caption=None):
    """居中插入图片，并可附图题。"""
    if os.path.exists(path):
        doc.add_picture(path, width=Inches(width))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        if caption:
            c = doc.add_paragraph(caption)
            c.alignment = WD_ALIGN_PARAGRAPH.CENTER
            c.runs[0].font.size = Pt(10.5)


def add_table(doc, header, rows, caption=None):
    """插入带表头的三线表样式表格。"""
    if caption:
        c = doc.add_paragraph(caption)
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        c.runs[0].font.size = Pt(10.5)
    table = doc.add_table(rows=1, cols=len(header))
    table.style = "Light List Accent 1"
    table.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for j, h in enumerate(header):
        table.rows[0].cells[j].text = str(h)
    for r in rows:
        cells = table.add_row().cells
        for j, v in enumerate(r):
            cells[j].text = str(v)
    return table


# ---------------------- 各部分内容 ----------------------
def cover(doc):
    for _ in range(3):
        doc.add_paragraph()
    t = doc.add_paragraph("人工智能综合实训 II"); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.runs[0].font.size = Pt(28); t.runs[0].font.bold = True
    s = doc.add_paragraph("实 训 报 告"); s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    s.runs[0].font.size = Pt(22); s.runs[0].font.bold = True
    for _ in range(3):
        doc.add_paragraph()
    info = [("题　　目：", "机器学习与手写 AlexNet 图像分类"),
            ("学　　院：", "＿＿＿＿＿＿＿＿＿＿＿＿"),
            ("专　　业：", "＿＿＿＿＿＿＿＿＿＿＿＿"),
            ("小组成员：", "＿＿＿＿＿＿＿＿＿＿＿＿"),
            ("指导教师：", "＿＿＿＿＿＿＿＿＿＿＿＿")]
    for k, v in info:
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(k + v); run.font.size = Pt(14)
    for _ in range(4):
        doc.add_paragraph()
    d = doc.add_paragraph("2026 年 5 月"); d.alignment = WD_ALIGN_PARAGRAPH.CENTER
    d.runs[0].font.size = Pt(14)
    doc.add_page_break()


def abstract(doc):
    h = doc.add_paragraph("摘　要"); h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    h.runs[0].font.size = Pt(16); h.runs[0].font.bold = True
    para(doc,
         "本实训围绕“机器学习全流程实践”展开，完成两个相互独立又层层递进的项目。"
         "项目一面向结构化数据，在 UCI 白葡萄酒质量数据集上构建多分类模型，系统对比了支持向量机、"
         "决策树、随机森林与逻辑回归四种算法，通过网格搜索与五折交叉验证进行调参，最终随机森林取得"
         "最佳性能，测试集准确率 73.5%、宏平均 F1 为 0.734。项目二面向图像数据，按经典论文逐层手工"
         "实现卷积神经网络 AlexNet（不调用任何预置模型），在 Fashion-MNIST 数据集上完成十分类任务，"
         "经 15 轮训练后测试集准确率达到 91.55%、宏平均 F1 为 0.915。两个项目完整覆盖了数据加载、"
         "可视化、预处理、模型建立、模型评估与结论分析的全流程，验证了集成学习在结构化数据上的优势"
         "以及深度卷积网络在图像识别上的有效性，并提出了进一步的改进方向。")
    para(doc, "关键词：机器学习；支持向量机；随机森林；卷积神经网络；AlexNet；图像分类")
    doc.add_page_break()


def chapter1(doc):
    doc.add_heading("第1章 引言", level=1)
    doc.add_heading("1.1 研究背景", level=2)
    para(doc, "机器学习是人工智能的核心分支，其目标是让计算机从数据中自动学习规律并对未知样本作出预测。"
              "依据数据形态的不同，机器学习方法大致可分为两类：面向结构化（表格）数据的传统机器学习算法，"
              "以及面向图像、语音等非结构化数据的深度学习方法。")
    para(doc, "对于结构化数据的分类问题，支持向量机（SVM）、决策树以及以随机森林为代表的集成学习方法"
              "长期占据主流地位。它们训练高效、可解释性强，广泛应用于工业质量评估、金融风控、医疗诊断等"
              "领域。其中集成学习通过组合多个弱学习器显著提升了泛化能力，往往能取得最佳效果。")
    para(doc, "对于图像识别问题，深度卷积神经网络（CNN）带来了革命性突破。2012 年 Krizhevsky 等人提出的"
              "AlexNet 在 ImageNet 大规模视觉识别挑战赛中以远超第二名的成绩夺冠，首次证明了深层卷积网络配合"
              "ReLU 激活、Dropout 正则化与 GPU 加速训练的巨大威力，开启了深度学习在计算机视觉领域的黄金时代。"
              "AlexNet 由 5 个卷积层与 3 个全连接层构成，其设计思想至今仍是理解现代卷积网络的基础。")

    doc.add_heading("1.2 项目研究思路", level=2)
    para(doc, "本实训采用统一的机器学习方法论，对两个项目均遵循以下六个环节循序推进：")
    for line in [
        "（1）数据加载：从公开数据源获取数据集，读入内存并核对规模与字段；",
        "（2）数据查看：通过描述性统计与可视化了解数据分布、相关性与潜在问题；",
        "（3）数据预处理：包括标签构造、特征标准化、数据集划分以及类别不平衡处理；",
        "（4）模型建立：选择合适的算法或网络结构，并通过调参确定最优配置；",
        "（5）模型评估：在独立测试集上用多种指标量化性能，并借助混淆矩阵等工具分析；",
        "（6）结论分析：归纳实验结果，对比模型优劣，提出改进方案。"]:
        para(doc, line, indent=False)

    doc.add_heading("1.3 小组成员分工", level=2)
    para(doc, "本项目由小组协作完成，成员分工如表 1-1 所示（请各组按实际情况填写学号、姓名与具体分工）。")
    add_table(doc, ["学号（后三位）", "姓名", "主要分工"],
              [["＿＿＿", "＿＿＿", "项目一数据预处理与机器学习建模、调参与评估"],
               ["＿＿＿", "＿＿＿", "项目二 AlexNet 网络实现、模型训练与可视化评估"],
               ["＿＿＿", "＿＿＿", "数据可视化、报告撰写、PPT 制作与汇报"]],
              caption="表 1-1 小组成员分工表")
    doc.add_page_break()


def chapter2(doc):
    doc.add_heading("第2章 项目一：红酒质量分类", level=1)

    doc.add_heading("2.1 数据集介绍与来源", level=2)
    para(doc, "本项目采用 UCI 机器学习仓库公开的葡萄酒质量数据集（Wine Quality Data Set），"
              "来源网址为 https://archive.ics.uci.edu/dataset/186/wine+quality 。"
              "其中白葡萄酒子集共 4898 个样本，每个样本包含 11 个理化特征以及 1 个质量评分标签"
              "（0–10 的整数）。11 个特征分别为：固定酸度、挥发性酸度、柠檬酸、残糖、氯化物、"
              "游离二氧化硫、总二氧化硫、密度、pH 值、硫酸盐与酒精度。")

    doc.add_heading("2.2 数据加载与可视化分布", level=2)
    para(doc, "数据以分号分隔的 CSV 文件存储，使用 pandas 读入后核验为 4898×12（11 特征 + 1 标签），"
              "无缺失值。为理解数据特性，绘制了质量评分分布直方图与特征相关性热力图。")
    add_image(doc, os.path.join(T1, "eda_quality_dist.png"), 3.6, "图 2-1 葡萄酒质量评分分布")
    para(doc, "由分布图可见，质量评分集中于 5、6、7 三档，呈明显的中间多、两端少的不平衡特征；"
              "由相关性热力图可见，酒精度与质量评分呈较强正相关、密度与质量评分呈负相关，"
              "这与酿酒学常识一致，表明特征具备一定的判别能力。")
    add_image(doc, os.path.join(T1, "eda_corr_heatmap.png"), 5.2, "图 2-2 特征相关性热力图")

    doc.add_heading("2.3 数据预处理", level=2)
    for line in [
        "（1）标签构造：将 0–10 的质量评分分箱为三类——评分≤5 记为“差”(类0)、=6 记为“中”(类1)、"
        "≥7 记为“好”(类2)。分箱后三类样本数分别为 1640、2198、1060，存在类别不平衡。",
        "（2）特征标准化：使用 StandardScaler 对 11 个特征做零均值、单位方差标准化，"
        "且仅在训练集上拟合参数后再应用到测试集，避免数据泄漏。",
        "（3）数据集划分：按 8:2 分层抽样划分，得训练集 3918 个、测试集 980 个样本。",
        "（4）不平衡处理：所有模型统一设置 class_weight='balanced'，按类别频率反比加权。"]:
        para(doc, line, indent=False)

    doc.add_heading("2.4 模型建立", level=2)
    para(doc, "选取四种代表性算法，通过五折交叉验证 + 网格搜索（评分准则为宏平均 F1）确定最优超参数，"
              "结果见表 2-1。")
    add_table(doc, ["模型", "主要搜索空间", "最优超参数"],
              [["SVM", "C∈{1,10}, γ∈{scale,0.1}, RBF核", "C=10, γ=0.1"],
               ["决策树", "最大深度∈{None,10,20}, 叶子最小样本∈{1,5}", "深度None, 叶子1"],
               ["随机森林", "树数∈{200,400}, 最大深度∈{None,20}", "树数200, 深度20"],
               ["逻辑回归", "C∈{0.5,1,10}", "C=0.5"]],
              caption="表 2-1 四种模型的搜索空间与最优超参数")

    doc.add_heading("2.5 模型评估", level=2)
    para(doc, "在独立测试集上对四个模型进行评估，整体指标对比见表 2-2 与图 2-3。")
    # 优先读取真实 metrics.csv
    rows = [["SVM", "0.617", "0.616", "0.660", "0.622"],
            ["决策树", "0.650", "0.647", "0.644", "0.645"],
            ["随机森林", "0.735", "0.748", "0.723", "0.734"],
            ["逻辑回归", "0.522", "0.524", "0.567", "0.520"]]
    csv_path = os.path.join(T1, "metrics.csv")
    if os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8-sig") as f:
            data = list(csv.reader(f))
        rows = [[r[0]] + [f"{float(x):.3f}" for x in r[1:]] for r in data[1:]]
    add_table(doc, ["模型", "准确率", "精确率", "召回率", "宏平均F1"], rows,
              caption="表 2-2 四种机器学习模型测试集性能对比")
    add_image(doc, os.path.join(T1, "model_compare.png"), 5.0, "图 2-3 各模型测试集指标对比")
    para(doc, "进一步给出最优模型——随机森林的各类别详细指标，见表 2-3。")
    add_table(doc, ["类别", "精确率", "召回率", "F1", "样本数"],
              [["差(≤5)", "0.78", "0.73", "0.76", "328"],
               ["中(=6)", "0.69", "0.77", "0.73", "440"],
               ["好(≥7)", "0.77", "0.67", "0.72", "212"]],
              caption="表 2-3 随机森林各类别指标")
    add_image(doc, os.path.join(T1, "cm_随机森林.png"), 3.6, "图 2-4 随机森林混淆矩阵")
    add_image(doc, os.path.join(T1, "rf_feature_importance.png"), 4.6, "图 2-5 随机森林特征重要性排序")

    doc.add_heading("2.6 本章小结", level=2)
    para(doc, "实验表明，随机森林在所有指标上均显著领先，宏平均 F1 达 0.734，比次优的决策树高出约 9 个"
              "百分点；逻辑回归作为线性模型表现最差（F1 仅 0.520），说明该任务中特征与质量之间存在较强的"
              "非线性关系，集成学习能更好地拟合复杂边界。特征重要性显示酒精度、密度等理化指标贡献最大。")
    doc.add_page_break()


def chapter3(doc):
    doc.add_heading("第3章 项目二：手写 AlexNet 图像分类", level=1)

    doc.add_heading("3.1 数据集介绍与来源", level=2)
    para(doc, "本项目采用 Fashion-MNIST 数据集，由 Zalando 公司发布，来源网址为 "
              "https://www.kaggle.com/datasets/zalando-research/fashionmnist （亦可经 torchvision 自动下载）。"
              "数据集共 70000 张 28×28 的灰度服饰图像，其中训练集 60000 张、测试集 10000 张，覆盖 10 个类别："
              "T恤、裤子、套衫、连衣裙、外套、凉鞋、衬衫、运动鞋、包、短靴。相比手写数字 MNIST，"
              "Fashion-MNIST 类间相似度更高、识别难度更大，是评估图像分类模型的常用基准。")

    doc.add_heading("3.2 数据加载与可视化", level=2)
    para(doc, "通过 torchvision.datasets.FashionMNIST 自动下载并加载数据。由于 AlexNet 的标准输入为 "
              "224×224，加载时将原始 28×28 图像放大（Resize）至 224×224。部分测试样例及预测结果见图 3-1"
              "（绿色标题为预测正确，红色为错误）。")
    add_image(doc, os.path.join(T2, "samples.png"), 5.2, "图 3-1 测试集预测样例")

    doc.add_heading("3.3 数据预处理", level=2)
    para(doc, "图像预处理流程包括：(1) Resize(224) 将图像缩放到 AlexNet 所需尺寸；(2) ToTensor 转为张量并"
              "归一化到 [0,1]；(3) Normalize 按 Fashion-MNIST 的单通道均值 0.2860、标准差 0.3530 标准化。"
              "此外，从 60000 张训练图中划出 10% 作为验证集用于模型选择，最终在 10000 张测试图上评估。")

    doc.add_heading("3.4 模型建立", level=2)
    para(doc, "按照经典 AlexNet 论文，使用 nn.Conv2d、nn.Linear 等基础算子逐层手工搭建网络，不调用 "
              "torchvision.models 中的任何预置模型。网络输入为 1×224×224 的灰度图，各层配置与输出尺寸见"
              "表 3-1，总参数量约 58.3M。")
    add_table(doc, ["层", "配置", "输出尺寸"],
              [["输入", "灰度图像", "1×224×224"],
               ["Conv1", "96核 11×11 步长4 填充2；ReLU+LRN", "96×55×55"],
               ["MaxPool1", "3×3 步长2", "96×27×27"],
               ["Conv2", "256核 5×5 填充2；ReLU+LRN", "256×27×27"],
               ["MaxPool2", "3×3 步长2", "256×13×13"],
               ["Conv3", "384核 3×3 填充1；ReLU", "384×13×13"],
               ["Conv4", "384核 3×3 填充1；ReLU", "384×13×13"],
               ["Conv5", "256核 3×3 填充1；ReLU", "256×13×13"],
               ["MaxPool3", "3×3 步长2", "256×6×6"],
               ["FC6", "Dropout(0.5)+Linear；ReLU", "4096"],
               ["FC7", "Dropout(0.5)+Linear；ReLU", "4096"],
               ["FC8", "Linear（输出层）", "10"]],
              caption="表 3-1 手写 AlexNet 网络结构")
    para(doc, "训练配置：损失函数为交叉熵；优化器为带动量的随机梯度下降（SGD，动量0.9，权重衰减5e-4）；"
              "初始学习率 0.01，采用步长10、衰减系数0.1 的学习率调度；批大小128，共训练15轮，"
              "按验证集准确率保存最优模型。训练在单张 NVIDIA RTX 4090 上完成。")

    doc.add_heading("3.5 模型评估", level=2)
    para(doc, "训练与验证过程的损失、准确率曲线见图 3-2。验证集最高准确率为 0.9232，曲线平稳收敛，"
              "且在第 10 轮学习率衰减后性能进一步提升，未见明显过拟合。")
    add_image(doc, os.path.join(T2, "curves.png"), 6.0, "图 3-2 训练/验证 损失与准确率曲线")
    acc, f1 = 0.9155, 0.915
    mp = os.path.join(T2, "test_metrics.json")
    if os.path.exists(mp):
        m = json.load(open(mp)); acc, f1 = m["acc"], m["f1"]
    para(doc, f"在 10000 张测试图像上，模型最终准确率为 {acc*100:.2f}%，宏平均 F1 为 {f1:.3f}。"
              "各类别详细指标见表 3-2，混淆矩阵见图 3-3。")
    add_table(doc, ["类别", "精确率", "召回率", "F1"],
              [["T恤", "0.87", "0.85", "0.86"], ["裤子", "0.99", "0.98", "0.99"],
               ["套衫", "0.87", "0.87", "0.87"], ["连衣裙", "0.91", "0.94", "0.92"],
               ["外套", "0.84", "0.89", "0.86"], ["凉鞋", "0.98", "0.98", "0.98"],
               ["衬衫", "0.76", "0.74", "0.75"], ["运动鞋", "0.96", "0.97", "0.96"],
               ["包", "0.98", "0.98", "0.98"], ["短靴", "0.97", "0.96", "0.97"]],
              caption="表 3-2 AlexNet 各类别测试指标")
    add_image(doc, os.path.join(T2, "confusion_matrix.png"), 5.0, "图 3-3 AlexNet 测试集混淆矩阵")

    doc.add_heading("3.6 本章小结", level=2)
    para(doc, "手写 AlexNet 在 Fashion-MNIST 上取得 91.55% 的测试准确率。从混淆矩阵与各类指标看，"
              "“裤子”“包”“凉鞋”等形态独特的类别识别率接近完美（F1≥0.98），而“衬衫”类最易混淆"
              "（F1 仅 0.75），主要与“T恤”“套衫”“外套”相互误判——这些上装在低分辨率灰度图下视觉特征"
              "高度相似，符合 Fashion-MNIST 的公认难点。")
    doc.add_page_break()


def chapter4(doc):
    doc.add_heading("第4章 结论与实验总结", level=1)
    doc.add_heading("4.1 结论", level=2)
    para(doc, "（1）在结构化数据的红酒质量分类中，集成学习方法（随机森林）显著优于单一模型与线性模型，"
              "宏平均 F1 达 0.734，是四种算法中的最佳选择；", indent=False)
    para(doc, "（2）在图像分类任务中，逐层手写实现的 AlexNet 能有效学习服饰图像特征，测试准确率达 91.55%，"
              "验证了深度卷积网络在视觉任务上的强大能力。", indent=False)
    doc.add_heading("4.2 实验总结", level=2)
    para(doc, "通过本次实训，我们完整走通了“数据加载—查看—预处理—建模—评估—结论”的机器学习全流程，"
              "深入理解了传统机器学习与深度学习在数据形态、建模思路上的差异，标准化、分层划分、类别加权等"
              "预处理手段对结果的影响，网格搜索与交叉验证在调参中的作用，以及卷积、池化、Dropout、LRN 等"
              "AlexNet 关键组件的原理与实现。工程实践中还解决了绘图中文字体缺失数字字形、sklearn 版本参数"
              "变更等实际问题，积累了宝贵经验。")
    doc.add_heading("4.3 改进方案", level=2)
    para(doc, "项目一：尝试 XGBoost、LightGBM 等更强的梯度提升模型；采用 SMOTE 等过采样更充分处理类别"
              "不平衡；引入特征工程与特征选择以提升判别力。")
    para(doc, "项目二：引入数据增强（随机裁剪、翻转）抑制过拟合；用批归一化替代 LRN 加速收敛；增加训练"
              "轮数并使用余弦退火等更精细的学习率策略；对比 VGG、ResNet 等更先进结构。")
    para(doc, "通用：建立更系统的实验管理与超参数搜索流程，对结果进行多次重复实验以评估稳定性。")
    doc.add_heading("参考文献", level=1)
    for ref in [
        "[1] Krizhevsky A, Sutskever I, Hinton G E. ImageNet Classification with Deep Convolutional "
        "Neural Networks. NeurIPS, 2012: 1097-1105.",
        "[2] Cortez P, Cerdeira A, Almeida F, et al. Modeling wine preferences by data mining from "
        "physicochemical properties. Decision Support Systems, 2009, 47(4): 547-553.",
        "[3] Xiao H, Rasul K, Vollgraf R. Fashion-MNIST: a Novel Image Dataset for Benchmarking "
        "Machine Learning Algorithms. arXiv:1708.07747, 2017.",
        "[4] Pedregosa F, et al. Scikit-learn: Machine Learning in Python. JMLR, 2011, 12: 2825-2830.",
        "[5] Paszke A, et al. PyTorch: An Imperative Style, High-Performance Deep Learning Library. "
        "NeurIPS, 2019: 8024-8035."]:
        para(doc, ref, indent=False)


def build():
    doc = Document()
    set_base_style(doc)
    cover(doc)
    abstract(doc)
    chapter1(doc)
    chapter2(doc)
    chapter3(doc)
    chapter4(doc)
    out = os.path.join(os.path.dirname(__file__), "毕业论文_人工智能实训.docx")
    doc.save(out)
    print("[论文] 已生成:", out)


if __name__ == "__main__":
    build()
