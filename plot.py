#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "matplotlib",
#     "numpy",
#     "pyqt6",
# ]
# ///
import os
import glob
import numpy as np
import matplotlib.pyplot as plt
import csv
from collections import defaultdict

# Path to the raw results folder
results_dir = "results/raw"

# --- COLOR PALETTE ---
C1_COLOR = "#21674f"  # Good All
C2_COLOR = "#4a90e2"  # Bad uArch
C3_COLOR = "#CC6666"  # Bad Mem
C4_COLOR = "#8e44ad"  # Bad Both

# --- METRIC DEFINITIONS ---
# Must match headers in results_*.csv (from headers.csv) + derived metrics
metrics = [
    # General
    "time",
    "energy",
    "instructions",
    "cycles",
    # Memory Hierarchy
    "ls_any_fills_from_sys.remote_cache",
    "ls_dmnd_fills_from_sys.remote_cache",
    "cache-misses",
    "ls_bad_status2.stli_other",
    # L1
    "ls_dmnd_fills_from_sys.all",
    "l1_miss_rate",  # Derived
    # L2
    "l2_cache_req_stat.all",
    "l2_miss_rate",  # Derived
    # L3
    "ls_dmnd_fills_from_sys.local_ccx",
    "ls_dmnd_fills_from_sys.dram_io_all",
    # Coherence (Zig-Zag Investigation)
    "l2_request_g1.rd_blk_x",  # Writes/RFO
    "ls_alloc_mab_count",  # MAB Congestion
    "l2_fill_rsp_src.local_ccx",  # Local Traffic
    "l2_fill_rsp_src.far_cache",  # Remote Traffic
    # Branch Prediction
    "branch-misses",
    "ex_ret_brn_misp",
    "bp_redirects.ex_redir",
    "bp_de_redirect",
    "bp_l2_btb_correct",
    "bp_l1_tlb_miss_l2_tlb_hit",
    # Speculation
    "de_src_op_disp.all",
    "ex_ret_ops",
    "speculation_efficiency",  # Derived
    # Pipeline Stalls
    "de_dispatch_stall_cycle_dynamic_tokens_part2.retq",  # ROB Full
    "de_no_dispatch_per_slot.backend_stalls",
    "ex_no_retire.load_not_complete",
    "ex_no_retire.empty",
    "bp_redirects.resync",
    "de_dispatch_stall_cycle_dynamic_tokens_part1.load_queue_rsrc_stall",
]

# Aliases for cleaner plot titles
metric_titles = {
    # General
    "Time": "Time",
    "Energy": "Energy",
    "instructions": "Total Instructions",
    "cycles": "CPU Cycles",
    # Memory
    "ls_any_fills_from_sys.remote_cache": "Any Remote Fills",
    "ls_dmnd_fills_from_sys.remote_cache": "Demand Remote Fills",
    "ls_bad_status2.stli_other": "Store-to-Load Conflicts",
    "cache-misses": "LLC Misses",
    "ls_dmnd_fills_from_sys.all": "L1 Accesses (Demand)",
    "l1_miss_rate": "L1 Miss Rate",
    "l2_cache_req_stat.all": "L2 Requests (Total)",
    "l2_miss_rate": "L2 Miss Rate",
    "ls_dmnd_fills_from_sys.local_ccx": "L3 Accesses (Local CCX)",
    "ls_dmnd_fills_from_sys.dram_io_all": "L3 Miss Rate",
    # Coherence
    "l2_request_g1.rd_blk_x": "L2 RFO (Writes)",
    "ls_alloc_mab_count": "MAB Congestion (Cycles)",
    "l2_fill_rsp_src.local_ccx": "Local CCX Fills (Same-CCD)",
    "l2_fill_rsp_src.far_cache": "Remote Fills (Cross-CCD)",
    # Branch
    "branch-misses": "Branch Misses (Total)",
    "ex_ret_brn_misp": "Retired Branch Mispredicts",
    "bp_redirects.ex_redir": "Pipeline Flush (Exec)",
    "bp_de_redirect": "Pipeline Flush (Decode)",
    "bp_l2_btb_correct": "L2 BTB Corrections",
    "bp_l1_tlb_miss_l2_tlb_hit": "L1 ITLB Miss",
    # Speculation
    "de_src_op_disp.all": "Ops Dispatched",
    "ex_ret_ops": "Ops Retired",
    "speculation_efficiency": "Speculation Efficiency (Ret/Disp)",
    # Stalls
    "de_dispatch_stall_cycle_dynamic_tokens_part2.retq": "ROB Full Stalls",
    "de_no_dispatch_per_slot.backend_stalls": "Backend Stalls",
    "ex_no_retire.load_not_complete": "Stall (Waiting for Load)",
    "ex_no_retire.empty": "Stall (Pipeline Empty)",
    "bp_redirects.resync": "Pipeline Resyncs",
    "de_dispatch_stall_cycle_dynamic_tokens_part1.load_queue_rsrc_stall": "Load Queue Stalls",
}

# Units for labeling
metric_units = {
    "Time": "seconds",
    "Energy": "joules",
    "instructions": "ops",
    "cycles": "cycles",
    "ls_any_fills_from_sys.remote_cache": "fills",
    "ls_dmnd_fills_from_sys.remote_cache": "fills",
    "ls_bad_status2.stli_other": "events",
    "cache-misses": "misses",
    "ls_dmnd_fills_from_sys.all": "accesses",
    "l1_miss_rate": "%",
    "l2_cache_req_stat.all": "reqs",
    "l2_miss_rate": "%",
    "ls_dmnd_fills_from_sys.local_ccx": "accesses",
    "l3_miss_rate": "%",
    "l2_request_g1.rd_blk_x": "reqs",
    "ls_alloc_mab_count": "cycles",
    "l2_fill_rsp_src.local_ccx": "fills",
    "l2_fill_rsp_src.far_cache": "fills",
    "branch-misses": "misses",
    "ex_ret_brn_misp": "ops",
    "bp_redirects.ex_redir": "events",
    "bp_de_redirect": "events",
    "bp_l2_btb_correct": "events",
    "bp_l1_tlb_miss_l2_tlb_hit": "events",
    "de_src_op_disp.all": "ops",
    "ex_ret_ops": "ops",
    "speculation_efficiency": "ratio",
    "de_dispatch_stall_cycle_dynamic_tokens_part2.retq": "cycles",
    "de_no_dispatch_per_slot.backend_stalls": "cycles",
    "ex_no_retire.load_not_complete": "cycles",
    "ex_no_retire.empty": "cycles",
    "bp_redirects.resync": "events",
    "de_dispatch_stall_cycle_dynamic_tokens_part1.load_queue_rsrc_stall": "cycles",
}

# Metrics to display on Log Scale
log_metrics = [
    "branch-misses",
    "ex_ret_brn_misp",
    "bp_redirects.ex_redir",
    "de_dispatch_stall_cycle_dynamic_tokens_part2.retq",
    "ls_alloc_mab_count",
    "bp_redirects.resync",
]

mode_names = {0: "Default", 1: "Same core", 2: "Same CCD", 3: "Different CCDs"}

# --- PARSING LOGIC ---
# --- 1. DATA COLLECTION ---
data = defaultdict(
    lambda: defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    )
)

files = glob.glob(os.path.join(results_dir, "*.txt")) + glob.glob(
    os.path.join(results_dir, "*.csv")
)

for filepath in files:
    filename = os.path.basename(filepath)
    # Expected format: results_{THREADS}_{EXECS}_mode{MODE}_stress{STRESS}_{TYPE}.csv
    parts = (
        filename.replace("results_", "")
        .replace(".csv", "")
        .replace(".txt", "")
        .split("_")
    )

    if len(parts) < 5:
        continue

    # Robust metadata extraction
    try:
        thread = int(parts[0])
        # Skip size (parts[1])
        mode = 0
        stress = 0
        goodbad = "good"

        for part in parts:
            if part.startswith("mode"):
                mode = int(part[4:])
            if part.startswith("stress"):
                stress = int(part[6:])
            if "good" in part:
                goodbad = "good"
            if "bad" in part:
                goodbad = "bad"
    except ValueError:
        continue  # Skip files with unexpected naming

    try:
        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                for key, val in row.items():
                    if not key or val is None:
                        continue

                    # Clean strings
                    key = key.strip()
                    val = val.strip()

                    # 1. Normalize Keys (Time -> time)
                    if key == "Time":
                        key = "time"
                    if key == "Energy":
                        key = "energy"

                    # 2. Skip invalid values
                    if val == "" or val == "NaN" or "<" in val:
                        continue

                    # 3. Robust Float Conversion
                    try:
                        data[thread][mode][stress][goodbad][key].append(float(val))
                    except ValueError:
                        # Silently skip non-numeric data to prevent crashing
                        continue

    except Exception as e:
        print(f"Warning: Could not parse file {filename}: {e}")

# --- DERIVED METRICS CALCULATOR ---
for t in data:
    for m in data[t]:
        for s in data[t][m]:
            for gb in data[t][m][s]:
                d = data[t][m][s][gb]

                # Helper: Safe list division
                def calc_ratio(num_list, den_list):
                    return [n / d if d > 0 else 0 for n, d in zip(num_list, den_list)]

                # L1 Miss Rate
                if "ls_dmnd_fills_from_sys.all" in d:
                    d["l1_accesses"] = d["ls_dmnd_fills_from_sys.all"]  # Approximate
                    # If you have misses explicitly or hits:
                    if "ls_dmnd_fills_from_sys.local_l2" in d:
                        # Misses = All - Hits (approx)
                        hits = d["ls_dmnd_fills_from_sys.local_l2"]
                        misses = [a - h for a, h in zip(d["l1_accesses"], hits)]
                        d["l1_miss_rate"] = [
                            m / a * 100 if a > 0 else 0
                            for m, a in zip(misses, d["l1_accesses"])
                        ]

                # L2 Miss Rate
                if "l2_cache_req_stat.all" in d:
                    d["l2_accesses"] = d["l2_cache_req_stat.all"]
                    if "l2_cache_req_stat.ic_dc_miss_in_l2" in d:
                        d["l2_miss_rate"] = [
                            m / a * 100 if a > 0 else 0
                            for m, a in zip(
                                d["l2_cache_req_stat.ic_dc_miss_in_l2"],
                                d["l2_accesses"],
                            )
                        ]

                # Speculation Efficiency (Ret / Disp)
                if "ex_ret_ops" in d and "de_src_op_disp.all" in d:
                    d["speculation_efficiency"] = calc_ratio(
                        d["ex_ret_ops"], d["de_src_op_disp.all"]
                    )

                # Map old names to generic plot names if not present
                if "ls_any_fills_from_sys.remote_cache" in d:
                    d["remote_cache_fills"] = d["ls_any_fills_from_sys.remote_cache"]


# --- PLOTTING ---
def get_stats(thread, mode, stress, goodbad, metric):
    vals = data[thread][mode][stress][goodbad].get(metric, [])
    if not vals:
        return 0, 0
    return np.mean(vals), np.std(vals, ddof=1) / np.sqrt(len(vals)) if len(
        vals
    ) > 1 else 0


for thread in sorted(data.keys()):
    modes = sorted(data[thread].keys())

    # Grid size: 6 rows x 5 columns
    fig, axes = plt.subplots(6, 5, figsize=(25, 24))
    axes = axes.flatten()

    for i, metric in enumerate(metrics):
        if i >= len(axes):
            break
        ax = axes[i]

        c1m, c1e, c2m, c2e, c3m, c3e, c4m, c4e = [], [], [], [], [], [], [], []

        for mode in modes:
            m1, e1 = get_stats(thread, mode, 0, "good", metric)
            c1m.append(m1)
            c1e.append(e1)
            m2, e2 = get_stats(thread, mode, 1, "good", metric)
            c2m.append(m2)
            c2e.append(e2)
            m3, e3 = get_stats(thread, mode, 0, "bad", metric)
            c3m.append(m3)
            c3e.append(e3)
            m4, e4 = get_stats(thread, mode, 1, "bad", metric)
            c4m.append(m4)
            c4e.append(e4)

        x = np.arange(len(modes))
        width = 0.2

        ax.bar(
            x - 1.5 * width,
            c1m,
            width,
            label="Good All",
            color=C1_COLOR,
            yerr=c1e,
            capsize=3,
        )
        ax.bar(
            x - 0.5 * width,
            c2m,
            width,
            label="Bad uArch",
            color=C2_COLOR,
            yerr=c2e,
            capsize=3,
        )
        ax.bar(
            x + 0.5 * width,
            c3m,
            width,
            label="Bad Mem",
            color=C3_COLOR,
            yerr=c3e,
            capsize=3,
        )
        ax.bar(
            x + 1.5 * width,
            c4m,
            width,
            label="Bad Both",
            color=C4_COLOR,
            yerr=c4e,
            capsize=3,
        )

        ax.set_xticks(x)
        ax.set_xticklabels([mode_names.get(m, f"Mode {m}") for m in modes])
        ax.set_title(metric_titles.get(metric, metric), fontsize=10)

        if metric in log_metrics:
            ax.set_yscale("log")

        if i == 0:
            ax.legend(loc="upper left", fontsize="x-small")
        ax.grid(True, alpha=0.3)

    for j in range(len(metrics), len(axes)):
        axes[j].axis("off")
    plt.suptitle(f"Results for {thread} Thread(s)", fontsize=16)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(f"results/plots/plot_thread_{thread}.png", dpi=300)
    plt.close()

# Time vs Threads plot (unchanged logic)
all_modes = set()
for t in data:
    all_modes.update(data[t].keys())
for target_mode in sorted(all_modes):
    if target_mode == 1:
        continue
    threads = sorted(data.keys())
    c1, e1, c2, e2, c3, e3, c4, e4, valid_threads = [], [], [], [], [], [], [], [], []
    for t in threads:
        if target_mode not in data[t]:
            continue
        valid_threads.append(t)
        m, e = get_stats(t, target_mode, 0, "good", "time")
        c1.append(m)
        e1.append(e)
        m, e = get_stats(t, target_mode, 1, "good", "time")
        c2.append(m)
        e2.append(e)
        m, e = get_stats(t, target_mode, 0, "bad", "time")
        c3.append(m)
        e3.append(e)
        m, e = get_stats(t, target_mode, 1, "bad", "time")
        c4.append(m)
        e4.append(e)

    if not valid_threads:
        continue
    plt.figure(figsize=(10, 6))
    plt.errorbar(
        valid_threads,
        c1,
        yerr=e1,
        fmt="o-",
        label="Good All",
        color=C1_COLOR,
        capsize=5,
    )
    plt.errorbar(
        valid_threads,
        c2,
        yerr=e2,
        fmt="s-",
        label="Bad uArch",
        color=C2_COLOR,
        capsize=5,
    )
    plt.errorbar(
        valid_threads, c3, yerr=e3, fmt="^-", label="Bad Mem", color=C3_COLOR, capsize=5
    )
    plt.errorbar(
        valid_threads,
        c4,
        yerr=e4,
        fmt="d-",
        label="Bad Both",
        color=C4_COLOR,
        capsize=5,
    )

    # Add ratio labels dynamically
    for i, x_val in enumerate(valid_threads):
        # Collect points at this x
        points = [
            (c1[i], C1_COLOR),
            (c2[i], C2_COLOR),
            (c3[i], C3_COLOR),
            (c4[i], C4_COLOR),
        ]
        # Sort by value (time) ascending
        points.sort(key=lambda p: p[0])

        # Iterate from the second point upwards
        for j in range(1, len(points)):
            curr_val, _ = points[j]

            # Iterate over all points below the current one
            label_count = 0
            for k in range(j):
                prev_val, prev_color = points[k]

                if prev_val > 0:
                    ratio = curr_val / prev_val
                    # Add annotation
                    plt.annotate(
                        f"{ratio:.1f}x",
                        (x_val, curr_val),
                        textcoords="offset points",
                        xytext=(0, 5 + (label_count * 10)),  # Stack them upwards
                        ha="center",
                        fontsize=8,
                        color=prev_color,  # Colored according to comparison baseline
                        fontweight="bold",
                    )
                    label_count += 1

    plt.xlabel("Number of Threads")
    plt.ylabel("Time (s)")
    plt.title(f"Execution Time vs Threads ({mode_names.get(target_mode, target_mode)})")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xticks(valid_threads)
    plt.savefig(f"results/plots/time_vs_threads_mode{target_mode}.png", dpi=300)
    plt.close()

print("Plots generated!")
