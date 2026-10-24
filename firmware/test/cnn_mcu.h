/*
 * cnn_mcu.h — suy luận CNN INT8 thuần trên MCU (bản đối chứng MCU-only, việc FW-15). C thuần, số học đúng A.5:
 * Conv k5 pad2 → requant (acc ≤ 0 → 0, min(acc >> n, 127)) → MaxPool2; đầu ra GAP ((Σ) >> log2 L) hoặc Flatten
 * (i = t·C + c); Dense; argmax (bằng nhau → chỉ số nhỏ); SCORE = clamp((top1 − top2) >> score_shift, 0, 127).
 * Weight theo thứ tự E1: W[oc][ic][k]; Dense [lớp][đặc trưng]. Chạy được N1, N2, N2-S, N2-L.
 * RAM: hai bộ đệm 1.024 byte. Đối chiếu: forward() trong ml/src/golden_model.py (tools/m0_test.py, mode 7).
 */
#ifndef CNN_MCU_H
#define CNN_MCU_H

#include <stdint.h>

#define CNN_MAX_LAYERS  3
#define CNN_BUF_BYTES   1024

typedef struct {
    uint16_t       oc, ic;
    uint8_t        shift;
    const int8_t  *w;           /* oc × ic × 5 */
    const int32_t *b;           /* oc */
} cnn_layer_t;

typedef struct {
    uint8_t        n_layers;
    uint8_t        head_gap;    /* 1: GAP (N1), 0: Flatten (N2) */
    uint8_t        score_shift;
    cnn_layer_t    L[CNN_MAX_LAYERS];
    uint16_t       F;           /* số đặc trưng vào Dense */
    const int8_t  *wd;          /* 4 × F */
    const int32_t *bd;          /* 4 */
} cnn_model_t;

/* x: 128 × 6 INT8, i = t·6 + c. Trả về lớp 0..3; logits và score có thể là 0. */
int cnn_mcu_run(const cnn_model_t *m, const int8_t *x, int32_t logits[4], uint8_t *score);

#endif
