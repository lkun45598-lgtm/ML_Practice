# -*- coding: utf-8 -*-
"""可解释性分析：用 Grad-CAM 可视化手写 AlexNet 在分类时“关注”图像的哪些区域。

对最后一个卷积层（Conv5）计算类激活映射，叠加到原图上，直观展示模型的判别依据。
需先有 outputs/alexnet_best.pt（由主模型训练命令生成）。
"""
import os
import sys
import numpy as np
import torch
import torch.nn.functional as F
import matplotlib.pyplot as plt

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.zh_font import set_chinese_font
from alexnet import AlexNet
from data import get_loaders, CLASS_NAMES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "outputs")
CKPT = os.path.join(OUT_DIR, "alexnet_best.pt")


def last_conv(model):
    """返回 features 中最后一个卷积层模块。"""
    conv = None
    for m in model.features:
        if isinstance(m, torch.nn.Conv2d):
            conv = m
    return conv


def grad_cam(model, x, target_layer, cls=None):
    """对单张图 x(1,1,224,224) 计算 Grad-CAM 热力图(224,224) 与预测类别。"""
    acts, grads = {}, {}
    h1 = target_layer.register_forward_hook(lambda m, i, o: acts.__setitem__("v", o))
    h2 = target_layer.register_full_backward_hook(lambda m, gi, go: grads.__setitem__("v", go[0]))
    logits = model(x)
    pred = int(logits.argmax(1)) if cls is None else cls
    model.zero_grad()
    logits[0, pred].backward()
    h1.remove(); h2.remove()
    a = acts["v"][0]                      # (C,H,W)
    g = grads["v"][0]                     # (C,H,W)
    w = g.mean(dim=(1, 2))                # (C,) 通道权重 = 梯度全局平均
    cam = F.relu((w[:, None, None] * a).sum(0))   # (H,W)
    cam = cam / (cam.max() + 1e-8)
    cam = F.interpolate(cam[None, None], size=(224, 224), mode="bilinear",
                        align_corners=False)[0, 0]
    return cam.detach().cpu().numpy(), pred


def main():
    set_chinese_font()
    if not os.path.exists(CKPT):
        raise FileNotFoundError(f"未找到 {CKPT}，请先运行 README 中的主模型训练命令。")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = AlexNet(num_classes=10, in_channels=1, use_bn=True).to(device)
    model.load_state_dict(torch.load(CKPT, map_location=device))
    model.eval()
    # 关闭 inplace ReLU，避免反向 hook 与原地操作冲突
    for m in model.modules():
        if isinstance(m, torch.nn.ReLU):
            m.inplace = False
    target = last_conv(model)

    _, _, test_loader = get_loaders(batch_size=8)
    xb, yb = next(iter(test_loader))
    xb = xb.to(device)

    n = 6
    plt.figure(figsize=(11, 4))
    for i in range(n):
        cam, pred = grad_cam(model, xb[i:i + 1], target)
        img = xb[i, 0].cpu().numpy()
        img = (img - img.min()) / (img.max() - img.min() + 1e-8)
        # 原图
        plt.subplot(2, n, i + 1)
        plt.imshow(img, cmap="gray"); plt.axis("off")
        plt.title(f"真:{CLASS_NAMES[yb[i]]}", fontsize=9)
        # Grad-CAM 叠加
        plt.subplot(2, n, n + i + 1)
        plt.imshow(img, cmap="gray")
        plt.imshow(cam, cmap="jet", alpha=0.5)
        plt.axis("off")
        c = "green" if pred == int(yb[i]) else "red"
        plt.title(f"预:{CLASS_NAMES[pred]}", fontsize=9, color=c)
    plt.suptitle("Grad-CAM：AlexNet 判别时关注的区域（上=原图，下=热力图叠加）", fontsize=11)
    plt.tight_layout()
    out = os.path.join(OUT_DIR, "gradcam.png")
    plt.savefig(out, dpi=150); plt.close()
    print("[Grad-CAM] 已保存:", out)


if __name__ == "__main__":
    main()
