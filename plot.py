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
import math
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
# Defined in the exact order they should appear in the plots.
# The keys generate the list of metrics to process.
metric_titles = {
    # --- OLD METRICS ---
    "time": "Time",
    "energy": "Energy",
    "ls_any_fills_from_sys.remote_cache": "Any Remote Fills",
    "ls_dmnd_fills_from_sys.all": "L1 Accesses (Demand)",
    "l1_miss_rate": "L1 Miss Rate",
    "l2_cache_req_stat.all": "L2 Requests (Total)",
    "l2_miss_rate": "L2 Miss Rate",
    "ls_dmnd_fills_from_sys.local_ccx": "L3 Accesses (Local CCX)",
    "l3_miss_rate": "L3 Miss Rate",
    "branch-misses": "Branch Misses (Total)",
    "ex_ret_brn_misp": "Retired Branch Mispredicts",
    "bp_redirects.ex_redir": "Pipeline Flush (Exec)",
    "bp_de_redirect": "Pipeline Flush (Decode)",
    "bp_l2_btb_correct": "L2 BTB Corrections",
    "bp_l1_tlb_miss_l2_tlb_hit": "L1 ITLB Miss",
    "bp_redirects.resync": "Pipeline Resyncs",
    "de_src_op_disp.all": "Ops Dispatched",
    "ex_ret_ops": "Ops Retired",
    "speculation_efficiency": "Speculation Efficiency (Ret/Disp)",
    "de_dispatch_stall_cycle_dynamic_tokens_part1.load_queue_rsrc_stall": "Load Queue Stalls",
    "ex_no_retire.empty": "Stall (Pipeline Empty)",
    "ex_no_retire.load_not_complete": "Stall (Waiting for Load)",
    "de_no_dispatch_per_slot.backend_stalls": "Backend Stalls",
    "de_dispatch_stall_cycle_dynamic_tokens_part2.retq": "ROB Full Stalls",
    "instructions": "Total Instructions",
    "ls_alloc_mab_count": "MAB Congestion (Cycles)",
    "l2_request_g1.rd_blk_x": "L2 RFO (Writes)",
    "l2_fill_rsp_src.local_ccx": "Local CCX Fills (Same-CCD)",
    "l2_fill_rsp_src.far_cache": "Remote Fills (Cross-CCD)",
    # --- NEW METRICS ---
    "cycles": "CPU Cycles",
    "ls_dmnd_fills_from_sys.remote_cache": "Demand Remote Fills",
    "cache-misses": "LLC Misses (System)",
    "ls_bad_status2.stli_other": "Store-to-Load Conflicts",
    "ls_dmnd_fills_from_sys.dram_io_all": "L3 Miss Count (DRAM IO)",
    "ex_no_retire.thread_not_selected": "Stall (SMT Contention)",
    "de_op_queue_empty": "Frontend Starvation (Op Q Empty)",
    "l2_request_g1.rd_blk_l": "L2 Read Requests",
    "ls_dispatch.store_dispatch": "Total Stores Dispatched",
    "ls_l1_d_tlb_miss.all": "L1 D-TLB Misses",
    "op_cache_hit_miss.op_cache_miss": "Op Cache Misses",
    "ex_div_busy": "Divider Busy Cycles",
    "de_dispatch_stall_cycle_dynamic_tokens_part1.store_queue_rsrc_stall": "Store Queue Stalls",
    "ls_stlf": "Store-to-Load Fwd Hits",
    "ls_dispatch.ld_dispatch": "Total Loads Dispatched",
    "l2_request_g1.l2_hw_pf": "L2 Prefetch Requests",
    "l2_pf_miss_l2_l3.l2_hwpf": "Useless Prefetches (Miss L2/L3)",
    "ipc": "IPC (Instr/Cycle)",
    "smt_contention_pct": "SMT Contention (% of Cycles)",
    "frontend_starvation_pct": "Frontend Starvation (% of Cycles)",
    "write_intensity_pct": "Write Intensity (% of L2 Traffic)",
    "prefetch_waste_pct": "Prefetcher Waste Rate (% Useless)",
    "op_cache_mpki": "Op Cache Misses per 1k Instr",
    "divider_busy_pct": "Divider Busy (% of Cycles)",
    "load_store_ratio": "Load-to-Store Ratio",
    "avg_mab_occupancy": "Avg MAB Occupancy (Entries)",
    "remote_traffic_pct": "Remote Traffic (% of L2 Fills)",
    "branch_mpki": "Branch MPKI (Misses/1k Instr)",
    "l2_mpki": "L2 MPKI (Misses/1k Instr)",
    "l3_mpki": "L3 MPKI (Misses/1k Instr)",
    "true_l1_miss_rate": "True L1 D-Cache Miss Rate (%)",
    "memory_bound_pct": "Memory Bound Stall (% of Cycles)",
    "stlf_rate": "STLF Rate (% of Loads)",
    "l1_dtlb_mpki": "L1 D-TLB MPKI (Misses/1k Instr)",
    "uop_density": "Micro-Op Density (uOps/Instr)",
}

# Automatically derive the list of metrics from the dictionary keys to maintain order
metrics = list(metric_titles.keys())

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

    try:
        thread = int(parts[0])
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
        continue

    try:
        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                for key, val in row.items():
                    if not key or val is None:
                        continue

                    key = key.strip()
                    val = val.strip()

                    # Normalize Keys
                    if key == "Time":
                        key = "time"
                    if key == "Energy":
                        key = "energy"

                    if val == "" or val == "NaN" or "<" in val:
                        continue

                    try:
                        data[thread][mode][stress][goodbad][key].append(float(val))
                    except ValueError:
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

                # 1. L1 Miss Rate
                # L1 Accesses = ls_dmnd_fills_from_sys.all
                # L1 Hits = ls_dmnd_fills_from_sys.local_l2
                if "ls_dmnd_fills_from_sys.all" in d:
                    acc = d["ls_dmnd_fills_from_sys.all"]
                    if "ls_dmnd_fills_from_sys.local_l2" in d:
                        hits = d["ls_dmnd_fills_from_sys.local_l2"]
                        misses = [a - h for a, h in zip(acc, hits)]
                        d["l1_miss_rate"] = [
                            m / a * 100 if a > 0 else 0 for m, a in zip(misses, acc)
                        ]

                # 2. L2 Miss Rate
                # L2 Accesses = l2_cache_req_stat.all
                # L2 Misses = l2_cache_req_stat.ic_dc_miss_in_l2
                if (
                    "l2_cache_req_stat.all" in d
                    and "l2_cache_req_stat.ic_dc_miss_in_l2" in d
                ):
                    d["l2_miss_rate"] = [
                        m / a * 100 if a > 0 else 0
                        for m, a in zip(
                            d["l2_cache_req_stat.ic_dc_miss_in_l2"],
                            d["l2_cache_req_stat.all"],
                        )
                    ]

                # 3. L3 Miss Rate (Restored Logic)
                # L3 Accesses = ls_dmnd_fills_from_sys.local_ccx
                # L3 Misses (DRAM IO) = ls_dmnd_fills_from_sys.dram_io_all
                if (
                    "ls_dmnd_fills_from_sys.local_ccx" in d
                    and "ls_dmnd_fills_from_sys.dram_io_all" in d
                ):
                    d["l3_miss_rate"] = [
                        m / a * 100 if a > 0 else 0
                        for m, a in zip(
                            d["ls_dmnd_fills_from_sys.dram_io_all"],
                            d["ls_dmnd_fills_from_sys.local_ccx"],
                        )
                    ]

                # 4. Speculation Efficiency
                if "ex_ret_ops" in d and "de_src_op_disp.all" in d:
                    d["speculation_efficiency"] = calc_ratio(
                        d["ex_ret_ops"], d["de_src_op_disp.all"]
                    )

                # 5. IPC
                if "instructions" in d and "cycles" in d:
                    d["ipc"] = calc_ratio(d["instructions"], d["cycles"])

                # 6. SMT Contention % (ex_no_retire.thread_not_selected / cycles)
                if "ex_no_retire.thread_not_selected" in d and "cycles" in d:
                    ratio = calc_ratio(
                        d["ex_no_retire.thread_not_selected"], d["cycles"]
                    )
                    d["smt_contention_pct"] = [r * 100 for r in ratio]

                # 7. Frontend Starvation % (de_op_queue_empty / cycles)
                if "de_op_queue_empty" in d and "cycles" in d:
                    ratio = calc_ratio(d["de_op_queue_empty"], d["cycles"])
                    d["frontend_starvation_pct"] = [r * 100 for r in ratio]

                # 8. Write Intensity (Writes / (Writes + Reads))
                # Uses: l2_request_g1.rd_blk_x (Writes) and l2_request_g1.rd_blk_l (Reads)
                if "l2_request_g1.rd_blk_x" in d and "l2_request_g1.rd_blk_l" in d:
                    writes = d["l2_request_g1.rd_blk_x"]
                    reads = d["l2_request_g1.rd_blk_l"]
                    total = [w + r for w, r in zip(writes, reads)]
                    d["write_intensity_pct"] = [
                        (w / t * 100) if t > 0 else 0 for w, t in zip(writes, total)
                    ]

                # 9. Prefetch Waste Rate (Missed L2&L3 / Total PF Reqs)
                if "l2_pf_miss_l2_l3.l2_hwpf" in d and "l2_request_g1.l2_hw_pf" in d:
                    missed = d["l2_pf_miss_l2_l3.l2_hwpf"]
                    total = d["l2_request_g1.l2_hw_pf"]
                    d["prefetch_waste_pct"] = [
                        (m / t * 100) if t > 0 else 0 for m, t in zip(missed, total)
                    ]

                # 10. Op Cache MPKI (Misses per 1000 Instructions)
                if "op_cache_hit_miss.op_cache_miss" in d and "instructions" in d:
                    misses = d["op_cache_hit_miss.op_cache_miss"]
                    instr = d["instructions"]
                    d["op_cache_mpki"] = [
                        (m * 1000 / i) if i > 0 else 0 for m, i in zip(misses, instr)
                    ]

                # 11. Divider Busy %
                if "ex_div_busy" in d and "cycles" in d:
                    ratio = calc_ratio(d["ex_div_busy"], d["cycles"])
                    d["divider_busy_pct"] = [r * 100 for r in ratio]

                # 12. Load/Store Ratio
                if "ls_dispatch.ld_dispatch" in d and "ls_dispatch.store_dispatch" in d:
                    d["load_store_ratio"] = calc_ratio(
                        d["ls_dispatch.ld_dispatch"], d["ls_dispatch.store_dispatch"]
                    )

                # 13. Average MAB Occupancy (MAB Alloc / Cycles)
                # Note: This metric counts accumulated allocations per cycle, so dividing by cycles gives avg depth.
                if "ls_alloc_mab_count" in d and "cycles" in d:
                    mab = d["ls_alloc_mab_count"]
                    cycles = d["cycles"]
                    d["avg_mab_occupancy"] = [
                        (m / c) if c > 0 else 0 for m, c in zip(mab, cycles)
                    ]

                # 14. Remote Traffic % (Remote Fills / (Local + Remote))
                if (
                    "l2_fill_rsp_src.far_cache" in d
                    and "l2_fill_rsp_src.local_ccx" in d
                ):
                    remote = d["l2_fill_rsp_src.far_cache"]
                    local = d["l2_fill_rsp_src.local_ccx"]
                    total = [r + l for r, l in zip(remote, local)]
                    d["remote_traffic_pct"] = [
                        (r / t * 100) if t > 0 else 0 for r, t in zip(remote, total)
                    ]

                # 15. MPKI Metrics (Misses * 1000 / Instructions)
                if "instructions" in d:
                    instr = d["instructions"]

                    # Branch MPKI
                    if "branch-misses" in d:
                        d["branch_mpki"] = [
                            (m * 1000 / i) if i > 0 else 0
                            for m, i in zip(d["branch-misses"], instr)
                        ]

                    # L2 MPKI
                    if "l2_cache_req_stat.ic_dc_miss_in_l2" in d:
                        d["l2_mpki"] = [
                            (m * 1000 / i) if i > 0 else 0
                            for m, i in zip(
                                d["l2_cache_req_stat.ic_dc_miss_in_l2"], instr
                            )
                        ]

                    # L3 MPKI
                    if (
                        "ls_dmnd_fills_from_sys.dram_io_all" in d
                    ):  # Using raw miss count
                        d["l3_mpki"] = [
                            (m * 1000 / i) if i > 0 else 0
                            for m, i in zip(
                                d["ls_dmnd_fills_from_sys.dram_io_all"], instr
                            )
                        ]

                # 16. True L1 D-Cache Miss Rate
                # Fills (Misses) / (Loads + Stores)
                if (
                    "ls_dmnd_fills_from_sys.all" in d
                    and "ls_dispatch.ld_dispatch" in d
                    and "ls_dispatch.store_dispatch" in d
                ):
                    fills = d["ls_dmnd_fills_from_sys.all"]
                    loads = d["ls_dispatch.ld_dispatch"]
                    stores = d["ls_dispatch.store_dispatch"]
                    accesses = [l + s for l, s in zip(loads, stores)]
                    d["true_l1_miss_rate"] = [
                        (f / a * 100) if a > 0 else 0 for f, a in zip(fills, accesses)
                    ]

                # 17. Memory Bound % (Stall on Load / Cycles)
                if "ex_no_retire.load_not_complete" in d and "cycles" in d:
                    stall = d["ex_no_retire.load_not_complete"]
                    cycles = d["cycles"]
                    d["memory_bound_pct"] = [
                        (s / c * 100) if c > 0 else 0 for s, c in zip(stall, cycles)
                    ]

                # 18. STLF Rate (STLF Hits / Total Loads)
                if "ls_stlf" in d and "ls_dispatch.ld_dispatch" in d:
                    stlf = d["ls_stlf"]
                    loads = d["ls_dispatch.ld_dispatch"]
                    d["stlf_rate"] = [
                        (s / l * 100) if l > 0 else 0 for s, l in zip(stlf, loads)
                    ]

                # 19. L1 D-TLB MPKI
                if "ls_l1_d_tlb_miss.all" in d and "instructions" in d:
                    d["l1_dtlb_mpki"] = [
                        (m * 1000 / i) if i > 0 else 0
                        for m, i in zip(d["ls_l1_d_tlb_miss.all"], d["instructions"])
                    ]

                # 20. Micro-Op Density (Retired Ops / Instructions)
                if "ex_ret_ops" in d and "instructions" in d:
                    d["uop_density"] = calc_ratio(d["ex_ret_ops"], d["instructions"])


# --- PLOTTING (Iterates over ordered 'metrics' list) ---
def get_stats(thread, mode, stress, goodbad, metric):
    vals = data[thread][mode][stress][goodbad].get(metric, [])
    if not vals:
        return 0, 0
    return np.mean(vals), np.std(vals, ddof=1) / np.sqrt(len(vals)) if len(
        vals
    ) > 1 else 0


for thread in sorted(data.keys()):
    modes = sorted(data[thread].keys())

    # Dynamic Grid Calculation
    num_plots = len(metrics)
    cols = 5
    rows = math.ceil(num_plots / cols)

    # Dynamic Figure Height: Assign ~4 inches of vertical space per row
    fig_height = rows * 4

    fig, axes = plt.subplots(rows, cols, figsize=(25, fig_height))
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
        # Use friendly title if available, otherwise raw name
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

# --- TIME VS THREADS PLOT (Unchanged) ---
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

    for i, x_val in enumerate(valid_threads):
        points = [
            (c1[i], C1_COLOR),
            (c2[i], C2_COLOR),
            (c3[i], C3_COLOR),
            (c4[i], C4_COLOR),
        ]
        points.sort(key=lambda p: p[0])
        for j in range(1, len(points)):
            curr_val, _ = points[j]
            label_count = 0
            for k in range(j):
                prev_val, prev_color = points[k]
                if prev_val > 0:
                    ratio = curr_val / prev_val
                    plt.annotate(
                        f"{ratio:.1f}x",
                        (x_val, curr_val),
                        textcoords="offset points",
                        xytext=(0, 5 + (label_count * 10)),
                        ha="center",
                        fontsize=8,
                        color=prev_color,
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
