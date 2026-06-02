# -*- coding: utf-8 -*-
"""评估手写 AlexNet：测试集指标、混淆矩阵、训练曲线、预测样例可视化。"""
import os
import json
import sys
import numpy as np
import torch
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (accuracy_score, precision_recall_fscore_support,
                             confusion_matrix, classification_report,
                             cohen_kappa_score, matthews_corrcoef, roc_auc_score)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.zh_font import set_chinese_font
from alexnet import AlexNet
from data import get_loaders, CLASS_NAMES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "outputs")
CKPT = os.path.join(OUT_DIR, "alexnet_best.pt")


def plot_curves():
    """从 history.json 画训练/验证 loss 与 acc 曲线。"""
    with open(os.path.join(OUT_DIR, "history.json")) as f:
        h = json.load(f)
    epochs = range(1, len(h["train_loss"]) + 1)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].plot(epochs, h["train_loss"], label="训练"); ax[0].plot(epochs, h["val_loss"], label="验证")
    ax[0].set_title("损失曲线"); ax[0].set_xlabel("epoch"); ax[0].set_ylabel("loss"); ax[0].legend()
    ax[1].plot(epochs, h["train_acc"], label="训练"); ax[1].plot(epochs, h["val_acc"], label="验证")
    ax[1].set_title("准确率曲线"); ax[1].set_xlabel("epoch"); ax[1].set_ylabel("acc"); ax[1].legend()
    plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, "curves.png"), dpi=150); plt.close()


@torch.no_grad()
def evaluate(device):
    """在测试集预测，返回 (y_true, y_pred, 部分图像)。"""
    _, _, test_loader = get_loaders(batch_size=256)
    # 主模型采用 BatchNorm（替代 LRN）+ 40 轮余弦退火 + 数据增强训练，详见正文第四章。
    model = AlexNet(num_classes=10, in_channels=1, use_bn=True).to(device)
    model.load_state_dict(torch.load(CKPT, map_location=device))
    model.eval()
    ys, ps, probs, sample_imgs, sample_meta = [], [], [], None, None
    for xb, yb in test_loader:
        out = model(xb.to(device))
        prob = out.softmax(1).cpu()          # 各类后验概率，用于 ROC-AUC
        pred = out.argmax(1).cpu()
        if sample_imgs is None:
            sample_imgs = xb[:12].cpu()
            sample_meta = (yb[:12].tolist(), pred[:12].tolist())
        ys.append(yb); ps.append(pred); probs.append(prob)
    return (torch.cat(ys).numpy(), torch.cat(ps).numpy(),
            torch.cat(probs).numpy(), sample_imgs, sample_meta)


def plot_samples(imgs, meta):
    """画 12 张预测样例（标题: 真/预测）。"""
    y_true, y_pred = meta
    plt.figure(figsize=(10, 6))
    for i in range(min(12, len(imgs))):
        plt.subplot(3, 4, i + 1)
        plt.imshow(imgs[i, 0], cmap="gray")
        c = "green" if y_true[i] == y_pred[i] else "red"
        plt.title(f"真:{CLASS_NAMES[y_true[i]]}\n预:{CLASS_NAMES[y_pred[i]]}", color=c, fontsize=8)
        plt.axis("off")
    plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, "samples.png"), dpi=150); plt.close()


def main():
    set_chinese_font()
    if not os.path.exists(CKPT):
        raise FileNotFoundError(
            f"未找到模型文件 {CKPT}，请先运行主模型训练命令："
            "`python task2_alexnet_fmnist/experiments.py --model alexnet --bn --augment --cosine "
            "--epochs 40 --seed 0 --tag main --save-ckpt task2_alexnet_fmnist/outputs/alexnet_best.pt "
            "--save-history task2_alexnet_fmnist/outputs/history.json`。")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    plot_curves()
    y_true, y_pred, y_prob, imgs, meta = evaluate(device)
    acc = accuracy_score(y_true, y_pred)
    p, r, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="macro")
    kappa = cohen_kappa_score(y_true, y_pred)                          # 一致性（排除碰运气）
    mcc = matthews_corrcoef(y_true, y_pred)                            # Matthews 相关系数
    auc = roc_auc_score(y_true, y_prob, multi_class="ovr", average="macro")  # 宏平均ROC-AUC(OvR)
    print(f"[评估] 测试集 acc={acc:.4f} 精确率={p:.4f} 召回率={r:.4f} F1={f1:.4f}")
    print(f"[评估] 宏ROC-AUC={auc:.4f} CohenKappa={kappa:.4f} MCC={mcc:.4f}")
    print(classification_report(y_true, y_pred, target_names=CLASS_NAMES))

    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(8, 7))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES)
    plt.title("AlexNet 测试集混淆矩阵"); plt.xlabel("预测"); plt.ylabel("真实")
    plt.xticks(rotation=45, ha="right"); plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "confusion_matrix.png"), dpi=150); plt.close()

    plot_samples(imgs, meta)
    with open(os.path.join(OUT_DIR, "test_metrics.json"), "w") as f:
        json.dump({"acc": acc, "precision": p, "recall": r, "f1": f1,
                   "roc_auc": float(auc), "kappa": float(kappa), "mcc": float(mcc)}, f)
    print(f"[评估] 图与指标已保存到 {OUT_DIR}")


if __name__ == "__main__":
    main()
