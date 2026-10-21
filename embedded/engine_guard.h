#ifndef ENGINE_GUARD_H
#define ENGINE_GUARD_H
#include <stdint.h>
/* Units/order: kg/s, rad/s, Pa, source throttle position, K, source wastegate position.
 * Explicit caller-owned state; initialize before each independent recording.
 * status: 0 ML valid, 1 outside training envelope, 2 invalid physical input.
 * Diagnostic flag indicates pressure disagreement, not root-cause isolation. */
typedef struct { float previous[6]; float filtered; uint32_t count; uint8_t initialized; } EgState;
typedef struct { float pressure_pa; float residual_pa; uint8_t status; uint8_t alarm; } EgOutput;
void eg_init(EgState *s);
EgOutput eg_step(EgState *s, const float input[6], float measured_pressure_pa);
float eg_predict(const float features[13]);
#endif
