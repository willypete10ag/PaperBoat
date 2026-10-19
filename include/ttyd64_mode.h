#ifndef TTYD64_MODE_H
#define TTYD64_MODE_H

// The running file owns this value. Reading a save preview must not select it.
typedef enum Ttyd64Mode {
    TTYD64_MODE_VANILLA = 0,
    TTYD64_MODE_TTYD64 = 1,
} Ttyd64Mode;

#ifdef __cplusplus
extern "C" {
#endif
int ttyd64_mode_enabled(void);
void ttyd64_mode_select_file(int mode);
int ttyd64_mode_fp_cost(int mode, int moveID, int vanillaCost);
int ttyd64_mode_bp_cost(int mode, int moveID, int vanillaCost);
int ttyd64_consumable_count(void);
int ttyd64_mode_consumable_id_at(int index);
#ifdef __cplusplus
}
#endif
#endif
