#include "ttyd64_mode_json.h"

Ttyd64Mode ttyd64_read_mode(const nlohmann::ordered_json& ship) {
    if (!ship.is_object()) return TTYD64_MODE_VANILLA;
    const auto found = ship.find("ttyd64Mode");
    if (found == ship.end() || !found->is_object()) return TTYD64_MODE_VANILLA;
    const auto version = found->find("version");
    const auto rules = found->find("rules");
    if (version == found->end() || !version->is_number_integer() || *version != 1
        || rules == found->end() || !rules->is_string() || *rules != "ttyd64")
        return TTYD64_MODE_VANILLA;
    return TTYD64_MODE_TTYD64;
}

void ttyd64_write_mode(nlohmann::ordered_json& ship, int mode) {
    if (!ship.is_object()) ship = nlohmann::ordered_json::object();
    ship["ttyd64Mode"] = { { "version", 1 }, { "rules", mode == TTYD64_MODE_TTYD64 ? "ttyd64" : "vanilla" } };
}
