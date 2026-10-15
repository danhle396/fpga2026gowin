// rtl/e2/cnn_e2.v — engine E2 (PROJECT_MASTER.md mục 4.1, A.6; việc RB-03, RB-04): 1 chu kỳ mỗi MAC, LANES làn.
// Chạy N1 (2 Conv + GAP) và N2 / N2-S / N2-L (3 Conv + Flatten) theo bảng lớp trong tham số (lấy từ cnn_params.vh
// do tools/export_mem.py sinh). Mô hình địa chỉ: ml/src/rom_layout.py, engine() — đã kiểm == golden.
//
//   for lớp: for j < L/2: for g < OC/LANES: for q < 2: acc[p] = bias; for k < 5: for ic < IC:
//            acc[p] += ROM[BASE + (g·5 + k)·IC + ic][p] · SRC[(2j + q − 2 + k)·IC + ic]   (ngoài biên = 0)
//            best[p] = max qua q;  DST[wr++] = requant(best[p])   (A.5: ≤ 0 → 0, min(>> n, 127))
//   GAP: f[c] = (Σ_t SRC[t·C + c]) >> log2(L)     Dense: logit[g·LANES + p] = bd + Σ_i ROM[DB + g·F + i][p] · f[i]
//
// Pipeline (mỗi cạnh clock): E0 phát địa chỉ → E1 BSRAM trả dữ liệu → E2 thanh ghi tích → E3 cộng dồn.
// Hai con trỏ (dữ liệu, weight) chỉ tăng 1. Giao diện giống cnn_core (E1). Verilog-2001.
module cnn_e2 #(
    parameter LANES      = 1,
    parameter NL         = 3,          // số lớp Conv (2 hoặc 3)
    parameter HEAD_GAP   = 0,
    parameter L1_OC = 8,  parameter L1_IC = 6,  parameter L1_SH = 7, parameter L1_BASE = 0,
    parameter L2_OC = 16, parameter L2_IC = 8,  parameter L2_SH = 7, parameter L2_BASE = 240,
    parameter L3_OC = 16, parameter L3_IC = 16, parameter L3_SH = 8, parameter L3_BASE = 880,
    parameter DENSE_F    = 256,
    parameter DENSE_BASE = 2160,
    parameter ROM_WORDS  = 3184,
    parameter BIAS_WORDS = 44,
    parameter WFILE      = "src/weights_e2.mem",
    parameter BFILE      = "src/bias_e2.mem"
) (
    input  wire                   clk,
    input  wire                   start,
    output wire [9:0]             input_read_addr,
    input  wire signed [7:0]      input_read_data,
    output reg                    busy = 1'b0,
    output reg                    inference_done = 1'b0,
    output reg  [1:0]             class_id = 2'd0,
    output reg  signed [31:0]     score = 32'sd0,       // logit lớn nhất (như cnn_core)
    output reg  signed [31:0]     logit0_out = 32'sd0,
    output reg  signed [31:0]     logit1_out = 32'sd0,
    output reg  signed [31:0]     logit2_out = 32'sd0,
    output reg  signed [31:0]     logit3_out = 32'sd0,
    output reg  [23:0]            cycles = 24'd0
);
    localparam W   = 8 * LANES;
    localparam BB2 = L1_OC, BB3 = L1_OC + L2_OC;
    localparam BBD = (NL == 3) ? (L1_OC + L2_OC + L3_OC) : (L1_OC + L2_OC);
    localparam LAST_OC = (NL == 3) ? L3_OC : L2_OC;
    localparam LAST_L  = (NL == 3) ? 16 : 32;               // 128 >> NL
    localparam GAP_SH  = (NL == 3) ? 4 : 5;                  // log2(LAST_L)
    localparam LAST_IN_A = (NL == 3);                        // lớp cuối ghi vào A (lớp 2) hay B (lớp 1)

    // ---------------- bộ nhớ: đọc đồng bộ 1 chu kỳ ----------------
    reg [W-1:0]  wrom [0:ROM_WORDS-1];
    reg [31:0]   brom [0:BIAS_WORDS-1];
    initial begin
        $readmemh(WFILE, wrom);
        $readmemh(BFILE, brom);
    end
    reg  [13:0]       w_addr = 14'd0;
    reg  [W-1:0]      w_q;
    reg  [6:0]        b_addr = 7'd0;
    reg  signed [31:0] b_q;
    always @(posedge clk) begin
        w_q <= wrom[w_addr];
        b_q <= brom[b_addr];
    end

    reg [7:0] ram_a [0:1023];
    reg [7:0] ram_b [0:1023];
    reg [9:0] sidx = 10'd0;                  // địa chỉ đọc nguồn (E0)
    reg [9:0] f_waddr = 10'd0;
    reg [7:0] f_wdata = 8'd0;
    reg       f_we_a = 1'b0, f_we_b = 1'b0;
    reg [7:0] fa_q, fb_q;
    always @(posedge clk) begin
        if (f_we_a) ram_a[f_waddr] <= f_wdata;
        if (f_we_b) ram_b[f_waddr] <= f_wdata;
        fa_q <= ram_a[sidx];
        fb_q <= ram_b[sidx];
    end
    assign input_read_addr = sidx;

    // ---------------- bảng lớp ----------------
    reg [1:0]  layer = 2'd0;
    reg [7:0]  L = 8'd128;
    reg [5:0]  IC, OC;
    reg [4:0]  SH;
    reg [13:0] BASE;
    reg [6:0]  BB;
    always @(*) begin
        case (layer)
        2'd0:    begin IC = L1_IC; OC = L1_OC; SH = L1_SH; BASE = L1_BASE; BB = 7'd0;  end
        2'd1:    begin IC = L2_IC; OC = L2_OC; SH = L2_SH; BASE = L2_BASE; BB = BB2;   end
        default: begin IC = L3_IC; OC = L3_OC; SH = L3_SH; BASE = L3_BASE; BB = BB3;   end
        endcase
    end

    // nguồn của dữ liệu đang về (E1): chọn theo nguồn đã phát ở E0, trễ 1 nhịp
    localparam SRC_IN = 2'd0, SRC_A = 2'd1, SRC_B = 2'd2, SRC_GAP = 2'd3;
    reg  [1:0] src_e0 = SRC_IN, src_e1 = SRC_IN;
    reg  [7:0] gapf [0:31];
    reg  [7:0] gap_q;
    always @(posedge clk) gap_q <= gapf[sidx[4:0]];
    wire signed [7:0] s_q = (src_e1 == SRC_IN) ? input_read_data :
                            (src_e1 == SRC_A)  ? fa_q : (src_e1 == SRC_B) ? fb_q : gap_q;

    // ---------------- pipeline MAC ----------------
    reg        v0 = 1'b0, v1 = 1'b0, v2 = 1'b0;     // phần tử hợp lệ ở E0 / E1 / E2
    reg        z0 = 1'b0, z1 = 1'b0;                // đệm biên → x = 0
    reg signed [15:0] prod [0:LANES-1];
    reg signed [31:0] acc  [0:LANES-1];
    reg signed [31:0] best [0:LANES-1];
    reg signed [31:0] lg   [0:3];
    integer p;

    function [7:0] requant;
        input signed [31:0] v;
        input [4:0] n;
        reg signed [31:0] s;
        begin
            s = v >>> n;
            requant = (v <= 0) ? 8'd0 : ((s > 127) ? 8'd127 : s[7:0]);
        end
    endfunction

    // ---------------- điều khiển ----------------
    localparam S_IDLE = 4'd0, S_B0 = 4'd1, S_B1 = 4'd2, S_B2 = 4'd3, S_RUN = 4'd4, S_DRAIN = 4'd5, S_WR = 4'd6,
               S_GAP = 4'd7, S_GAPD = 4'd8, S_DONE1 = 4'd9, S_DONE2 = 4'd10, S_DONE3 = 4'd11;
    reg [3:0]  st = S_IDLE;
    reg        dense = 1'b0;                 // đang chạy Dense (dùng chung S_B*, S_RUN, S_DRAIN)
    reg [6:0]  j = 7'd0;
    reg [5:0]  g = 6'd0;
    reg        q = 1'b0;
    reg [2:0]  k = 3'd0;
    reg [5:0]  ic = 6'd0;
    reg [9:0]  fi = 10'd0;                   // chỉ số Dense
    reg signed [9:0]  pos = 10'sd0;          // t − 2 + k
    reg signed [12:0] sptr = 13'sd0;         // (t − 2 + k)·IC + ic
    reg [9:0]  wr = 10'd0;
    reg [2:0]  lane = 3'd0;
    reg [2:0]  drain = 3'd0;
    reg [5:0]  gc = 6'd0;                    // GAP: kênh
    reg [6:0]  gt = 7'd0;                    // GAP: vị trí
    reg [12:0] gsum = 13'd0;
    reg        gv0 = 1'b0, gv1 = 1'b0;
    reg [1:0]  a_cls, b_cls;
    reg signed [31:0] a_val, b_val;

    wire run_last = dense ? (fi == DENSE_F - 1) : ((k == 3'd4) && (ic == IC - 1));
    // địa chỉ tính rộng 32 bit rồi cắt (giá trị luôn vừa đích; viết tường minh để công cụ không cảnh báo)
    wire [31:0] b_next  = (dense ? BBD : BB) + g * LANES + lane;
    wire [31:0] wd_base = DENSE_BASE + g * DENSE_F;
    wire [31:0] wc_base = BASE + g * 5 * IC;
    wire [31:0] g_addr  = gt * LAST_OC + gc;
    wire [12:0] g_avg   = gsum >> GAP_SH;

    always @(posedge clk) begin
        inference_done <= 1'b0;
        f_we_a <= 1'b0;
        f_we_b <= 1'b0;
        if (busy && cycles != 24'hFFFFFF) cycles <= cycles + 24'd1;

        // E1 → E2 → E3
        v1 <= v0; z1 <= z0; src_e1 <= src_e0;
        v2 <= v1;
        for (p = 0; p < LANES; p = p + 1) begin
            prod[p] <= $signed(w_q[8*p +: 8]) * (z1 ? 8'sd0 : s_q);
            if (v2) acc[p] <= acc[p] + prod[p];
        end
        v0 <= 1'b0;
        gv1 <= gv0;
        gv0 <= 1'b0;
        if (gv1) gsum <= gsum + {5'd0, s_q};          // GAP: kích hoạt 0..127

        case (st)
        S_IDLE: if (start) begin
            busy <= 1'b1; cycles <= 24'd1;
            layer <= 2'd0; L <= 8'd128; dense <= 1'b0;
            j <= 0; g <= 0; q <= 0; wr <= 0; lane <= 0;
            st <= S_B0;
        end
        // ---- bias cho từng làn: E0 phát địa chỉ, E1 dữ liệu, E2 chốt ----
        S_B0: begin
            b_addr <= b_next[6:0];
            st <= S_B1;
        end
        S_B1: st <= S_B2;
        S_B2: begin
            acc[lane] <= b_q;
            if (lane == LANES - 1) begin
                lane <= 0;
                if (dense) begin
                    fi <= 0;
                    sidx <= 10'd0;
                    w_addr <= wd_base[13:0];
                end else begin
                    k <= 0; ic <= 0;
                    pos  <= $signed({2'd0, j, q}) - 10'sd2;
                    sptr <= ($signed({4'd0, j, q}) - 13'sd2) * $signed({7'd0, IC});
                    w_addr <= wc_base[13:0];
                end
                st <= S_RUN;
            end else begin
                lane <= lane + 1'b1;
                st <= S_B0;
            end
        end
        // ---- một phần tử mỗi chu kỳ ----
        S_RUN: begin
            v0 <= 1'b1;
            if (dense) begin
                src_e0 <= HEAD_GAP ? SRC_GAP : (LAST_IN_A ? SRC_A : SRC_B);
                z0 <= 1'b0;
                sidx <= fi;
                if (fi != 0) w_addr <= w_addr + 1'b1;
                fi <= fi + 1'b1;
            end else begin
                src_e0 <= (layer == 2'd0) ? SRC_IN : (layer == 2'd1) ? SRC_A : SRC_B;
                z0 <= (pos < 0) || (pos >= $signed({2'd0, L}));
                sidx <= (sptr < 0) ? 10'd0 : sptr[9:0];
                if (!(k == 3'd0 && ic == 6'd0)) w_addr <= w_addr + 1'b1;
                sptr <= sptr + 1'b1;
                if (ic == IC - 1) begin ic <= 0; k <= k + 1'b1; pos <= pos + 1'b1; end
                else ic <= ic + 1'b1;
            end
            if (run_last) begin st <= S_DRAIN; drain <= 3'd0; end
        end
        S_DRAIN: begin                                  // phần tử cuối tới bộ cộng sau 3 cạnh
            drain <= drain + 1'b1;
            if (drain == 3'd3) begin
                if (dense) begin
                    for (p = 0; p < LANES; p = p + 1) lg[g * LANES + p] <= acc[p];
                    if (g == 4 / LANES - 1) st <= S_DONE1;
                    else begin g <= g + 1'b1; st <= S_B0; end
                end else begin
                    for (p = 0; p < LANES; p = p + 1)
                        if (!q || acc[p] > best[p]) best[p] <= acc[p];
                    if (!q) begin q <= 1'b1; st <= S_B0; end
                    else begin q <= 1'b0; lane <= 0; st <= S_WR; end
                end
            end
        end
        // ---- ghi LANES đầu ra đã requant ----
        S_WR: begin
            f_waddr <= wr;
            f_wdata <= requant(best[lane], SH);
            if (layer == 2'd1) f_we_b <= 1'b1; else f_we_a <= 1'b1;
            wr <= wr + 1'b1;
            if (lane == LANES - 1) begin
                lane <= 0;
                if (g == OC / LANES - 1) begin
                    g <= 0;
                    if (j == L / 2 - 1) begin
                        j <= 0; wr <= 0;
                        if (layer == NL - 1) begin
                            dense <= 1'b1;
                            if (HEAD_GAP) begin gc <= 0; gt <= 0; gsum <= 0; st <= S_GAP; end
                            else st <= S_B0;
                        end else begin
                            layer <= layer + 1'b1; L <= L / 2; st <= S_B0;
                        end
                    end else begin j <= j + 1'b1; st <= S_B0; end
                end else begin g <= g + 1'b1; st <= S_B0; end
            end else lane <= lane + 1'b1;
        end
        // ---- GAP: f[c] = (Σ_t SRC[t·C + c]) >> log2(L) ----
        S_GAP: begin
            src_e0 <= LAST_IN_A ? SRC_A : SRC_B;
            sidx <= g_addr[9:0];
            gv0 <= 1'b1;
            if (gt == LAST_L - 1) begin gt <= 0; st <= S_GAPD; drain <= 3'd0; end
            else gt <= gt + 1'b1;
        end
        S_GAPD: begin
            drain <= drain + 1'b1;
            if (drain == 3'd2) begin
                gapf[gc] <= g_avg[7:0];
                gsum <= 13'd0;
                if (gc == LAST_OC - 1) begin g <= 0; st <= S_B0; end
                else begin gc <= gc + 1'b1; st <= S_GAP; end
            end
        end
        // ---- argmax 2 tầng (bằng nhau → chỉ số nhỏ) ----
        S_DONE1: begin
            a_cls <= (lg[1] > lg[0]) ? 2'd1 : 2'd0;  a_val <= (lg[1] > lg[0]) ? lg[1] : lg[0];
            b_cls <= (lg[3] > lg[2]) ? 2'd3 : 2'd2;  b_val <= (lg[3] > lg[2]) ? lg[3] : lg[2];
            st <= S_DONE2;
        end
        S_DONE2: begin
            if (b_val > a_val) begin class_id <= b_cls; score <= b_val; end
            else               begin class_id <= a_cls; score <= a_val; end
            logit0_out <= lg[0]; logit1_out <= lg[1]; logit2_out <= lg[2]; logit3_out <= lg[3];
            st <= S_DONE3;
        end
        S_DONE3: begin
            inference_done <= 1'b1;
            busy <= 1'b0;
            dense <= 1'b0;
            st <= S_IDLE;
        end
        default: st <= S_IDLE;
        endcase
    end
endmodule
