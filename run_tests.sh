#!/bin/bash
# Must be run with sudo privileges

set -e
set +x

# Settings
PERF_PATH=/usr/lib/linux-tools/6.14.0-33-generic/perf
RESULTS_DIR="./results/raw/"
REPEATS=10
RUNS=$((REPEATS+1))

# Added branch-misses to metrics to measure the uArch stress
METRICS_ENERGY="power/energy-pkg/,branch-misses"
METRICS_CACHE="ls_any_fills_from_sys.remote_cache,ls_dmnd_fills_from_sys.remote_cache,ls_bad_status2.stli_other,cache-misses"
METRICS_L1="ls_dmnd_fills_from_sys.all,ls_dmnd_fills_from_sys.local_l2"
METRICS_L2="l2_cache_req_stat.all,l2_cache_req_stat.ic_dc_hit_in_l2,l2_cache_req_stat.ic_dc_miss_in_l2"
METRICS_L3="ls_dmnd_fills_from_sys.local_ccx,ls_dmnd_fills_from_sys.dram_io_all"

NUM_THREADS=(1 2 3 4 5 6 7 8 9 10)
NUM_EXECUTIONS=(125000000 250000000 500000000 1000000000)
TARGET_GOOD="./bin/good.exe"
TARGET_BAD="./bin/bad.exe"

# Compile first
./compile_sources.sh || { echo "Error compiling sources."; exit 1; }

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

# Cold start mitigation: run 2 times at the beginning to warm up the processor
printf "Warming up the processor with initial test runs...\n"
$TARGET_BAD 2 125000000 0 > /dev/null 2>&1 || true
$TARGET_GOOD 2 125000000 0 > /dev/null 2>&1 || true
printf "Warm-up complete.\n\n"

for THREADS in "${NUM_THREADS[@]}"; do
    for NUM_EXECUTIONS in "${NUM_EXECUTIONS[@]}"; do
        # Determine available modes
        MODES=(0 2 3)
        if [ "$THREADS" -eq 2 ]; then
            MODES+=(1)
        fi

        for MODE in "${MODES[@]}"; do
            # NEW: Loop for uArch Stress (0 = Normal, 1 = Bad uArch)
            for STRESS in 0 1; do
                
                printf "Running tests with %d threads, mode %d, stress %d...\n" "$THREADS" "$MODE" "$STRESS"

                # Output files (Added _stress${STRESS} suffix)
                energy_bad_file="${RESULTS_DIR}/energy_${THREADS}_${NUM_EXECUTIONS}_mode${MODE}_stress${STRESS}_bad.txt"
                perf_cache_bad_file="${RESULTS_DIR}/perf_cache_${THREADS}_${NUM_EXECUTIONS}_mode${MODE}_stress${STRESS}_bad.txt"
                perf_uarch_bad_file="${RESULTS_DIR}/perf_uarch_${THREADS}_${NUM_EXECUTIONS}_mode${MODE}_stress${STRESS}_bad.txt"
                perf_l1_bad_file="${RESULTS_DIR}/perf_l1_${THREADS}_${NUM_EXECUTIONS}_mode${MODE}_stress${STRESS}_bad.txt"
                perf_l2_bad_file="${RESULTS_DIR}/perf_l2_${THREADS}_${NUM_EXECUTIONS}_mode${MODE}_stress${STRESS}_bad.txt"
                perf_l3_bad_file="${RESULTS_DIR}/perf_l3_${THREADS}_${NUM_EXECUTIONS}_mode${MODE}_stress${STRESS}_bad.txt"
                time_bad_file="${RESULTS_DIR}/time_${THREADS}_${NUM_EXECUTIONS}_mode${MODE}_stress${STRESS}_bad.txt"
                
                energy_good_file="${RESULTS_DIR}/energy_${THREADS}_${NUM_EXECUTIONS}_mode${MODE}_stress${STRESS}_good.txt"
                perf_cache_good_file="${RESULTS_DIR}/perf_cache_${THREADS}_${NUM_EXECUTIONS}_mode${MODE}_stress${STRESS}_good.txt"
                perf_uarch_good_file="${RESULTS_DIR}/perf_uarch_${THREADS}_${NUM_EXECUTIONS}_mode${MODE}_stress${STRESS}_good.txt"
                perf_l1_good_file="${RESULTS_DIR}/perf_l1_${THREADS}_${NUM_EXECUTIONS}_mode${MODE}_stress${STRESS}_good.txt"
                perf_l2_good_file="${RESULTS_DIR}/perf_l2_${THREADS}_${NUM_EXECUTIONS}_mode${MODE}_stress${STRESS}_good.txt"
                perf_l3_good_file="${RESULTS_DIR}/perf_l3_${THREADS}_${NUM_EXECUTIONS}_mode${MODE}_stress${STRESS}_good.txt"
                time_good_file="${RESULTS_DIR}/time_${THREADS}_${NUM_EXECUTIONS}_mode${MODE}_stress${STRESS}_good.txt"

                # Check if tests are already completed
                if [ -f "$time_bad_file" ] && [ "$(wc -l < "$time_bad_file")" -ge "$RUNS" ] && \
                   [ -f "$time_good_file" ] && [ "$(wc -l < "$time_good_file")" -ge "$RUNS" ]; then
                    printf "Tests already completed for %d threads, mode %d, stress %d. Skipping...\n" "$THREADS" "$MODE" "$STRESS"
                    continue
                fi

                # Initialize files
                > "$energy_bad_file"
                > "$perf_uarch_bad_file"
                echo "ls_any_fills_from_sys.remote_cache,ls_dmnd_fills_from_sys.remote_cache,ls_bad_status2.stli_other,cache-misses" > "$perf_cache_bad_file"
                echo "ls_dmnd_fills_from_sys.all,ls_dmnd_fills_from_sys.local_l2" > "$perf_l1_bad_file"
                echo "l2_cache_req_stat.all,l2_cache_req_stat.ic_dc_hit_in_l2,l2_cache_req_stat.ic_dc_miss_in_l2" > "$perf_l2_bad_file"
                echo "ls_dmnd_fills_from_sys.local_ccx,ls_dmnd_fills_from_sys.dram_io_all" > "$perf_l3_bad_file"
                > "$time_bad_file"
                
                > "$energy_good_file"
                > "$perf_uarch_good_file"
                echo "ls_any_fills_from_sys.remote_cache,ls_dmnd_fills_from_sys.remote_cache,ls_bad_status2.stli_other,cache-misses" > "$perf_cache_good_file"
                echo "ls_dmnd_fills_from_sys.all,ls_dmnd_fills_from_sys.local_l2" > "$perf_l1_good_file"
                echo "l2_cache_req_stat.all,l2_cache_req_stat.ic_dc_hit_in_l2,l2_cache_req_stat.ic_dc_miss_in_l2" > "$perf_l2_good_file"
                echo "ls_dmnd_fills_from_sys.local_ccx,ls_dmnd_fills_from_sys.dram_io_all" > "$perf_l3_good_file"
                > "$time_good_file"

                printf "  Running bad coherency test (Mode %d, Stress %d)...\n" "$MODE" "$STRESS"
                
                for ((r=1; r<=RUNS; r++)); do
                    # NOTE: Added $STRESS as the 4th argument
                    
                    # 1. Energy
                    energy_output=$($PERF_PATH stat -e $METRICS_ENERGY -- $TARGET_BAD $THREADS $NUM_EXECUTIONS $MODE $STRESS 2>&1) || true
                    energy_val=$(echo "$energy_output" | awk '/power\/energy-pkg/ {gsub(",", "", $1); print $1; exit}' || echo "NaN")
                    echo "$energy_val" >> "$energy_bad_file"
                    
                    # Time parsing (from energy output)
                    time_val=$(echo "$energy_output" | grep "Time for bad coherency" | sed 's/.*: \([0-9.]*\) ms/\1/' || echo "NaN")
                    echo "$time_val" >> "$time_bad_file"

                    # Extract Branch Misses
                    uarch_val=$(echo "$energy_output" | awk '/branch-misses/ {gsub(",", "", $1); print $1; exit}' || echo "NaN")
                    echo "$uarch_val" >> "$perf_uarch_bad_file"
                    
                    # 2. Cache (Remote/Bad Status)
                    cache_output=$($PERF_PATH stat -e $METRICS_CACHE -- $TARGET_BAD $THREADS $NUM_EXECUTIONS $MODE $STRESS 2>&1) || true
                    cache_vals=$(echo "$cache_output" | awk '
                        /ls_any_fills_from_sys\.remote_cache/ {gsub(",", "", $1); remote=$1}
                        /ls_dmnd_fills_from_sys\.remote_cache/ {gsub(",", "", $1); dmnd=$1}
                        /ls_bad_status2\.stli_other/ {gsub(",", "", $1); stli=$1}
                        /cache-misses/ {gsub(",", "", $1); misses=$1}
                        END {print remote "," dmnd "," stli "," misses}
                    ' || echo "NaN,NaN,NaN,NaN")
                    echo "$cache_vals" >> "$perf_cache_bad_file"
                    
                    # 3. L1 Cache
                    l1_output=$($PERF_PATH stat -e $METRICS_L1 -- $TARGET_BAD $THREADS $NUM_EXECUTIONS $MODE $STRESS 2>&1) || true
                    l1_vals=$(echo "$l1_output" | awk '
                        /ls_dmnd_fills_from_sys\.all/ {gsub(",", "", $1); l1_fills=$1}
                        /ls_dmnd_fills_from_sys\.local_l2/ {gsub(",", "", $1); l1_l2_hits=$1}
                        END {print l1_fills "," l1_l2_hits}
                    ' || echo "NaN,NaN")
                    echo "$l1_vals" >> "$perf_l1_bad_file"
                    
                    # 4. L2 Cache
                    l2_output=$($PERF_PATH stat -e $METRICS_L2 -- $TARGET_BAD $THREADS $NUM_EXECUTIONS $MODE $STRESS 2>&1) || true
                    l2_vals=$(echo "$l2_output" | awk '
                        /l2_cache_req_stat\.all/ {gsub(",", "", $1); l2_all=$1}
                        /l2_cache_req_stat\.ic_dc_hit_in_l2/ {gsub(",", "", $1); l2_hits=$1}
                        /l2_cache_req_stat\.ic_dc_miss_in_l2/ {gsub(",", "", $1); l2_miss=$1}
                        END {print l2_all "," l2_hits "," l2_miss}
                    ' || echo "NaN,NaN,NaN")
                    echo "$l2_vals" >> "$perf_l2_bad_file"
                    
                    # 5. L3 Cache
                    l3_output=$($PERF_PATH stat -e $METRICS_L3 -- $TARGET_BAD $THREADS $NUM_EXECUTIONS $MODE $STRESS 2>&1) || true
                    l3_vals=$(echo "$l3_output" | awk '
                        /ls_dmnd_fills_from_sys\.local_ccx/ {gsub(",", "", $1); l3_access=$1}
                        /ls_dmnd_fills_from_sys\.dram_io_all/ {gsub(",", "", $1); l3_miss=$1}
                        END {print l3_access "," l3_miss}
                    ' || echo "NaN,NaN")
                    echo "$l3_vals" >> "$perf_l3_bad_file"
                done

                printf "  Running good coherency test (Mode %d, Stress %d)...\n" "$MODE" "$STRESS"
                
                for ((r=1; r<=RUNS; r++)); do
                    # NOTE: Added $STRESS as the 4th argument
                    
                    # 1. Energy
                    energy_output=$($PERF_PATH stat -e $METRICS_ENERGY -- $TARGET_GOOD $THREADS $NUM_EXECUTIONS $MODE $STRESS 2>&1) || true
                    energy_val=$(echo "$energy_output" | awk '/power\/energy-pkg/ {gsub(",", "", $1); print $1; exit}' || echo "NaN")
                    echo "$energy_val" >> "$energy_good_file"
                    
                    # Time parsing (from energy output)
                    time_val=$(echo "$energy_output" | grep "Time for good coherency" | sed 's/.*: \([0-9.]*\) ms/\1/' || echo "NaN")
                    echo "$time_val" >> "$time_good_file"

                    # Extract Branch Misses
                    uarch_val=$(echo "$energy_output" | awk '/branch-misses/ {gsub(",", "", $1); print $1; exit}' || echo "NaN")
                    echo "$uarch_val" >> "$perf_uarch_good_file"
                    
                    # 2. Cache
                    cache_output=$($PERF_PATH stat -e $METRICS_CACHE -- $TARGET_GOOD $THREADS $NUM_EXECUTIONS $MODE $STRESS 2>&1) || true
                    cache_vals=$(echo "$cache_output" | awk '
                        /ls_any_fills_from_sys\.remote_cache/ {gsub(",", "", $1); remote=$1}
                        /ls_dmnd_fills_from_sys\.remote_cache/ {gsub(",", "", $1); dmnd=$1}
                        /ls_bad_status2\.stli_other/ {gsub(",", "", $1); stli=$1}
                        /cache-misses/ {gsub(",", "", $1); misses=$1}
                        END {print remote "," dmnd "," stli "," misses}
                    ' || echo "NaN,NaN,NaN,NaN")
                    echo "$cache_vals" >> "$perf_cache_good_file"
                    
                    # 3. L1 Cache
                    l1_output=$($PERF_PATH stat -e $METRICS_L1 -- $TARGET_GOOD $THREADS $NUM_EXECUTIONS $MODE $STRESS 2>&1) || true
                    l1_vals=$(echo "$l1_output" | awk '
                        /ls_dmnd_fills_from_sys\.all/ {gsub(",", "", $1); l1_fills=$1}
                        /ls_dmnd_fills_from_sys\.local_l2/ {gsub(",", "", $1); l1_l2_hits=$1}
                        END {print l1_fills "," l1_l2_hits}
                    ' || echo "NaN,NaN")
                    echo "$l1_vals" >> "$perf_l1_good_file"
                    
                    # 4. L2 Cache
                    l2_output=$($PERF_PATH stat -e $METRICS_L2 -- $TARGET_GOOD $THREADS $NUM_EXECUTIONS $MODE $STRESS 2>&1) || true
                    l2_vals=$(echo "$l2_output" | awk '
                        /l2_cache_req_stat\.all/ {gsub(",", "", $1); l2_all=$1}
                        /l2_cache_req_stat\.ic_dc_hit_in_l2/ {gsub(",", "", $1); l2_hits=$1}
                        /l2_cache_req_stat\.ic_dc_miss_in_l2/ {gsub(",", "", $1); l2_miss=$1}
                        END {print l2_all "," l2_hits "," l2_miss}
                    ' || echo "NaN,NaN,NaN")
                    echo "$l2_vals" >> "$perf_l2_good_file"
                    
                    # 5. L3 Cache
                    l3_output=$($PERF_PATH stat -e $METRICS_L3 -- $TARGET_GOOD $THREADS $NUM_EXECUTIONS $MODE $STRESS 2>&1) || true
                    l3_vals=$(echo "$l3_output" | awk '
                        /ls_dmnd_fills_from_sys\.local_ccx/ {gsub(",", "", $1); l3_access=$1}
                        /ls_dmnd_fills_from_sys\.dram_io_all/ {gsub(",", "", $1); l3_miss=$1}
                        END {print l3_access "," l3_miss}
                    ' || echo "NaN,NaN")
                    echo "$l3_vals" >> "$perf_l3_good_file"
                done

                printf "Completed tests with %d threads, mode %d, stress %d and %d executions.\n\n" "$THREADS" "$MODE" "$STRESS" "$NUM_EXECUTIONS"
            done
        done
    done
done

# Restore perf_event_paranoid to original value
printf "Restoring perf_event_paranoid to 4...\n"
echo 4 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
printf "perf_event_paranoid restored.\n\n"

printf "End of this script. All experiments completed successfully!\n"
