# -*- coding: utf-8 -*-
"""Fashion-MNIST 数据加载：下载、变换、train/val/test 三划分。

支持可配置输入尺寸 img_size 与训练集数据增强 augment（验证/测试集始终不增强）。
默认 img_size=224、augment=False，与基线 AlexNet 一致，保证向后兼容。
"""
import os
import torch
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")

CLASS_NAMES = ["T恤", "裤子", "套衫", "连衣裙", "外套",
               "凉鞋", "衬衫", "运动鞋", "包", "短靴"]

# Fashion-MNIST 单通道均值/方差
_MEAN, _STD = (0.2860,), (0.3530,)


def _make_tf(img_size, augment):
    """构造变换；augment=True 时加入随机水平翻转与小角度旋转（仅用于训练集）。"""
    ops = []
    if img_size != 28:
        ops.append(transforms.Resize(img_size))
    if augment:
        ops += [transforms.RandomHorizontalFlip(),
                transforms.RandomRotation(10)]
    ops += [transforms.ToTensor(), transforms.Normalize(_MEAN, _STD)]
    return transforms.Compose(ops)


def get_loaders(batch_size=128, val_ratio=0.1, num_workers=4, subset=None,
                seed=42, img_size=224, augment=False):
    """返回 (train_loader, val_loader, test_loader)。

    img_size: 输入边长（AlexNet 用 224，SimpleCNN 用 28）。
    augment:  仅对训练集启用数据增强；验证集与测试集始终使用无增强变换。
    subset:   若给整数，仅取该数量样本用于冒烟测试。
    """
    train_tf = _make_tf(img_size, augment)
    eval_tf = _make_tf(img_size, False)
    train_aug = datasets.FashionMNIST(DATA_DIR, train=True, download=True, transform=train_tf)
    train_eval = datasets.FashionMNIST(DATA_DIR, train=True, download=True, transform=eval_tf)
    test_set = datasets.FashionMNIST(DATA_DIR, train=False, download=True, transform=eval_tf)

    n_total = len(train_aug) if subset is None else min(subset, len(train_aug))
    g = torch.Generator().manual_seed(seed)
    perm = torch.randperm(n_total, generator=g).tolist()
    n_val = int(n_total * val_ratio)
    val_idx, train_idx = perm[:n_val], perm[n_val:]
    train_set = Subset(train_aug, train_idx)     # 训练集（可增强）
    val_set = Subset(train_eval, val_idx)        # 验证集（不增强）
    if subset is not None:
        test_set = Subset(test_set, range(min(subset, len(test_set))))

    mk = lambda ds, sh: DataLoader(ds, batch_size=batch_size, shuffle=sh,
                                   num_workers=num_workers, pin_memory=True)
    return mk(train_set, True), mk(val_set, False), mk(test_set, False)


if __name__ == "__main__":
    tr, va, te = get_loaders(batch_size=8, subset=64)
    xb, yb = next(iter(tr))
    print("batch:", tuple(xb.shape), "标签样例:", yb[:8].tolist())
    assert xb.shape[1:] == (1, 224, 224)
    print("[自检] 数据加载通过；train/val/test 批数:", len(tr), len(va), len(te))
