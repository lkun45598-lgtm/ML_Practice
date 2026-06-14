#!/usr/bin/env bash
# 跨数据集对照实验驱动：AlexNet@224 vs SimpleCNN@64，跑遍 PPT 任务②的三个真实数据集。
# 用法：
#   bash run_cross_dataset.sh smoke    # 摸底：各 12 轮、单种子（快）
#   bash run_cross_dataset.sh report   # 报告级：AlexNet 30 轮 + SimpleCNN 25 轮×3 种子
# 结果写入 outputs/exp_x_<...>.json，再由 analysis/cross_dataset_summary.py 聚合。
set -e
MODE="${1:-smoke}"
PY=/home/lz/miniconda3/envs/pytorch312/bin/python
cd "$(dirname "$0")/../.."   # 切到仓库根目录
DATASETS="flowers garbage catsdogs"

log() { echo "[$(date +%T)] $*"; }

run() {  # run <tag> <args...>
  local tag="$1"; shift
  if [ -f "task2_alexnet_fmnist/outputs/exp_${tag}.json" ] && [ "$FORCE" != "1" ]; then
    log "跳过 ${tag}（已存在，设 FORCE=1 可重跑）"; return
  fi
  log "▶ ${tag}"
  $PY -m task2_alexnet_fmnist.experiments --tag "$tag" --amp "$@" 2>&1 \
    | grep -E "数据集|epoch|每轮|完成" | sed "s/^/    /"
}

if [ "$MODE" = "smoke" ]; then
  EP=12
  for ds in $DATASETS; do
    run "x_alex_${ds}_smoke"  --model alexnet  --dataset "$ds" --img-size 224 --bn --augment --cosine --epochs $EP --batch-size 128 --seed 0
    run "x_scnn_${ds}_smoke"  --model simplecnn --dataset "$ds" --img-size 64  --epochs $EP --batch-size 128 --seed 0
  done
  log "✅ 摸底完成"
elif [ "$MODE" = "report" ]; then
  AEP=40; SEP=30
  for ds in $DATASETS; do
    # 主模型：AlexNet@224，BN + 数据增强 + 余弦退火（对齐 Fashion 主模型方法）
    run "x_alex_${ds}"        --model alexnet  --dataset "$ds" --img-size 224 --bn --augment --cosine --epochs $AEP --batch-size 128 --seed 0 \
        --save-history "task2_alexnet_fmnist/outputs/hist_x_alex_${ds}.json"
    # 轻量对照：SimpleCNN@64，3 种子估方差
    for s in 0 1 2; do
      run "x_scnn_${ds}_s${s}" --model simplecnn --dataset "$ds" --img-size 64 --augment --epochs $SEP --batch-size 128 --seed $s
    done
  done
  log "✅ 报告级完成"
else
  echo "未知模式：$MODE（应为 smoke 或 report）"; exit 1
fi
