import os
import glob
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

# Path to the raw results folder
results_dir = 'results/raw'

# Color palette - pastel green and red tones
GOOD_COLOR = '#21674f' 
BAD_COLOR = '#CC6666'  

# Color gradients for time_vs_executions graphs
GOOD_COLORS = ['#21674f', '#3f907a', '#75b9a0', '#b7dbbf']  # Light to medium green pastels
BAD_COLORS = ['#CC6666', '#D17A7A', '#D98F8F', '#E3A3A3']   # Light to medium red/pink pastels

# Metrics to plot
metrics = ['time', 'energy', 'remote_cache_fills',
           'l1_accesses', 'l1_miss_rate',
           'l2_accesses', 'l2_miss_rate',
           'l3_accesses', 'l3_miss_rate']

# Mode names mapping
mode_names = {
    0: 'Default',
    1: 'Same core',
    2: 'Same CCD',
    3: 'Different CCDs'
}

# Units for each metric
metric_units = {
    'time': 'seconds',
    'energy': 'joules',
    'remote_cache_fills': 'fills',
    'l1_accesses': 'accesses',
    'l1_miss_rate': '%',
    'l2_accesses': 'accesses',
    'l2_miss_rate': '%',
    'l3_accesses': 'accesses',
    'l3_miss_rate': '%'
}

# Metric titles (custom names for display)
metric_titles = {
    'time': 'Time',
    'energy': 'Energy',
    'remote_cache_fills': 'Demand/Remote Cache Fills',
    'l1_accesses': 'L1 Cache Accesses',
    'l1_miss_rate': 'L1 Cache Miss Rate',
    'l2_accesses': 'L2 Cache Accesses',
    'l2_miss_rate': 'L2 Cache Miss Rate',
    'l3_accesses': 'L3 Cache Accesses',
    'l3_miss_rate': 'L3 Cache Miss Rate'
}

# Function to parse a file based on metric
def parse_file(filepath, metric):
    with open(filepath, 'r') as f:
        lines = f.readlines()
    if metric in ['time', 'energy']:
        # Each line is a float
        return [float(line.strip()) for line in lines if line.strip()]
    elif metric == 'perf_cache':
        # Skip header, each line has 4 comma-separated values: remote_fills,demand_remote_fills,conflicts,cache_misses
        data = []
        for line in lines[1:]:  # Skip header
            if line.strip():
                values = [int(x.strip()) if x.strip() != 'NaN' else 0 for x in line.split(',')]
                data.append(values)
        return data
    elif metric == 'perf_l1':
        # Skip header, each line has 2 comma-separated values: l1_fills,l1_l2_hits
        data = []
        for line in lines[1:]:  # Skip header
            if line.strip():
                values = [int(x.strip()) if x.strip() != 'NaN' else 0 for x in line.split(',')]
                data.append(values)
        return data
    elif metric == 'perf_l2':
        # Skip header, each line has 3 comma-separated values: l2_all,l2_hits,l2_misses
        data = []
        for line in lines[1:]:  # Skip header
            if line.strip():
                values = [int(x.strip()) if x.strip() != 'NaN' else 0 for x in line.split(',')]
                data.append(values)
        return data
    elif metric == 'perf_l3':
        # Skip header, each line has 2 comma-separated values: l3_accesses,l3_misses
        data = []
        for line in lines[1:]:  # Skip header
            if line.strip():
                values = [int(x.strip()) if x.strip() != 'NaN' else 0 for x in line.split(',')]
                data.append(values)
        return data
    return []

# Collect all data
data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

# Get all txt files
files = glob.glob(os.path.join(results_dir, '*.txt'))

for file in files:
    filename = os.path.basename(file)
    parts = filename.split('_')
    if len(parts) < 5:
        continue
    
    # Handle perf_* files
    if parts[0] == 'perf' and len(parts) > 1:
        if parts[1] == 'cache':
            metric = 'perf_cache'
            thread_idx = 2
        elif parts[1] == 'l1':
            metric = 'perf_l1'
            thread_idx = 2
        elif parts[1] == 'l2':
            metric = 'perf_l2'
            thread_idx = 2
        elif parts[1] == 'l3':
            metric = 'perf_l3'
            thread_idx = 2
        else:
            continue
    else:
        metric = parts[0]
        thread_idx = 1
    
    if metric not in ['time', 'energy', 'perf_cache', 'perf_l1', 'perf_l2', 'perf_l3']:
        continue
    
    thread = int(parts[thread_idx])
    size = int(parts[thread_idx + 1])
    mode = int(parts[thread_idx + 2][4:])  # modeX -> X
    goodbad = parts[thread_idx + 3].split('.')[0]  # good or bad
    
    parsed = parse_file(file, metric)
    if metric == 'perf_cache':
        # For each run, extract the perf cache metrics
        for run in parsed:
            remote_fills, demand_remote_fills, conflicts, cache_misses = run
            # Use demand_remote_fills as the main remote cache fills metric
            data[thread][mode][goodbad]['remote_cache_fills'].append(demand_remote_fills)
            data[thread][mode][goodbad]['_cache_misses_raw'].append(cache_misses)
            data[thread][mode][goodbad]['_cache_references_raw'].append(cache_misses)  # Will be updated with actual references
    elif metric == 'perf_l1':
        # For each run, extract L1 metrics
        for run in parsed:
            l1_fills, l1_l2_hits = run
            data[thread][mode][goodbad]['l1_fills'].append(l1_fills)
            data[thread][mode][goodbad]['l1_l2_hits'].append(l1_l2_hits)
    elif metric == 'perf_l2':
        # For each run, extract L2 metrics
        for run in parsed:
            l2_requests, l2_hits, l2_misses = run
            data[thread][mode][goodbad]['l2_requests'].append(l2_requests)
            data[thread][mode][goodbad]['l2_hits'].append(l2_hits)
            data[thread][mode][goodbad]['l2_misses'].append(l2_misses)
    elif metric == 'perf_l3':
        # For each run, extract L3 metrics
        for run in parsed:
            l3_accesses, l3_misses = run
            data[thread][mode][goodbad]['l3_accesses'].append(l3_accesses)
            data[thread][mode][goodbad]['l3_misses'].append(l3_misses)
    else:
        data[thread][mode][goodbad][metric].extend(parsed)

# Calculate cache access counts and miss rates for L1, L2, L3
for thread in data:
    for mode in data[thread]:
        for goodbad in data[thread][mode]:
            # L1: accesses = l1_fills (all L1 misses are accesses to L2)
            # L1 miss rate = (l1_fills - l1_l2_hits) / l1_fills * 100
            if 'l1_fills' in data[thread][mode][goodbad]:
                l1_fills = data[thread][mode][goodbad]['l1_fills']
                l1_l2_hits = data[thread][mode][goodbad].get('l1_l2_hits', [0] * len(l1_fills))
                
                data[thread][mode][goodbad]['l1_accesses'] = l1_fills
                
                l1_miss_rates = []
                for i in range(len(l1_fills)):
                    if l1_fills[i] > 0:
                        # L1 misses that didn't hit in L2 = l1_fills - l1_l2_hits
                        l1_misses = l1_fills[i] - l1_l2_hits[i]
                        miss_rate = (l1_misses / l1_fills[i]) * 100
                        l1_miss_rates.append(miss_rate)
                    else:
                        l1_miss_rates.append(0)
                data[thread][mode][goodbad]['l1_miss_rate'] = l1_miss_rates
            
            # L2: accesses = l2_requests, miss rate = l2_misses / l2_requests * 100
            if 'l2_requests' in data[thread][mode][goodbad] and 'l2_misses' in data[thread][mode][goodbad]:
                l2_reqs = data[thread][mode][goodbad]['l2_requests']
                l2_misses = data[thread][mode][goodbad]['l2_misses']
                
                data[thread][mode][goodbad]['l2_accesses'] = l2_reqs
                
                l2_miss_rates = []
                for i in range(len(l2_reqs)):
                    if l2_reqs[i] > 0:
                        miss_rate = (l2_misses[i] / l2_reqs[i]) * 100
                        l2_miss_rates.append(miss_rate)
                    else:
                        l2_miss_rates.append(0)
                data[thread][mode][goodbad]['l2_miss_rate'] = l2_miss_rates
            
            # L3: accesses = l3_accesses, miss rate = l3_misses / l3_accesses * 100
            if 'l3_accesses' in data[thread][mode][goodbad] and 'l3_misses' in data[thread][mode][goodbad]:
                l3_accs = data[thread][mode][goodbad]['l3_accesses']
                l3_misses = data[thread][mode][goodbad]['l3_misses']
                
                l3_miss_rates = []
                for i in range(len(l3_accs)):
                    if l3_accs[i] > 0:
                        miss_rate = (l3_misses[i] / l3_accs[i]) * 100
                        l3_miss_rates.append(miss_rate)
                    else:
                        l3_miss_rates.append(0)
                data[thread][mode][goodbad]['l3_miss_rate'] = l3_miss_rates

# Now, for each thread, compute means and stds
for thread in range(1, 11):
    if thread not in data:
        continue
    
    # Get all modes for this thread
    modes = sorted(data[thread].keys())
    
    # Prepare figure - now we have 9 metrics
    # Using 3 rows x 3 columns = 9 subplots (perfect fit)
    fig, axes = plt.subplots(3, 3, figsize=(18, 15))
    axes = axes.flatten()
    
    for i, metric in enumerate(metrics):
        ax = axes[i]
        
        good_means = []
        good_stds = []
        bad_means = []
        bad_stds = []
        
        for mode in modes:
            if 'good' in data[thread][mode] and metric in data[thread][mode]['good']:
                good_values = data[thread][mode]['good'][metric]
                if len(good_values) > 1:
                    good_means.append(np.mean(good_values))
                    # Use standard error of the mean instead of standard deviation
                    good_stds.append(np.std(good_values, ddof=1) / np.sqrt(len(good_values)))
                else:
                    good_means.append(np.mean(good_values) if good_values else 0)
                    good_stds.append(0)
            else:
                good_means.append(0)
                good_stds.append(0)
            
            if 'bad' in data[thread][mode] and metric in data[thread][mode]['bad']:
                bad_values = data[thread][mode]['bad'][metric]
                if len(bad_values) > 1:
                    bad_means.append(np.mean(bad_values))
                    # Use standard error of the mean instead of standard deviation
                    bad_stds.append(np.std(bad_values, ddof=1) / np.sqrt(len(bad_values)))
                else:
                    bad_means.append(np.mean(bad_values) if bad_values else 0)
                    bad_stds.append(0)
            else:
                bad_means.append(0)
                bad_stds.append(0)
        
        x = np.arange(len(modes))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, good_means, width, label='Good', color=GOOD_COLOR, yerr=good_stds, capsize=5)
        bars2 = ax.bar(x + width/2, bad_means, width, label='Bad', color=BAD_COLOR, yerr=bad_stds, capsize=5)
        
        # Add value labels on top of bars
        for bar, value in zip(bars1, good_means):
            if value > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + bar.get_y(), 
                       f'{value:.2f}', ha='center', va='bottom', fontsize=8)
        
        for bar, value in zip(bars2, bad_means):
            if value > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + bar.get_y(), 
                       f'{value:.2f}', ha='center', va='bottom', fontsize=8)
        
        # Calculate ratios for each mode and create labels
        mode_labels = []
        ratios = []
        for idx, mode in enumerate(modes):
            mode_label = mode_names.get(mode, f'Mode {mode}')
            if good_means[idx] > 0:
                ratio = bad_means[idx] / good_means[idx]
                ratios.append(ratio)
                mode_labels.append(f'{mode_label}\n({ratio:.2f}x)')
            else:
                mode_labels.append(mode_label)
        
        ax.set_xticks(x)
        ax.set_xticklabels(mode_labels, fontsize=9)
        
        # Calculate global ratio (worst vs best)
        all_values = good_means + bad_means
        valid_values = [v for v in all_values if v > 0]
        global_ratio_text = ""
        if valid_values:
            max_val = max(valid_values)
            min_val = min(valid_values)
            if min_val > 0:
                global_ratio = max_val / min_val
                global_ratio_text = f'\nGlobal Ratio (Max/Min): {global_ratio:.2f}x'
        
        # Use custom title if available, otherwise format the metric name
        title = metric_titles.get(metric, metric.replace("_", " ").title())
        ax.set_title(f'{title} ({metric_units[metric]}){global_ratio_text}', fontsize=10)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
    
    plt.suptitle(f'Results for {thread} Thread(s)', fontsize=16, fontweight='bold')
    plt.tight_layout()
    # High resolution for cropping individual subplots without pixelation
    plt.savefig(f'results/plots/plot_thread_{thread}.png', dpi=600, bbox_inches='tight')
    plt.close()

# ============================================================================
# Additional Plot 1: Time vs Number of Threads (Mode 0, largest execution count)
# ============================================================================

# Find the largest execution count available
all_sizes = set()
for thread in data:
    for mode in data[thread]:
        for goodbad in data[thread][mode]:
            # Get the size from the file names (we need to track this)
            pass

# We need to get sizes from the files again
sizes_per_thread_mode = defaultdict(lambda: defaultdict(set))
for file in files:
    filename = os.path.basename(file)
    parts = filename.split('_')
    if len(parts) < 5:
        continue
    
    if parts[0] == 'time':
        thread = int(parts[1])
        size = int(parts[2])
        mode = int(parts[3][4:])
        sizes_per_thread_mode[thread][mode].add(size)

# Find the largest common size for mode 0
largest_size = 0
for thread in range(1, 11):
    if thread in sizes_per_thread_mode and 0 in sizes_per_thread_mode[thread]:
        sizes = sizes_per_thread_mode[thread][0]
        if sizes:
            largest_size = max(largest_size, max(sizes))

# Collect time data for mode 0 with largest size
thread_time_data = defaultdict(lambda: {'good': [], 'bad': []})
for file in files:
    filename = os.path.basename(file)
    parts = filename.split('_')
    if len(parts) < 5 or parts[0] != 'time':
        continue
    
    thread = int(parts[1])
    size = int(parts[2])
    mode = int(parts[3][4:])
    goodbad = parts[4].split('.')[0]
    
    if mode == 0 and size == largest_size:
        parsed = parse_file(file, 'time')
        thread_time_data[thread][goodbad].extend(parsed)

# Plot time vs threads
if thread_time_data:
    threads = sorted(thread_time_data.keys())
    good_means = []
    good_stds = []
    bad_means = []
    bad_stds = []
    ratios = []
    
    for t in threads:
        if 'good' in thread_time_data[t] and thread_time_data[t]['good']:
            good_vals = thread_time_data[t]['good']
            good_means.append(np.mean(good_vals))
            good_stds.append(np.std(good_vals, ddof=1) / np.sqrt(len(good_vals)))
        else:
            good_means.append(0)
            good_stds.append(0)
        
        if 'bad' in thread_time_data[t] and thread_time_data[t]['bad']:
            bad_vals = thread_time_data[t]['bad']
            bad_means.append(np.mean(bad_vals))
            bad_stds.append(np.std(bad_vals, ddof=1) / np.sqrt(len(bad_vals)))
        else:
            bad_means.append(0)
            bad_stds.append(0)
        
        # Calculate ratio
        if good_means[-1] > 0:
            ratios.append(bad_means[-1] / good_means[-1])
        else:
            ratios.append(0)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    x = np.array(threads)
    ax.errorbar(x, good_means, yerr=good_stds, label='Good', color=GOOD_COLOR, 
                marker='o', markersize=8, linewidth=2, capsize=5)
    ax.errorbar(x, bad_means, yerr=bad_stds, label='Bad', color=BAD_COLOR, 
                marker='s', markersize=8, linewidth=2, capsize=5)
    
    # Add ratio labels for each point
    for i, (t, ratio) in enumerate(zip(threads, ratios)):
        if ratio > 0:
            # Position the ratio label above the bad (red) line
            y_pos = max(bad_means[i], good_means[i]) * 1.05
            ax.text(t, y_pos, f'{ratio:.2f}x', ha='center', va='bottom', 
                   fontsize=9, fontweight='bold', color='#CC6666')
    
    ax.set_xlabel('Number of Threads', fontsize=12, fontweight='bold')
    ax.set_ylabel('Execution Time (seconds)', fontsize=12, fontweight='bold')
    mode_name = mode_names.get(0, 'Mode 0')
    ax.set_title(f'Execution Time vs Number of Threads\n({mode_name}, {largest_size} executions)', 
                fontsize=14, fontweight='bold')
    ax.set_xticks(threads)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'results/plots/time_vs_threads_mode0.png', dpi=300, bbox_inches='tight')
    plt.close()

# ============================================================================
# Additional Plot 2: Time vs Number of Executions (Mode 0, varying threads)
# ============================================================================

# Collect time data organized by size
size_time_data = defaultdict(lambda: defaultdict(lambda: {'good': [], 'bad': []}))
available_sizes = set()

for file in files:
    filename = os.path.basename(file)
    parts = filename.split('_')
    if len(parts) < 5 or parts[0] != 'time':
        continue
    
    thread = int(parts[1])
    size = int(parts[2])
    mode = int(parts[3][4:])
    goodbad = parts[4].split('.')[0]
    
    if mode == 0:  # Only mode 0
        parsed = parse_file(file, 'time')
        size_time_data[size][thread][goodbad].extend(parsed)
        available_sizes.add(size)

# Plot time vs executions for different thread counts (combined good and bad)
if size_time_data and available_sizes:
    sizes = sorted(available_sizes)
    
    # Select a few thread counts to display (2, 3, 5, 7)
    selected_threads = [t for t in [2, 3, 5, 7] if any(t in size_time_data[s] for s in sizes)]
    
    # Use the pastel color gradients defined at the top
    markers = ['o', 's', '^', 'd']
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Plot both Good and Bad on the same graph
    for idx, t in enumerate(selected_threads):
        # Good implementation
        good_means = []
        good_stds = []
        for s in sizes:
            if t in size_time_data[s] and 'good' in size_time_data[s][t]:
                vals = size_time_data[s][t]['good']
                if vals:
                    good_means.append(np.mean(vals))
                    good_stds.append(np.std(vals, ddof=1) / np.sqrt(len(vals)))
                else:
                    good_means.append(0)
                    good_stds.append(0)
            else:
                good_means.append(0)
                good_stds.append(0)
        
        if good_means:
            ax.errorbar(sizes, good_means, yerr=good_stds, label=f'{t} threads (Good)', 
                       color=GOOD_COLORS[idx % len(GOOD_COLORS)], 
                       marker=markers[idx % len(markers)],
                       markersize=8, linewidth=2, capsize=5, linestyle='-')
        
        # Bad implementation
        bad_means = []
        bad_stds = []
        for s in sizes:
            if t in size_time_data[s] and 'bad' in size_time_data[s][t]:
                vals = size_time_data[s][t]['bad']
                if vals:
                    bad_means.append(np.mean(vals))
                    bad_stds.append(np.std(vals, ddof=1) / np.sqrt(len(vals)))
                else:
                    bad_means.append(0)
                    bad_stds.append(0)
            else:
                bad_means.append(0)
                bad_stds.append(0)
        
        if bad_means:
            ax.errorbar(sizes, bad_means, yerr=bad_stds, label=f'{t} threads (Bad)', 
                       color=BAD_COLORS[idx % len(BAD_COLORS)], 
                       marker=markers[idx % len(markers)],
                       markersize=8, linewidth=2, capsize=5, linestyle='--')
    
    ax.set_xlabel('Number of Executions', fontsize=12, fontweight='bold')
    ax.set_ylabel('Execution Time (seconds)', fontsize=12, fontweight='bold')
    mode_name = mode_names.get(0, 'Mode 0')
    ax.set_title(f'Execution Time vs Number of Executions\n({mode_name})', 
                fontsize=14, fontweight='bold')
    ax.legend(fontsize=9, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.ticklabel_format(style='scientific', axis='x', scilimits=(0,0))
    
    plt.tight_layout()
    plt.savefig('results/plots/time_vs_executions_mode0.png', dpi=300, bbox_inches='tight')
    plt.close()

# ============================================================================
# Generate Time vs Threads and Time vs Executions for ALL modes (except mode 1)
# ============================================================================

# Get all available modes
all_modes = set()
for thread in sizes_per_thread_mode:
    all_modes.update(sizes_per_thread_mode[thread].keys())
all_modes = sorted(all_modes)

# For each mode, generate both graphs (skip mode 1)
for current_mode in all_modes:
    if current_mode == 1:  # Skip mode 1 (Same core)
        continue
    mode_name = mode_names.get(current_mode, f'Mode {current_mode}')
    
    # Find the largest common size for this mode
    largest_size_mode = 0
    for thread in range(1, 11):
        if thread in sizes_per_thread_mode and current_mode in sizes_per_thread_mode[thread]:
            sizes = sizes_per_thread_mode[thread][current_mode]
            if sizes:
                largest_size_mode = max(largest_size_mode, max(sizes))
    
    if largest_size_mode == 0:
        continue
    
    # ========================================================================
    # Time vs Threads for this mode
    # ========================================================================
    thread_time_data_mode = defaultdict(lambda: {'good': [], 'bad': []})
    for file in files:
        filename = os.path.basename(file)
        parts = filename.split('_')
        if len(parts) < 5 or parts[0] != 'time':
            continue
        
        thread = int(parts[1])
        size = int(parts[2])
        mode = int(parts[3][4:])
        goodbad = parts[4].split('.')[0]
        
        if mode == current_mode and size == largest_size_mode:
            parsed = parse_file(file, 'time')
            thread_time_data_mode[thread][goodbad].extend(parsed)
    
    if thread_time_data_mode:
        threads = sorted(thread_time_data_mode.keys())
        good_means = []
        good_stds = []
        bad_means = []
        bad_stds = []
        ratios = []
        
        for t in threads:
            if 'good' in thread_time_data_mode[t] and thread_time_data_mode[t]['good']:
                good_vals = thread_time_data_mode[t]['good']
                good_means.append(np.mean(good_vals))
                good_stds.append(np.std(good_vals, ddof=1) / np.sqrt(len(good_vals)))
            else:
                good_means.append(0)
                good_stds.append(0)
            
            if 'bad' in thread_time_data_mode[t] and thread_time_data_mode[t]['bad']:
                bad_vals = thread_time_data_mode[t]['bad']
                bad_means.append(np.mean(bad_vals))
                bad_stds.append(np.std(bad_vals, ddof=1) / np.sqrt(len(bad_vals)))
            else:
                bad_means.append(0)
                bad_stds.append(0)
            
            # Calculate ratio
            if good_means[-1] > 0:
                ratios.append(bad_means[-1] / good_means[-1])
            else:
                ratios.append(0)
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        x = np.array(threads)
        ax.errorbar(x, good_means, yerr=good_stds, label='Good', color=GOOD_COLOR, 
                    marker='o', markersize=8, linewidth=2, capsize=5)
        ax.errorbar(x, bad_means, yerr=bad_stds, label='Bad', color=BAD_COLOR, 
                    marker='s', markersize=8, linewidth=2, capsize=5)
        
        # Add ratio labels for each point
        for i, (t, ratio) in enumerate(zip(threads, ratios)):
            if ratio > 0:
                y_pos = max(bad_means[i], good_means[i]) * 1.05
                ax.text(t, y_pos, f'{ratio:.2f}x', ha='center', va='bottom', 
                       fontsize=9, fontweight='bold', color='#CC6666')
        
        ax.set_xlabel('Number of Threads', fontsize=12, fontweight='bold')
        ax.set_ylabel('Execution Time (seconds)', fontsize=12, fontweight='bold')
        ax.set_title(f'Execution Time vs Number of Threads\n({mode_name}, {largest_size_mode} executions)', 
                    fontsize=14, fontweight='bold')
        ax.set_xticks(threads)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'results/plots/time_vs_threads_mode{current_mode}.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    # ========================================================================
    # Time vs Executions for this mode
    # ========================================================================
    size_time_data_mode = defaultdict(lambda: defaultdict(lambda: {'good': [], 'bad': []}))
    available_sizes_mode = set()
    
    for file in files:
        filename = os.path.basename(file)
        parts = filename.split('_')
        if len(parts) < 5 or parts[0] != 'time':
            continue
        
        thread = int(parts[1])
        size = int(parts[2])
        mode = int(parts[3][4:])
        goodbad = parts[4].split('.')[0]
        
        if mode == current_mode:
            parsed = parse_file(file, 'time')
            size_time_data_mode[size][thread][goodbad].extend(parsed)
            available_sizes_mode.add(size)
    
    if size_time_data_mode and available_sizes_mode:
        sizes = sorted(available_sizes_mode)
        selected_threads = [t for t in [2, 3, 5, 7] if any(t in size_time_data_mode[s] for s in sizes)]
        
        markers = ['o', 's', '^', 'd']
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        for idx, t in enumerate(selected_threads):
            # Good implementation
            good_means = []
            good_stds = []
            for s in sizes:
                if t in size_time_data_mode[s] and 'good' in size_time_data_mode[s][t]:
                    vals = size_time_data_mode[s][t]['good']
                    if vals:
                        good_means.append(np.mean(vals))
                        good_stds.append(np.std(vals, ddof=1) / np.sqrt(len(vals)))
                    else:
                        good_means.append(0)
                        good_stds.append(0)
                else:
                    good_means.append(0)
                    good_stds.append(0)
            
            if good_means:
                ax.errorbar(sizes, good_means, yerr=good_stds, label=f'{t} threads (Good)', 
                           color=GOOD_COLORS[idx % len(GOOD_COLORS)], 
                           marker=markers[idx % len(markers)],
                           markersize=8, linewidth=2, capsize=5, linestyle='-')
            
            # Bad implementation
            bad_means = []
            bad_stds = []
            for s in sizes:
                if t in size_time_data_mode[s] and 'bad' in size_time_data_mode[s][t]:
                    vals = size_time_data_mode[s][t]['bad']
                    if vals:
                        bad_means.append(np.mean(vals))
                        bad_stds.append(np.std(vals, ddof=1) / np.sqrt(len(vals)))
                    else:
                        bad_means.append(0)
                        bad_stds.append(0)
                else:
                    bad_means.append(0)
                    bad_stds.append(0)
            
            if bad_means:
                ax.errorbar(sizes, bad_means, yerr=bad_stds, label=f'{t} threads (Bad)', 
                           color=BAD_COLORS[idx % len(BAD_COLORS)], 
                           marker=markers[idx % len(markers)],
                           markersize=8, linewidth=2, capsize=5, linestyle='--')
        
        ax.set_xlabel('Number of Executions', fontsize=12, fontweight='bold')
        ax.set_ylabel('Execution Time (seconds)', fontsize=12, fontweight='bold')
        ax.set_title(f'Execution Time vs Number of Executions\n({mode_name})', 
                    fontsize=14, fontweight='bold')
        ax.legend(fontsize=9, ncol=2)
        ax.grid(True, alpha=0.3)
        ax.ticklabel_format(style='scientific', axis='x', scilimits=(0,0))
        
        plt.tight_layout()
        plt.savefig(f'results/plots/time_vs_executions_mode{current_mode}.png', dpi=300, bbox_inches='tight')
        plt.close()

# ============================================================================
# Additional Plot: Time vs Mode Comparison
# ============================================================================

# Collect time data for each mode (using largest execution count, various threads)
mode_comparison_data = defaultdict(lambda: defaultdict(lambda: {'good': [], 'bad': []}))

# Find the largest common size across all modes
largest_common_size = 0
for thread in range(1, 11):
    if thread in sizes_per_thread_mode:
        common_sizes = None
        for mode in sizes_per_thread_mode[thread]:
            if common_sizes is None:
                common_sizes = sizes_per_thread_mode[thread][mode].copy()
            else:
                common_sizes = common_sizes.intersection(sizes_per_thread_mode[thread][mode])
        if common_sizes:
            largest_common_size = max(largest_common_size, max(common_sizes))

# Collect data for mode comparison
for file in files:
    filename = os.path.basename(file)
    parts = filename.split('_')
    if len(parts) < 5 or parts[0] != 'time':
        continue
    
    thread = int(parts[1])
    size = int(parts[2])
    mode = int(parts[3][4:])
    goodbad = parts[4].split('.')[0]
    
    if size == largest_common_size:
        parsed = parse_file(file, 'time')
        mode_comparison_data[mode][thread][goodbad].extend(parsed)

# Create comparison plots for ALL thread counts
if mode_comparison_data:
    # Get all available thread counts (1-10)
    all_thread_counts = [t for t in range(1, 11) 
                        if any(t in mode_comparison_data[m] for m in mode_comparison_data)]
    
    if all_thread_counts:
        # Create a figure with subplots for each thread count (2 rows x 5 columns for 10 threads)
        n_threads = len(all_thread_counts)
        fig, axes = plt.subplots(2, 5, figsize=(24, 10))
        axes = axes.flatten()
        
        # Collect all values to determine global y-axis scale
        all_good_values = []
        all_bad_values = []
        
        for thread_count in all_thread_counts:
            modes_with_data = sorted([m for m in mode_comparison_data 
                                     if thread_count in mode_comparison_data[m]])
            for mode in modes_with_data:
                if 'good' in mode_comparison_data[mode][thread_count]:
                    good_vals = mode_comparison_data[mode][thread_count]['good']
                    if good_vals:
                        all_good_values.append(np.mean(good_vals))
                
                if 'bad' in mode_comparison_data[mode][thread_count]:
                    bad_vals = mode_comparison_data[mode][thread_count]['bad']
                    if bad_vals:
                        all_bad_values.append(np.mean(bad_vals))
        
        # Determine global y-axis limits
        if all_good_values or all_bad_values:
            all_values = all_good_values + all_bad_values
            y_max = max(all_values) * 1.15  # Add 15% padding at top
            y_min = 0
        else:
            y_max = 1
            y_min = 0
        
        for idx, thread_count in enumerate(all_thread_counts):
            ax = axes[idx]
            
            # Get all modes that have data for this thread count
            modes_with_data = sorted([m for m in mode_comparison_data 
                                     if thread_count in mode_comparison_data[m]])
            
            if not modes_with_data:
                continue
            
            good_means = []
            good_stds = []
            bad_means = []
            bad_stds = []
            mode_labels = []
            ratios = []
            
            for mode in modes_with_data:
                mode_labels.append(mode_names.get(mode, f'Mode {mode}'))
                
                if 'good' in mode_comparison_data[mode][thread_count]:
                    good_vals = mode_comparison_data[mode][thread_count]['good']
                    if good_vals:
                        good_means.append(np.mean(good_vals))
                        good_stds.append(np.std(good_vals, ddof=1) / np.sqrt(len(good_vals)))
                    else:
                        good_means.append(0)
                        good_stds.append(0)
                else:
                    good_means.append(0)
                    good_stds.append(0)
                
                if 'bad' in mode_comparison_data[mode][thread_count]:
                    bad_vals = mode_comparison_data[mode][thread_count]['bad']
                    if bad_vals:
                        bad_means.append(np.mean(bad_vals))
                        bad_stds.append(np.std(bad_vals, ddof=1) / np.sqrt(len(bad_vals)))
                    else:
                        bad_means.append(0)
                        bad_stds.append(0)
                else:
                    bad_means.append(0)
                    bad_stds.append(0)
                
                # Calculate ratio
                if good_means[-1] > 0:
                    ratios.append(bad_means[-1] / good_means[-1])
                else:
                    ratios.append(0)
            
            x = np.arange(len(modes_with_data))
            width = 0.35
            
            bars1 = ax.bar(x - width/2, good_means, width, label='Good', color=GOOD_COLOR, 
                          yerr=good_stds, capsize=5)
            bars2 = ax.bar(x + width/2, bad_means, width, label='Bad', color=BAD_COLOR, 
                          yerr=bad_stds, capsize=5)
            
            # Add value labels on top of bars
            for bar, value in zip(bars1, good_means):
                if value > 0:
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(), 
                           f'{value:.2f}', ha='center', va='bottom', fontsize=8)
            
            for bar, value in zip(bars2, bad_means):
                if value > 0:
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(), 
                           f'{value:.2f}', ha='center', va='bottom', fontsize=8)
            
            # Add ratio labels below mode names
            mode_labels_with_ratio = []
            for i, (label, ratio) in enumerate(zip(mode_labels, ratios)):
                if ratio > 0:
                    mode_labels_with_ratio.append(f'{label}\n({ratio:.2f}x)')
                else:
                    mode_labels_with_ratio.append(label)
            
            ax.set_xticks(x)
            ax.set_xticklabels(mode_labels_with_ratio, fontsize=8)
            ax.set_ylabel('Time (s)', fontsize=9, fontweight='bold')
            ax.set_title(f'{thread_count} Thread(s)', fontsize=10, fontweight='bold')
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3, axis='y')
            
            # Set the same y-axis scale for all subplots
            ax.set_ylim(y_min, y_max)
        
        # Hide unused subplots if less than 10 thread counts
        for j in range(len(all_thread_counts), len(axes)):
            axes[j].set_visible(False)
        
        # Calculate global ratio (best/worst across all modes and threads)
        all_values_global = all_good_values + all_bad_values
        if all_values_global:
            best_value = min(all_values_global)
            worst_value = max(all_values_global)
            if best_value > 0:
                global_ratio = worst_value / best_value
                title_text = f'Execution Time Comparison Across Modes\n({largest_common_size} executions)\nGlobal Ratio (Worst/Best): {global_ratio:.2f}x'
            else:
                title_text = f'Execution Time Comparison Across Modes\n({largest_common_size} executions)'
        else:
            title_text = f'Execution Time Comparison Across Modes\n({largest_common_size} executions)'
        
        plt.suptitle(title_text, fontsize=16, fontweight='bold')
        plt.tight_layout()
        # High resolution for cropping individual subplots without pixelation
        plt.savefig('results/plots/time_vs_modes.png', dpi=600, bbox_inches='tight')
        plt.close()

print("Plots generated successfully!")