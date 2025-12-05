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
from collections import defaultdict

# Path to the raw results folder
results_dir = "results/raw"

# --- COLOR PALETTE (4 Cases) ---
C1_COLOR = "#21674f"  # Good All
C2_COLOR = "#4a90e2"  # Bad uArch
C3_COLOR = "#CC6666"  # Bad Mem
C4_COLOR = "#8e44ad"  # Bad Both

# --- METRIC DEFINITIONS ---
metrics = [
    # General
    "time",
    "energy",
    # Memory Hierarchy
    "remote_cache_fills",
    "l1_accesses",
    "l1_miss_rate",
    "l2_accesses",
    "l2_miss_rate",
    "l3_accesses",
    "l3_miss_rate",
    # Branch Prediction
    "branch_misses",
    "ex_ret_brn_misp",  # Retired branch mispredictions
    "bp_redir_ex",  # Execution redirects
    "bp_de_redir",  # Decode redirects
    "bp_l2_btb",  # L2 BTB Correct (L2 overrides L1)
    "bp_l1_tlb",  # L1 TLB Miss / L2 TLB Hit
    "resync",  # Pipeline Resyncs
    # Speculation & Execution
    "disp_all",  # Dispatched Ops
    "ret_ops",  # Retired Ops
    "speculation_efficiency",  # (Derived: ret_ops / disp_all)
    # Pipeline Stalls
    "ld_q_stall",  # Load Queue Stalls
    "no_ret_empty",  # Empty Pipeline (Frontend Starved/Flush)
    "no_ret_ld",  # Waiting for Load (Backend Bound)
    "backend_stall",  # General Backend Stalls
    "rob_stall",  # ROB Full
]

log_metrics = [
    "branch_misses",
    "ex_ret_brn_misp",
    "bp_redir_ex",
    "rob_stall",
    "resync",
    "bp_de_redir",
]

# Mode names mapping
mode_names = {0: "Default", 1: "Same core", 2: "Same CCD", 3: "Different CCDs"}

# Units for each metric
metric_units = {
    "time": "seconds",
    "energy": "joules",
    "remote_cache_fills": "fills",
    "l1_accesses": "accesses",
    "l1_miss_rate": "%",
    "l2_accesses": "accesses",
    "l2_miss_rate": "%",
    "l3_accesses": "accesses",
    "l3_miss_rate": "%",
    # uArch Units
    "branch_misses": "misses",
    "ex_ret_brn_misp": "ops",
    "bp_redir_ex": "events",
    "bp_de_redir": "events",
    "bp_l2_btb": "events",
    "bp_l1_tlb": "events",
    "resync": "events",
    "disp_all": "ops",
    "ret_ops": "ops",
    "speculation_efficiency": "ratio (0-1)",
    "ld_q_stall": "cycles",
    "no_ret_empty": "cycles",
    "no_ret_ld": "cycles",
    "backend_stall": "cycles",
    "rob_stall": "cycles",
    # Coherence Units
    "l3_latency": "cycles",
    "l2_write_reqs": "reqs",
    "mab_alloc": "cycle-occupancy",
    "local_bw": "events/bytes",
}

# Metric titles
metric_titles = {
    "time": "Time",
    "energy": "Energy",
    "remote_cache_fills": "Remote/Demand Cache Fills",
    "l1_accesses": "L1 Accesses",
    "l1_miss_rate": "L1 Miss Rate",
    "l2_accesses": "L2 Accesses",
    "l2_miss_rate": "L2 Miss Rate",
    "l3_accesses": "L3 Accesses",
    "l3_miss_rate": "L3 Miss Rate",
    "branch_misses": "Branch Misses (Total)",
    "ex_ret_brn_misp": "Retired Branch Mispredicts",
    "bp_redir_ex": "Pipeline Flush (Exec)",
    "bp_de_redir": "Pipeline Flush (Decode)",
    "bp_l2_btb": "L2 BTB Corrections",
    "bp_l1_tlb": "L1 ITLB Miss",
    "resync": "Pipeline Resyncs",
    "disp_all": "Ops Dispatched",
    "ret_ops": "Ops Retired",
    "speculation_efficiency": "Speculation Efficiency\n(Ret/Disp)",
    "ld_q_stall": "Load Queue Stalls",
    "no_ret_empty": "No Retire (Empty/Flush)",
    "no_ret_ld": "No Retire (Waiting for Load)",
    "backend_stall": "Backend Stalls",
    "rob_stall": "ROB Full Stalls",
    "l3_latency": "L3 Read Miss Latency",
    "l2_write_reqs": "L2 Write Reqs (RFO)",
    "mab_alloc": "MAB Congestion",
    "local_bw": "Outbound Fabric BW",
}


def parse_file(filepath, metric):
    try:
        with open(filepath, "r") as f:
            lines = f.readlines()

        if metric in ["time", "energy"]:
            return [
                float(line.strip())
                for line in lines
                if line.strip() and line.strip() != "NaN"
            ]

        data = []
        start_idx = 0

        # Robust Header Detection
        if len(lines) > 0:
            try:
                first_item = lines[0].split(",")[0].strip()
                if not first_item or first_item == "NaN":
                    pass
                else:
                    float(first_item)
            except ValueError:
                start_idx = 1

        for line in lines[start_idx:]:
            if line.strip():
                values = []
                for x in line.split(","):
                    x = x.strip()
                    if x == "NaN" or not x:
                        values.append(0)
                    else:
                        values.append(float(x))
                data.append(values)
        return data
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return []


# --- 1. DATA COLLECTION ---
data = defaultdict(
    lambda: defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    )
)

files = glob.glob(os.path.join(results_dir, "*.txt"))

for file in files:
    filename = os.path.basename(file)
    parts = filename.split("_")

    if len(parts) < 6:
        continue

    if parts[0] == "perf":
        if len(parts) < 2:
            continue
        metric_type = f"perf_{parts[1]}"
        thread_idx = 2
    else:
        metric_type = parts[0]
        thread_idx = 1

    if not parts[thread_idx].isdigit():
        continue

    thread = int(parts[thread_idx])
    size = int(parts[thread_idx + 1])
    mode_str = parts[thread_idx + 2]
    stress_str = parts[thread_idx + 3]
    goodbad_file = parts[thread_idx + 4]

    mode = int(mode_str[4:])

    if "stress" in stress_str:
        stress = int(stress_str[6:])
    else:
        stress = 0
        goodbad_file = stress_str

    goodbad = goodbad_file.split(".")[0]

    parsed = parse_file(file, metric_type)
    target_dict = data[thread][mode][stress][goodbad]

    if metric_type == "perf_cache":
        for run in parsed:
            if len(run) >= 4:
                target_dict["remote_cache_fills"].append(run[1])
    elif metric_type == "perf_l1":
        for run in parsed:
            if len(run) >= 2:
                target_dict["l1_fills"].append(run[0])
                target_dict["l1_l2_hits"].append(run[1])
    elif metric_type == "perf_l2":
        for run in parsed:
            if len(run) >= 3:
                target_dict["l2_requests"].append(run[0])
                target_dict["l2_hits"].append(run[1])
                target_dict["l2_misses"].append(run[2])
    elif metric_type == "perf_l3":
        for run in parsed:
            if len(run) >= 2:
                target_dict["l3_accesses"].append(run[0])
                target_dict["l3_misses"].append(run[1])

    elif metric_type == "perf_uarch":
        # Parsing extended to 18 columns
        for run in parsed:
            if len(run) >= 14:
                target_dict["branch_misses"].append(run[0])
                target_dict["ex_ret_brn_misp"].append(run[1])
                target_dict["bp_redir_ex"].append(run[2])
                target_dict["bp_de_redir"].append(run[3])
                target_dict["bp_l2_btb"].append(run[4])
                target_dict["bp_l1_tlb"].append(run[5])
                target_dict["disp_all"].append(run[6])
                target_dict["ret_ops"].append(run[7])
                target_dict["ld_q_stall"].append(run[8])
                target_dict["no_ret_empty"].append(run[9])
                target_dict["no_ret_ld"].append(run[10])
                target_dict["resync"].append(run[11])
                target_dict["backend_stall"].append(run[12])
                target_dict["rob_stall"].append(run[13])

            # New Coherence Metrics (Check if they exist)
            if len(run) >= 18:
                target_dict["l3_latency"].append(run[14])
                target_dict["l2_write_reqs"].append(run[15])
                target_dict["mab_alloc"].append(run[16])
                target_dict["local_bw"].append(run[17])

    elif metric_type in ["time", "energy"]:
        target_dict[metric_type].extend(parsed)

# --- 2. CALCULATE DERIVED METRICS ---
for t in data:
    for m in data[t]:
        for s in data[t][m]:
            for gb in data[t][m][s]:
                d = data[t][m][s][gb]

                if "l1_fills" in d:
                    d["l1_accesses"] = d["l1_fills"]
                    d["l1_miss_rate"] = [
                        ((f - h) / f * 100) if f > 0 else 0
                        for f, h in zip(d["l1_fills"], d["l1_l2_hits"])
                    ]

                if "l2_requests" in d:
                    d["l2_accesses"] = d["l2_requests"]
                    d["l2_miss_rate"] = [
                        (miss / req * 100) if req > 0 else 0
                        for req, miss in zip(d["l2_requests"], d["l2_misses"])
                    ]

                if "l3_accesses" in d:
                    d["l3_miss_rate"] = [
                        (miss / acc * 100) if acc > 0 else 0
                        for acc, miss in zip(d["l3_accesses"], d["l3_misses"])
                    ]

                if "ret_ops" in d and "disp_all" in d:
                    d["speculation_efficiency"] = [
                        (ret / disp) if disp > 0 else 0
                        for ret, disp in zip(d["ret_ops"], d["disp_all"])
                    ]


# --- 3. HELPER STATS ---
def get_stats(thread, mode, stress, goodbad, metric):
    vals = data[thread][mode][stress][goodbad].get(metric, [])
    if not vals:
        return 0, 0
    return np.mean(vals), np.std(vals, ddof=1) / np.sqrt(len(vals)) if len(
        vals
    ) > 1 else 0


# --- 4. PLOTTING: METRIC vs MODE ---
for thread in sorted(data.keys()):
    modes = sorted(data[thread].keys())

    # Expanded to 6 rows to fit 28 metrics
    fig, axes = plt.subplots(6, 5, figsize=(25, 24))
    axes = axes.flatten()

    for i, metric in enumerate(metrics):
        if i >= len(axes):
            break
        ax = axes[i]

        case1_means, case1_errs = [], []
        case2_means, case2_errs = [], []
        case3_means, case3_errs = [], []
        case4_means, case4_errs = [], []

        for mode in modes:
            m1, e1 = get_stats(thread, mode, 0, "good", metric)
            m2, e2 = get_stats(thread, mode, 1, "good", metric)
            m3, e3 = get_stats(thread, mode, 0, "bad", metric)
            m4, e4 = get_stats(thread, mode, 1, "bad", metric)

            case1_means.append(m1)
            case1_errs.append(e1)
            case2_means.append(m2)
            case2_errs.append(e2)
            case3_means.append(m3)
            case3_errs.append(e3)
            case4_means.append(m4)
            case4_errs.append(e4)

        x = np.arange(len(modes))
        width = 0.2

        ax.bar(
            x - 1.5 * width,
            case1_means,
            width,
            label="Good All",
            color=C1_COLOR,
            yerr=case1_errs,
            capsize=3,
        )
        ax.bar(
            x - 0.5 * width,
            case2_means,
            width,
            label="Bad uArch",
            color=C2_COLOR,
            yerr=case2_errs,
            capsize=3,
        )
        ax.bar(
            x + 0.5 * width,
            case3_means,
            width,
            label="Bad Mem",
            color=C3_COLOR,
            yerr=case3_errs,
            capsize=3,
        )
        ax.bar(
            x + 1.5 * width,
            case4_means,
            width,
            label="Bad Both",
            color=C4_COLOR,
            yerr=case4_errs,
            capsize=3,
        )

        ax.set_xticks(x)
        ax.set_xticklabels([mode_names.get(m, f"Mode {m}") for m in modes])
        ax.set_title(metric_titles.get(metric, metric), fontsize=10)
        ax.tick_params(axis="x", labelsize=8)
        ax.tick_params(axis="y", labelsize=8)

        if i == 0:
            ax.legend(loc="upper left", fontsize="x-small")
        if metric in log_metrics:
            ax.set_yscale("log")

        ax.grid(True, alpha=0.3)

    for j in range(len(metrics), len(axes)):
        axes[j].axis("off")

    plt.suptitle(f"Results for {thread} Thread(s)", fontsize=16)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(f"results/plots/plot_thread_{thread}.png", dpi=300)
    plt.close()

# --- 5. PLOTTING: TIME vs THREADS ---
all_modes = set()
for t in data:
    all_modes.update(data[t].keys())

for target_mode in sorted(all_modes):
    if target_mode == 1:
        continue

    threads = sorted(data.keys())
    c1, c2, c3, c4 = [], [], [], []
    e1, e2, e3, e4 = [], [], [], []
    valid_threads = []

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

print("Plots generated successfully with Extended uArch Analysis!")
