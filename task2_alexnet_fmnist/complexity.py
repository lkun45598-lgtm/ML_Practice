# -*- coding: utf-8 -*-
"""计算复杂度对照：手写 AlexNet@224 vs 轻量 SimpleCNN@28。

量化三项：参数量、FLOPs（单张前向乘加）、单图推理延迟（GPU/CPU）。
用于分析 AlexNet 在 Fashion-MNIST 上的容量与计算开销。
结果写入 outputs/complexity.json。
"""
import os
import json
import time
import torch
from thop import profile

from alexnet import AlexNet
from simplecnn import SimpleCNN

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "outputs")


@torch.no_grad()
def latency_ms(model, shape, device, n=100, warmup=20):
    """单图（batch=1）平均推理延迟（毫秒）。"""
    model.eval().to(device)
    x = torch.randn(*shape, device=device)
    for _ in range(warmup):
        model(x)
    if device.type == "cuda":
        torch.cuda.synchronize()
    t0 = time.time()
    for _ in range(n):
        model(x)
    if device.type == "cuda":
        torch.cuda.synchronize()
    return (time.time() - t0) / n * 1000.0


def measure(model, shape, device):
    params = sum(p.numel() for p in model.parameters())
    flops, _ = profile(model, inputs=(torch.randn(*shape),), verbose=False)
    lat_gpu = latency_ms(model, shape, device) if device.type == "cuda" else None
    lat_cpu = latency_ms(model, shape, torch.device("cpu"), n=30, warmup=5)
    return {"params_M": round(params / 1e6, 3),
            "flops_M": round(flops / 1e6, 1),
            "latency_gpu_ms": round(lat_gpu, 3) if lat_gpu else None,
            "latency_cpu_ms": round(lat_cpu, 3)}


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    alex = AlexNet(num_classes=10, in_channels=1, use_bn=True)
    simple = SimpleCNN(num_classes=10, in_channels=1)
    res = {
        "AlexNet@224": measure(alex, (1, 1, 224, 224), device),
        "SimpleCNN@28": measure(simple, (1, 1, 28, 28), device),
        "device": device.type,
    }
    a, s = res["AlexNet@224"], res["SimpleCNN@28"]
    res["ratio"] = {
        "params": round(a["params_M"] / s["params_M"], 1),
        "flops": round(a["flops_M"] / s["flops_M"], 1),
        "latency_cpu": round(a["latency_cpu_ms"] / s["latency_cpu_ms"], 1),
    }
    with open(os.path.join(OUT_DIR, "complexity.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    print(f"\n[复杂度] AlexNet 相对 SimpleCNN：参数 ×{res['ratio']['params']}，"
          f"FLOPs ×{res['ratio']['flops']}，CPU 延迟 ×{res['ratio']['latency_cpu']}")


if __name__ == "__main__":
    main()
