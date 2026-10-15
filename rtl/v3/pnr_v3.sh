#!/usr/bin/env bash
# rtl/v3/pnr_v3.sh — tổng hợp + P&R fpga_top_v3 (giao thức v3) hoặc fpga_top (PROTO 1, kèm top.sdc) trên BẢN SAO
# project Gowin, không đụng impl/ của đồng đội.
#   bash rtl/v3/pnr_v3.sh <thư mục làm việc> [v3|p1]
#   bash rtl/v3/pnr_v3.sh <thư mục làm việc> e2 <thư mục export_mem.py --engine e2>     # fpga_top_v3 + engine E2
#   SIM_NETLIST=1 bash rtl/v3/pnr_v3.sh ...      # thêm netlist mô phỏng sau P&R (.vo), dùng cho rtl/gl/run_gl.sh
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROJ="$ROOT/Document Board Kiwi Primer 20K/Kiwi20K_FallDetection_FPGA"
W="$1"; TOP="${2:-v3}"; E2DIR="${3:-}"
GW="${GW_SH:-/c/Gowin/Gowin_V1.9.11.03_Education_x64/IDE/bin/gw_sh.exe}"
rm -rf "$W"; mkdir -p "$W"
cp -r "$PROJ/src" "$W/"
python -I "$ROOT/tools/gen_cnn_params.py" --project "$W" >/dev/null
CORE="argmax4 bias_rom cnn_controller cnn_core conv1d_engine dense_engine feature_ram gap_buffer gap_engine
      input_buffer mac_unit maxpool1d_engine requantize_relu spi_slave weight_rom"
{
    echo "set_device -name GW2A-18C GW2A-LV18PG256C8/I7"
    if [ "$TOP" = "e2" ]; then CORE="input_buffer spi_slave"; fi
    for m in $CORE; do echo "add_file src/$m.v"; done
    echo "add_file src/gowin_rpll/pll_50m.v"
    if [ "$TOP" = "e2" ]; then
        CORE=""
        cp "$E2DIR/cnn_params.vh" "$W/src/cnn_params.vh"
        cp "$E2DIR/weights.mem" "$W/src/weights_e2.mem"
        cp "$E2DIR/bias.mem" "$W/src/bias_e2.mem"
        cp "$ROOT/rtl/e2/cnn_e2.v" "$ROOT/rtl/v3/"{fpga_top_v3,packet_parser_v3,result_frame_v3,spi_result_tx_v3,crc16_ccitt}.v            "$ROOT/rtl/v3/fpga_top_v3.cst" "$ROOT/rtl/v3/fpga_top_v3.sdc" "$W/src/"
        for m in cnn_e2 fpga_top_v3 packet_parser_v3 result_frame_v3 spi_result_tx_v3 crc16_ccitt; do echo "add_file src/$m.v"; done
        echo "add_file src/fpga_top_v3.cst"
        echo "add_file src/fpga_top_v3.sdc"
        echo "set_option -top_module fpga_top_v3"
    elif [ "$TOP" = "v3" ]; then
        cp "$ROOT/rtl/v3/"{fpga_top_v3,packet_parser_v3,result_frame_v3,spi_result_tx_v3,crc16_ccitt}.v \
           "$ROOT/rtl/v3/fpga_top_v3.cst" "$ROOT/rtl/v3/fpga_top_v3.sdc" "$W/src/"
        for m in fpga_top_v3 packet_parser_v3 result_frame_v3 spi_result_tx_v3 crc16_ccitt; do echo "add_file src/$m.v"; done
        echo "add_file src/fpga_top_v3.cst"
        echo "add_file src/fpga_top_v3.sdc"
        echo "set_option -top_module fpga_top_v3"
    else
        cp "$ROOT/rtl/v3/top.sdc" "$W/src/"
        for m in fpga_top packet_parser crc8 result_register spi_result_tx; do echo "add_file src/$m.v"; done
        echo "add_file src/fpga_top.cst"
        echo "add_file src/top.sdc"
        echo "set_option -top_module fpga_top"
    fi
    echo "set_option -include_path src"
    echo "set_option -output_base_name fpga_project"
    # SIM_NETLIST=1: thêm netlist mô phỏng sau P&R impl/pnr/fpga_project.vo (không mã hóa) cho rtl/gl/run_gl.sh
    [ "${SIM_NETLIST:-0}" = "1" ] && echo "set_option -gen_verilog_sim_netlist 1"
    echo "run all"
} > "$W/build.tcl"
cd "$W"
"$GW" build.tcl > pnr.log 2>&1
grep -E "ERROR|WARN" pnr.log | sort | uniq -c | head -20 || true
R=impl/pnr/fpga_project.rpt.txt
grep -E "^\s+(Logic|Register|BSRAM|DSP|I/O Port)\s+\|" "$R" || true
sed 's/<[^>]*>/ /g' impl/pnr/fpga_project_tr_content.html | tr -d '\r' | tr '\n' ' ' | tr -s ' ' |
    grep -oE '(Max Frequency Summary|Total Negative Slack Summary).{0,330}' || true
ls -l impl/pnr/fpga_project.fs
