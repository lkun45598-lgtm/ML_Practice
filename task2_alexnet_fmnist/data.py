# -*- coding: utf-8 -*-
"""Fashion-MNIST 数据加载：下载、变换(Resize224)、train/val/test 三划分。"""
import os
import torch
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")

CLASS_NAMES = ["T恤", "裤子", "套衫", "连衣裙", "外套",
               "凉鞋", "衬衫", "运动鞋", "包", "短靴"]

# Fashion-MNIST 单通道均值/方差
_MEAN, _STD = (0.2860,), (0.3530,)


def _transform():
    return transforms.Compose([
        transforms.Resize(224),
        transforms.ToTensor(),
        transforms.Normalize(_MEAN, _STD),
    ])


def get_loaders(batch_size=128, val_ratio=0.1, num_workers=4, subset=None, seed=42):
    """返回 (train_loader, val_loader, test_loader)。
    subset: 若给整数，仅取该数量训练样本用于冒烟测试。"""
    tf = _transform()
    full_train = datasets.FashionMNIST(DATA_DIR, train=True, download=True, transform=tf)
    test_set = datasets.FashionMNIST(DATA_DIR, train=False, download=True, transform=tf)

    if subset is not None:
        full_train = torch.utils.data.Subset(full_train, range(subset))
        test_set = torch.utils.data.Subset(test_set, range(min(subset, len(test_set))))

    n_val = int(len(full_train) * val_ratio)
    n_train = len(full_train) - n_val
    g = torch.Generator().manual_seed(seed)
    train_set, val_set = random_split(full_train, [n_train, n_val], generator=g)

    mk = lambda ds, sh: DataLoader(ds, batch_size=batch_size, shuffle=sh,
                                   num_workers=num_workers, pin_memory=True)
    return mk(train_set, True), mk(val_set, False), mk(test_set, False)


if __name__ == "__main__":
    tr, va, te = get_loaders(batch_size=8, subset=64)
    xb, yb = next(iter(tr))
    print("batch:", tuple(xb.shape), "标签样例:", yb[:8].tolist())
    assert xb.shape[1:] == (1, 224, 224)
    print("[自检] 数据加载通过；train/val/test 批数:", len(tr), len(va), len(te))
