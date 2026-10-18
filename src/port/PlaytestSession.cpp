#include "PlaytestSession.h"

#include <SDL2/SDL.h>
#include <libultraship.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <nlohmann/json.hpp>

namespace {
int pendingProfile = 0;
namespace fs = std::filesystem;

std::string Utf8(const fs::path& path) {
    const auto utf8 = path.u8string();
    return std::string(utf8.begin(), utf8.end());
}

void RequireFile(const fs::path& path) {
    if (!fs::is_regular_file(path) || fs::file_size(path) == 0) {
        throw std::runtime_error("Missing or empty file: " + Utf8(path));
    }
}
} // namespace

int PreparePlaytestSession(int argc, char** argv) {
    if (argc < 2 || std::string(argv[1]).rfind("--ttyd64-playtest", 0) != 0) {
        return 0;
    }
    const bool preflight = std::string(argv[1]) == "--ttyd64-playtest-preflight";
    if (argc != 6 || (!preflight && std::string(argv[1]) != "--ttyd64-playtest")) {
        std::cerr << "Usage: --ttyd64-playtest[-preflight] NEW_SESSION PACKAGE ROM_ARCHIVE healing|status\n";
        return -1;
    }
    try {
        const std::string profile = argv[5];
        if (profile != "healing" && profile != "status") {
            throw std::runtime_error("Profile must be healing or status");
        }
        const fs::path session = fs::weakly_canonical(fs::absolute(fs::u8path(argv[2])));
        const fs::path package = fs::canonical(fs::u8path(argv[3]));
        const fs::path archive = fs::canonical(fs::u8path(argv[4]));
        for (const auto& file : { "paperboat.o2r", "config.yml", "playtest-keyboard.json" }) {
            RequireFile(package / file);
        }
        if (!fs::is_directory(package / "assets")) {
            throw std::runtime_error("Package is missing assets/");
        }
        RequireFile(archive);
        const fs::path assets = fs::canonical(package / "assets");
        for (auto parent = session; parent.has_relative_path(); parent = parent.parent_path()) {
            if (parent == assets) {
                throw std::runtime_error("Session cannot be inside the package assets folder");
            }
        }
        // Refuse even an empty existing folder: no existing configuration/save can be reused.
        fs::create_directories(session.parent_path());
        if (!fs::create_directory(session)) {
            throw std::runtime_error("Session already exists; choose a NEW folder: " + Utf8(session));
        }
        std::ofstream(session / ".ttyd64-playtest-session") << "PaperBoat isolated playtest v1\n";
        fs::copy_file(package / "paperboat.o2r", session / "paperboat.o2r");
        fs::copy_file(archive, session / "pm64.o2r");
        fs::copy_file(package / "config.yml", session / "config.yml");
        fs::copy_file(package / "playtest-keyboard.json", session / "paperboat.cfg.json");
        fs::copy(package / "assets", session / "assets", fs::copy_options::recursive);
        if (fs::is_regular_file(package / "gamecontrollerdb.txt")) {
            fs::copy_file(package / "gamecontrollerdb.txt", session / "gamecontrollerdb.txt");
        }
        fs::current_path(session);
        if (SDL_setenv("SHIP_HOME", Utf8(session).c_str(), 1) != 0) {
            throw std::runtime_error("Could not set the isolated SHIP_HOME");
        }
        // Windows portable builds use CWD; other builds may use SDL preference paths.
        // Check the actual engine paths BEFORE engine/config/save initialization.
        for (const auto& app : { "boat", "pm64" }) {
            if (!fs::equivalent(fs::u8path(Ship::Context::GetAppDirectoryPath(app)), session)) {
                throw std::runtime_error("This build does not support isolated playtests (app path escapes session)");
            }
        }
        nlohmann::json info = { { "profile", profile },
                                { "preflight_only", preflight },
                                { "session", Utf8(session) },
                                { "package", Utf8(package) },
                                { "save_directory", Utf8(session / "saves") },
                                { "config", Utf8(session / "paperboat.cfg.json") },
                                { "setup", "native new game; deliberate developer inventory/progression/wounds" } };
        std::ofstream report(session / "playtest-session.json");
        report << info.dump(2) << '\n';
        if (!report) {
            throw std::runtime_error("Could not write playtest session report");
        }
        std::cout << "TTYD64 isolated session: " << Utf8(session) << std::endl;
        if (!preflight) {
            pendingProfile = profile == "healing" ? 1 : 2;
        }
        return preflight ? 2 : 1;
    } catch (const std::exception& error) {
        std::cerr << "TTYD64 playtest setup failed: " << error.what() << '\n';
        return -1;
    }
}

extern "C" int ttyd64_playtest_take_request(void) {
    const int profile = pendingProfile;
    pendingProfile = 0; // Reset/new-game must never reactivate the prototype.
    return profile;
}
