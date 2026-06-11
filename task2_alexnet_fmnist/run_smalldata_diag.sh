#!/usr/bin/env bash
# 拆解 garbage 改进版的两个因素：强增强 vs 类加权（各 3 种子）。
#   A 仅强增强(+LS)：x_alexaug_garbage   —— 与"改进(强+LS+CW)"比 => 类加权的边际效应
#   B 仅类加权(基础增强+LS)：x_alexcw_garbage —— 与"改进"比 => 强增强的边际效应
PY=/home/lz/miniconda3/envs/pytorch312/bin/python
cd "$(dirname "$0")"
EP=40
log(){ echo "[$(date +%T)][gpu$1] $2"; }
run(){ local gpu=$1 tag=$2; shift 2
  log $gpu "▶ $tag"
  CUDA_VISIBLE_DEVICES=$gpu $PY experiments.py --tag "$tag" --device cuda --amp \
    --model alexnet --dataset garbage --img-size 224 --bn --cosine \
    --label-smoothing 0.1 "$@" --epochs $EP --batch-size 128 \
    > "outputs/log_$tag.txt" 2>&1
  log $gpu "✓ $tag  $(grep 完成 outputs/log_$tag.txt|tail -1)"
}
( run 0 x_alexaug_garbage_s0 --strong-aug --seed 0 ) &
( run 1 x_alexaug_garbage_s1 --strong-aug --seed 1 ) &
( run 2 x_alexaug_garbage_s2 --strong-aug --seed 2 ) &
( run 3 x_alexcw_garbage_s0  --augment --class-weight --seed 0 ) &
( run 4 x_alexcw_garbage_s1  --augment --class-weight --seed 1 ) &
( run 5 x_alexcw_garbage_s2  --augment --class-weight --seed 2 ) &
wait
echo "[$(date +%T)] ✅ 拆解实验 6 个任务完成"
