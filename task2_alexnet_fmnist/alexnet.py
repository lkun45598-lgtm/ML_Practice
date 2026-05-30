# -*- coding: utf-8 -*-
"""逐层手写的 AlexNet（输入 1x224x224）。仅用基础算子搭建，不调用 torchvision 预置模型。"""
import torch
import torch.nn as nn


class AlexNet(nn.Module):
    """经典 AlexNet 结构，按论文逐层手工组装。

    输入: (N, in_channels, 224, 224)
    输出: (N, num_classes)
    """

    def __init__(self, num_classes=10, in_channels=1, use_lrn=True):
        super().__init__()
        # ---- 特征提取：5 个卷积块 ----
        layers = []
        # Conv1: 1->96, 11x11, stride4, pad2 -> 96x55x55
        layers += [nn.Conv2d(in_channels, 96, kernel_size=11, stride=4, padding=2),
                   nn.ReLU(inplace=True)]
        if use_lrn:
            layers += [nn.LocalResponseNorm(size=5, alpha=1e-4, beta=0.75, k=2)]
        layers += [nn.MaxPool2d(kernel_size=3, stride=2)]            # -> 96x27x27
        # Conv2: 96->256, 5x5, pad2 -> 256x27x27
        layers += [nn.Conv2d(96, 256, kernel_size=5, padding=2),
                   nn.ReLU(inplace=True)]
        if use_lrn:
            layers += [nn.LocalResponseNorm(size=5, alpha=1e-4, beta=0.75, k=2)]
        layers += [nn.MaxPool2d(kernel_size=3, stride=2)]            # -> 256x13x13
        # Conv3: 256->384, 3x3, pad1
        layers += [nn.Conv2d(256, 384, kernel_size=3, padding=1),
                   nn.ReLU(inplace=True)]
        # Conv4: 384->384, 3x3, pad1
        layers += [nn.Conv2d(384, 384, kernel_size=3, padding=1),
                   nn.ReLU(inplace=True)]
        # Conv5: 384->256, 3x3, pad1 -> pool -> 256x6x6
        layers += [nn.Conv2d(384, 256, kernel_size=3, padding=1),
                   nn.ReLU(inplace=True),
                   nn.MaxPool2d(kernel_size=3, stride=2)]            # -> 256x6x6
        self.features = nn.Sequential(*layers)

        # ---- 分类器：3 个全连接 ----
        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(256 * 6 * 6, 4096), nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(4096, 4096), nn.ReLU(inplace=True),
            nn.Linear(4096, num_classes),
        )

    def forward(self, x):
        x = self.features(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x


if __name__ == "__main__":
    # 自检：前向输出形状应为 (2, 10)
    net = AlexNet(num_classes=10, in_channels=1)
    dummy = torch.randn(2, 1, 224, 224)
    out = net(dummy)
    n_param = sum(p.numel() for p in net.parameters())
    print("输出形状:", tuple(out.shape), "参数量:", f"{n_param/1e6:.1f}M")
    assert out.shape == (2, 10)
    print("[自检] AlexNet 前向通过")
