#!/usr/bin/env bash
# 大核 vs 小核 受控对照：同一 AlexNet 框架，唯一变量是卷积核。
#   大核版：第1层 11×11、第2层 5×5（原版）
#   小核版：上述大核换成 3×3 堆叠（--small-kernel），通道/输出尺寸/FC头/训练预算全一致
# flowers + garbage 各 2 变体 × 3 种子 = 12 个任务，铺到 8 张 GPU。
PY=/home/lz/miniconda3/envs/pytorch312/bin/python
cd "$(dirname "$0")"
EP=40
log() { echo "[$(date +%T)][gpu$1] $2"; }

# alex <gpu> <dataset> <seed> <big|small>
alex() {
  local gpu=$1 ds=$2 s=$3 kind=$4
  local sk=""; [ "$kind" = "small" ] && sk="--small-kernel"
  local tag="x_alex${kind}_${ds}_s${s}"
  log $gpu "▶ $tag"
  CUDA_VISIBLE_DEVICES=$gpu $PY experiments.py --tag "$tag" --device cuda --amp \
    --model alexnet --dataset "$ds" --img-size 224 --bn --augment --cosine $sk \
    --epochs $EP --batch-size 128 --seed $s \
    > "outputs/log_$tag.txt" 2>&1
  log $gpu "✓ $tag  $(grep 完成 outputs/log_$tag.txt | tail -1)"
}

# 12 个任务铺到 8 张卡（gpu0-3 各跑两个串行队列）
( alex 0 flowers 0 big;   alex 0 flowers 0 small ) &
( alex 1 flowers 1 big;   alex 1 flowers 1 small ) &
( alex 2 flowers 2 big;   alex 2 flowers 2 small ) &
( alex 3 garbage 0 big;   alex 3 garbage 0 small ) &
( alex 4 garbage 1 big ) &
( alex 5 garbage 1 small ) &
( alex 6 garbage 2 big ) &
( alex 7 garbage 2 small ) &
wait
echo "[$(date +%T)] ✅ 大核 vs 小核 12 个任务全部完成"
