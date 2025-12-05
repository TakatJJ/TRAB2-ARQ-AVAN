import os
import glob
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

# Path to the raw results folder
results_dir = "results/raw"

# --- NEW COLOR PALETTE (4 Cases) ---
# Case 1: Good Everything (Green)
C1_COLOR = "#21674f"
# Case 2: Bad uArch (Blue - distinct from Green/Red)
C2_COLOR = "#4a90e2"
# Case 3: Bad Memory (Red - existing bad color)
C3_COLOR = "#CC6666"
# Case 4: Bad Both (Purple - showing the combination intensity)
C4_COLOR = "#8e44ad"

# Metrics to plot
metrics = [
    "time",
    "energy",
    "branch_misses",
    "remote_cache_fills",
    "l1_accesses",
    "l1_miss_rate",
    "l2_accesses",
    "l2_miss_rate",
    "l3_accesses",
    "l3_miss_rate",
]

# Mode names mapping
mode_names = {0: "Default", 1: "Same core", 2: "Same CCD", 3: "Different CCDs"}

# Units for each metric
metric_units = {
    "time": "seconds",
    "energy": "joules",
    "branch_misses": "misses",
    "remote_cache_fills": "fills",
    "l1_accesses": "accesses",
    "l1_miss_rate": "%",
    "l2_accesses": "accesses",
    "l2_miss_rate": "%",
    "l3_accesses": "accesses",
    "l3_miss_rate": "%",
}

# Metric titles
metric_titles = {
    "time": "Time",
    "energy": "Energy",
    "branch_misses": "Branch Misses",
    "remote_cache_fills": "Demand/Remote Cache Fills",
    "l1_accesses": "L1 Cache Accesses",
    "l1_miss_rate": "L1 Cache Miss Rate",
    "l2_accesses": "L2 Cache Accesses",
    "l2_miss_rate": "L2 Cache Miss Rate",
    "l3_accesses": "L3 Cache Accesses",
    "l3_miss_rate": "L3 Cache Miss Rate",
}


def parse_file(filepath, metric):
    try:
        with open(filepath, "r") as f:
            lines = f.readlines()

        # Simple float metrics
        if metric in ["time", "energy", "branch_misses"]:
            return [
                float(line.strip())
                for line in lines
                if line.strip() and line.strip() != "NaN"
            ]

        # CSV style metrics
        data = []

        start_idx = 0
        if len(lines) > 0:
            # Try converting the first item of the first line to a float.
            # If it fails (ValueError), it's a header, so we start at index 1.
            try:
                first_item = lines[0].split(",")[0].strip()
                if not first_item or first_item == "NaN":
                    # If it's empty or NaN, we assume it's data (or bad data),
                    # but usually headers are distinct text like 'l2_cache...'
                    pass
                else:
                    float(first_item)
            except ValueError:
                start_idx = 1

        for line in lines[start_idx:]:
            if line.strip():
                # Handle potential NaN
                values = []
                for x in line.split(","):
                    x = x.strip()
                    if x == "NaN" or not x:
                        values.append(0)
                    else:
                        values.append(float(x))  # Use float for safety
                data.append(values)
        return data
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return []


# --- 1. DATA COLLECTION ---
# Structure: data[thread][mode][stress][goodbad][metric]
data = defaultdict(
    lambda: defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    )
)

files = glob.glob(os.path.join(results_dir, "*.txt"))

for file in files:
    filename = os.path.basename(file)
    parts = filename.split("_")

    # We need at least: metric_threads_size_mode_stress_goodbad.txt
    if len(parts) < 6:
        continue

    # Identify Metric and Index Offset
    # Format 1: metric_... (e.g., time_2_...)
    # Format 2: perf_metric_... (e.g., perf_l1_2_...)

    if parts[0] == "perf":
        if len(parts) < 2:
            continue
        metric_type = f"perf_{parts[1]}"  # perf_cache, perf_l1, etc.
        thread_idx = 2
    else:
        metric_type = parts[0]
        thread_idx = 1

    # Check if thread_idx points to a number (validating offset)
    if not parts[thread_idx].isdigit():
        continue

    thread = int(parts[thread_idx])
    size = int(parts[thread_idx + 1])
    mode_str = parts[thread_idx + 2]  # mode0
    stress_str = parts[thread_idx + 3]  # stress0
    goodbad_file = parts[thread_idx + 4]  # good.txt or bad.txt

    mode = int(mode_str[4:])

    # Parse Stress (New Parameter)
    if "stress" in stress_str:
        stress = int(stress_str[6:])
    else:
        # Fallback for old files if mixed
        stress = 0
        goodbad_file = stress_str  # Shift if stress missing

    goodbad = goodbad_file.split(".")[0]

    parsed = parse_file(file, metric_type)

    # Store raw data
    target_dict = data[thread][mode][stress][goodbad]

    if metric_type == "perf_cache":
        for run in parsed:
            if len(run) >= 4:
                target_dict["remote_cache_fills"].append(run[1])  # demand_remote
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
        # If you saved branch misses in a separate file (from my previous fix)
        target_dict["branch_misses"].extend(parsed)
    elif metric_type in ["time", "energy"]:
        target_dict[metric_type].extend(parsed)

# --- 2. CALCULATE DERIVED METRICS ---
for t in data:
    for m in data[t]:
        for s in data[t][m]:
            for gb in data[t][m][s]:
                d = data[t][m][s][gb]

                # L1 Miss Rate
                if "l1_fills" in d:
                    d["l1_accesses"] = d["l1_fills"]
                    rates = []
                    for i in range(len(d["l1_fills"])):
                        if i < len(d["l1_l2_hits"]) and d["l1_fills"][i] > 0:
                            misses = d["l1_fills"][i] - d["l1_l2_hits"][i]
                            rates.append((misses / d["l1_fills"][i]) * 100)
                        else:
                            rates.append(0)
                    d["l1_miss_rate"] = rates

                # L2 Miss Rate
                if "l2_requests" in d:
                    d["l2_accesses"] = d["l2_requests"]
                    rates = []
                    for i in range(len(d["l2_requests"])):
                        if i < len(d["l2_misses"]) and d["l2_requests"][i] > 0:
                            rates.append(
                                (d["l2_misses"][i] / d["l2_requests"][i]) * 100
                            )
                        else:
                            rates.append(0)
                    d["l2_miss_rate"] = rates

                # L3 Miss Rate
                if "l3_accesses" in d:
                    rates = []
                    for i in range(len(d["l3_accesses"])):
                        if i < len(d["l3_misses"]) and d["l3_accesses"][i] > 0:
                            rates.append(
                                (d["l3_misses"][i] / d["l3_accesses"][i]) * 100
                            )
                        else:
                            rates.append(0)
                    d["l3_miss_rate"] = rates


# --- 3. HELPER TO GET STATISTICS ---
def get_stats(thread, mode, stress, goodbad, metric):
    # Determine the "Case" based on stress/goodbad
    # Case 1: Good Mem (good.cpp) + No Stress (0)
    # Case 2: Good Mem (good.cpp) + Stress (1)
    # Case 3: Bad Mem (bad.cpp) + No Stress (0)
    # Case 4: Bad Mem (bad.cpp) + Stress (1)

    vals = data[thread][mode][stress][goodbad].get(metric, [])
    if not vals:
        return 0, 0
    return np.mean(vals), np.std(vals, ddof=1) / np.sqrt(len(vals)) if len(
        vals
    ) > 1 else 0


# --- 4. PLOTTING: METRIC vs MODE (4 Bars per Mode) ---
for thread in sorted(data.keys()):
    modes = sorted(data[thread].keys())

    # 3x4 grid for metrics
    fig, axes = plt.subplots(3, 4, figsize=(22, 14))  # Slightly larger
    axes = axes.flatten()

    for i, metric in enumerate(metrics):
        if i >= len(axes):
            break
        ax = axes[i]

        # Prepare data for 4 bars per mode
        case1_means, case1_errs = [], []  # Good All
        case2_means, case2_errs = [], []  # Bad uArch
        case3_means, case3_errs = [], []  # Bad Mem
        case4_means, case4_errs = [], []  # Bad Both

        for mode in modes:
            # Case 1: Good + Stress 0
            m, e = get_stats(thread, mode, 0, "good", metric)
            case1_means.append(m)
            case1_errs.append(e)

            # Case 2: Good + Stress 1
            m, e = get_stats(thread, mode, 1, "good", metric)
            case2_means.append(m)
            case2_errs.append(e)

            # Case 3: Bad + Stress 0
            m, e = get_stats(thread, mode, 0, "bad", metric)
            case3_means.append(m)
            case3_errs.append(e)

            # Case 4: Bad + Stress 1
            m, e = get_stats(thread, mode, 1, "bad", metric)
            case4_means.append(m)
            case4_errs.append(e)

        x = np.arange(len(modes))
        width = 0.2

        # Plot 4 bars
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
        ax.set_title(metric_titles.get(metric, metric))

        if i == 0:  # Legend only on first plot to save space
            ax.legend(loc="upper left", fontsize="small")

        ax.grid(True, alpha=0.3)

    plt.suptitle(f"Results for {thread} Thread(s)", fontsize=16)
    plt.tight_layout()
    plt.savefig(f"results/plots/plot_thread_{thread}.png", dpi=300)
    plt.close()

# --- 5. PLOTTING: TIME vs THREADS (4 Lines) ---
# We generally look at Mode 0 (Default) or Mode 3 (Worst layout)
# Let's generate one for every mode found

all_modes = set()
for t in data:
    all_modes.update(data[t].keys())

for target_mode in sorted(all_modes):
    if target_mode == 1:
        continue  # Skip same core usually

    threads = sorted(data.keys())
    c1, c2, c3, c4 = [], [], [], []
    e1, e2, e3, e4 = [], [], [], []
    valid_threads = []

    for t in threads:
        # Check if we have data for this mode
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

    plt.xlabel("Number of Threads")
    plt.ylabel("Time (s)")
    plt.title(f"Execution Time vs Threads ({mode_names.get(target_mode, target_mode)})")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xticks(valid_threads)

    plt.savefig(f"results/plots/time_vs_threads_mode{target_mode}.png", dpi=300)
    plt.close()

print("Plots generated successfully with 4-case Analysis!")
