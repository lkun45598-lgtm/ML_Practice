# -*- coding: utf-8 -*-
"""逐层手写的小型 ResNet（残差网络），用于 28x28 Fashion-MNIST 的架构对照。

设计动机：AlexNet 为 224x224 自然图像设计，用到本任务需把 28x28 上采样 8 倍，
存在容量与算力冗余。本网络改用现代残差结构，直接在原生 28x28 上训练：
小卷积核（3x3）、批归一化、残差连接缓解深层退化、全局平均池化替代巨大全连接层。
仅用基础算子手工搭建，不调用 torchvision 预置模型，以与项目要求保持一致。
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class BasicBlock(nn.Module):
    """残差基本块：Conv3x3-BN-ReLU-Conv3x3-BN + 捷径(shortcut)，再 ReLU。"""

    def __init__(self, cin, cout, stride=1):
        super().__init__()
        self.conv1 = nn.Conv2d(cin, cout, 3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(cout)
        self.conv2 = nn.Conv2d(cout, cout, 3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(cout)
        # 当通道或空间尺寸变化时，用 1x1 卷积对齐捷径分支
        self.shortcut = nn.Sequential()
        if stride != 1 or cin != cout:
            self.shortcut = nn.Sequential(
                nn.Conv2d(cin, cout, 1, stride=stride, bias=False),
                nn.BatchNorm2d(cout))

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = out + self.shortcut(x)          # 残差相加
        return F.relu(out)


class ResNetSmall(nn.Module):
    """小型 ResNet（类 ResNet-18，3 个 stage，每 stage 2 个残差块）。

    输入: (N, in_channels, 28, 28)；不做上采样，保持原生分辨率。
    """

    def __init__(self, num_classes=10, in_channels=1, widths=(64, 128, 256)):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(in_channels, widths[0], 3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(widths[0]), nn.ReLU(inplace=True))      # 28x28
        self.layer1 = self._stage(widths[0], widths[0], stride=1)  # 28x28
        self.layer2 = self._stage(widths[0], widths[1], stride=2)  # 14x14
        self.layer3 = self._stage(widths[1], widths[2], stride=2)  # 7x7
        self.pool = nn.AdaptiveAvgPool2d(1)                        # 全局平均池化
        self.fc = nn.Linear(widths[2], num_classes)

    def _stage(self, cin, cout, stride):
        return nn.Sequential(BasicBlock(cin, cout, stride), BasicBlock(cout, cout, 1))

    def forward(self, x):
        x = self.stem(x)
        x = self.layer1(x); x = self.layer2(x); x = self.layer3(x)
        x = torch.flatten(self.pool(x), 1)
        return self.fc(x)


if __name__ == "__main__":
    net = ResNetSmall(num_classes=10, in_channels=1)
    out = net(torch.randn(2, 1, 28, 28))
    n = sum(p.numel() for p in net.parameters())
    print("输出形状:", tuple(out.shape), "参数量:", f"{n/1e6:.2f}M")
    assert out.shape == (2, 10)
    print("[自检] ResNetSmall 前向通过")
