#ifndef TTYD64_HEALTH_JSON_H
#define TTYD64_HEALTH_JSON_H
#include "ttyd64_rules.h"
#include <nlohmann/json.hpp>
void ttyd64_read_health(Ttyd64PartnerHP* health, const int* ranks, const nlohmann::ordered_json& ship);
nlohmann::ordered_json ttyd64_write_health(const Ttyd64PartnerHP* health, const int* ranks);
#endif
