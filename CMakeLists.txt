cmake_minimum_required(VERSION 3.10)

project(MOESI_Coherency_Test CXX)

# Set standard to C++14 and make it mandatory
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED True)
set(CMAKE_CXX_EXTENSIONS OFF) # Ensure we stick strictly to the standard

# Find the necessary thread library package
find_package(Threads REQUIRED)

add_executable(coherency_test moesi_coherency_test.cpp)

# ⭐ PRIMARY FIX: Ensure C++14 features are enabled.
# This forces the compiler to use the correct standard.
target_compile_features(coherency_test PRIVATE cxx_std_14)

# SECONDARY FIX (Fallback): Explicitly add the standard flag just in case
target_compile_options(coherency_test PRIVATE "-std=c++14")

# Link the portable CMake Threads target
target_link_libraries(coherency_test Threads::Threads)

# CRITICAL FOR MINGW: Statically link libstdc++ and libgcc 
target_link_options(coherency_test PRIVATE 
    "-static-libstdc++"
    "-static-libgcc"
)