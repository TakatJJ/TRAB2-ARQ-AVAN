import os
import re
import matplotlib.pyplot as plt
import numpy as np
import glob

# Ensure plots directory exists
os.makedirs('results/plots', exist_ok=True)

# Threads to analyze
threads = [2, 3, 4]

# Data structure
data = {'good': {'time': {}, 'energy': {}, 'cache_miss_rate': {}, 'instructions': {}, 'time_std': {}, 'energy_err': {}, 'instructions_err': {}},
        'bad': {'time': {}, 'energy': {}, 'cache_miss_rate': {}, 'instructions': {}, 'time_std': {}, 'energy_err': {}, 'instructions_err': {}}}

# Parse data from files
data = {}
files = glob.glob('results/raw/*_results_*.txt')
for file in files:
    match = re.match(r'(good|bad)_results_(cache|energy)_(\d+)_threads_(\d+)_executions_mode(\d+)\.txt', os.path.basename(file))
    if match:
        coherency, type_, threads_str, executions_str, mode_str = match.groups()
        threads = int(threads_str)
        executions = int(executions_str)
        mode = int(mode_str)
        key = (coherency, threads, executions, mode)
        if key not in data:
            data[key] = {}
        with open(file, 'r') as f:
            content = f.read()
        if type_ == 'cache':
            # parse time, cache, instructions
            times = [float(x) for x in re.findall(r'Time for .* coherency.*: ([\d.]+) ms', content)]
            avg_time = sum(times) / len(times) if times else 0
            time_std = np.std(times) if times else 0
            
            cache_refs_match = re.search(r'(\d+(?:,\d+)*)\s+cache-references.*?(\+-.*?%)', content, re.DOTALL)
            if cache_refs_match:
                cache_refs = int(cache_refs_match.group(1).replace(',', ''))
                pct_str = cache_refs_match.group(2)
                pct = float(re.search(r'(\d+(?:\.\d+)?)', pct_str).group(1))
                cache_refs_err = cache_refs * (pct / 100)
            else:
                cache_refs = 0
                cache_refs_err = 0
            
            cache_misses_match = re.search(r'(\d+(?:,\d+)*)\s+cache-misses.*?(\+-.*?%)', content, re.DOTALL)
            if cache_misses_match:
                cache_misses = int(cache_misses_match.group(1).replace(',', ''))
                pct_str = cache_misses_match.group(2)
                pct = float(re.search(r'(\d+(?:\.\d+)?)', pct_str).group(1))
                cache_misses_err = cache_misses * (pct / 100)
            else:
                cache_misses = 0
                cache_misses_err = 0
            
            miss_rate = (cache_misses / cache_refs * 100) if cache_refs else 0
            
            instructions_match = re.search(r'(\d+(?:,\d+)*)\s+instructions.*?(\+-.*?%)', content, re.DOTALL)
            if instructions_match:
                instructions = int(instructions_match.group(1).replace(',', ''))
                pct_str = instructions_match.group(2)
                pct = float(re.search(r'(\d+(?:\.\d+)?)', pct_str).group(1))
                instructions_err = instructions * (pct / 100)
            else:
                instructions = 0
                instructions_err = 0
            
            data[key]['time'] = avg_time
            data[key]['time_std'] = time_std
            data[key]['cache_miss_rate'] = miss_rate
            data[key]['instructions'] = instructions
            data[key]['instructions_err'] = instructions_err
        elif type_ == 'energy':
            energy_match = re.search(r'(\d+(?:\.\d+)?) Joules.*?(\+-.*?%)', content, re.DOTALL)
            if energy_match:
                energy = float(energy_match.group(1))
                pct_str = energy_match.group(2)
                pct = float(re.search(r'(\d+(?:\.\d+)?)', pct_str).group(1))
                energy_err = energy * (pct / 100)
            else:
                energy = 0
                energy_err = 0
            data[key]['energy'] = energy
            data[key]['energy_err'] = energy_err

# Get all executions and threads
all_executions = sorted(set(k[2] for k in data.keys()))
all_threads = sorted(set(k[1] for k in data.keys()))

# For main plots, use the largest execution count
main_executions = max(all_executions)
main_threads = sorted(set(k[1] for k in data.keys() if k[2] == main_executions))

# Restructure data for main plots (using mode 0 as default)
main_data = {'good': {'time': {}, 'energy': {}, 'cache_miss_rate': {}, 'instructions': {}, 'time_std': {}, 'energy_err': {}, 'instructions_err': {}},
             'bad': {'time': {}, 'energy': {}, 'cache_miss_rate': {}, 'instructions': {}, 'time_std': {}, 'energy_err': {}, 'instructions_err': {}}}

for coherency in ['good', 'bad']:
    for t in main_threads:
        key = (coherency, t, main_executions, 0)
        if key in data:
            for metric in main_data[coherency]:
                main_data[coherency][metric][t] = data[key].get(metric, 0)

# Plot 1: Comparison for each thread count
for t in main_threads:
    fig, axs = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(f'Results for {main_executions} Executions', fontsize=16)
    
    metrics = ['time', 'energy', 'cache_miss_rate', 'instructions']
    titles = ['Execution Time', 'Energy Consumption', 'Cache Miss Rate', 'Instructions Executed']
    ylabels = ['Time (ms)', 'Energy (Joules)', 'Miss Rate (%)', 'Instructions']
    
    for i, (metric, title, ylabel) in enumerate(zip(metrics, titles, ylabels)):
        good_val = main_data['good'][metric][t]
        bad_val = main_data['bad'][metric][t]
        times = bad_val / good_val if good_val != 0 else 0
        
        if metric == 'time':
            yerr = [main_data['good']['time_std'][t], main_data['bad']['time_std'][t]]
        elif metric == 'energy':
            yerr = [main_data['good']['energy_err'][t], main_data['bad']['energy_err'][t]]
        elif metric == 'instructions':
            yerr = [main_data['good']['instructions_err'][t], main_data['bad']['instructions_err'][t]]
        else:
            yerr = None  # For cache_miss_rate, no error for now
        
        axs.flat[i].bar(['Good', 'Bad'], [good_val, bad_val], yerr=yerr, color=['green', 'red'], capsize=5)
        axs.flat[i].set_title(f'{title} for {t} Threads')
        axs.flat[i].set_ylabel(ylabel)
        # Add value labels on top of bars
        for j, (label, val) in enumerate(zip(['Good', 'Bad'], [good_val, bad_val])):
            if metric == 'instructions':
                text = f'{val:.0f}'
            else:
                text = f'{val:.2f}'
            axs.flat[i].text(j, val, text, ha='center', va='bottom', fontsize=9)
        axs.flat[i].text(0.5, -0.1, f'Bad/Good: {times:.2f}x', transform=axs.flat[i].transAxes, ha='center', va='top', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(f'results/plots/comparison_{t}_threads.png')
    plt.close()  # Close to avoid display issues

# Plot 2: Scalability - Time and Energy vs Threads
fig, axs = plt.subplots(1, 2, figsize=(12, 5))

# Execution Time vs Threads
for coherency in ['good', 'bad']:
    color = 'green' if coherency == 'good' else 'red'
    axs[0].plot(main_threads, [main_data[coherency]['time'][t] for t in main_threads], marker='o', color=color, label=coherency.capitalize() + ' Coherency')
axs[0].set_xlabel('Number of Threads')
axs[0].set_ylabel('Execution Time (ms)')
axs[0].set_title(f'Execution Time vs Number of Threads\n(Default, {main_executions} Executions)')
axs[0].set_xticks(main_threads)
axs[0].legend()
axs[0].grid(True)

# Energy vs Threads
for coherency in ['good', 'bad']:
    color = 'green' if coherency == 'good' else 'red'
    axs[1].plot(main_threads, [main_data[coherency]['energy'][t] for t in main_threads], marker='o', color=color, label=coherency.capitalize() + ' Coherency')
axs[1].set_xlabel('Number of Threads')
axs[1].set_ylabel('Energy (Joules)')
axs[1].set_title(f'Energy Consumption vs Number of Threads\n(Default, {main_executions} Executions)')
axs[1].set_xticks(main_threads)
axs[1].legend()
axs[1].grid(True)

plt.tight_layout()
plt.savefig('results/plots/scalability.png')
plt.close()

print("Plots generated successfully. Check the 'results/plots/' directory.")

# Compute average across threads
avg_data = {'good': {}, 'bad': {}}
for coherency in ['good', 'bad']:
    for metric in ['time', 'energy', 'cache_miss_rate', 'instructions']:
        values = [main_data[coherency][metric][t] for t in main_threads]
        avg_data[coherency][metric] = sum(values) / len(values)

# Plot 3: Average comparison across all threads
fig, axs = plt.subplots(2, 2, figsize=(12, 8))

metrics = ['time', 'energy', 'cache_miss_rate', 'instructions']
titles = ['Average Execution Time', 'Average Energy Consumption', 'Average Cache Miss Rate', 'Average Instructions Executed']
ylabels = ['Time (ms)', 'Energy (Joules)', 'Miss Rate (%)', 'Instructions']

for i, (metric, title, ylabel) in enumerate(zip(metrics, titles, ylabels)):
    good_val = avg_data['good'][metric]
    bad_val = avg_data['bad'][metric]
    times = bad_val / good_val if good_val != 0 else 0
    
    axs.flat[i].bar(['Good', 'Bad'], [good_val, bad_val], color=['green', 'red'])
    axs.flat[i].set_title(title)
    axs.flat[i].set_ylabel(ylabel)
    # Add value labels on top of bars
    for j, (label, val) in enumerate(zip(['Good', 'Bad'], [good_val, bad_val])):
        if metric == 'instructions':
            text = f'{val:.0f}'
        else:
            text = f'{val:.2f}'
        axs.flat[i].text(j, val, text, ha='center', va='bottom', fontsize=9)
    axs.flat[i].text(0.5, -0.1, f'Bad/Good: {times:.2f}x', transform=axs.flat[i].transAxes, ha='center', va='top', fontsize=10)

plt.tight_layout()
plt.savefig('results/plots/average_comparison.png')
plt.close()

print("Average comparison plot added.")

# Plot 4: Time vs Executions combined
fig, ax = plt.subplots(figsize=(8, 6))
markers = ['o', 's', '^', 'D', 'v', 'p']  # Different markers for threads
colors_good = ['darkgreen', 'green', 'lightgreen']  # Shades of green
colors_bad = ['darkred', 'red', 'lightcoral']  # Shades of red

for i, coherency in enumerate(['good', 'bad']):
    color_list = colors_good if coherency == 'good' else colors_bad
    for j, t in enumerate(all_threads):
        execs = sorted([k[2] for k in data.keys() if k[0] == coherency and k[1] == t])
        if len(execs) > 1:  # Only plot if multiple executions
            times = [data[(coherency, t, e, 0)]['time'] for e in execs]
            color = color_list[j % len(color_list)]
            marker = markers[j % len(markers)]
            label = f'{coherency.capitalize()} {t} threads'
            ax.plot(execs, times, marker=marker, color=color, label=label, linestyle='-')

ax.set_xlabel('Number of Executions')
ax.set_ylabel('Execution Time (ms)')
ax.set_title('Execution Time vs Number of Executions\n(Default)')
ax.legend()
ax.grid(True)

plt.tight_layout()
plt.savefig('results/plots/time_vs_executions.png')
plt.close()

print("Time vs executions plot added.")

# Plot for modes with 2 threads
threads_for_modes = 2
modes = [0, 1, 2, 3]
mode_names = ['Default', 'Same Core', 'Same CCD', 'Different CCDs']

# Restructure data for modes
modes_data = {'good': {}, 'bad': {}}
for coherency in ['good', 'bad']:
    modes_data[coherency] = {mode: {} for mode in modes}
    for mode in modes:
        key = (coherency, threads_for_modes, main_executions, mode)
        if key in data:
            modes_data[coherency][mode] = data[key]

# Plot comparison for each mode
fig, axs = plt.subplots(2, 2, figsize=(12, 8))
fig.suptitle(f'Results for {threads_for_modes} Threads Across Modes ({main_executions} Executions)', fontsize=16)

metrics = ['time', 'energy', 'cache_miss_rate', 'instructions']
titles = ['Execution Time', 'Energy Consumption', 'Cache Miss Rate', 'Instructions Executed']
ylabels = ['Time (ms)', 'Energy (Joules)', 'Miss Rate (%)', 'Instructions']
lower_better = [True, True, True, False]  # For time, energy, miss_rate lower better; instructions higher better

x = np.arange(len(modes))
width = 0.35

for i, (metric, title, ylabel, lb) in enumerate(zip(metrics, titles, ylabels, lower_better)):
    good_vals = [modes_data['good'][mode].get(metric, 0) for mode in modes]
    bad_vals = [modes_data['bad'][mode].get(metric, 0) for mode in modes]
    good_err = [modes_data['good'][mode].get(f'{metric}_err' if metric != 'time' else 'time_std', 0) for mode in modes]
    bad_err = [modes_data['bad'][mode].get(f'{metric}_err' if metric != 'time' else 'time_std', 0) for mode in modes]
    
    axs.flat[i].bar(x - width/2, good_vals, width, yerr=good_err, color='green', capsize=5, label='Good Coherency')
    axs.flat[i].bar(x + width/2, bad_vals, width, yerr=bad_err, color='red', capsize=5, label='Bad Coherency')
    
    axs.flat[i].set_title(title)
    axs.flat[i].set_ylabel(ylabel)
    axs.flat[i].set_xticks(x)
    axs.flat[i].set_xticklabels(mode_names)
    axs.flat[i].legend()
    
    # Add value labels on top of bars
    for j, mode in enumerate(modes):
        good_val = good_vals[j]
        bad_val = bad_vals[j]
        if metric == 'instructions':
            good_text = f'{good_val:.0f}'
            bad_text = f'{bad_val:.0f}'
        else:
            good_text = f'{good_val:.2f}'
            bad_text = f'{bad_val:.2f}'
        axs.flat[i].text(j - width/2, good_val, good_text, ha='center', va='bottom', fontsize=8)
        axs.flat[i].text(j + width/2, bad_val, bad_text, ha='center', va='bottom', fontsize=8)
    
    # Calculate best and worst for good and bad
    if lb:
        good_best_idx = good_vals.index(min(good_vals))
        good_worst_idx = good_vals.index(max(good_vals))
        bad_best_idx = bad_vals.index(min(bad_vals))
        bad_worst_idx = bad_vals.index(max(bad_vals))
    else:
        good_best_idx = good_vals.index(max(good_vals))
        good_worst_idx = good_vals.index(min(good_vals))
        bad_best_idx = bad_vals.index(max(bad_vals))
        bad_worst_idx = bad_vals.index(min(bad_vals))
    
    good_ratio = good_vals[good_worst_idx] / good_vals[good_best_idx] if good_vals[good_best_idx] != 0 else 0
    bad_ratio = bad_vals[bad_worst_idx] / bad_vals[bad_best_idx] if bad_vals[bad_best_idx] != 0 else 0
    
    good_best_mode = mode_names[good_best_idx]
    good_worst_mode = mode_names[good_worst_idx]
    bad_best_mode = mode_names[bad_best_idx]
    bad_worst_mode = mode_names[bad_worst_idx]
    
    # Overall best and worst
    all_vals = good_vals + bad_vals
    if lb:
        overall_best = min(all_vals)
        overall_worst = max(all_vals)
    else:
        overall_best = max(all_vals)
        overall_worst = min(all_vals)
    overall_ratio = overall_worst / overall_best if overall_best != 0 else 0
    
    ratio_text = f'Good: {good_best_mode} / {good_worst_mode} = {good_ratio:.2f}x\nBad: {bad_best_mode} / {bad_worst_mode} = {bad_ratio:.2f}x\nOverall: Best / Worst = {overall_ratio:.2f}x'
    axs.flat[i].text(0.5, -0.25, ratio_text, transform=axs.flat[i].transAxes, ha='center', va='top', fontsize=8)

plt.tight_layout()
plt.savefig('results/plots/modes_comparison_2_threads.png')
plt.close()

print("Modes comparison plot for 2 threads added.")

# Plot for modes with 3 threads
threads_for_modes = 3
modes = [0, 2, 3]
mode_names = ['Default', 'Same CCD', 'Different CCDs']

# Restructure data for modes
modes_data = {'good': {}, 'bad': {}}
for coherency in ['good', 'bad']:
    modes_data[coherency] = {mode: {} for mode in modes}
    for mode in modes:
        key = (coherency, threads_for_modes, main_executions, mode)
        if key in data:
            modes_data[coherency][mode] = data[key]

# Plot comparison for each mode
fig, axs = plt.subplots(2, 2, figsize=(12, 8))
fig.suptitle(f'Results for {threads_for_modes} Threads Across Modes ({main_executions} Executions)', fontsize=16)

metrics = ['time', 'energy', 'cache_miss_rate', 'instructions']
titles = ['Execution Time', 'Energy Consumption', 'Cache Miss Rate', 'Instructions Executed']
ylabels = ['Time (ms)', 'Energy (Joules)', 'Miss Rate (%)', 'Instructions']
lower_better = [True, True, True, False]  # For time, energy, miss_rate lower better; instructions higher better

x = np.arange(len(modes))
width = 0.35

for i, (metric, title, ylabel, lb) in enumerate(zip(metrics, titles, ylabels, lower_better)):
    good_vals = [modes_data['good'][mode].get(metric, 0) for mode in modes]
    bad_vals = [modes_data['bad'][mode].get(metric, 0) for mode in modes]
    good_err = [modes_data['good'][mode].get(f'{metric}_err' if metric != 'time' else 'time_std', 0) for mode in modes]
    bad_err = [modes_data['bad'][mode].get(f'{metric}_err' if metric != 'time' else 'time_std', 0) for mode in modes]
    
    axs.flat[i].bar(x - width/2, good_vals, width, yerr=good_err, color='green', capsize=5, label='Good Coherency')
    axs.flat[i].bar(x + width/2, bad_vals, width, yerr=bad_err, color='red', capsize=5, label='Bad Coherency')
    
    axs.flat[i].set_title(title)
    axs.flat[i].set_ylabel(ylabel)
    axs.flat[i].set_xticks(x)
    axs.flat[i].set_xticklabels(mode_names)
    axs.flat[i].legend()
    
    # Add value labels on top of bars
    for j, mode in enumerate(modes):
        good_val = good_vals[j]
        bad_val = bad_vals[j]
        if metric == 'instructions':
            good_text = f'{good_val:.0f}'
            bad_text = f'{bad_val:.0f}'
        else:
            good_text = f'{good_val:.2f}'
            bad_text = f'{bad_val:.2f}'
        axs.flat[i].text(j - width/2, good_val, good_text, ha='center', va='bottom', fontsize=8)
        axs.flat[i].text(j + width/2, bad_val, bad_text, ha='center', va='bottom', fontsize=8)
    
    # Calculate best and worst for good and bad
    if lb:
        good_best_idx = good_vals.index(min(good_vals))
        good_worst_idx = good_vals.index(max(good_vals))
        bad_best_idx = bad_vals.index(min(bad_vals))
        bad_worst_idx = bad_vals.index(max(bad_vals))
    else:
        good_best_idx = good_vals.index(max(good_vals))
        good_worst_idx = good_vals.index(min(good_vals))
        bad_best_idx = bad_vals.index(max(bad_vals))
        bad_worst_idx = bad_vals.index(min(bad_vals))
    
    good_ratio = good_vals[good_worst_idx] / good_vals[good_best_idx] if good_vals[good_best_idx] != 0 else 0
    bad_ratio = bad_vals[bad_worst_idx] / bad_vals[bad_best_idx] if bad_vals[bad_best_idx] != 0 else 0
    
    good_best_mode = mode_names[good_best_idx]
    good_worst_mode = mode_names[good_worst_idx]
    bad_best_mode = mode_names[bad_best_idx]
    bad_worst_mode = mode_names[bad_worst_idx]
    
    # Overall best and worst
    all_vals = good_vals + bad_vals
    if lb:
        overall_best = min(all_vals)
        overall_worst = max(all_vals)
    else:
        overall_best = max(all_vals)
        overall_worst = min(all_vals)
    overall_ratio = overall_worst / overall_best if overall_best != 0 else 0
    
    ratio_text = f'Good: {good_best_mode} / {good_worst_mode} = {good_ratio:.2f}x\nBad: {bad_best_mode} / {bad_worst_mode} = {bad_ratio:.2f}x\nOverall: Best / Worst = {overall_ratio:.2f}x'
    axs.flat[i].text(0.5, -0.25, ratio_text, transform=axs.flat[i].transAxes, ha='center', va='top', fontsize=8)

plt.tight_layout()
plt.savefig(f'results/plots/modes_comparison_{threads_for_modes}_threads.png')
plt.close()

print(f"Modes comparison plot for {threads_for_modes} threads added.")

# Plot for modes with 4 threads
threads_for_modes = 4
modes = [0, 2, 3]
mode_names = ['Default', 'Same CCD', 'Different CCDs']

# Restructure data for modes
modes_data = {'good': {}, 'bad': {}}
for coherency in ['good', 'bad']:
    modes_data[coherency] = {mode: {} for mode in modes}
    for mode in modes:
        key = (coherency, threads_for_modes, main_executions, mode)
        if key in data:
            modes_data[coherency][mode] = data[key]

# Plot comparison for each mode
fig, axs = plt.subplots(2, 2, figsize=(12, 8))
fig.suptitle(f'Results for {threads_for_modes} Threads Across Modes ({main_executions} Executions)', fontsize=16)

for i, (metric, title, ylabel, lb) in enumerate(zip(metrics, titles, ylabels, lower_better)):
    good_vals = [modes_data['good'][mode].get(metric, 0) for mode in modes]
    bad_vals = [modes_data['bad'][mode].get(metric, 0) for mode in modes]
    good_err = [modes_data['good'][mode].get(f'{metric}_err' if metric != 'time' else 'time_std', 0) for mode in modes]
    bad_err = [modes_data['bad'][mode].get(f'{metric}_err' if metric != 'time' else 'time_std', 0) for mode in modes]
    
    axs.flat[i].bar(x - width/2, good_vals, width, yerr=good_err, color='green', capsize=5, label='Good Coherency')
    axs.flat[i].bar(x + width/2, bad_vals, width, yerr=bad_err, color='red', capsize=5, label='Bad Coherency')
    
    axs.flat[i].set_title(title)
    axs.flat[i].set_ylabel(ylabel)
    axs.flat[i].set_xticks(x)
    axs.flat[i].set_xticklabels(mode_names)
    axs.flat[i].legend()
    
    # Add value labels on top of bars
    for j, mode in enumerate(modes):
        good_val = good_vals[j]
        bad_val = bad_vals[j]
        if metric == 'instructions':
            good_text = f'{good_val:.0f}'
            bad_text = f'{bad_val:.0f}'
        else:
            good_text = f'{good_val:.2f}'
            bad_text = f'{bad_val:.2f}'
        axs.flat[i].text(j - width/2, good_val, good_text, ha='center', va='bottom', fontsize=8)
        axs.flat[i].text(j + width/2, bad_val, bad_text, ha='center', va='bottom', fontsize=8)
    
    # Calculate best and worst for good and bad
    if lb:
        good_best_idx = good_vals.index(min(good_vals))
        good_worst_idx = good_vals.index(max(good_vals))
        bad_best_idx = bad_vals.index(min(bad_vals))
        bad_worst_idx = bad_vals.index(max(bad_vals))
    else:
        good_best_idx = good_vals.index(max(good_vals))
        good_worst_idx = good_vals.index(min(good_vals))
        bad_best_idx = bad_vals.index(max(bad_vals))
        bad_worst_idx = bad_vals.index(min(bad_vals))
    
    good_ratio = good_vals[good_worst_idx] / good_vals[good_best_idx] if good_vals[good_best_idx] != 0 else 0
    bad_ratio = bad_vals[bad_worst_idx] / bad_vals[bad_best_idx] if bad_vals[bad_best_idx] != 0 else 0
    
    good_best_mode = mode_names[good_best_idx]
    good_worst_mode = mode_names[good_worst_idx]
    bad_best_mode = mode_names[bad_best_idx]
    bad_worst_mode = mode_names[bad_worst_idx]
    
    # Overall best and worst
    all_vals = good_vals + bad_vals
    if lb:
        overall_best = min(all_vals)
        overall_worst = max(all_vals)
    else:
        overall_best = max(all_vals)
        overall_worst = min(all_vals)
    overall_ratio = overall_worst / overall_best if overall_best != 0 else 0
    
    ratio_text = f'Good: {good_best_mode} / {good_worst_mode} = {good_ratio:.2f}x\nBad: {bad_best_mode} / {bad_worst_mode} = {bad_ratio:.2f}x\nOverall: Best / Worst = {overall_ratio:.2f}x'
    axs.flat[i].text(0.5, -0.25, ratio_text, transform=axs.flat[i].transAxes, ha='center', va='top', fontsize=8)

plt.tight_layout()
plt.savefig(f'results/plots/modes_comparison_{threads_for_modes}_threads.png')
plt.close()

print(f"Modes comparison plot for {threads_for_modes} threads added.")