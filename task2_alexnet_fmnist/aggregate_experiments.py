# -*- coding: utf-8 -*-
"""聚合 experiments.py 产出的 exp_*.json，生成对照实验汇总表与对比柱状图。

输出：outputs/experiments_summary.json、outputs/exp_compare.png
"""
import os
import sys
import json
import glob
import numpy as np
import matplotlib.pyplot as plt

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.zh_font import set_chinese_font

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "outputs")


def load_results():
    res = []
    for fp in glob.glob(os.path.join(OUT_DIR, "exp_*.json")):
        if "smoke" in fp:
            continue
        with open(fp) as f:
            res.append(json.load(f))
    return res


def build_summary(res):
    """归并 SimpleCNN 多种子为均值±标准差，AlexNet 各变体单列。返回有序行列表。"""
    scnn = [r for r in res if r["model"] == "simplecnn"]
    rows = []
    if scnn:
        acc = np.array([r["test_acc"] for r in scnn])
        f1 = np.array([r["test_f1"] for r in scnn])
        rows.append({"name": "SimpleCNN（轻量基线，3 种子）", "params": scnn[0]["n_params_M"],
                     "acc": acc.mean(), "acc_std": acc.std(ddof=1),
                     "f1": f1.mean(), "f1_std": f1.std(ddof=1), "note": "28×28 输入"})

    def pick(model, use_lrn, aug):
        for r in res:
            if r["model"] == model and r["use_lrn"] == use_lrn and r["augment"] == aug:
                return r
        return None

    base = pick("alexnet", True, False)
    nolrn = pick("alexnet", False, False)
    aug = pick("alexnet", True, True)
    if base:
        rows.append({"name": "AlexNet（基线：LRN，无增强）", "params": base["n_params_M"],
                     "acc": base["test_acc"], "acc_std": None, "f1": base["test_f1"],
                     "f1_std": None, "note": "224×224 输入"})
    if nolrn:
        rows.append({"name": "AlexNet（消融：去掉 LRN）", "params": nolrn["n_params_M"],
                     "acc": nolrn["test_acc"], "acc_std": None, "f1": nolrn["test_f1"],
                     "f1_std": None, "note": "去 LRN"})
    if aug:
        rows.append({"name": "AlexNet（+ 数据增强）", "params": aug["n_params_M"],
                     "acc": aug["test_acc"], "acc_std": None, "f1": aug["test_f1"],
                     "f1_std": None, "note": "翻转+旋转"})
    return rows


def main():
    set_chinese_font()
    res = load_results()
    rows = build_summary(res)
    with open(os.path.join(OUT_DIR, "experiments_summary.json"), "w") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    print(f"{'模型':<28}{'参数量(M)':>10}{'测试准确率':>14}{'macro-F1':>12}")
    for r in rows:
        acc = f"{r['acc']:.4f}" + (f"±{r['acc_std']:.4f}" if r['acc_std'] else "")
        f1 = f"{r['f1']:.4f}" + (f"±{r['f1_std']:.4f}" if r['f1_std'] else "")
        print(f"{r['name']:<28}{r['params']:>10}{acc:>16}{f1:>14}")

    # 对比柱状图（测试准确率）
    labels = ["SimpleCNN", "AlexNet\n基线", "AlexNet\n去LRN", "AlexNet\n+增强"]
    accs = [r["acc"] for r in rows]
    errs = [r["acc_std"] if r["acc_std"] else 0 for r in rows]
    colors = ["#55A868", "#4C72B0", "#8172B3", "#C44E52"]
    plt.figure(figsize=(7.5, 4.6))
    bars = plt.bar(labels, accs, yerr=errs, capsize=5, color=colors, alpha=0.9)
    for b, a in zip(bars, accs):
        plt.text(b.get_x() + b.get_width() / 2, a + 0.001, f"{a:.4f}",
                 ha="center", va="bottom", fontsize=10)
    plt.ylim(0.88, 0.93)
    plt.ylabel("测试集准确率")
    plt.title("不同模型/配置在 Fashion-MNIST 测试集上的准确率对比")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "exp_compare.png"), dpi=150)
    plt.close()
    print(f"[聚合] 汇总与对比图已保存到 {OUT_DIR}")


if __name__ == "__main__":
    main()
