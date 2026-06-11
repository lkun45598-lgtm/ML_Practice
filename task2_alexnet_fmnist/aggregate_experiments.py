# -*- coding: utf-8 -*-
"""聚合 experiments.py 产出的关键实验结果，生成对照实验汇总表与对比图。

输出：
- outputs/experiments_summary.json
- outputs/component_ablation_summary.json
- outputs/architecture_summary.json
- outputs/improve_summary.json
- outputs/exp_compare.png

说明：本脚本按明确 tag 与指定汇总文件取数，避免把旧的 15 轮增强实验误作为主模型。
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
CLASS_NAMES = ["T恤", "裤子", "套衫", "连衣裙", "外套", "凉鞋", "衬衫", "运动鞋", "包", "短靴"]


def read_json(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def load_exp_results():
    res = []
    for fp in glob.glob(os.path.join(OUT_DIR, "exp_*.json")):
        if "smoke" in fp:
            continue
        with open(fp) as f:
            res.append(json.load(f))
    return res


def by_tag(results):
    return {r.get("tag"): r for r in results}


def class_f1(result, class_name):
    if not result:
        return None
    f1s = result.get("f1_per_class")
    if isinstance(f1s, dict):
        return f1s.get(class_name)
    if isinstance(f1s, list):
        return f1s[CLASS_NAMES.index(class_name)]
    return None


def round4(x):
    return None if x is None else round(float(x), 4)


def metric_row(name, result, note, shirt_f1=None, acc=None, f1=None, params=None, source=None):
    return {
        "name": name,
        "params_M": round4(params if params is not None else result.get("n_params_M")),
        "acc": round4(acc if acc is not None else result.get("test_acc")),
        "f1": round4(f1 if f1 is not None else result.get("test_f1")),
        "shirt_f1": round4(shirt_f1 if shirt_f1 is not None else class_f1(result, "衬衫")),
        "note": note,
        "source": source or result.get("tag"),
    }


def build_component_ablation(tags):
    """返回与论文表 5-1 一致的 AlexNet 组件消融行。"""
    # 15 轮基线指标来自已提交的 baseline_15ep_metrics.json（不再依赖未跟踪的 .bak 文件）；
    # 若该文件缺失则回退到 exp_alexnet_base.json，避免硬编码。
    baseline_metrics = read_json(os.path.join(OUT_DIR, "baseline_15ep_metrics.json"))
    base_exp = tags.get("alexnet_base") or {}
    baseline_acc = baseline_metrics.get("acc") if baseline_metrics else base_exp.get("test_acc")
    baseline_f1 = baseline_metrics.get("f1") if baseline_metrics else base_exp.get("test_f1")
    baseline_shirt = (baseline_metrics or {}).get("shirt_f1", class_f1(base_exp, "衬衫"))

    rows = [
        metric_row("最小配置（15轮，LRN，无增强）", base_exp, "15 轮 LRN 基线",
                   shirt_f1=baseline_shirt, acc=baseline_acc, f1=baseline_f1,
                   params=(baseline_metrics or {}).get("n_params_M", 58.299),
                   source="baseline_15ep_metrics.json"),
        metric_row("+ 充分训练（40轮，余弦退火）", tags["alexnet_long_base"],
                   "40 轮 LRN，无增强"),
        metric_row("+ BatchNorm 替代 LRN", tags["alexnet_long_bn"],
                   "40 轮 BN，无增强"),
        metric_row("+ 数据增强（主模型）", tags["alexnet_long_bn_aug"],
                   "40 轮 BN，随机翻转和小角度旋转"),
    ]
    prev = None
    for row in rows:
        row["delta_acc_pp"] = None if prev is None else round((row["acc"] - prev) * 100, 2)
        prev = row["acc"]
    return rows


def build_architecture_summary(results, tags):
    """归并 SimpleCNN 多种子，并加入 AlexNet 主模型与小型 ResNet 对照。"""
    rows = []
    scnn = [r for r in results if r.get("model") == "simplecnn" and r.get("tag", "").startswith("simplecnn_s")]
    if scnn:
        acc = np.array([r["test_acc"] for r in scnn])
        f1 = np.array([r["test_f1"] for r in scnn])
        rows.append({
            "name": "SimpleCNN@28（3 种子）",
            "params_M": round4(scnn[0]["n_params_M"]),
            "acc": round4(acc.mean()),
            "acc_std": round4(acc.std(ddof=1)),
            "f1": round4(f1.mean()),
            "f1_std": round4(f1.std(ddof=1)),
            "note": "轻量 CNN，原始 28×28 输入",
            "source": "exp_simplecnn_s0/s1/s2.json",
        })

    main = tags.get("alexnet_long_bn_aug")
    if main:
        rows.append(metric_row("AlexNet@224（主模型）", main, "40 轮 BN+增强"))

    resnet_eval = read_json(os.path.join(OUT_DIR, "resnet_eval.json"))
    resnet_exp = tags.get("resnet")
    if resnet_eval:
        rows.append({
            "name": "ResNetSmall@224",
            "params_M": round4(resnet_eval.get("params_M")),
            "acc": round4(resnet_eval.get("acc")),
            "acc_std": None,
            "f1": round4(resnet_eval.get("f1")),
            "f1_std": None,
            "shirt_f1": round4((resnet_eval.get("f1_per_class") or {}).get("衬衫")),
            "note": "小型残差网络架构对照",
            "source": "resnet_eval.json",
        })
    elif resnet_exp:
        rows.append(metric_row("ResNetSmall@224", resnet_exp, "小型残差网络架构对照"))
    return rows


def write_json(name, data):
    with open(os.path.join(OUT_DIR, name), "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def plot_compare(component_rows, arch_rows):
    """绘制关键对照实验准确率柱状图。"""
    rows = component_rows + [r for r in arch_rows if r["name"].startswith("SimpleCNN") or r["name"].startswith("ResNet")]
    labels = ["15轮\nLRN", "40轮\nLRN", "40轮\nBN", "BN+增强\n主模型"]
    labels += ["SimpleCNN\n3种子", "ResNet\n对照"][: max(0, len(rows) - len(labels))]
    accs = [r["acc"] for r in rows]
    errs = [r.get("acc_std") or 0 for r in rows]
    colors = ["#6B7280", "#4C72B0", "#55A868", "#C44E52", "#8172B3", "#CCB974"]

    plt.figure(figsize=(8.2, 4.8))
    bars = plt.bar(labels, accs, yerr=errs, capsize=5, color=colors[:len(rows)], alpha=0.92)
    for b, a in zip(bars, accs):
        plt.text(b.get_x() + b.get_width() / 2, a + 0.001, f"{a:.4f}",
                 ha="center", va="bottom", fontsize=9)
    plt.ylim(0.90, 0.955)
    plt.ylabel("测试集准确率")
    plt.title("Fashion-MNIST 关键对照实验准确率汇总")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "exp_compare.png"), dpi=150)
    plt.close()


def main():
    set_chinese_font()
    results = load_exp_results()
    tags = by_tag(results)
    required = ["alexnet_long_base", "alexnet_long_bn", "alexnet_long_bn_aug"]
    missing = [t for t in required if t not in tags]
    if missing:
        raise FileNotFoundError(f"缺少关键实验 JSON: {missing}")

    component_rows = build_component_ablation(tags)
    arch_rows = build_architecture_summary(results, tags)
    summary = {
        "component_ablation": component_rows,
        "architecture_compare": arch_rows,
        "note": "按明确 tag 聚合；不再使用粗粒度 (model, use_lrn, augment) 匹配。",
    }
    write_json("experiments_summary.json", summary)
    write_json("component_ablation_summary.json", component_rows)
    write_json("architecture_summary.json", arch_rows)
    write_json("improve_summary.json", {
        "baseline_15ep": component_rows[0]["acc"],
        "long40_lrn": component_rows[1]["acc"],
        "bn40": component_rows[2]["acc"],
        "bn40_aug": component_rows[3]["acc"],
        "macro_f1": {
            "baseline_15ep": component_rows[0]["f1"],
            "long40_lrn": component_rows[1]["f1"],
            "bn40": component_rows[2]["f1"],
            "bn40_aug": component_rows[3]["f1"],
        },
        "衬衫F1": {
            "baseline": component_rows[0]["shirt_f1"],
            "long40_lrn": component_rows[1]["shirt_f1"],
            "bn40": component_rows[2]["shirt_f1"],
            "bn_aug": component_rows[3]["shirt_f1"],
        },
    })

    print("组件消融：")
    print(f"{'配置':<26}{'参数量(M)':>10}{'测试准确率':>12}{'macro-F1':>12}{'衬衫F1':>10}")
    for r in component_rows:
        print(f"{r['name']:<26}{r['params_M']:>10.3f}{r['acc']:>12.4f}{r['f1']:>12.4f}{r['shirt_f1']:>10.4f}")

    print("\n架构对照：")
    print(f"{'模型':<24}{'参数量(M)':>10}{'测试准确率':>12}{'macro-F1':>12}")
    for r in arch_rows:
        acc = f"{r['acc']:.4f}" + (f"±{r['acc_std']:.4f}" if r.get("acc_std") else "")
        f1 = f"{r['f1']:.4f}" + (f"±{r['f1_std']:.4f}" if r.get("f1_std") else "")
        print(f"{r['name']:<24}{r['params_M']:>10.3f}{acc:>14}{f1:>12}")

    plot_compare(component_rows, arch_rows)
    print(f"\n[聚合] 汇总 JSON 与 exp_compare.png 已保存到 {OUT_DIR}")


if __name__ == "__main__":
    main()
