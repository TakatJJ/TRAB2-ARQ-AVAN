#!/bin/bash
# Must be run with sudo privileges

set -e
set +x

# Settings
CXX=g++
CXXFLAGS="-std=c++17"
TARGET_GOOD=./bin/good.exe
SRC_GOOD=./src/good_coherency.cpp
TARGET_BAD=./bin/bad.exe
SRC_BAD=./src/bad_coherency.cpp
PERF_PATH=perf
RESULTS_DIR="./results/raw/"
REPEATS=10
METRICS_CACHE="cache-references,cache-misses,instructions"
METRICS_ENERGY="power/energy-pkg/" # the energy consumed only by the current core running the process

NUM_THREADS=(2 3 4)
NUM_EXECUTIONS=(100000000 200000000 500000000 1000000000)

# Compile the good program
printf "Compiling $SRC_GOOD...\n"
if ! $CXX $CXXFLAGS -o $TARGET_GOOD $SRC_GOOD; then
    printf "Compilation failed for $SRC_GOOD.\n"
    exit 1
fi
# Compile the bad program
printf "Compiling $SRC_BAD...\n"
if ! $CXX $CXXFLAGS -o $TARGET_BAD $SRC_BAD; then
    printf "Compilation failed for $SRC_BAD.\n"
    exit 1
fi
printf "Compilation finished.\n\n"

# Prepare results directory
printf "Preparing results directory at '$RESULTS_DIR'...\n\n"
if [ -d "$RESULTS_DIR" ]; then
    rm -rf -- "$RESULTS_DIR"
fi
mkdir -p -- "$RESULTS_DIR"

# Ensure directory is owned by the user running the script (even if invoked via sudo)
owner_user="${SUDO_USER:-$(id -un)}"
owner_group="$(id -gn "$owner_user" 2>/dev/null || echo "$owner_user")"
sudo chown -R "$owner_user:$owner_group" "$RESULTS_DIR" 2>/dev/null || \
chown -R "$owner_user:$owner_group" "$RESULTS_DIR" 2>/dev/null || true

# Configure perf_event_paranoid for perf access
printf "Configuring perf permissions...\n"
echo -1 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
printf "perf_event_paranoid set to -1.\n\n"

for THREADS in "${NUM_THREADS[@]}"; do
    for NUM_EXECUTIONS in "${NUM_EXECUTIONS[@]}"; do
        # Determine available modes
        MODES=(0 2 3)
        if [ "$THREADS" -eq 2 ]; then
            MODES+=(1)
        fi

        for MODE in "${MODES[@]}"; do
            printf "Running tests with %d threads, mode %d...\n" "$THREADS" "$MODE"

            printf "  Running bad coherency test...\n"
            $PERF_PATH stat -e $METRICS_CACHE -r $REPEATS $TARGET_BAD $THREADS $NUM_EXECUTIONS $MODE > "${RESULTS_DIR}/bad_results_cache_${THREADS}_threads_${NUM_EXECUTIONS}_executions_mode${MODE}.txt" 2>&1
            $PERF_PATH stat -e $METRICS_ENERGY -r $REPEATS $TARGET_BAD $THREADS $NUM_EXECUTIONS $MODE > "${RESULTS_DIR}/bad_results_energy_${THREADS}_threads_${NUM_EXECUTIONS}_executions_mode${MODE}.txt" 2>&1

            printf "  Running good coherency test...\n"
            $PERF_PATH stat -e $METRICS_CACHE -r $REPEATS $TARGET_GOOD $THREADS $NUM_EXECUTIONS $MODE > "${RESULTS_DIR}/good_results_cache_${THREADS}_threads_${NUM_EXECUTIONS}_executions_mode${MODE}.txt" 2>&1
            $PERF_PATH stat -e $METRICS_ENERGY -r $REPEATS $TARGET_GOOD $THREADS $NUM_EXECUTIONS $MODE > "${RESULTS_DIR}/good_results_energy_${THREADS}_threads_${NUM_EXECUTIONS}_executions_mode${MODE}.txt" 2>&1

            printf "Completed tests with %d threads, mode %d and %d executions.\n\n" "$THREADS" "$MODE" "$NUM_EXECUTIONS"
        done
    done
done

# Restore perf_event_paranoid to original value
printf "Restoring perf_event_paranoid to 4...\n"
echo 4 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
printf "perf_event_paranoid restored.\n\n"

printf "End of this script. All experiments completed successfully!\n"
