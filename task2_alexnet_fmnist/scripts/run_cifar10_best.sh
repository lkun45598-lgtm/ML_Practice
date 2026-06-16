#!/usr/bin/env bash
# CIFAR-10「数据充足标准基准」三模型 × 3 种子的公平配方驱动（与其它数据集同口径）。
#   AlexNet : img224 + BN + strong_aug + cosine + label_smoothing0.1 + 100 轮（公平升级，
#             避免大核大头被弱配方拖累，干净对比"架构"）
#   ResNet  : img32 原生 + strong_aug + cosine + ls0.1 + 100 轮 + lr0.1
#   SimpleCNN: img32 原生 + strong_aug + cosine + ls0.1 + 60 轮 + lr0.05
# 结果写 outputs/exp_x_{alex,resnet,scnn}_cifar10_best_s*.json，由
# analysis/cross_dataset_summary.py 聚合。9 个任务按 round-robin 铺到 GPUS（默认 0 1 2）。
# 用法：bash scripts/run_cifar10_best.sh           # 缺省 3 卡
#       GPUS="0 1 2 3" bash scripts/run_cifar10_best.sh   # 自定义可用卡
#       FORCE=1 bash scripts/run_cifar10_best.sh          # 强制重跑已存在结果
PY=/home/lz/miniconda3/envs/pytorch312/bin/python
cd "$(dirname "$0")/../.."        # 切到仓库根目录
mkdir -p task2_alexnet_fmnist/outputs
GPUS=${GPUS:-"0 1 2"}
read -ra GPU_ARR <<< "$GPUS"
NGPU=${#GPU_ARR[@]}

ALEX="--model alexnet --dataset cifar10 --img-size 224 --bn --strong-aug --cosine --label-smoothing 0.1 --epochs 100 --batch-size 128 --lr 0.01"
RESNET="--model resnet --dataset cifar10 --img-size 32 --strong-aug --cosine --label-smoothing 0.1 --epochs 100 --batch-size 128 --lr 0.1"
SCNN="--model simplecnn --dataset cifar10 --img-size 32 --strong-aug --cosine --label-smoothing 0.1 --epochs 60 --batch-size 128 --lr 0.05"

run() {  # run <gpu> <tag> <args...>
  local gpu="$1" tag="$2"; shift 2
  local out="task2_alexnet_fmnist/outputs/exp_${tag}.json"
  if [ -f "$out" ] && [ "$FORCE" != "1" ]; then
    echo "[GPU$gpu] 跳过 ${tag}（已存在，FORCE=1 可重跑）"; return
  fi
  echo "[GPU$gpu] ▶ ${tag}"
  CUDA_VISIBLE_DEVICES="$gpu" $PY -m task2_alexnet_fmnist.experiments --tag "$tag" "$@" \
    > "task2_alexnet_fmnist/outputs/log_${tag}.txt" 2>&1
  echo "[GPU$gpu] ✅ ${tag} -> $($PY -c "import json;print('test_acc=%.4f'%json.load(open('$out'))['test_acc'])")"
}

# 9 个任务（model_args : seed）round-robin 到各 GPU，每卡一条串行队列。
TASKS=(
  "x_alex_cifar10_best_s0|$ALEX|0" "x_alex_cifar10_best_s1|$ALEX|1" "x_alex_cifar10_best_s2|$ALEX|2"
  "x_resnet_cifar10_best_s0|$RESNET|0" "x_resnet_cifar10_best_s1|$RESNET|1" "x_resnet_cifar10_best_s2|$RESNET|2"
  "x_scnn_cifar10_best_s0|$SCNN|0" "x_scnn_cifar10_best_s1|$SCNN|1" "x_scnn_cifar10_best_s2|$SCNN|2"
)

# 为每张 GPU 组装其任务队列，再后台并行启动
for gi in "${!GPU_ARR[@]}"; do
  gpu="${GPU_ARR[$gi]}"
  (
    for ti in "${!TASKS[@]}"; do
      [ $((ti % NGPU)) -ne "$gi" ] && continue
      IFS='|' read -r tag margs seed <<< "${TASKS[$ti]}"
      # alex s0 额外保存训练曲线，供论文画收敛图
      hist=""; [ "$tag" = "x_alex_cifar10_best_s0" ] && \
        hist="--save-history task2_alexnet_fmnist/outputs/hist_x_alex_cifar10_best.json"
      run "$gpu" "$tag" $margs --seed "$seed" $hist
    done
  ) &
done
wait
echo "全部完成。CIFAR-10 三模型均已 3 种子齐备。"
