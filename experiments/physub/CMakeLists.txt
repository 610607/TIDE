cmake_minimum_required(VERSION 3.20)
project(physub LANGUAGES CXX)

# Exploration substrate, not the TIDE kernel. See README.md.

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

if(MSVC)
  set(PHYSUB_WARNINGS /W4 /WX)
else()
  set(PHYSUB_WARNINGS -Wall -Wextra -Werror)
endif()

# GCC 13 false positives under -O2/-O3, silenced only in the files that trigger them:
# - ps_physics.cpp: -Warray-bounds inside std::sort over the 4-element `outs` array,
#   which never holds more than 4 entries.
# - ps_run.cpp: -Wstringop-overread inside std::vector<uint8_t> comparison (std::map key).
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  set_source_files_properties(src/ps_physics.cpp PROPERTIES COMPILE_OPTIONS -Wno-array-bounds)
  set_source_files_properties(apps/ps_run.cpp PROPERTIES COMPILE_OPTIONS -Wno-stringop-overread)
endif()

add_library(physub STATIC
  src/ps_world.cpp
  src/ps_exec.cpp
  src/ps_resolve.cpp
  src/ps_physics.cpp)
target_include_directories(physub PUBLIC src)
target_compile_options(physub PRIVATE ${PHYSUB_WARNINGS})

foreach(app ps_run ps_probe ps_knockout ps_copycut ps_scan)
  add_executable(${app} apps/${app}.cpp)
  target_link_libraries(${app} PRIVATE physub)
  target_compile_options(${app} PRIVATE ${PHYSUB_WARNINGS})
endforeach()

option(PHYSUB_CHECKS "Build the small-grid checks in checks/" ON)
if(PHYSUB_CHECKS)
  add_subdirectory(checks)
endif()

# Tests rely on assert, so keep it active in every build type.
add_executable(ps_test tests/ps_test.cpp)
target_link_libraries(ps_test PRIVATE physub)
target_include_directories(ps_test PRIVATE apps)
target_compile_options(ps_test PRIVATE ${PHYSUB_WARNINGS} -UNDEBUG)

enable_testing()
add_test(NAME ps_test COMMAND ps_test)
# Default-config replay digest; a change here means default dynamics changed.
set_tests_properties(ps_test PROPERTIES
  PASS_REGULAR_EXPRESSION "test 2\\] digest=6fb0e06a3160cc24.*all physub tests passed")
