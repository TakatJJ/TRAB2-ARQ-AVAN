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
import argparse
from matplotlib.ticker import FuncFormatter

# Path to the raw results folder
results_dir = "results/raw"

# --- COLOR PALETTE (BARS) ---
C1_COLOR = "#21674f"  # Good All
C2_COLOR = "#4a90e2"  # Bad uArch
C3_COLOR = "#CC6666"  # Bad Mem
C4_COLOR = "#8e44ad"  # Bad Both

# --- LEGEND LABELS ---
LABEL_GOOD_ALL = "Bom Ambos"  # Changed from "Bom (Tudo)"
LABEL_BAD_UARCH = "Ruim uArq"
LABEL_BAD_MEM = "Ruim Mem"
LABEL_BAD_BOTH = "Ruim Ambos"

# --- CLUSTER DISPLAY TOGGLES ---
ENABLE_DOTTED_LINES = True       # Toggle 1: Dotted line between clusters
ENABLE_COLORED_LABELS = True     # Toggle 2: Colored name for cluster at bottom
ENABLE_SHADED_BACKGROUND = True  # Toggle 3: Colored/shaded background for clusters
LEGEND_LOC_BEST = True           # Toggle: Switch legend loc to "best" (False = "upper left")

# --- CLUSTER COLORS (BACKGROUND/LABELS) ---
CLUSTER_COLORS = {
    0: "#F39C12",  # Default (Padrão) - PastelOrange
    1: "#16A085",  # Same Core (Mesmo Core) - PastelTeal
    2: "#D81B60",  # Same CCD (Mesmo CCD) - PastelPink
    3: "#8D6E63",  # Different CCDs (CCDs diferentes) - PastelBrown
}

# --- METRIC DEFINITIONS (TRANSLATED TO PT-BR) ---
metric_titles = {
    # --- OLD METRICS ---
    "time": "Tempo",
    "energy": "Energia",
    "ls_any_fills_from_sys.remote_cache": "Preenchimentos Remotos",
    "ls_dmnd_fills_from_sys.all": "Acessos L1",
    "l1_miss_rate": "Taxa de Miss L1",
    "l2_cache_req_stat.all": "Requisições L2",
    "l2_miss_rate": "Taxa de Miss L2",
    "ls_dmnd_fills_from_sys.local_ccx": "Acessos L3 (CCD Local)",
    "l3_miss_rate": "Taxa de Miss L3",
    "branch-misses": "Misses de Desvio",
    "ex_ret_brn_misp": "Desvios Mal Preditos (Aposentados)",
    "bp_redirects.ex_redir": "Flush de Pipeline",
    "bp_de_redirect": "Flush de Pipeline (Decode)",
    "bp_l2_btb_correct": "Correções L2 BTB",
    "bp_l1_tlb_miss_l2_tlb_hit": "Miss L1 ITLB",
    "bp_redirects.resync": "Ressincronizações de Pipeline",
    "de_src_op_disp.all": "Ops Despachadas",
    "ex_ret_ops": "Ops Aposentadas",
    "speculation_efficiency": "Eficiência de Especulação",
    "de_dispatch_stall_cycle_dynamic_tokens_part1.load_queue_rsrc_stall": "Stalls de Fila de Load",
    "ex_no_retire.empty": "Stall (Pipeline Vazio)",
    "ex_no_retire.load_not_complete": "Stall (Esperando Load)",
    "de_no_dispatch_per_slot.backend_stalls": "Stalls de Backend",
    "de_dispatch_stall_cycle_dynamic_tokens_part2.retq": "Stalls por ROB Cheio",
    "instructions": "Instruções Totais",
    "ls_alloc_mab_count": "Congestionamento MAB (Ciclos)",
    "l2_request_g1.rd_blk_x": "L2 RFO",
    "l2_fill_rsp_src.local_ccx": "Preenchimentos CCX Local (Mesmo CCD)",
    "l2_fill_rsp_src.far_cache": "Preenchimentos Remotos (Outro CCD)",
    # --- NEW METRICS ---
    "cycles": "Ciclos de CPU",
    "ls_dmnd_fills_from_sys.remote_cache": "Preenchimentos Remotos (Demanda)",
    "cache-misses": "Misses LLC (Sistema)",
    "ls_bad_status2.stli_other": "Conflitos Store-to-Load",
    "ls_dmnd_fills_from_sys.dram_io_all": "Contagem Miss L3 (DRAM IO)",
    "ex_no_retire.thread_not_selected": "Stall (Contenção SMT)",
    "de_op_queue_empty": "Starvation de Frontend (Op Q Vazia)",
    "l2_request_g1.rd_blk_l": "Requisições de Leitura L2",
    "ls_dispatch.store_dispatch": "Total de Stores Despachados",
    "ls_l1_d_tlb_miss.all": "Misses L1 D-TLB",
    "op_cache_hit_miss.op_cache_miss": "Misses Op Cache",
    "ex_div_busy": "Ciclos Divisor Ocupado",
    "de_dispatch_stall_cycle_dynamic_tokens_part1.store_queue_rsrc_stall": "Stalls de Fila de Store",
    "ls_stlf": "Hits de Encaminhamento Store-to-Load",
    "ls_dispatch.ld_dispatch": "Total de Loads Despachados",
    "l2_request_g1.l2_hw_pf": "Requisições de Prefetch L2",
    "l2_pf_miss_l2_l3.l2_hwpf": "Prefetches Inúteis (Miss L2/L3)",
    "ipc": "IPC (Instr/Ciclo)",
    "smt_contention_pct": "Contenção SMT (% de Ciclos)",
    "frontend_starvation_pct": "Starvation de Frontend (% de Ciclos)",
    "write_intensity_pct": "Intensidade de Escrita (% do Tráfego L2)",
    "prefetch_waste_pct": "Taxa de Desperdício do Prefetcher (% Inútil)",
    "op_cache_mpki": "Misses Op Cache por 1k Instr",
    "divider_busy_pct": "Divisor Ocupado (% de Ciclos)",
    "load_store_ratio": "Razão Load-to-Store",
    "avg_mab_occupancy": "Ocupação Média MAB (Entradas)",
    "remote_traffic_pct": "Tráfego Remoto (% de Preenchimentos L2)",
    "branch_mpki": "Branch MPKI (Misses/1k Instr)",
    "l2_mpki": "L2 MPKI (Misses/1k Instr)",
    "l3_mpki": "L3 MPKI (Misses/1k Instr)",
    "true_l1_miss_rate": "Taxa de Miss Real L1 D-Cache (%)",
    "memory_bound_pct": "Stall Memory Bound (% de Ciclos)",
    "stlf_rate": "Taxa STLF (% de Loads)",
    "l1_dtlb_mpki": "L1 D-TLB MPKI (Misses/1k Instr)",
    "uop_density": "Densidade de Micro-Op (uOps/Instr)",
}

metrics = list(metric_titles.keys())

log_metrics = [
    "branch-misses",
    "ex_ret_brn_misp",
    "bp_redirects.ex_redir",
    "de_dispatch_stall_cycle_dynamic_tokens_part2.retq",
    "ls_alloc_mab_count",
    "bp_redirects.resync",
    "l2_cache_req_stat.all",
    "l2_request_g1.rd_blk_x",
    "ex_no_retire.thread_not_selected"
]

# --- Y-AXIS LIMITS ---
# Define explicit limits for specific metrics here.
# Value can be:
#   - Single number (e.g., 100): Sets TOP limit. Bottom defaults to 0 (linear) or auto (log).
#   - Tuple (e.g., (1e3, 1e7)): Sets (BOTTOM, TOP) limits.
#   - Dictionary {thread_count: value_or_tuple}: Thread-specific limits.
METRIC_YMAX = {
    "l1_miss_rate": 100,
    "l2_miss_rate": 100,
    "l3_miss_rate": 100,
    "tempo": 4e3,
    "ls_any_fills_from_sys.remote_cache": {3: 150e6, 6: 18e6, 7: 18e6},
    "ex_no_retire.thread_not_selected": (1e5, 1e9),
    "l2_cache_req_stat.all": {3: (1e4, 2e8)},
    "l2_request_g1.rd_blk_x": {3: (1e4, 2e8)},
    "ls_dmnd_fills_from_sys.local_ccx": 150e6,
}

metric_ylabels = {
    # Time & Energy
    "time": "Segundos (s)",
    "energy": "Energia (J)",
    # Rates & Percentages
    "l1_miss_rate": "Taxa de Miss (%)",
    "l2_miss_rate": "Taxa de Miss (%)",
    "l3_miss_rate": "Taxa de Miss (%)",
    "true_l1_miss_rate": "Taxa de Miss (%)",
    "smt_contention_pct": "Porcentagem (%)",
    "frontend_starvation_pct": "Porcentagem (%)",
    "write_intensity_pct": "Porcentagem (%)",
    "prefetch_waste_pct": "Porcentagem (%)",
    "divider_busy_pct": "Porcentagem (%)",
    "remote_traffic_pct": "Porcentagem (%)",
    "memory_bound_pct": "Porcentagem (%)",
    "stlf_rate": "Taxa (%)",
    "speculation_efficiency": "Eficiência (%)",
    # Ratios & Densities
    "ipc": "IPC",
    "load_store_ratio": "Razão (Ld/St)",
    "uop_density": "uOps / Instr",
    # MPKI
    "branch_mpki": "MPKI",
    "l2_mpki": "MPKI",
    "l3_mpki": "MPKI",
    "l1_dtlb_mpki": "MPKI",
    "op_cache_mpki": "MPKI",
    # Cycles / Latency / Occupancy
    "cycles": "Ciclos",
    "ls_alloc_mab_count": "Ciclos Acumulados",
    "avg_mab_occupancy": "Entradas",
    "ex_div_busy": "Ciclos",
    "de_dispatch_stall_cycle_dynamic_tokens_part1.load_queue_rsrc_stall": "Ciclos de Stall",
    "ex_no_retire.empty": "Ciclos de Stall",
    "ex_no_retire.load_not_complete": "Ciclos de Stall",
    "de_no_dispatch_per_slot.backend_stalls": "Ciclos de Stall",
    "de_dispatch_stall_cycle_dynamic_tokens_part2.retq": "Ciclos de Stall",
    "ex_no_retire.thread_not_selected": "Ciclos de Stall",
    "de_dispatch_stall_cycle_dynamic_tokens_part1.store_queue_rsrc_stall": "Ciclos de Stall",
    # Default fallbacks
    "instructions": "Contagem",
}

# Portuguese mode names
mode_names_pt = {0: "Padrão", 1: "Mesmo núcleo", 2: "Mesmo CCD", 3: "CCDs diferentes"}

# --- FORMATTING FUNCTION ---
def large_num_formatter(x, pos):
    """Formats large numbers with K, M, B, T suffixes."""
    if x == 0:
        return "0"
    abs_x = abs(x)
    
    if abs_x >= 1e12:
        val = x / 1e12
        return f'{val:.0f}T' if val.is_integer() else f'{val:.1f}T'
    elif abs_x >= 1e9:
        val = x / 1e9
        return f'{val:.0f}B' if val.is_integer() else f'{val:.1f}B'
    elif abs_x >= 1e6:
        val = x / 1e6
        return f'{val:.0f}M' if val.is_integer() else f'{val:.1f}M'
    elif abs_x >= 1000:
        val = x / 1e3
        return f'{val:.0f}K' if val.is_integer() else f'{val:.1f}K'
    else:
        return f'{x:g}'

# --- PARSING LOGIC ---
data = defaultdict(
    lambda: defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    )
)

files = glob.glob(os.path.join(results_dir, "*.txt")) + glob.glob(
    os.path.join(results_dir, "*.csv")
)
print(f"Encontrados {len(files)} arquivos de resultado.")

for filepath in files:
    filename = os.path.basename(filepath)
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
                    if key == "Time": key = "time"
                    if key == "Energy": key = "energy"
                    if val == "" or val == "NaN" or "<" in val:
                        continue
                    try:
                        data[thread][mode][stress][goodbad][key].append(float(val))
                    except ValueError:
                        continue
    except Exception as e:
        print(f"Aviso: Não foi possível analisar o arquivo {filename}: {e}")

print("Análise de dados completa.")

# --- DERIVED METRICS ---
print("Calculando métricas derivadas...")
for t in data:
    for m in data[t]:
        for s in data[t][m]:
            for gb in data[t][m][s]:
                d = data[t][m][s][gb]
                def calc_ratio(num_list, den_list):
                    return [n / d if d > 0 else 0 for n, d in zip(num_list, den_list)]

                if "ls_dmnd_fills_from_sys.all" in d:
                    acc = d["ls_dmnd_fills_from_sys.all"]
                    if "ls_dmnd_fills_from_sys.local_l2" in d:
                        hits = d["ls_dmnd_fills_from_sys.local_l2"]
                        misses = [a - h for a, h in zip(acc, hits)]
                        d["l1_miss_rate"] = [m / a * 100 if a > 0 else 0 for m, a in zip(misses, acc)]

                if "l2_cache_req_stat.all" in d and "l2_cache_req_stat.ic_dc_miss_in_l2" in d:
                    d["l2_miss_rate"] = [m / a * 100 if a > 0 else 0 for m, a in zip(d["l2_cache_req_stat.ic_dc_miss_in_l2"], d["l2_cache_req_stat.all"])]

                if "ls_dmnd_fills_from_sys.local_ccx" in d and "ls_dmnd_fills_from_sys.dram_io_all" in d:
                    d["l3_miss_rate"] = [m / a * 100 if a > 0 else 0 for m, a in zip(d["ls_dmnd_fills_from_sys.dram_io_all"], d["ls_dmnd_fills_from_sys.local_ccx"])]

                if "ex_ret_ops" in d and "de_src_op_disp.all" in d:
                    ratio = calc_ratio(d["ex_ret_ops"], d["de_src_op_disp.all"])
                    d["speculation_efficiency"] = [r * 100 for r in ratio]

                if "instructions" in d and "cycles" in d:
                    d["ipc"] = calc_ratio(d["instructions"], d["cycles"])

                if "ex_no_retire.thread_not_selected" in d and "cycles" in d:
                    ratio = calc_ratio(d["ex_no_retire.thread_not_selected"], d["cycles"])
                    d["smt_contention_pct"] = [r * 100 for r in ratio]

                if "de_op_queue_empty" in d and "cycles" in d:
                    ratio = calc_ratio(d["de_op_queue_empty"], d["cycles"])
                    d["frontend_starvation_pct"] = [r * 100 for r in ratio]

                if "l2_request_g1.rd_blk_x" in d and "l2_request_g1.rd_blk_l" in d:
                    writes = d["l2_request_g1.rd_blk_x"]
                    reads = d["l2_request_g1.rd_blk_l"]
                    total = [w + r for w, r in zip(writes, reads)]
                    d["write_intensity_pct"] = [(w / t * 100) if t > 0 else 0 for w, t in zip(writes, total)]

                if "l2_pf_miss_l2_l3.l2_hwpf" in d and "l2_request_g1.l2_hw_pf" in d:
                    missed = d["l2_pf_miss_l2_l3.l2_hwpf"]
                    total = d["l2_request_g1.l2_hw_pf"]
                    d["prefetch_waste_pct"] = [(m / t * 100) if t > 0 else 0 for m, t in zip(missed, total)]

                if "op_cache_hit_miss.op_cache_miss" in d and "instructions" in d:
                    misses = d["op_cache_hit_miss.op_cache_miss"]
                    instr = d["instructions"]
                    d["op_cache_mpki"] = [(m * 1000 / i) if i > 0 else 0 for m, i in zip(misses, instr)]

                if "ex_div_busy" in d and "cycles" in d:
                    ratio = calc_ratio(d["ex_div_busy"], d["cycles"])
                    d["divider_busy_pct"] = [r * 100 for r in ratio]

                if "ls_dispatch.ld_dispatch" in d and "ls_dispatch.store_dispatch" in d:
                    d["load_store_ratio"] = calc_ratio(d["ls_dispatch.ld_dispatch"], d["ls_dispatch.store_dispatch"])

                if "ls_alloc_mab_count" in d and "cycles" in d:
                    mab = d["ls_alloc_mab_count"]
                    cycles = d["cycles"]
                    d["avg_mab_occupancy"] = [(m / c) if c > 0 else 0 for m, c in zip(mab, cycles)]

                if "l2_fill_rsp_src.far_cache" in d and "l2_fill_rsp_src.local_ccx" in d:
                    remote = d["l2_fill_rsp_src.far_cache"]
                    local = d["l2_fill_rsp_src.local_ccx"]
                    total = [r + l for r, l in zip(remote, local)]
                    d["remote_traffic_pct"] = [(r / t * 100) if t > 0 else 0 for r, t in zip(remote, total)]

                if "instructions" in d:
                    instr = d["instructions"]
                    if "branch-misses" in d:
                        d["branch_mpki"] = [(m * 1000 / i) if i > 0 else 0 for m, i in zip(d["branch-misses"], instr)]
                    if "l2_cache_req_stat.ic_dc_miss_in_l2" in d:
                        d["l2_mpki"] = [(m * 1000 / i) if i > 0 else 0 for m, i in zip(d["l2_cache_req_stat.ic_dc_miss_in_l2"], instr)]
                    if "ls_dmnd_fills_from_sys.dram_io_all" in d:
                        d["l3_mpki"] = [(m * 1000 / i) if i > 0 else 0 for m, i in zip(d["ls_dmnd_fills_from_sys.dram_io_all"], instr)]

                if "ls_dmnd_fills_from_sys.all" in d and "ls_dispatch.ld_dispatch" in d and "ls_dispatch.store_dispatch" in d:
                    fills = d["ls_dmnd_fills_from_sys.all"]
                    loads = d["ls_dispatch.ld_dispatch"]
                    stores = d["ls_dispatch.store_dispatch"]
                    accesses = [l + s for l, s in zip(loads, stores)]
                    d["true_l1_miss_rate"] = [(f / a * 100) if a > 0 else 0 for f, a in zip(fills, accesses)]

                if "ex_no_retire.load_not_complete" in d and "cycles" in d:
                    stall = d["ex_no_retire.load_not_complete"]
                    cycles = d["cycles"]
                    d["memory_bound_pct"] = [(s / c * 100) if c > 0 else 0 for s, c in zip(stall, cycles)]

                if "ls_stlf" in d and "ls_dispatch.ld_dispatch" in d:
                    stlf = d["ls_stlf"]
                    loads = d["ls_dispatch.ld_dispatch"]
                    d["stlf_rate"] = [(s / l * 100) if l > 0 else 0 for s, l in zip(stlf, loads)]

                if "ls_l1_d_tlb_miss.all" in d and "instructions" in d:
                    d["l1_dtlb_mpki"] = [(m * 1000 / i) if i > 0 else 0 for m, i in zip(d["ls_l1_d_tlb_miss.all"], d["instructions"])]

                if "ex_ret_ops" in d and "instructions" in d:
                    d["uop_density"] = calc_ratio(d["ex_ret_ops"], d["instructions"])

print("Cálculo de métricas derivadas completo.")

# --- PLOTTING FUNCTIONS ---

def generate_thread_plots(thread, thread_data, selected_indices):
    """Generates plots for a single thread count, filtered by selected_indices."""
    print(f"  Gerando gráficos para {thread} thread(s)...")
    
    # Helper for stats extraction
    def get_stats_local(data_slice, mode, stress, goodbad, metric):
        vals = data_slice[mode][stress][goodbad].get(metric, [])
        if not vals:
            return 0, 0
        return np.mean(vals), np.std(vals, ddof=1) / np.sqrt(len(vals)) if len(vals) > 1 else 0

    modes = sorted(thread_data.keys())
    thread_pdf_dir = os.path.join("results", "plots", f"plots_thread_{thread}")
    os.makedirs(thread_pdf_dir, exist_ok=True)

    # Filter metrics based on indices (1-based)
    plots_to_generate = []
    for idx in selected_indices:
        if 1 <= idx <= len(metrics):
            plots_to_generate.append((idx, metrics[idx - 1])) # Keep track of original ID
    
    num_plots = len(plots_to_generate)
    if num_plots == 0:
        return

    cols = 5
    rows = math.ceil(num_plots / cols)
    fig_height = rows * 4
    fig, axes = plt.subplots(rows, cols, figsize=(25, fig_height))
    
    if num_plots == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    for i, (original_idx, metric) in enumerate(plots_to_generate):
        c1m, c1e, c2m, c2e, c3m, c3e, c4m, c4e = [], [], [], [], [], [], [], []
        for mode in modes:
            m, e = get_stats_local(thread_data, mode, 0, "good", metric)
            c1m.append(m); c1e.append(e)
            m, e = get_stats_local(thread_data, mode, 1, "good", metric)
            c2m.append(m); c2e.append(e)
            m, e = get_stats_local(thread_data, mode, 0, "bad", metric)
            c3m.append(m); c3e.append(e)
            m, e = get_stats_local(thread_data, mode, 1, "bad", metric)
            c4m.append(m); c4e.append(e)

        # Function to draw bars and apply common and toggleable styles
        def draw_bars(ax_target, show_legend_local=False, custom_title=None):
            x = np.arange(len(modes))
            width = 0.2
            ax_target.bar(x - 1.5 * width, c1m, width, label=LABEL_GOOD_ALL, color=C1_COLOR, yerr=c1e, capsize=3)
            ax_target.bar(x - 0.5 * width, c2m, width, label=LABEL_BAD_UARCH, color=C2_COLOR, yerr=c2e, capsize=3)
            ax_target.bar(x + 0.5 * width, c3m, width, label=LABEL_BAD_MEM, color=C3_COLOR, yerr=c3e, capsize=3)
            ax_target.bar(x + 1.5 * width, c4m, width, label=LABEL_BAD_BOTH, color=C4_COLOR, yerr=c4e, capsize=3)
            
            ax_target.set_xticks(x)
            ax_target.set_xticklabels([mode_names_pt.get(m, f"Modo {m}") for m in modes])
            
            # --- CUSTOMIZATION 1: COLORED LABELS ---
            if ENABLE_COLORED_LABELS:
                for tick, mode_idx in zip(ax_target.get_xticklabels(), modes):
                    tick.set_color(CLUSTER_COLORS.get(mode_idx, "black"))
                    tick.set_fontweight("bold")

            # --- CUSTOMIZATION 2: SHADED BACKGROUND ---
            if ENABLE_SHADED_BACKGROUND:
                for idx_m, mode_id in enumerate(modes):
                    # Bars are centered at idx_m. Span goes from idx_m - 0.5 to idx_m + 0.5
                    bg_color = CLUSTER_COLORS.get(mode_id, "white")
                    ax_target.axvspan(idx_m - 0.5, idx_m + 0.5, facecolor=bg_color, alpha=0.15, zorder=0)

            # --- CUSTOMIZATION 3: DOTTED LINES ---
            if ENABLE_DOTTED_LINES:
                # Draw lines between clusters (0.5, 1.5, etc.)
                for idx_m in range(len(modes) - 1):
                    ax_target.axvline(x=idx_m + 0.5, color='gray', linestyle=':', linewidth=1, alpha=0.5)

            # Titles and Labels
            if custom_title:
                ax_target.set_title(custom_title, fontsize=14)
            else:
                # For Grid
                title_txt = metric_titles.get(metric, metric)
                # Plot number is handled by caller for grid
                ax_target.text(0.5, 1.05, title_txt, transform=ax_target.transAxes, ha='center', va='bottom', fontsize=10)

            ylabel_txt = metric_ylabels.get(metric, "Contagem")
            if metric in log_metrics:
                ylabel_txt += " (log)"
                ax_target.set_yscale("log")
            
            # Font size for individual plots passed via custom logic/defaults, here default small for grid
            fontsize_lbl = 12 if custom_title else 9
            ax_target.set_ylabel(ylabel_txt, fontsize=fontsize_lbl)

            # APPLY FORMATTER AFTER SETTING LOG SCALE
            ax_target.yaxis.set_major_formatter(FuncFormatter(large_num_formatter))

            # --- CUSTOMIZATION 4: LEGEND LOCATION ---
            if show_legend_local:
                loc = "best" if LEGEND_LOC_BEST else "upper left"
                fontsize_leg = 12 if custom_title else "x-small"
                ax_target.legend(loc=loc, fontsize=fontsize_leg)
            
            # --- APPLY Y-LIMITS ---
            if metric in METRIC_YMAX:
                raw_config = METRIC_YMAX[metric]
                limit = None
                
                # Check for thread-specific config (dict)
                if isinstance(raw_config, dict):
                    if thread in raw_config:
                        limit = raw_config[thread]
                else:
                    # Global config
                    limit = raw_config
                
                if limit is not None:
                    if isinstance(limit, (tuple, list)):
                        ax_target.set_ylim(bottom=limit[0], top=limit[1])
                    else:
                        # For log scale, bottom cannot be 0.
                        if metric in log_metrics:
                            ax_target.set_ylim(top=limit)
                        else:
                            ax_target.set_ylim(bottom=0, top=limit)

            ax_target.grid(True, alpha=0.3)

        # 1. Plot on Grid (Includes Numbering)
        ax = axes[i]
        # Add Plot Number to Grid PNG (Top Left, Bold)
        ax.set_title(str(original_idx), loc='left', fontsize=12, fontweight='bold')
        draw_bars(ax, show_legend_local=(i == 0))

        # 2. Plot Individual PDF (NO Numbering, Adjusted Fonts/Margins)
        fig_single, ax_single = plt.subplots(figsize=(6, 5))
        
        # Standard Title for PDF
        base_title = metric_titles.get(metric, metric)
        pdf_title = f"{base_title} ({thread} Threads)"
        
        draw_bars(ax_single, show_legend_local=True, custom_title=pdf_title)
        
        # Tight layout with tight padding
        plt.tight_layout(pad=0.1)
        
        safe_metric_name = metric.replace("/", "_")
        pdf_filename = f"t{thread}_{original_idx}_{safe_metric_name}.pdf"
        pdf_path = os.path.join(thread_pdf_dir, pdf_filename)
        fig_single.savefig(pdf_path)
        plt.close(fig_single)

    # Turn off unused axes in the grid
    for j in range(num_plots, len(axes)):
        axes[j].axis("off")
    
    plt.suptitle(f"Resultados para {thread} Thread(s)", fontsize=16)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(f"results/plots/plot_thread_{thread}.png", dpi=300)
    plt.close()


def generate_time_vs_threads_plots(data):
    """Generates the Time vs Threads comparison plots."""
    print("Gerando gráficos de Tempo vs Threads...")
    
    def get_stats_global(thread, mode, stress, goodbad, metric):
        vals = data[thread][mode][stress][goodbad].get(metric, [])
        if not vals:
            return 0, 0
        return np.mean(vals), np.std(vals, ddof=1) / np.sqrt(len(vals)) if len(vals) > 1 else 0

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
            m, e = get_stats_global(t, target_mode, 0, "good", "time")
            c1.append(m); e1.append(e)
            m, e = get_stats_global(t, target_mode, 1, "good", "time")
            c2.append(m); e2.append(e)
            m, e = get_stats_global(t, target_mode, 0, "bad", "time")
            c3.append(m); e3.append(e)
            m, e = get_stats_global(t, target_mode, 1, "bad", "time")
            c4.append(m); e4.append(e)

        if not valid_threads:
            continue

        # Calculate global Y limit
        y_max = 0
        for arrays in [(c1, e1), (c2, e2), (c3, e3), (c4, e4)]:
            means, errs = arrays
            if not means: continue
            current_max = max([m + e for m, e in zip(means, errs)]) if means else 0
            if current_max > y_max:
                y_max = current_max
                
        y_limit = y_max * 1.1 if y_max > 0 else None

        # 4 Versions Configuration
        plot_versions = [
            ("_v1", False, False, False, False), 
            ("_v2", True, False, False, True),   
            ("_v3", True, True, False, True),    
            ("_v4", True, True, True, True),     
        ]

        for suffix, show_uarch, show_mem, show_both, show_labels in plot_versions:
            plt.figure(figsize=(10, 6))
            
            # Apply Y-Axis Formatter
            plt.gca().yaxis.set_major_formatter(FuncFormatter(large_num_formatter))

            if y_limit:
                plt.ylim(0, y_limit)
            
            plt.errorbar(
                valid_threads, c1, yerr=e1, fmt="o-", label=LABEL_GOOD_ALL, color=C1_COLOR, capsize=5
            )

            if show_uarch:
                 plt.errorbar(valid_threads, c2, yerr=e2, fmt="s-", label=LABEL_BAD_UARCH, color=C2_COLOR, capsize=5)
            
            if show_mem:
                 plt.errorbar(valid_threads, c3, yerr=e3, fmt="^-", label=LABEL_BAD_MEM, color=C3_COLOR, capsize=5)
            
            if show_both:
                 plt.errorbar(valid_threads, c4, yerr=e4, fmt="d-", label=LABEL_BAD_BOTH, color=C4_COLOR, capsize=5)

            if show_labels:
                for i, x_val in enumerate(valid_threads):
                    good_val = c1[i]
                    if good_val <= 0: continue

                    to_label = []
                    if show_uarch: to_label.append((c2[i], C2_COLOR))
                    if show_mem: to_label.append((c3[i], C3_COLOR))
                    if show_both: to_label.append((c4[i], C4_COLOR))

                    to_label.sort(key=lambda x: x[0])
                    
                    for idx, (val, col) in enumerate(to_label):
                        ratio = val / good_val
                        label_text = f"{ratio:.1f}x"
                        
                        plt.annotate(
                            label_text,
                            (x_val, val),
                            textcoords="offset points",
                            xytext=(0, 5),
                            ha="center",
                            fontsize=12,
                            color=col,
                            fontweight="bold",
                            bbox=dict(boxstyle="round,pad=0.1", fc="white", alpha=0.6, edgecolor="none")
                        )

            plt.xlabel("Número de Threads", fontsize=12)
            plt.ylabel("Tempo (s)", fontsize=12)
            plt.title(f"Tempo de Execução vs Threads ({mode_names_pt.get(target_mode, target_mode)})", fontsize=14)
            plt.legend(fontsize=12)
            plt.grid(True, alpha=0.3)
            plt.xticks(valid_threads)
            
            plt.tight_layout(pad=0.1)
            
            filename = f"results/plots/time_vs_threads_mode{target_mode}{suffix}.pdf"
            plt.savefig(filename)
            plt.close()

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate performance plots.")
    parser.add_argument("--plots", nargs="+", type=int, help="List of plot numbers to generate (1-based index). If omitted, all plots are generated.")
    parser.add_argument("--threads", nargs="+", type=int, help="List of thread counts to generate individual plots for. If omitted, all thread counts are processed.")
    args = parser.parse_args()

    # Determine which plots to generate
    if args.plots:
        selected_plot_indices = args.plots
        print(f"Filtrando gráficos (índices): {selected_plot_indices}")
    else:
        # Generate all 1..N
        selected_plot_indices = list(range(1, len(metrics) + 1))

    # Determine which threads to process
    available_threads = sorted(data.keys())
    if args.threads:
        selected_threads = [t for t in args.threads if t in data]
        print(f"Filtrando threads: {selected_threads}")
    else:
        selected_threads = available_threads

    print("Iniciando geração de gráficos...")
    
    # Sequential execution as requested
    for t in selected_threads:
        if t in data:
             generate_thread_plots(t, data[t], selected_plot_indices)
        
    print("Geração de gráficos por thread concluída.")
    
    # Generate Time vs Threads plots
    generate_time_vs_threads_plots(data)
    
    print("Todos os gráficos foram gerados!")