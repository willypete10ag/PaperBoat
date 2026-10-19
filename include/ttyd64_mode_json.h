#ifndef TTYD64_MODE_JSON_H
#define TTYD64_MODE_JSON_H
#include "ttyd64_mode.h"
#include <nlohmann/json.hpp>

Ttyd64Mode ttyd64_read_mode(const nlohmann::ordered_json& ship);
void ttyd64_write_mode(nlohmann::ordered_json& ship, int mode);
#endif
