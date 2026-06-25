cmake_minimum_required(VERSION 3.18)
project(bergner_spichtinger_2026_loca LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(Trilinos_DIR "/opt/Trilinos/lib64/cmake/Trilinos" CACHE PATH "Path to Trilinos CMake package")
find_package(Trilinos REQUIRED CONFIG)

set(BS2026_MPI_ROOT "/usr/lib64/mpi/gcc/openmpi5" CACHE PATH "MPI root used by this Trilinos build when compiler wrappers are unavailable")

add_executable(bs2026_loca_model
  src/model_cli.cpp
)

target_include_directories(bs2026_loca_model PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${Trilinos_INCLUDE_DIRS}
)

if(EXISTS "${BS2026_MPI_ROOT}/include/mpi.h")
  target_include_directories(bs2026_loca_model PRIVATE "${BS2026_MPI_ROOT}/include")
endif()
if(EXISTS "${BS2026_MPI_ROOT}/lib64/libmpi.so")
  target_link_directories(bs2026_loca_model PRIVATE "${BS2026_MPI_ROOT}/lib64")
  target_link_libraries(bs2026_loca_model PRIVATE mpi)
  set_property(TARGET bs2026_loca_model APPEND PROPERTY BUILD_RPATH "${BS2026_MPI_ROOT}/lib64")
endif()

separate_arguments(BS2026_TRILINOS_CXX_FLAGS NATIVE_COMMAND "${Trilinos_CXX_COMPILER_FLAGS}")
target_compile_options(bs2026_loca_model PRIVATE ${BS2026_TRILINOS_CXX_FLAGS})
target_link_libraries(bs2026_loca_model PRIVATE ${Trilinos_LIBRARIES})
