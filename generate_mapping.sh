#!/bin/bash

# Generate mapping of threads to cores and cores to CCDs using lscpu -e

# Get lscpu output (skip header)
lscpu_output=$(lscpu -e | tail -n +2)

# Create associative arrays for mapping
declare -A core_to_l3
declare -A threads_per_core

# Parse lscpu output
while read -r cpu node socket core rest; do
    # Extract L3 from the L1d:L1i:L2:L3 field (5th field in rest)
    l3=$(echo "$rest" | awk '{print $1}' | cut -d: -f4)
    core_to_l3[$core]=$l3
    threads_per_core[$core]="${threads_per_core[$core]} $cpu"
done <<< "$lscpu_output"

# Generate the mapping text
output=""

# Group by L3 (CCD)
declare -A l3_cores
for core in "${!core_to_l3[@]}"; do
    l3=${core_to_l3[$core]}
    l3_cores[$l3]="${l3_cores[$l3]} $core"
done

# Sort L3s
for l3 in $(echo "${!l3_cores[@]}" | tr ' ' '\n' | sort -n); do
    output+="CCD $l3:\n"
    # Sort cores within CCD
    for core in $(echo "${l3_cores[$l3]}" | tr ' ' '\n' | sort -n); do
        output+="  Core $core:\n"
        # Sort threads within core
        for thread in $(echo "${threads_per_core[$core]}" | tr ' ' '\n' | sort -n); do
            output+="    Thread $thread\n"
        done
    done
    output+="\n"
done

# Write to file
echo -e "$output" > thread_core_ccd_mapping.txt

echo "Mapping generated in thread_core_ccd_mapping.txt"