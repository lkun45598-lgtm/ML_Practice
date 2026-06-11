#!/usr/bin/env bash
# 多卡并行版跨数据集对照实验：把 12 个训练任务铺到 8 张 RTX 4090 上。
# 每张卡跑自己的任务队列（串行），不同卡之间并行；重活 catsdogs 单独占卡。
# 结果同样写 outputs/exp_x_*.json，由 cross_dataset_summary.py 聚合。
PY=/home/lz/miniconda3/envs/pytorch312/bin/python
cd "$(dirname "$0")"
AEP=40; SEP=30
log() { echo "[$(date +%T)][gpu$1] $2"; }

# alex <gpu> <dataset>
alex() {
  local gpu=$1 ds=$2 tag="x_alex_$2"
  log $gpu "▶ $tag"
  CUDA_VISIBLE_DEVICES=$gpu $PY experiments.py --tag "$tag" --device cuda --amp \
    --model alexnet --dataset "$ds" --img-size 224 --bn --augment --cosine \
    --epochs $AEP --batch-size 128 --seed 0 --save-history "outputs/hist_$tag.json" \
    > "outputs/log_$tag.txt" 2>&1
  log $gpu "✓ $tag  $(grep 完成 outputs/log_$tag.txt | tail -1)"
}
# scnn <gpu> <dataset> <seed>
scnn() {
  local gpu=$1 ds=$2 s=$3 tag="x_scnn_$2_s$3"
  log $gpu "▶ $tag"
  CUDA_VISIBLE_DEVICES=$gpu $PY experiments.py --tag "$tag" --device cuda --amp \
    --model simplecnn --dataset "$ds" --img-size 64 --augment \
    --epochs $SEP --batch-size 128 --seed $s \
    > "outputs/log_$tag.txt" 2>&1
  log $gpu "✓ $tag  $(grep 完成 outputs/log_$tag.txt | tail -1)"
}

# 卡分配（括号内顺序即该卡的串行队列）
( alex 0 catsdogs ) &
( scnn 1 catsdogs 0 ) &
( scnn 2 catsdogs 1 ) &
( scnn 3 catsdogs 2 ) &
( alex 4 flowers; alex 4 garbage ) &
( scnn 5 flowers 0; scnn 5 flowers 1; scnn 5 flowers 2 ) &
( scnn 6 garbage 0; scnn 6 garbage 1; scnn 6 garbage 2 ) &

wait
echo "[$(date +%T)] ✅ 全部 12 个训练任务完成"
