#!/bin/bash
# Must be run with sudo privileges

set -e
set +x

# Settings
PERF_PATH=/usr/lib/linux-tools/6.14.0-33-generic/perf
RESULTS_DIR="./results/raw/"
REPEATS=10
RUNS=$((REPEATS+1))

# --- METRIC DEFINITIONS ---

# 1. Energy (Separate run due to system limitations/frequency scaling impact)
METRICS_ENERGY="power/energy-pkg/"

# 2. Memory Hierarchy
METRICS_CACHE="ls_any_fills_from_sys.remote_cache,ls_dmnd_fills_from_sys.remote_cache,ls_bad_status2.stli_other,cache-misses"
METRICS_L1="ls_dmnd_fills_from_sys.all,ls_dmnd_fills_from_sys.local_l2"
METRICS_L2="l2_cache_req_stat.all,l2_cache_req_stat.ic_dc_hit_in_l2,l2_cache_req_stat.ic_dc_miss_in_l2"
METRICS_L3="ls_dmnd_fills_from_sys.local_ccx,ls_dmnd_fills_from_sys.dram_io_all"

# 3. New Micro-Architecture Metrics (Branch, Speculation, Pipeline, ROB)
# Fixed typo: METRICS_BANCH -> METRICS_BRANCH
METRICS_BRANCH="branch-misses,ex_ret_brn_misp,bp_redirects.ex_redir,bp_de_redirect,bp_l2_btb_correct,bp_l1_tlb_miss_l2_tlb_hit"
METRICS_SPECULATION="de_src_op_disp.all,ex_ret_ops,de_dispatch_stall_cycle_dynamic_tokens_part1.load_queue_rsrc_stall"
METRICS_PIPELINE="ex_no_retire.empty,ex_no_retire.load_not_complete,bp_redirects.resync,de_no_dispatch_per_slot.backend_stalls"
METRICS_ROB="de_dispatch_stall_cycle_dynamic_tokens_part2.retq"

# Concatenate uArch metrics
METRICS_UARCH="$METRICS_BRANCH,$METRICS_SPECULATION,$METRICS_PIPELINE,$METRICS_ROB"

# 4. BIG COMBINED METRIC STRING (Non-Energy)
# We join all non-energy metrics to run perf only once for these.
METRICS_ALL="$METRICS_CACHE,$METRICS_L1,$METRICS_L2,$METRICS_L3,$METRICS_UARCH"

NUM_THREADS=(1 2 3 4 5 6 7 8 9 10)
NUM_EXECUTIONS=(1000000000)
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
        
        MODES=(0 2 3)
        if [ "$THREADS" -eq 2 ]; then MODES+=(1); fi

        for MODE in "${MODES[@]}"; do
            # Loop over Stress levels (0=Normal, 1=Bad uArch)
            for STRESS in 0 1; do
                
                printf "Running: Threads=%d, Mode=%d, Stress=%d\n" "$THREADS" "$MODE" "$STRESS"

                suffix="${THREADS}_${NUM_EXECUTIONS}_mode${MODE}_stress${STRESS}"
                
                # Define Output Files
                energy_bad_file="${RESULTS_DIR}/energy_${suffix}_bad.txt"
                perf_cache_bad_file="${RESULTS_DIR}/perf_cache_${suffix}_bad.txt"
                perf_l1_bad_file="${RESULTS_DIR}/perf_l1_${suffix}_bad.txt"
                perf_l2_bad_file="${RESULTS_DIR}/perf_l2_${suffix}_bad.txt"
                perf_l3_bad_file="${RESULTS_DIR}/perf_l3_${suffix}_bad.txt"
                perf_uarch_bad_file="${RESULTS_DIR}/perf_uarch_${suffix}_bad.txt"
                time_bad_file="${RESULTS_DIR}/time_${suffix}_bad.txt"
                
                energy_good_file="${RESULTS_DIR}/energy_${suffix}_good.txt"
                perf_cache_good_file="${RESULTS_DIR}/perf_cache_${suffix}_good.txt"
                perf_l1_good_file="${RESULTS_DIR}/perf_l1_${suffix}_good.txt"
                perf_l2_good_file="${RESULTS_DIR}/perf_l2_${suffix}_good.txt"
                perf_l3_good_file="${RESULTS_DIR}/perf_l3_${suffix}_good.txt"
                perf_uarch_good_file="${RESULTS_DIR}/perf_uarch_${suffix}_good.txt"
                time_good_file="${RESULTS_DIR}/time_${suffix}_good.txt"

                # Check if done
                if [ -f "$time_bad_file" ] && [ "$(wc -l < "$time_bad_file")" -ge "$RUNS" ] && \
                   [ -f "$time_good_file" ] && [ "$(wc -l < "$time_good_file")" -ge "$RUNS" ]; then
                    printf "  Skipping (Already done)\n"
                    continue
                fi

                # Initialize Files with CSV Headers
                > "$energy_bad_file"
                > "$time_bad_file"
                echo "ls_any_fills_from_sys.remote_cache,ls_dmnd_fills_from_sys.remote_cache,ls_bad_status2.stli_other,cache-misses" > "$perf_cache_bad_file"
                echo "ls_dmnd_fills_from_sys.all,ls_dmnd_fills_from_sys.local_l2" > "$perf_l1_bad_file"
                echo "l2_cache_req_stat.all,l2_cache_req_stat.ic_dc_hit_in_l2,l2_cache_req_stat.ic_dc_miss_in_l2" > "$perf_l2_bad_file"
                echo "ls_dmnd_fills_from_sys.local_ccx,ls_dmnd_fills_from_sys.dram_io_all" > "$perf_l3_bad_file"
                # Header for new uArch file (Matches the order in awk below)
                echo "branch_misses,ex_ret_brn_misp,bp_redir_ex,bp_de_redir,bp_l2_btb,bp_l1_tlb,disp_all,ret_ops,ld_q_stall,no_ret_empty,no_ret_ld,resync,backend_stall,rob_stall" > "$perf_uarch_bad_file"

                > "$energy_good_file"
                > "$time_good_file"
                echo "ls_any_fills_from_sys.remote_cache,ls_dmnd_fills_from_sys.remote_cache,ls_bad_status2.stli_other,cache-misses" > "$perf_cache_good_file"
                echo "ls_dmnd_fills_from_sys.all,ls_dmnd_fills_from_sys.local_l2" > "$perf_l1_good_file"
                echo "l2_cache_req_stat.all,l2_cache_req_stat.ic_dc_hit_in_l2,l2_cache_req_stat.ic_dc_miss_in_l2" > "$perf_l2_good_file"
                echo "ls_dmnd_fills_from_sys.local_ccx,ls_dmnd_fills_from_sys.dram_io_all" > "$perf_l3_good_file"
                echo "branch_misses,ex_ret_brn_misp,bp_redir_ex,bp_de_redir,bp_l2_btb,bp_l1_tlb,disp_all,ret_ops,ld_q_stall,no_ret_empty,no_ret_ld,resync,backend_stall,rob_stall" > "$perf_uarch_good_file"

                # === BAD COHERENCY ===
                for ((r=1; r<=RUNS; r++)); do
                    # RUN 1: Energy & Time
                    energy_output=$(LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/nathan/Documents/TRAB2-ARQ-AVAN/papi/install/lib $PERF_PATH stat -e $METRICS_ENERGY -- $TARGET_BAD $THREADS $NUM_EXECUTIONS $MODE $STRESS 2>&1) || true
                    
                    { echo "$energy_output" | awk '/power\/energy-pkg/ {gsub(",", "", $1); print $1; exit}' || echo "NaN"; } >> "$energy_bad_file"
                    { echo "$energy_output" | grep "Time for bad coherency" | sed 's/.*: \([0-9.]*\) ms/\1/' || echo "NaN"; } >> "$time_bad_file"
                    
                    # RUN 2: All Other Metrics (Cache + uArch)
                    all_output=$(LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/nathan/Documents/TRAB2-ARQ-AVAN/papi/install/lib $PERF_PATH stat -e $METRICS_ALL -- $TARGET_BAD $THREADS $NUM_EXECUTIONS $MODE $STRESS 2>&1) || true
                    
                    # Parse Cache
                    { echo "$all_output" | awk '
                        /ls_any_fills_from_sys\.remote_cache/ {gsub(",", "", $1); remote=$1}
                        /ls_dmnd_fills_from_sys\.remote_cache/ {gsub(",", "", $1); dmnd=$1}
                        /ls_bad_status2\.stli_other/ {gsub(",", "", $1); stli=$1}
                        /cache-misses/ {gsub(",", "", $1); misses=$1}
                        END {print remote "," dmnd "," stli "," misses}
                    ' || echo "NaN,NaN,NaN,NaN"; } >> "$perf_cache_bad_file"
                    
                    # Parse L1
                    { echo "$all_output" | awk '
                        /ls_dmnd_fills_from_sys\.all/ {gsub(",", "", $1); l1_fills=$1}
                        /ls_dmnd_fills_from_sys\.local_l2/ {gsub(",", "", $1); l1_l2_hits=$1}
                        END {print l1_fills "," l1_l2_hits}
                    ' || echo "NaN,NaN"; } >> "$perf_l1_bad_file"
                    
                    # Parse L2
                    { echo "$all_output" | awk '
                        /l2_cache_req_stat\.all/ {gsub(",", "", $1); l2_all=$1}
                        /l2_cache_req_stat\.ic_dc_hit_in_l2/ {gsub(",", "", $1); l2_hits=$1}
                        /l2_cache_req_stat\.ic_dc_miss_in_l2/ {gsub(",", "", $1); l2_miss=$1}
                        END {print l2_all "," l2_hits "," l2_miss}
                    ' || echo "NaN,NaN,NaN"; } >> "$perf_l2_bad_file"
                    
                    # Parse L3
                    { echo "$all_output" | awk '
                        /ls_dmnd_fills_from_sys\.local_ccx/ {gsub(",", "", $1); l3_access=$1}
                        /ls_dmnd_fills_from_sys\.dram_io_all/ {gsub(",", "", $1); l3_miss=$1}
                        END {print l3_access "," l3_miss}
                    ' || echo "NaN,NaN"; } >> "$perf_l3_bad_file"

                    # Parse NEW uArch Metrics (Matches header order)
                    { echo "$all_output" | awk '
                        /branch-misses/ {gsub(",", "", $1); br_miss=$1}
                        /ex_ret_brn_misp/ {gsub(",", "", $1); ex_br_misp=$1}
                        /bp_redirects\.ex_redir/ {gsub(",", "", $1); bp_redir_ex=$1}
                        /bp_de_redirect/ {gsub(",", "", $1); bp_de_redir=$1}
                        /bp_l2_btb_correct/ {gsub(",", "", $1); bp_l2_btb=$1}
                        /bp_l1_tlb_miss_l2_tlb_hit/ {gsub(",", "", $1); bp_l1_tlb=$1}
                        /de_src_op_disp\.all/ {gsub(",", "", $1); disp_all=$1}
                        /ex_ret_ops/ {gsub(",", "", $1); ret_ops=$1}
                        /load_queue_rsrc_stall/ {gsub(",", "", $1); ld_q_stall=$1}
                        /ex_no_retire\.empty/ {gsub(",", "", $1); no_ret_empty=$1}
                        /ex_no_retire\.load_not_complete/ {gsub(",", "", $1); no_ret_ld=$1}
                        /bp_redirects\.resync/ {gsub(",", "", $1); resync=$1}
                        /de_no_dispatch_per_slot\.backend_stalls/ {gsub(",", "", $1); backend_stall=$1}
                        /de_dispatch_stall_cycle_dynamic_tokens_part2\.retq/ {gsub(",", "", $1); rob_stall=$1}
                        END {
                            print br_miss "," ex_br_misp "," bp_redir_ex "," bp_de_redir "," bp_l2_btb "," bp_l1_tlb "," disp_all "," ret_ops "," ld_q_stall "," no_ret_empty "," no_ret_ld "," resync "," backend_stall "," rob_stall
                        }
                    ' || echo "NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN"; } >> "$perf_uarch_bad_file"
                done

                # === GOOD COHERENCY ===
                for ((r=1; r<=RUNS; r++)); do
                    # RUN 1: Energy & Time
                    energy_output=$(LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/nathan/Documents/TRAB2-ARQ-AVAN/papi/install/lib $PERF_PATH stat -e $METRICS_ENERGY -- $TARGET_GOOD $THREADS $NUM_EXECUTIONS $MODE $STRESS 2>&1) || true
                    
                    { echo "$energy_output" | awk '/power\/energy-pkg/ {gsub(",", "", $1); print $1; exit}' || echo "NaN"; } >> "$energy_good_file"
                    { echo "$energy_output" | grep "Time for good coherency" | sed 's/.*: \([0-9.]*\) ms/\1/' || echo "NaN"; } >> "$time_good_file"
                    
                    # RUN 2: All Other Metrics
                    all_output=$(LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/nathan/Documents/TRAB2-ARQ-AVAN/papi/install/lib $PERF_PATH stat -e $METRICS_ALL -- $TARGET_GOOD $THREADS $NUM_EXECUTIONS $MODE $STRESS 2>&1) || true
                    
                    # Parse Cache
                    { echo "$all_output" | awk '
                        /ls_any_fills_from_sys\.remote_cache/ {gsub(",", "", $1); remote=$1}
                        /ls_dmnd_fills_from_sys\.remote_cache/ {gsub(",", "", $1); dmnd=$1}
                        /ls_bad_status2\.stli_other/ {gsub(",", "", $1); stli=$1}
                        /cache-misses/ {gsub(",", "", $1); misses=$1}
                        END {print remote "," dmnd "," stli "," misses}
                    ' || echo "NaN,NaN,NaN,NaN"; } >> "$perf_cache_good_file"
                    
                    # Parse L1
                    { echo "$all_output" | awk '
                        /ls_dmnd_fills_from_sys\.all/ {gsub(",", "", $1); l1_fills=$1}
                        /ls_dmnd_fills_from_sys\.local_l2/ {gsub(",", "", $1); l1_l2_hits=$1}
                        END {print l1_fills "," l1_l2_hits}
                    ' || echo "NaN,NaN"; } >> "$perf_l1_good_file"
                    
                    # Parse L2
                    { echo "$all_output" | awk '
                        /l2_cache_req_stat\.all/ {gsub(",", "", $1); l2_all=$1}
                        /l2_cache_req_stat\.ic_dc_hit_in_l2/ {gsub(",", "", $1); l2_hits=$1}
                        /l2_cache_req_stat\.ic_dc_miss_in_l2/ {gsub(",", "", $1); l2_miss=$1}
                        END {print l2_all "," l2_hits "," l2_miss}
                    ' || echo "NaN,NaN,NaN"; } >> "$perf_l2_good_file"
                    
                    # Parse L3
                    { echo "$all_output" | awk '
                        /ls_dmnd_fills_from_sys\.local_ccx/ {gsub(",", "", $1); l3_access=$1}
                        /ls_dmnd_fills_from_sys\.dram_io_all/ {gsub(",", "", $1); l3_miss=$1}
                        END {print l3_access "," l3_miss}
                    ' || echo "NaN,NaN"; } >> "$perf_l3_good_file"

                    # Parse NEW uArch Metrics
                    { echo "$all_output" | awk '
                        /branch-misses/ {gsub(",", "", $1); br_miss=$1}
                        /ex_ret_brn_misp/ {gsub(",", "", $1); ex_br_misp=$1}
                        /bp_redirects\.ex_redir/ {gsub(",", "", $1); bp_redir_ex=$1}
                        /bp_de_redirect/ {gsub(",", "", $1); bp_de_redir=$1}
                        /bp_l2_btb_correct/ {gsub(",", "", $1); bp_l2_btb=$1}
                        /bp_l1_tlb_miss_l2_tlb_hit/ {gsub(",", "", $1); bp_l1_tlb=$1}
                        /de_src_op_disp\.all/ {gsub(",", "", $1); disp_all=$1}
                        /ex_ret_ops/ {gsub(",", "", $1); ret_ops=$1}
                        /load_queue_rsrc_stall/ {gsub(",", "", $1); ld_q_stall=$1}
                        /ex_no_retire\.empty/ {gsub(",", "", $1); no_ret_empty=$1}
                        /ex_no_retire\.load_not_complete/ {gsub(",", "", $1); no_ret_ld=$1}
                        /bp_redirects\.resync/ {gsub(",", "", $1); resync=$1}
                        /de_no_dispatch_per_slot\.backend_stalls/ {gsub(",", "", $1); backend_stall=$1}
                        /de_dispatch_stall_cycle_dynamic_tokens_part2\.retq/ {gsub(",", "", $1); rob_stall=$1}
                        END {
                            print br_miss "," ex_br_misp "," bp_redir_ex "," bp_de_redir "," bp_l2_btb "," bp_l1_tlb "," disp_all "," ret_ops "," ld_q_stall "," no_ret_empty "," no_ret_ld "," resync "," backend_stall "," rob_stall
                        }
                    ' || echo "NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN"; } >> "$perf_uarch_good_file"
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
