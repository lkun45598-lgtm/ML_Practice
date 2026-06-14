# -*- coding: utf-8 -*-
"""[旧版/基础脚本] 训练手写 AlexNet 的最小训练循环（默认 LRN、无 BatchNorm）。

注意：本项目的主入口是 experiments.py（统一运行器，支持 --bn/--augment/--cosine/--dataset/
--small-kernel 等开关，并保存 outputs/alexnet_best.pt）。主模型结果均由 experiments.py 产生；
evaluate.py 默认评估 BatchNorm 版主模型。train.py 仅作为最简训练流程的演示保留，若用它训练出的
（LRN 版）检查点喂给 evaluate.py，请加 `--no-bn` 使架构一致，否则结构不匹配会加载失败。
"""
import os
import json
import argparse
import torch
import torch.nn as nn

from alexnet import AlexNet
from data import get_loaders

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "outputs")
os.makedirs(OUT_DIR, exist_ok=True)


def run_epoch(model, loader, criterion, optimizer, device, train=True):
    """跑一个 epoch，返回 (平均loss, 准确率)。train=False 时不更新参数。"""
    model.train(train)
    total, correct, loss_sum = 0, 0, 0.0
    with torch.set_grad_enabled(train):
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            if train:
                optimizer.zero_grad()
            out = model(xb)
            loss = criterion(out, yb)
            if train:
                loss.backward(); optimizer.step()
            loss_sum += loss.item() * xb.size(0)
            correct += (out.argmax(1) == yb).sum().item()
            total += xb.size(0)
    return loss_sum / total, correct / total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--batch-size", type=int, default=128)
    ap.add_argument("--lr", type=float, default=0.01)
    ap.add_argument("--subset", type=int, default=None, help="冒烟测试用样本数")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    device = torch.device(args.device)
    print(f"[训练] 设备={device} epochs={args.epochs} subset={args.subset}")
    train_loader, val_loader, _ = get_loaders(
        batch_size=args.batch_size, subset=args.subset)

    model = AlexNet(num_classes=10, in_channels=1).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.SGD(model.parameters(), lr=args.lr, momentum=0.9,
                                weight_decay=5e-4)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.1)

    history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}
    best_val = 0.0
    for ep in range(1, args.epochs + 1):
        tr_loss, tr_acc = run_epoch(model, train_loader, criterion, optimizer, device, True)
        va_loss, va_acc = run_epoch(model, val_loader, criterion, optimizer, device, False)
        scheduler.step()
        history["train_loss"].append(tr_loss); history["train_acc"].append(tr_acc)
        history["val_loss"].append(va_loss); history["val_acc"].append(va_acc)
        print(f"[epoch {ep:2d}] train loss={tr_loss:.4f} acc={tr_acc:.4f} | "
              f"val loss={va_loss:.4f} acc={va_acc:.4f}")
        if va_acc > best_val:
            best_val = va_acc
            torch.save(model.state_dict(), os.path.join(OUT_DIR, "alexnet_best.pt"))
            print(f"        ↳ 保存最优模型 (val_acc={va_acc:.4f})")

    with open(os.path.join(OUT_DIR, "history.json"), "w") as f:
        json.dump(history, f)
    print(f"[训练] 完成，最优 val_acc={best_val:.4f}")


if __name__ == "__main__":
    main()
