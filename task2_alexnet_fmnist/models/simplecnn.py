# -*- coding: utf-8 -*-
"""轻量级基线 CNN（SimpleCNN），用于与手写 AlexNet 做对照实验。

直接在原始 28×28 灰度图上工作，参数量远小于 AlexNet，用于回答
“一个轻量网络在该任务上能达到什么水平”这一对照问题。
"""
import torch
import torch.nn as nn


class SimpleCNN(nn.Module):
    """3 个卷积块 + 2 个全连接的小型 CNN，输入 1×28×28，输出 num_classes。"""

    def __init__(self, num_classes=10, in_channels=1):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(in_channels, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(inplace=True),
            nn.MaxPool2d(2),                                   # 28 -> 14
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(inplace=True),
            nn.MaxPool2d(2),                                   # 14 -> 7
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(inplace=True),
            nn.MaxPool2d(2),                                   # 7 -> 3
            nn.AdaptiveAvgPool2d((3, 3)),                      # 尺寸无关：任意输入都收敛到 3×3
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 3 * 3, 256), nn.ReLU(inplace=True), nn.Dropout(0.5),
            nn.Linear(256, num_classes),
        )

    def forward(self, x):
        return self.classifier(self.features(x))


if __name__ == "__main__":
    net = SimpleCNN()
    out = net(torch.randn(2, 1, 28, 28))
    n = sum(p.numel() for p in net.parameters())
    print("输出形状:", tuple(out.shape), "参数量:", f"{n/1e6:.3f}M")
    assert out.shape == (2, 10)
    print("[自检] SimpleCNN 前向通过")
