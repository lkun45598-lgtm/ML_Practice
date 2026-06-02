# -*- coding: utf-8 -*-
"""对照实验统一运行器：训练一个模型变体并在测试集评估，结果写入独立 JSON。

支持的变体：SimpleCNN 基线、AlexNet（基线/去LRN消融/数据增强）。
每次运行写出 outputs/exp_<tag>.json，便于多 GPU 并行而不发生写冲突；
聚合由 aggregate_experiments.py 完成。

示例：
  python experiments.py --model simplecnn --img-size 28 --seed 0 --epochs 10 --tag simplecnn_s0
  python experiments.py --model alexnet --img-size 224 --no-lrn --seed 0 --epochs 15 --tag alexnet_nolrn
  python experiments.py --model alexnet --img-size 224 --augment --seed 0 --epochs 15 --tag alexnet_aug
"""
import os
import json
import copy
import argparse
import torch
import torch.nn as nn

from data import get_loaders
from alexnet import AlexNet
from simplecnn import SimpleCNN
from resnet_small import ResNetSmall

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "outputs")
os.makedirs(OUT_DIR, exist_ok=True)


def run_epoch(model, loader, criterion, optimizer, device, train, scaler=None, mixup_alpha=0.0):
    model.train(train)
    total, correct, loss_sum = 0, 0, 0.0
    use_amp = scaler is not None
    dev_type = "cuda" if device.type == "cuda" else "cpu"
    use_mixup = train and mixup_alpha > 0
    beta = torch.distributions.Beta(mixup_alpha, mixup_alpha) if use_mixup else None
    with torch.set_grad_enabled(train):
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            if train:
                optimizer.zero_grad()
            with torch.autocast(device_type=dev_type, enabled=use_amp):
                if use_mixup:                          # MixUp：线性混合样本与标签，强正则
                    lam = float(beta.sample())
                    idx = torch.randperm(xb.size(0), device=device)
                    xb = lam * xb + (1 - lam) * xb[idx]
                    out = model(xb)
                    loss = lam * criterion(out, yb) + (1 - lam) * criterion(out, yb[idx])
                else:
                    out = model(xb)
                    loss = criterion(out, yb)
            if train:
                if use_amp:                       # 混合精度：scaler 防止 fp16 梯度下溢
                    scaler.scale(loss).backward(); scaler.step(optimizer); scaler.update()
                else:
                    loss.backward(); optimizer.step()
            loss_sum += loss.item() * xb.size(0)
            correct += (out.argmax(1) == yb).sum().item()
            total += xb.size(0)
    return loss_sum / total, correct / total


class FocalLoss(nn.Module):
    """Focal Loss：对难分样本加权，缓解“易分样本主导梯度”的问题。gamma 越大越聚焦难样本。"""

    def __init__(self, gamma=2.0):
        super().__init__()
        self.gamma = gamma

    def forward(self, logits, target):
        import torch.nn.functional as F
        ce = F.cross_entropy(logits, target, reduction="none")
        pt = torch.exp(-ce)
        return ((1 - pt) ** self.gamma * ce).mean()


@torch.no_grad()
def test_metrics(model, loader, device):
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support
    model.eval()
    ys, ps = [], []
    for xb, yb in loader:
        ps.append(model(xb.to(device)).argmax(1).cpu()); ys.append(yb)
    import torch as _t
    y = _t.cat(ys).numpy(); p = _t.cat(ps).numpy()
    acc = accuracy_score(y, p)
    pr, rc, f1, _ = precision_recall_fscore_support(y, p, average="macro", zero_division=0)
    # 每类 F1（用于困难类对比）
    _, _, f1_cls, _ = precision_recall_fscore_support(y, p, average=None, zero_division=0)
    return float(acc), float(pr), float(rc), float(f1), [round(float(x), 4) for x in f1_cls]


def build_model(name, use_lrn, use_bn=False):
    if name == "simplecnn":
        return SimpleCNN(num_classes=10, in_channels=1)
    if name == "resnet":
        return ResNetSmall(num_classes=10, in_channels=1)
    return AlexNet(num_classes=10, in_channels=1, use_lrn=use_lrn, use_bn=use_bn)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["simplecnn", "alexnet", "resnet"], required=True)
    ap.add_argument("--img-size", type=int, default=224)
    ap.add_argument("--augment", action="store_true")
    ap.add_argument("--no-lrn", action="store_true", help="AlexNet 去掉 LRN 的消融")
    ap.add_argument("--bn", action="store_true", help="AlexNet 用 BatchNorm 替代 LRN")
    ap.add_argument("--cosine", action="store_true", help="使用余弦退火学习率(适合更长训练)")
    ap.add_argument("--loss", choices=["ce", "focal"], default="ce", help="损失函数")
    ap.add_argument("--label-smoothing", type=float, default=0.0, help="交叉熵标签平滑系数(0=关闭)")
    ap.add_argument("--amp", action="store_true", help="启用混合精度训练(加速、省显存)")
    ap.add_argument("--patience", type=int, default=0, help="早停耐心轮数(0=关闭，跑满 epochs)")
    ap.add_argument("--strong-aug", action="store_true", help="更强增强：平移+随机擦除")
    ap.add_argument("--mixup", type=float, default=0.0, help="MixUp 的 Beta 系数(0=关闭)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--batch-size", type=int, default=128)
    ap.add_argument("--lr", type=float, default=0.01)
    ap.add_argument("--subset", type=int, default=None)
    ap.add_argument("--save-ckpt", default=None, help="若给定路径，则保存最优权重(.pt)")
    ap.add_argument("--save-history", default=None, help="若给定路径，则保存逐轮训练曲线(.json)")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    device = torch.device(args.device)
    if device.type == "cuda":
        torch.backends.cudnn.benchmark = True   # 固定输入尺寸下自动选最快卷积算法，加速
    use_lrn = not args.no_lrn
    print(f"[{args.tag}] model={args.model} img={args.img_size} aug={args.augment} "
          f"lrn={use_lrn} seed={args.seed} epochs={args.epochs} device={device}")

    train_loader, val_loader, test_loader = get_loaders(
        batch_size=args.batch_size, subset=args.subset, seed=args.seed,
        img_size=args.img_size, augment=args.augment, strong_aug=args.strong_aug)

    model = build_model(args.model, use_lrn, use_bn=args.bn).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    if args.loss == "focal":
        criterion = FocalLoss(gamma=2.0)
    else:
        criterion = nn.CrossEntropyLoss(label_smoothing=args.label_smoothing)
    optimizer = torch.optim.SGD(model.parameters(), lr=args.lr, momentum=0.9, weight_decay=5e-4)
    if args.cosine:
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    else:
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.1)
    scaler = torch.cuda.amp.GradScaler() if (args.amp and device.type == "cuda") else None

    import time
    best_val, best_state, best_epoch = 0.0, None, 0
    no_improve, stopped_epoch = 0, args.epochs
    epoch_times = []
    history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}
    for ep in range(1, args.epochs + 1):
        t0 = time.time()
        tr_loss, tr_acc = run_epoch(model, train_loader, criterion, optimizer, device, True,
                                    scaler, mixup_alpha=args.mixup)
        va_loss, va_acc = run_epoch(model, val_loader, criterion, optimizer, device, False)
        scheduler.step()
        epoch_times.append(time.time() - t0)
        history["train_loss"].append(tr_loss); history["val_loss"].append(va_loss)
        history["train_acc"].append(tr_acc); history["val_acc"].append(va_acc)
        print(f"[{args.tag}] epoch {ep:2d} train_acc={tr_acc:.4f} val_acc={va_acc:.4f} "
              f"({epoch_times[-1]:.1f}s)")
        if va_acc > best_val:
            best_val = va_acc; best_epoch = ep
            best_state = copy.deepcopy(model.state_dict())
            no_improve = 0
        else:
            no_improve += 1
            if args.patience > 0 and no_improve >= args.patience:
                stopped_epoch = ep
                print(f"[{args.tag}] 早停触发：第 {ep} 轮（最优在第 {best_epoch} 轮 val={best_val:.4f}）")
                break
    sec_per_epoch = sum(epoch_times) / len(epoch_times)
    print(f"[{args.tag}] 平均每轮 {sec_per_epoch:.1f}s，共 {len(epoch_times)} 轮 "
          f"(amp={bool(scaler)})")

    model.load_state_dict(best_state)
    if args.save_ckpt:
        torch.save(best_state, args.save_ckpt)
        print(f"[{args.tag}] 最优权重已保存 -> {args.save_ckpt}")
    if args.save_history:
        with open(args.save_history, "w") as f:
            json.dump(history, f)
        print(f"[{args.tag}] 训练曲线已保存 -> {args.save_history}")
    acc, pr, rc, f1, f1_cls = test_metrics(model, test_loader, device)
    result = {"tag": args.tag, "model": args.model, "img_size": args.img_size,
              "augment": args.augment, "use_lrn": use_lrn, "use_bn": args.bn,
              "cosine": args.cosine, "loss": args.loss,
              "label_smoothing": args.label_smoothing, "amp": bool(scaler),
              "patience": args.patience, "stopped_epoch": stopped_epoch,
              "best_epoch": best_epoch, "sec_per_epoch": round(sec_per_epoch, 2),
              "seed": args.seed,
              "epochs": args.epochs, "batch_size": args.batch_size, "lr": args.lr,
              "n_params_M": round(n_params / 1e6, 3), "best_val_acc": round(best_val, 4),
              "test_acc": round(acc, 4), "test_precision": round(pr, 4),
              "test_recall": round(rc, 4), "test_f1": round(f1, 4), "f1_per_class": f1_cls}
    with open(os.path.join(OUT_DIR, f"exp_{args.tag}.json"), "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[{args.tag}] 完成 test_acc={acc:.4f} f1={f1:.4f} -> exp_{args.tag}.json")


if __name__ == "__main__":
    main()
