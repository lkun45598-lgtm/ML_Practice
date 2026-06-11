#!/usr/bin/env bash
# 公平版 SimpleCNN 补跑：与 AlexNet/ResNet 对齐训练预算 —— 40 轮 + 余弦退火。
# 覆盖原 30 轮无退火的 exp_x_scnn_<ds>_s<seed>.json，使跨数据集对照成为「同预算」比较。
# 3 数据集 × 3 种子 = 9 个任务，铺到空闲 GPU 上并行。
PY=/home/lz/miniconda3/envs/pytorch312/bin/python
cd "$(dirname "$0")"
SEP=40
log() { echo "[$(date +%T)][gpu$1] $2"; }

scnn() {  # scnn <gpu> <dataset> <seed>
  local gpu=$1 ds=$2 s=$3 tag="x_scnn_$2_s$3"
  log $gpu "▶ $tag (40轮+余弦)"
  CUDA_VISIBLE_DEVICES=$gpu $PY experiments.py --tag "$tag" --device cuda --amp \
    --model simplecnn --dataset "$ds" --img-size 64 --augment --cosine \
    --epochs $SEP --batch-size 128 --seed $s \
    > "outputs/log_$tag.txt" 2>&1
  log $gpu "✓ $tag  $(grep 完成 outputs/log_$tag.txt | tail -1)"
}

# 9 个任务铺到 9 个队列（gpu 0-7，gpu0 兜底跑两个）
( scnn 0 flowers 0 ) &
( scnn 1 flowers 1 ) &
( scnn 2 flowers 2 ) &
( scnn 3 garbage 0 ) &
( scnn 4 garbage 1 ) &
( scnn 5 garbage 2 ) &
( scnn 6 catsdogs 0 ) &
( scnn 7 catsdogs 1 ) &
( scnn 0 catsdogs 2 ) &
wait
echo "[$(date +%T)] ✅ 公平版 SimpleCNN 9 个任务全部完成"
