#ifndef SO_LIEU_H
#define SO_LIEU_H
#include <stdint.h>
#include "cnn_mcu.h"
#define SO_CUA_SO 6
typedef struct {
    const char *ten;
    int32_t     lg[4];
    uint8_t     lop, diem;
} dap_an_t;
extern const cnn_model_t MO_HINH;
extern const int8_t      VAO[SO_CUA_SO][768];
extern const dap_an_t    DAP_AN[SO_CUA_SO];
#endif
