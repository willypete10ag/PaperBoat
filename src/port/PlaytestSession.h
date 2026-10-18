#pragma once

#ifdef __cplusplus
// Returns -1 on error, 0 for normal startup, 1 to start the game, 2 for preflight only.
int PreparePlaytestSession(int argc, char** argv);
extern "C" {
#endif
int ttyd64_playtest_take_request(void);
int ttyd64_playtest_startup(void);
#ifdef __cplusplus
}
#endif
