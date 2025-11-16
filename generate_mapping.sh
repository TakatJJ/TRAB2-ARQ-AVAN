#!/bin/bash

# Generate mapping of threads to cores and cores to CCDs using /sys topology

# Function to expand CPU list with ranges
expand_cpus() {
    local list=$1
    local expanded=""
    for item in $(echo $list | tr ',' ' '); do
        if [[ $item == *-* ]]; then
            start=${item%-*}
            end=${item#*-}
            for ((i=start; i<=end; i++)); do
                expanded="$expanded $i"
            done
        else
            expanded="$expanded $item"
        fi
    done
    echo $expanded | tr ' ' '\n' | sort -n | uniq | tr '\n' ' ' | sed 's/ $//'
}

# Get all CPUs
cpus=$(ls /sys/devices/system/cpu/ | grep '^cpu[0-9]\+$' | sed 's/cpu//' | sort -n)

# Create associative array for CPU to L3 shared CPUs
declare -A cpu_to_l3_shared

for cpu in $cpus; do
    if [ -f "/sys/devices/system/cpu/cpu$cpu/cache/index3/shared_cpu_list" ]; then
        shared=$(cat /sys/devices/system/cpu/cpu$cpu/cache/index3/shared_cpu_list)
        sorted_shared=$(expand_cpus "$shared")
        cpu_to_l3_shared[$cpu]=$sorted_shared
    fi
done

# Group CPUs by their L3 shared list (each unique shared list is a CCD)
declare -A l3_to_cpus
for cpu in "${!cpu_to_l3_shared[@]}"; do
    shared=${cpu_to_l3_shared[$cpu]}
    l3_to_cpus[$shared]="${l3_to_cpus[$shared]} $cpu"
done

# Generate the mapping text
output=""
ccd_id=0

declare -A core_to_cpus
declare -A core_id_to_cpus

for shared in "${!l3_to_cpus[@]}"; do
    ccd_cpus=${l3_to_cpus[$shared]}
    ccd_cpus=$(echo $ccd_cpus | sed 's/^ *//')
    output+="CCD $ccd_id:\n"
    
    core_to_cpus=()  # Clear the array for each CCD
    # Group CPUs within CCD by thread_siblings_list (cores)
    for cpu in $ccd_cpus; do
        if [ -f "/sys/devices/system/cpu/cpu$cpu/topology/thread_siblings_list" ]; then
            siblings=$(cat /sys/devices/system/cpu/cpu$cpu/topology/thread_siblings_list)
            sorted_siblings=$(expand_cpus "$siblings")
            core_to_cpus[$sorted_siblings]="${core_to_cpus[$sorted_siblings]} $cpu"
        fi
    done
    
    core_id_to_cpus=()  # Clear
    # Sort cores by core_id
    for core_siblings in "${!core_to_cpus[@]}"; do
        core_cpus=${core_to_cpus[$core_siblings]}
        core_cpus=$(echo $core_cpus | sed 's/^ *//')
        # Get core_id from first CPU in the group
        first_cpu=${core_cpus%% *}
        if [ -f "/sys/devices/system/cpu/cpu$first_cpu/topology/core_id" ]; then
            core_id=$(cat /sys/devices/system/cpu/cpu$first_cpu/topology/core_id)
            core_id_to_cpus[$core_id]=$core_cpus
        fi
    done
    
    for core_id in $(echo "${!core_id_to_cpus[@]}" | tr ' ' '\n' | sort -n); do
        core_cpus=${core_id_to_cpus[$core_id]}
        output+="  Core $core_id:\n"
        # Sort threads within core
        for thread in $(echo $core_cpus | tr ' ' '\n' | sort -n); do
            output+="    Thread $thread\n"
        done
    done
    output+="\n"
    ((ccd_id++))
done

# Write to file
echo -e "$output" > thread_core_ccd_mapping.txt

echo "Mapping generated in thread_core_ccd_mapping.txt"