find_package(nlohmann_json 3.11 REQUIRED)
add_library(ttyd64_logic STATIC ../src/ttyd64_mode.c ../src/ttyd64_mode_json.cpp ../src/ttyd64_rules.c ../src/ttyd64_health_json.cpp)
target_include_directories(ttyd64_logic PUBLIC ../include)
target_link_libraries(ttyd64_logic PUBLIC nlohmann_json::nlohmann_json)
target_compile_features(ttyd64_logic PUBLIC cxx_std_17)
add_executable(ttyd64_logic_tests ttyd64_logic_tests.cpp)
target_link_libraries(ttyd64_logic_tests PRIVATE ttyd64_logic)
add_test(NAME ttyd64_gameplay_logic COMMAND ttyd64_logic_tests)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
add_test(NAME ttyd64_source_rules
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/check_source_rules.py
        --source ${CMAKE_SOURCE_DIR} --logic $<TARGET_FILE:ttyd64_logic_tests>)
