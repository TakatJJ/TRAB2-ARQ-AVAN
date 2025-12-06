#!/bin/bash
# Must be run with sudo privileges

set -e
set +x

# Settings
PERF_PATH=/usr/lib/linux-tools/6.14.0-33-generic/perf
RESULTS_DIR="./results/raw/"
REPEATS=10
RUNS=$((REPEATS+1))
CHUNK_SIZE=5  # Maximum number of counters to record at once

# --- EXECUTION PARAMETERS ---
NUM_THREADS=(1 2 3 4 5 6 7 8 9 10)
NUM_EXECUTIONS=(100000000)
TARGET_GOOD="./bin/good.exe"
TARGET_BAD="./bin/bad.exe"

# --- METRIC DEFINITIONS ---

# 1. Energy (Separate run due to system limitations/frequency scaling impact)
# NOTE: Energy is run separately but merged into the final CSV.
METRICS_ENERGY="power/energy-pkg/"

# General
METRICS_GENERAL="instructions cycles"

# Memory Hierarchy
METRICS_CACHE="ls_any_fills_from_sys.remote_cache ls_dmnd_fills_from_sys.remote_cache ls_bad_status2.stli_other cache-misses"
METRICS_L1="ls_dmnd_fills_from_sys.all ls_dmnd_fills_from_sys.local_l2"
METRICS_L2="l2_cache_req_stat.all l2_cache_req_stat.ic_dc_hit_in_l2 l2_cache_req_stat.ic_dc_miss_in_l2"
METRICS_L3="ls_dmnd_fills_from_sys.local_ccx ls_dmnd_fills_from_sys.dram_io_all"

# Micro-Architecture
METRICS_BRANCH="branch-misses ex_ret_brn_misp bp_redirects.ex_redir bp_de_redirect bp_l2_btb_correct bp_l1_tlb_miss_l2_tlb_hit"
METRICS_SPECULATION="de_src_op_disp.all ex_ret_ops de_dispatch_stall_cycle_dynamic_tokens_part1.load_queue_rsrc_stall"
METRICS_PIPELINE="ex_no_retire.empty ex_no_retire.load_not_complete bp_redirects.resync de_no_dispatch_per_slot.backend_stalls"
METRICS_ROB="de_dispatch_stall_cycle_dynamic_tokens_part2.retq"

# Coherence (Congestion, Writes, Traffic Source)
METRICS_COHERENCE="ls_alloc_mab_count l2_request_g1.rd_blk_x l2_fill_rsp_src.local_ccx l2_fill_rsp_src.far_cache"

# --- COMBINE METRICS ---
# The order here determines the column order in the CSV (after Time/Energy)
METRICS_LIST="$METRICS_GENERAL $METRICS_CACHE $METRICS_L1 $METRICS_L2 $METRICS_L3 $METRICS_BRANCH $METRICS_SPECULATION $METRICS_PIPELINE $METRICS_ROB $METRICS_COHERENCE"

# Convert space-separated list to comma-separated for perf input (if needed) and array for chunking
IFS=' ' read -r -a METRICS_ARRAY <<< "$METRICS_LIST"

# --- CHUNKING LOGIC ---
METRIC_CHUNKS=()
current_chunk=""
count=0

for metric in "${METRICS_ARRAY[@]}"; do
    if [ -z "$current_chunk" ]; then
        current_chunk="$metric"
    else
        current_chunk="$current_chunk,$metric"
    fi
    ((count+=1))
    if [ "$count" -ge "$CHUNK_SIZE" ]; then
        METRIC_CHUNKS+=("$current_chunk")
        current_chunk=""
        count=0
    fi
done

# Add any remaining metrics as the final chunk
if [ -n "$current_chunk" ]; then
    METRIC_CHUNKS+=("$current_chunk")
fi

printf "Metrics split into %d chunks (Max size: %d):\n" "${#METRIC_CHUNKS[@]}" "$CHUNK_SIZE"
for i in "${!METRIC_CHUNKS[@]}"; do
    printf "  Chunk %d: %s\n" "$((i+1))" "${METRIC_CHUNKS[$i]}"
done
printf "\n"

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
        
        MODES=(0 2 3)
        if [ "$THREADS" -eq 2 ]; then MODES+=(1); fi

        for MODE in "${MODES[@]}"; do
            # Loop over Stress levels (0=Normal, 1=Bad uArch)
            for STRESS in 0 1; do
                printf "Running: Threads=%d, Mode=%d, Stress=%d\n" "$THREADS" "$MODE" "$STRESS"
                suffix="${THREADS}_${NUM_EXECUTIONS}_mode${MODE}_stress${STRESS}"

                for TEST_TYPE in "bad" "good"; do
                    # Configure variables based on type
                    if [ "$TEST_TYPE" == "bad" ]; then
                        CURRENT_TARGET="$TARGET_BAD"
                        TIME_GREP="Time for bad coherency"
                    else
                        CURRENT_TARGET="$TARGET_GOOD"
                        TIME_GREP="Time for good coherency"
                    fi

                    # Single Result File
                    output_file="${RESULTS_DIR}/results_${suffix}_${TEST_TYPE}.csv"

                    if [ -f "$output_file" ] && [ "$(wc -l < "$output_file")" -ge "$((RUNS + 1))" ]; then
                         printf "  Skipping %s (Already done)\n" "$TEST_TYPE"
                         continue
                    fi

                    # 1. GENERATE DYNAMIC HEADER
                    # Converts spaces in METRICS_LIST to commas for the CSV header
                    csv_header="Time,Energy,$(echo "$METRICS_LIST" | tr ' ' ',')"
                    echo "$csv_header" > "$output_file"

                    for ((r=1; r<=RUNS; r++)); do
                        # A. RUN ENERGY & TIME (Standard Output Parsing)
                        # We use standard output for Time parsing from the app
                        energy_out=$($PERF_PATH stat -e $METRICS_ENERGY -- $CURRENT_TARGET $THREADS $NUM_EXECUTIONS $MODE $STRESS 2>&1) || true
                        
                        time_val=$(echo "$energy_out" | grep "$TIME_GREP" | sed 's/.*: \([0-9.]*\) ms/\1/' || echo "NaN")
                        energy_val=$(echo "$energy_out" | awk '/power\/energy-pkg/ {gsub(",", "", $1); print $1; exit}' || echo "NaN")

                        # B. RUN METRICS (Chunked, CSV Output -x,)
                        # We accumulate the raw CSV output from all chunks
                        raw_perf_csv=""
                        for chunk in "${METRIC_CHUNKS[@]}"; do
                             # -x, forces CSV output: value,,name,...
                             chunk_out=$($PERF_PATH stat -x, -e $chunk -- $CURRENT_TARGET $THREADS $NUM_EXECUTIONS $MODE $STRESS 2>&1) || true
                             raw_perf_csv="${raw_perf_csv}"$'\n'"${chunk_out}"
                        done

                        # C. DYNAMIC PARSING (AWK)
                        # We pass the full ordered metric list to awk. 
                        # Awk looks up each metric in the raw_perf_csv output and prints them in order.
                        metrics_csv=$(echo "$raw_perf_csv" | awk -F, -v cols="$METRICS_LIST" '
                            BEGIN {
                                split(cols, required, " ");
                            }
                            {
                                # Map Event Name ($3) to Value ($1)
                                # Handles basic naming. If perf output differs slightly (e.g. cpu/event/), 
                                # ensure METRICS_LIST matches perf output exactly or add logic here.
                                if ($3 != "") {
                                    results[$3] = $1;
                                }
                            }
                            END {
                                for (i = 1; i <= length(required); i++) {
                                    key = required[i];
                                    val = results[key];
                                    if (val == "") val = "NaN";
                                    printf "%s", val;
                                    if (i < length(required)) printf ",";
                                }
                            }
                        ')

                        # Write combined row: Time,Energy,Metrics...
                        echo "$time_val,$energy_val,$metrics_csv" >> "$output_file"
                    done
                done
                printf "Completed config.\n\n"
            done
        done
    done
done

# Restore perf_event_paranoid to original value
printf "Restoring perf_event_paranoid to 4...\n"
echo 4 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
printf "perf_event_paranoid restored.\n\n"

printf "End of this script. All experiments completed successfully!\n"
