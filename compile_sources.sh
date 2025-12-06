#!/bin/bash
# Script para compilar os códigos fonte good_coherency.cpp e bad_coherency.cpp

set -e
set +x

# Settings
CXX="g++"
CXXFLAGS="-std=c++17 -pthread"
TARGET_GOOD=./bin/good.exe
SRC_GOOD=./src/coherency.cpp
DEFINE_GOOD="ALIGNED_COUNTER"
TARGET_BAD=./bin/bad.exe
SRC_BAD=./src/coherency.cpp
DEFINE_BAD="UNALIGNED_COUNTER"

# Compile the good program
printf "Compiling $SRC_GOOD to $TARGET_GOOD...\n"
if ! $CXX $CXXFLAGS -D$DEFINE_GOOD $SRC_GOOD -o $TARGET_GOOD; then
    printf "Failed to compile $SRC_GOOD.\n"
    exit 1
fi

# Compile the bad program
printf "Compiling $SRC_BAD to $TARGET_BAD...\n"
if ! $CXX $CXXFLAGS -D$DEFINE_BAD $SRC_BAD -o $TARGET_BAD; then
    printf "Failed to compile $SRC_BAD.\n"
    exit 1
fi
printf "\nCompilation finished.\n"
