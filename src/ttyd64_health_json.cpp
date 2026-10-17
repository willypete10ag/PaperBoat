#include "ttyd64_health_json.h"
#include <algorithm>
#include <iterator>
using nlohmann::ordered_json;
void ttyd64_read_health(Ttyd64PartnerHP* health, const int* ranks, const ordered_json& ship) {
    ttyd64_health_init(health, ranks);
    auto found = ship.find("ttyd64PartnerHP");
    if (found == ship.end() || !found->is_object() || !found->contains("version")
        || !(*found)["version"].is_number_integer() || (*found)["version"] != 1 || !found->contains("partners")
        || !(*found)["partners"].is_array())
        return;
    const auto& partners = (*found)["partners"];
    for (size_t i = 0; i < TTYD64_PARTNER_HP_COUNT && i < partners.size(); ++i) {
        const auto& entry = partners[i];
        if (!entry.is_object() || !entry.contains("curHP") || !entry["curHP"].is_number_integer())
            continue;
        const auto& current = entry["curHP"];
        // Split signed/unsigned before narrowing: UINT64_MAX must clamp high.
        // Max HP derives from rank, never the supplied JSON maxHP.
        if (current.is_number_unsigned())
            health[i].curHP = std::min<uint64_t>(current.get<uint64_t>(), health[i].maxHP);
        else
            health[i].curHP = std::clamp<int64_t>(current.get<int64_t>(), 0, health[i].maxHP);
    }
}
ordered_json ttyd64_write_health(const Ttyd64PartnerHP* health, const int* ranks) {
    Ttyd64PartnerHP normalized[TTYD64_PARTNER_HP_COUNT];
    std::copy(health, health + TTYD64_PARTNER_HP_COUNT, normalized);
    ttyd64_health_normalize(normalized, ranks);
    ordered_json partners = ordered_json::array();
    for (const auto& entry : normalized)
        partners.push_back({ { "curHP", entry.curHP }, { "maxHP", entry.maxHP } });
    return { { "version", 1 }, { "partners", partners } };
}
