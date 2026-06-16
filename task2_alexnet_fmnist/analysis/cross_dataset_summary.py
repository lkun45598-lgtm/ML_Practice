# -*- coding: utf-8 -*-
"""聚合跨数据集对照实验，量化「任务难度」与「架构演进：大核大头 → 小核深网」。

三个模型同台对照：
- AlexNet@224   大核大头（58M），经典实现
- ResNetSmall@64 小核(3×3)+更深(13层)+残差+全局平均池化（2.8M）
- SimpleCNN@64  浅层轻量基线（0.39M）

读取 outputs/exp_x_*.json + 复用 Fashion-MNIST 既有结果，输出：
- outputs/cross_dataset_summary.json
- outputs/cross_dataset_acc.png   难度阶梯 + 三模型分组柱状
- outputs/cross_dataset_gap.png    过拟合对比：AlexNet vs ResNet 的训练/验证 gap
"""
import os
import sys
import json
import glob
import numpy as np
import matplotlib.pyplot as plt

from common.zh_font import set_chinese_font

from task2_alexnet_fmnist import OUT_DIR as OUT

# 数据集固定展示顺序（fmnist, catsdogs, flowers, garbage, cifar10）
DS = [
    ("fmnist", "Fashion-MNIST\n灰度28·10类", 10),
    ("catsdogs", "Cats vs Dogs\n彩色·2类", 2),
    ("flowers", "Flowers\n彩色·5类", 5),
    ("garbage", "Garbage\n彩色·6类", 6),
    ("cifar10", "CIFAR-10\n彩色32·10类", 10),
]


def rj(path):
    return json.load(open(path)) if os.path.exists(path) else None


def first_exp(*tags):
    for t in tags:
        d = rj(os.path.join(OUT, f"exp_{t}.json"))
        if d:
            return d
    return None


def agg(glob_pat, smoke_tag=None):
    """多种子聚合 → (acc_mean, acc_std, params, gap_mean)；无则返回 None。"""
    seeds = [rj(p) for p in sorted(glob.glob(os.path.join(OUT, glob_pat)))]
    seeds = [d for d in seeds if d]
    if not seeds and smoke_tag:
        seeds = [d for d in [first_exp(smoke_tag)] if d]
    if not seeds:
        return None
    acc = np.array([d["test_acc"] for d in seeds])
    gap = np.array([d.get("train_val_gap") or 0 for d in seeds])
    std = float(acc.std(ddof=1)) if len(acc) > 1 else None
    return float(acc.mean()), std, seeds[0]["n_params_M"], float(gap.mean())


def alexnet_of(ds):
    if ds == "fmnist":
        d = first_exp("alexnet_long_bn_aug")
        return (d["test_acc"], None, d.get("n_params_M"), d.get("train_val_gap")) if d else None
    if ds == "cifar10":                 # CIFAR-10 走调好的 _best 三种子（与 resnet/scnn 同口径）
        return agg("exp_x_alex_cifar10_best_s*.json")
    return agg(f"exp_x_alex_{ds}.json", f"x_alex_{ds}_smoke")


def resnet_of(ds):
    if ds == "fmnist":
        d = first_exp("resnet")          # 既有 Fashion ResNet 结果
        return (d["test_acc"], None, d.get("n_params_M"), d.get("train_val_gap")) if d else None
    if ds == "cifar10":
        return agg("exp_x_resnet_cifar10_best_s*.json")
    return agg(f"exp_x_resnet_{ds}_s*.json")


def simplecnn_of(ds):
    if ds == "fmnist":
        return agg("exp_simplecnn_s*.json")
    if ds == "cifar10":
        return agg("exp_x_scnn_cifar10_best_s*.json")
    return agg(f"exp_x_scnn_{ds}_s*.json", f"x_scnn_{ds}_smoke")


def main():
    set_chinese_font()
    rows = []
    for ds, label, k in DS:
        a, r, s = alexnet_of(ds), resnet_of(ds), simplecnn_of(ds)
        rows.append({
            "dataset": ds, "label": label.replace("\n", " "), "num_classes": k,
            "random_baseline": round(1.0 / k, 4),
            "alexnet_acc": round(a[0], 4) if a else None,
            "alexnet_params_M": a[2] if a else None,
            "alexnet_gap": round(a[3], 4) if a and a[3] is not None else None,
            "resnet_acc": round(r[0], 4) if r else None,
            "resnet_acc_std": round(r[1], 4) if r and r[1] else None,
            "resnet_params_M": r[2] if r else None,
            "resnet_gap": round(r[3], 4) if r and r[3] is not None else None,
            "simplecnn_acc": round(s[0], 4) if s else None,
            "simplecnn_acc_std": round(s[1], 4) if s and s[1] else None,
            "simplecnn_params_M": s[2] if s else None,
            "resnet_minus_alex_pp": round((r[0] - a[0]) * 100, 2) if (r and a) else None,
        })

    json.dump({"rows": rows, "note": "三模型：AlexNet@224 / ResNetSmall@64 / SimpleCNN@64"},
              open(os.path.join(OUT, "cross_dataset_summary.json"), "w"),
              ensure_ascii=False, indent=2)

    # ---- 表 ----
    print(f"{'数据集':<14}{'AlexNet 58M':>12}{'ResNet 2.8M':>13}{'SimpleCNN 0.4M':>15}{'R−A(pp)':>9}")
    for r in rows:
        def fmt(a, sd):
            return "—" if a is None else f"{a:.4f}" + (f"±{sd:.3f}" if sd else "")
        print(f"{r['label']:<14}{fmt(r['alexnet_acc'],None):>12}{fmt(r['resnet_acc'],r['resnet_acc_std']):>13}"
              f"{fmt(r['simplecnn_acc'],r['simplecnn_acc_std']):>15}"
              f"{(r['resnet_minus_alex_pp'] if r['resnet_minus_alex_pp'] is not None else 0):>9.2f}")

    # ---- 图1：难度阶梯 + 三模型分组柱状 ----
    labels = [d[1] for d in DS]
    x = np.arange(len(DS)); w = 0.26
    A = [r["alexnet_acc"] or 0 for r in rows]
    R = [r["resnet_acc"] or 0 for r in rows]
    S = [r["simplecnn_acc"] or 0 for r in rows]
    Re = [r["resnet_acc_std"] or 0 for r in rows]
    Se = [r["simplecnn_acc_std"] or 0 for r in rows]
    rnd = [r["random_baseline"] for r in rows]
    plt.figure(figsize=(10, 5.4))
    b1 = plt.bar(x - w, A, w, label="AlexNet@224 大核大头 (58M)", color="#C44E52")
    b2 = plt.bar(x, R, w, yerr=Re, capsize=3, label="ResNetSmall@64 小核+深 (2.8M)", color="#55A868")
    b3 = plt.bar(x + w, S, w, yerr=Se, capsize=3, label="SimpleCNN@64 浅层 (0.4M)", color="#4C72B0")
    plt.plot(x, rnd, "k--o", lw=1.1, ms=4, label="随机基线 1/类别数")
    for bs, vs in [(b1, A), (b2, R), (b3, S)]:
        for b, v in zip(bs, vs):
            if v:
                plt.text(b.get_x() + b.get_width() / 2, v + 0.012, f"{v:.2f}", ha="center", va="bottom", fontsize=7.5)
    plt.xticks(x, labels, fontsize=9)
    plt.ylim(0, 1.08); plt.ylabel("测试集准确率")
    plt.title("任务难度阶梯 + 架构演进：大核大头 → 小核深网（跨五个数据集）")
    plt.legend(loc="lower left", fontsize=8.5, ncol=1); plt.grid(axis="y", alpha=0.3)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "cross_dataset_acc.png"), dpi=150); plt.close()

    # ---- 图2：过拟合 gap，AlexNet vs ResNet ----
    gd = [(r["label"], r["alexnet_gap"], r["resnet_gap"]) for r in rows
          if r["alexnet_gap"] is not None or r["resnet_gap"] is not None]
    if gd:
        gl = [g[0] for g in gd]; xx = np.arange(len(gd)); w2 = 0.36
        av = [(g[1] or 0) * 100 for g in gd]; rv = [(g[2] or 0) * 100 for g in gd]
        plt.figure(figsize=(8.5, 4.6))
        ba = plt.bar(xx - w2 / 2, av, w2, label="AlexNet (58M)", color="#C44E52")
        br = plt.bar(xx + w2 / 2, rv, w2, label="ResNetSmall (2.8M)", color="#55A868")
        for bs, vs in [(ba, av), (br, rv)]:
            for b, v in zip(bs, vs):
                if v:
                    plt.text(b.get_x() + b.get_width() / 2, v + 0.2, f"{v:.1f}", ha="center", va="bottom", fontsize=8)
        plt.xticks(xx, gl, fontsize=9)
        plt.ylabel("训练-验证准确率差 (pp)")
        plt.title("过拟合程度：模型够强后，瓶颈从「容量」转为「数据量」")
        plt.legend(fontsize=9); plt.grid(axis="y", alpha=0.3); plt.tight_layout()
        plt.savefig(os.path.join(OUT, "cross_dataset_gap.png"), dpi=150); plt.close()

    print(f"\n[聚合] -> cross_dataset_summary.json, cross_dataset_acc.png, cross_dataset_gap.png")


if __name__ == "__main__":
    main()
