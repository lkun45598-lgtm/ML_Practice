# -*- coding: utf-8 -*-
"""CIFAR-10 数据加载：torchvision 自动下载，3 通道、10 类。

作为跨数据集对照中「数据充足的标准基准」加入：官方 train 50000 中切 10% 作验证集，
test 10000 独立不动。增强在原生 32×32 上完成（RandomCrop pad4 为 CIFAR 标准配方），
最后再缩放到目标尺寸，避免「先放大到 224 再裁回」破坏大输入模型。

与 fmnist.py 一致返回 (train, val, test, info) 四元组（info 供 experiments.py 取类别数等）。
"""
import torch
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms

from task2_alexnet_fmnist import DATA_DIR

# 数据集中文展示名（用于图表）
DATASET_CN = "CIFAR-10"

# CIFAR-10 三通道均值/方差（官方统计值）
_MEAN = (0.4914, 0.4822, 0.4465)
_STD = (0.2023, 0.1994, 0.2010)

CLASS_NAMES = ["airplane", "automobile", "bird", "cat", "deer",
               "dog", "frog", "horse", "ship", "truck"]


def get_cifar10_loaders(batch_size=128, img_size=224, augment=False, seed=42,
                        val_ratio=0.1, num_workers=4, subset=None, strong_aug=False):
    """返回 (train_loader, val_loader, test_loader, info)。

    img_size: 输入边长（AlexNet 用 224，ResNet/SimpleCNN 用原生 32）。
    augment:  仅对训练集启用；strong_aug 独立生效（不依赖 augment）。
    subset:   若给整数，仅取该数量样本用于冒烟测试。
    """
    def _make_tf(augment, strong=False):
        # 增强在原生 32×32 上完成（RandomCrop pad4 是 CIFAR 标准配方），最后再缩放到目标尺寸。
        ops = []
        if strong:
            ops += [transforms.RandomCrop(32, padding=4),
                    transforms.RandomHorizontalFlip(),
                    transforms.ColorJitter(0.2, 0.2, 0.2)]
        elif augment:
            ops += [transforms.RandomHorizontalFlip(),
                    transforms.RandomRotation(10)]
        if img_size != 32:
            ops.append(transforms.Resize(img_size))
        ops += [transforms.ToTensor(), transforms.Normalize(_MEAN, _STD)]
        return transforms.Compose(ops)

    train_tf = _make_tf(augment, strong=strong_aug)
    eval_tf = _make_tf(False)

    train_aug = datasets.CIFAR10(DATA_DIR, train=True, download=True, transform=train_tf)
    train_eval = datasets.CIFAR10(DATA_DIR, train=True, download=True, transform=eval_tf)
    test_set = datasets.CIFAR10(DATA_DIR, train=False, download=True, transform=eval_tf)

    n_total = len(train_aug) if subset is None else min(subset, len(train_aug))
    g = torch.Generator().manual_seed(seed)
    perm = torch.randperm(n_total, generator=g).tolist()
    n_val = int(n_total * val_ratio)
    val_idx, train_idx = perm[:n_val], perm[n_val:]

    train_ds = Subset(train_aug, train_idx)
    val_ds = Subset(train_eval, val_idx)
    if subset:
        test_set = Subset(test_set, range(min(subset, len(test_set))))

    mk = lambda ds, sh: DataLoader(ds, batch_size=batch_size, shuffle=sh,
                                   num_workers=num_workers, pin_memory=True)
    info = {"dataset": "cifar10", "num_classes": 10, "in_channels": 3,
            "class_names": CLASS_NAMES, "skipped": 0,
            "n_train": len(train_ds), "n_val": len(val_ds), "n_test": len(test_set),
            "train_class_counts": [int(n_total * (1 - val_ratio) / 10)] * 10}
    return mk(train_ds, True), mk(val_ds, False), mk(test_set, False), info


if __name__ == "__main__":
    tr, va, te, info = get_cifar10_loaders(batch_size=8, img_size=64, subset=64)
    xb, yb = next(iter(tr))
    print("batch:", tuple(xb.shape), "标签样例:", yb[:8].tolist(), "信息:", info)
    print("[自检] CIFAR-10 加载通过")
