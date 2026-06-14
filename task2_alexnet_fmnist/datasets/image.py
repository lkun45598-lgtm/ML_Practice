# -*- coding: utf-8 -*-
"""通用彩色图像数据集加载器（ImageFolder 风格）。

把手写 AlexNet / SimpleCNN 从 Fashion-MNIST 扩展到三个真实彩色图像数据集：
- flowers  : Kaggle Flowers Recognition，5 类花卉，约 4317 张
- garbage  : Kaggle Garbage Classification，6 类，约 2527 张
- catsdogs : Microsoft Cats vs. Dogs，2 类，约 25000 张（含少量损坏文件，自动跳过）

与 data.py（Fashion-MNIST）解耦：这些数据集是 3 通道、无官方 train/test 划分，
统一用 ImageNet 归一化 + 按种子的分层 70/15/15 划分，并在首次扫描时缓存有效样本清单。
"""
import os
import json
import collections
import torch
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True          # 容忍截断 JPEG

from task2_alexnet_fmnist import DATA_DIR

# ImageNet 三通道均值/方差：真实彩色照片的通用归一化
_MEAN = (0.485, 0.456, 0.406)
_STD = (0.229, 0.224, 0.225)

# 解压后类别根目录候选（按优先级），运行时挑第一个含 >=2 个子目录的
_ROOTS = {
    "flowers": ["flowers_ds/flowers/flowers", "flowers_ds/flowers"],
    "garbage": ["garbage_ds/Garbage classification/Garbage classification",
                "garbage_ds/Garbage classification"],
    "catsdogs": ["catsdogs_ds/PetImages"],
}

# 数据集中文展示名（用于图表）
DATASET_CN = {"flowers": "Flowers 花卉", "garbage": "Garbage 垃圾分类",
              "catsdogs": "Cats vs Dogs 猫狗"}


def _find_root(dataset):
    for rel in _ROOTS[dataset]:
        p = os.path.join(DATA_DIR, rel)
        if os.path.isdir(p):
            subs = [d for d in os.listdir(p) if os.path.isdir(os.path.join(p, d))]
            if len(subs) >= 2:
                return p
    raise FileNotFoundError(f"找不到 {dataset} 的类别根目录；候选={_ROOTS[dataset]}，"
                            f"请确认 zip 已解压到 {DATA_DIR}")


def _is_valid_image(path):
    """跳过空文件/损坏图（Cats-vs-Dogs 有名的坑）。"""
    try:
        if os.path.getsize(path) == 0:
            return False
        with Image.open(path) as im:
            im.verify()
        return True
    except Exception:
        return False


def _scan_samples(root):
    """扫描类别目录，返回 (samples=[(path,label)], classes, skipped)。一次性校验有效性。"""
    classes = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))
    cls_to_idx = {c: i for i, c in enumerate(classes)}
    samples, skipped = [], 0
    for c in classes:
        cdir = os.path.join(root, c)
        for fn in sorted(os.listdir(cdir)):
            p = os.path.join(cdir, fn)
            if not os.path.isfile(p):
                continue
            if _is_valid_image(p):
                samples.append((p, cls_to_idx[c]))
            else:
                skipped += 1
    return samples, classes, skipped


def _load_samples_cached(dataset, root, rescan=False):
    """缓存有效样本清单，避免每次（×3 个 split 数据集 / 多次 run）重复校验 2.5 万张图。"""
    cache = os.path.join(DATA_DIR, f".cache_{dataset}_samples.json")
    if not rescan and os.path.exists(cache):
        with open(cache) as f:
            d = json.load(f)
        if d.get("root") == root:
            return [(p, l) for p, l in d["samples"]], d["classes"], d["skipped"]
    samples, classes, skipped = _scan_samples(root)
    with open(cache, "w") as f:
        json.dump({"root": root, "classes": classes, "skipped": skipped,
                   "samples": samples}, f)
    return samples, classes, skipped


class ListImageDataset(Dataset):
    """持有 (path,label) 清单 + 一套 transform；可低成本地按不同 transform 复用同一份样本。"""

    def __init__(self, samples, transform):
        self.samples = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        path, label = self.samples[i]
        with Image.open(path) as im:
            img = im.convert("RGB")
        return self.transform(img), label


def _make_tf(img_size, augment, strong=False):
    """构造图像变换。strong=True 时启用针对小数据集的强增强：
    随机裁剪缩放 + 颜色抖动 + 翻转旋转，并在张量化后加随机擦除。"""
    if strong:
        ops = [transforms.RandomResizedCrop(img_size, scale=(0.6, 1.0)),
               transforms.RandomHorizontalFlip(),
               transforms.RandomRotation(15),
               transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.05),
               transforms.ToTensor(), transforms.Normalize(_MEAN, _STD),
               transforms.RandomErasing(p=0.25)]
        return transforms.Compose(ops)
    ops = [transforms.Resize((img_size, img_size))]
    if augment:
        ops += [transforms.RandomHorizontalFlip(), transforms.RandomRotation(15)]
    ops += [transforms.ToTensor(), transforms.Normalize(_MEAN, _STD)]
    return transforms.Compose(ops)


def get_image_loaders(dataset, batch_size=64, img_size=224, augment=False, seed=42,
                      val_ratio=0.15, test_ratio=0.15, num_workers=4, subset=None,
                      strong_aug=False):
    """返回 (train_loader, val_loader, test_loader, info)。

    分层（按类）70/15/15 划分；训练集可增强，验证/测试集恒定无增强。
    subset: 给整数则裁剪为小样本冒烟测试。
    """
    root = _find_root(dataset)
    samples, classes, skipped = _load_samples_cached(dataset, root)

    by_cls = collections.defaultdict(list)
    for idx, (_, lbl) in enumerate(samples):
        by_cls[lbl].append(idx)
    g = torch.Generator().manual_seed(seed)
    train_idx, val_idx, test_idx = [], [], []
    for lbl, idxs in by_cls.items():
        perm = [idxs[i] for i in torch.randperm(len(idxs), generator=g).tolist()]
        n = len(perm); nt = int(n * test_ratio); nv = int(n * val_ratio)
        test_idx += perm[:nt]; val_idx += perm[nt:nt + nv]; train_idx += perm[nt + nv:]

    train_tf, eval_tf = _make_tf(img_size, augment, strong=strong_aug), _make_tf(img_size, False)
    pick = lambda ids: [samples[i] for i in ids]
    train_ds = ListImageDataset(pick(train_idx), train_tf)
    val_ds = ListImageDataset(pick(val_idx), eval_tf)
    test_ds = ListImageDataset(pick(test_idx), eval_tf)
    if subset:                                  # 冒烟用：跨类随机抽样，避免只取到单一类别
        def _take(ds, k):
            k = min(k, len(ds.samples))
            sel = torch.randperm(len(ds.samples), generator=g)[:k].tolist()
            ds.samples = [ds.samples[i] for i in sel]
        _take(train_ds, subset)
        _take(val_ds, max(1, subset // 5))
        _take(test_ds, max(1, subset // 5))

    mk = lambda ds, sh: DataLoader(ds, batch_size=batch_size, shuffle=sh,
                                   num_workers=num_workers, pin_memory=True)
    train_class_counts = [0] * len(classes)
    for _, lbl in train_ds.samples:
        train_class_counts[lbl] += 1
    info = {"dataset": dataset, "num_classes": len(classes), "in_channels": 3,
            "class_names": classes, "skipped": skipped,
            "n_train": len(train_ds), "n_val": len(val_ds), "n_test": len(test_ds),
            "train_class_counts": train_class_counts}
    return mk(train_ds, True), mk(val_ds, False), mk(test_ds, False), info


if __name__ == "__main__":
    import sys
    ds = sys.argv[1] if len(sys.argv) > 1 else "flowers"
    tr, va, te, info = get_image_loaders(ds, batch_size=8, img_size=64, subset=64)
    xb, yb = next(iter(tr))
    print("数据集:", ds, "信息:", info)
    print("batch:", tuple(xb.shape), "标签样例:", yb[:8].tolist())
    print("[自检] 图像加载通过")
