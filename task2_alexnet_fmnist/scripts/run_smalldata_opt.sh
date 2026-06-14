#!/usr/bin/env bash
# 小数据集专门优化：在 baseline(alexbig，基础增强) 之上加强增强+标签平滑(garbage再加类加权)。
# baseline 复用已有的 exp_x_alexbig_{flowers,garbage}_s{0,1,2}.json，本脚本只跑改进版 6 个任务。
PY=/home/lz/miniconda3/envs/pytorch312/bin/python
cd "$(dirname "$0")/../.."   # 切到仓库根目录
EP=40
log() { echo "[$(date +%T)][gpu$1] $2"; }
opt() {  # opt <gpu> <dataset> <seed> <extra-args...>
  local gpu=$1 ds=$2 s=$3; shift 3
  local tag="x_alexopt_${ds}_s${s}"
  log $gpu "▶ $tag"
  CUDA_VISIBLE_DEVICES=$gpu $PY -m task2_alexnet_fmnist.experiments --tag "$tag" --device cuda --amp \
    --model alexnet --dataset "$ds" --img-size 224 --bn --cosine --strong-aug \
    --label-smoothing 0.1 "$@" --epochs $EP --batch-size 128 --seed $s \
    > "task2_alexnet_fmnist/outputs/log_$tag.txt" 2>&1
  log $gpu "✓ $tag  $(grep 完成 outputs/log_$tag.txt | tail -1)"
}
( opt 0 flowers 0 ) &
( opt 1 flowers 1 ) &
( opt 2 flowers 2 ) &
( opt 3 garbage 0 --class-weight ) &
( opt 4 garbage 1 --class-weight ) &
( opt 5 garbage 2 --class-weight ) &
wait
echo "[$(date +%T)] ✅ 小数据优化 6 个任务全部完成"
