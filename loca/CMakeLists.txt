cmake_minimum_required(VERSION 3.18)
project(bergner_spichtinger_2026_loca LANGUAGES CXX)

file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/include/bergner_spichtinger_2026_loca/midpoint_loca.hpp" BS2026_MIDPOINT_LOCA_SHA256)
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/include/bergner_spichtinger_2026_loca/midpoint_orbit.hpp" BS2026_MIDPOINT_ORBIT_SHA256)
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/include/bergner_spichtinger_2026_loca/model.hpp" BS2026_MODEL_SHA256)
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/include/bergner_spichtinger_2026_loca/midpoint_nox.hpp" BS2026_MIDPOINT_NOX_SHA256)
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/include/bergner_spichtinger_2026_loca/collocation_coefficients.hpp" BS2026_COLLOCATION_COEFFICIENTS_SHA256)
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/src/midpoint_orbit_cli.cpp" BS2026_MIDPOINT_CLI_SHA256)
file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/CMakeLists.txt" BS2026_CMAKE_SOURCE_SHA256)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON CACHE BOOL "Export compile_commands.json for C++ LSP tooling")

set(Trilinos_DIR "/opt/Trilinos/lib64/cmake/Trilinos" CACHE PATH "Path to Trilinos CMake package")
find_package(Trilinos REQUIRED CONFIG)

set(BS2026_MPI_ROOT "/usr/lib64/mpi/gcc/openmpi5" CACHE PATH "MPI root used by this Trilinos build when compiler wrappers are unavailable")

add_executable(bs2026_loca_model
  src/model_cli.cpp
)

add_executable(bs2026_midpoint_orbit
  src/midpoint_orbit_cli.cpp
)
target_compile_definitions(bs2026_midpoint_orbit PRIVATE
  BS2026_MIDPOINT_LOCA_SHA256="${BS2026_MIDPOINT_LOCA_SHA256}"
  BS2026_MIDPOINT_ORBIT_SHA256="${BS2026_MIDPOINT_ORBIT_SHA256}"
  BS2026_MODEL_SHA256="${BS2026_MODEL_SHA256}"
  BS2026_MIDPOINT_NOX_SHA256="${BS2026_MIDPOINT_NOX_SHA256}"
  BS2026_COLLOCATION_COEFFICIENTS_SHA256="${BS2026_COLLOCATION_COEFFICIENTS_SHA256}"
  BS2026_MIDPOINT_CLI_SHA256="${BS2026_MIDPOINT_CLI_SHA256}"
  BS2026_CMAKE_SOURCE_SHA256="${BS2026_CMAKE_SOURCE_SHA256}"
  BS2026_CMAKE_BUILD_TYPE="${CMAKE_BUILD_TYPE}"
)

set(BS2026_LOCA_TARGETS bs2026_loca_model bs2026_midpoint_orbit)

foreach(target IN LISTS BS2026_LOCA_TARGETS)
  target_include_directories(${target} PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${Trilinos_INCLUDE_DIRS}
  )
endforeach()

if(EXISTS "${BS2026_MPI_ROOT}/include/mpi.h")
  foreach(target IN LISTS BS2026_LOCA_TARGETS)
    target_include_directories(${target} PRIVATE "${BS2026_MPI_ROOT}/include")
  endforeach()
endif()
if(EXISTS "${BS2026_MPI_ROOT}/lib64/libmpi.so")
  foreach(target IN LISTS BS2026_LOCA_TARGETS)
    target_link_directories(${target} PRIVATE "${BS2026_MPI_ROOT}/lib64")
    target_link_libraries(${target} PRIVATE mpi)
    set_property(TARGET ${target} APPEND PROPERTY BUILD_RPATH "${BS2026_MPI_ROOT}/lib64")
  endforeach()
endif()

separate_arguments(BS2026_TRILINOS_CXX_FLAGS NATIVE_COMMAND "${Trilinos_CXX_COMPILER_FLAGS}")
foreach(target IN LISTS BS2026_LOCA_TARGETS)
  target_compile_options(${target} PRIVATE ${BS2026_TRILINOS_CXX_FLAGS})
  target_link_libraries(${target} PRIVATE ${Trilinos_LIBRARIES})
endforeach()
