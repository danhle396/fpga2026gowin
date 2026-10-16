#!/usr/bin/env bash
# Lô AI-09 / AI-10 trên D1 8 người, chạy tách khỏi phiên Claude (Win32_Process.Create). Chạy lại được: bỏ qua lượt đã có report.txt.
#   N2 chỉ đầu, 3 seed; N2 + dữ liệu thân (ngực, thắt lưng chỉ để huấn luyện), 3 seed; phát lại FSM từng mô hình và gộp 3 seed.
set -u
R=/e/FPGA2026_GOWIN/runs
RW=E:/FPGA2026_GOWIN/runs
P=/c/Users/nhath/venvs/fpga2026/Scripts/python.exe
cd /e/FPGA2026_GOWIN/fpga2026gowin || exit 1
export OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
D=ml/data/public
SEEDS="20261014 7 99"
st() { echo "$(date '+%F %T') $*" >> $R/status.txt; }

train() {   # train <tên> <seed> [tham số thêm...]
    local name=$1 seed=$2; shift 2
    if [ -f $R/$name/report.txt ]; then st "$name đã có, bỏ qua"; return; fi
    st "$name bắt đầu"
    $P -I ml/train_cnn.py --arch n2 --seed $seed --out $RW/$name "$@" > $R/$name.log 2>&1
    st "$name xong exit=$?"
}
play() {    # play <tag> <thư mục mô hình...>
    local tag=$1; shift
    local first=$1
    if [ -f $R/$first/playback_$tag.txt ]; then st "playback $tag đã có"; return; fi
    local args=""; for m in "$@"; do args="$args $RW/$m"; done
    $P -I tools/playback_d1.py --model $args --t-score 0 8 16 32 --tag $tag > $R/playback_$tag.log 2>&1
    st "playback $tag xong exit=$?"
}

st "=== lô bắt đầu"
for s in $SEEDS; do train n2_8_s$s $s & done; wait
for s in $SEEDS; do play v31 n2_8_s$s & done
play ens3 n2_8_s20261014 n2_8_s7 n2_8_s99 &
wait
for s in $SEEDS; do
    train n2t_8_s$s $s --train-only $D/d1_windows_nguc_340539.npz $D/d1_windows_that_lung_340535.npz &
done; wait
for s in $SEEDS; do play v31 n2t_8_s$s & done
play ens3 n2t_8_s20261014 n2t_8_s7 n2t_8_s99 &
wait
st "=== lô xong"
