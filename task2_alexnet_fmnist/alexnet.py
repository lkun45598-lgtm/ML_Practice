# -*- coding: utf-8 -*-
"""逐层手写的 AlexNet（输入 1x224x224）。仅用基础算子搭建，不调用 torchvision 预置模型。"""
import torch
import torch.nn as nn


class AlexNet(nn.Module):
    """经典 AlexNet 结构，按论文逐层手工组装。

    输入: (N, in_channels, 224, 224)
    输出: (N, num_classes)
    """

    def __init__(self, num_classes=10, in_channels=1, use_lrn=True, use_bn=False):
        super().__init__()

        def block(cin, cout, k, s=1, p=0, pool=False, lrn=False):
            """卷积块：Conv(+BN)+ReLU(+LRN)(+MaxPool)。use_bn=True 时以 BatchNorm 取代 LRN。"""
            ls = [nn.Conv2d(cin, cout, kernel_size=k, stride=s, padding=p)]
            if use_bn:
                ls.append(nn.BatchNorm2d(cout))
            ls.append(nn.ReLU(inplace=True))
            if lrn and use_lrn and not use_bn:
                ls.append(nn.LocalResponseNorm(size=5, alpha=1e-4, beta=0.75, k=2))
            if pool:
                ls.append(nn.MaxPool2d(kernel_size=3, stride=2))
            return ls

        # ---- 特征提取：5 个卷积块（输出尺寸不受 BN 影响）----
        layers = []
        layers += block(in_channels, 96, 11, s=4, p=2, pool=True, lrn=True)  # -> 96x27x27
        layers += block(96, 256, 5, p=2, pool=True, lrn=True)                # -> 256x13x13
        layers += block(256, 384, 3, p=1)                                    # -> 384x13x13
        layers += block(384, 384, 3, p=1)                                    # -> 384x13x13
        layers += block(384, 256, 3, p=1, pool=True)                         # -> 256x6x6
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
