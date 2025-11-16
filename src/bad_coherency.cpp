#include <iostream>
#include <thread>
#include <vector>
#include <chrono>
#include <sched.h>

std::vector<int> cpus;

struct UnalignedCounter {
    volatile long long count = 0;
};

void worker_func(int id, volatile long long& counter, long long iterations) {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(cpus[id], &cpuset);
    sched_setaffinity(0, sizeof(cpu_set_t), &cpuset);

    for (long long i = 0; i < iterations; ++i) {
        counter++;
    }
}

double run_false_sharing_test(int num_threads, long long total_operations) {
    if (num_threads <= 0) return 0.0;
    
    std::vector<UnalignedCounter> bad_data(num_threads);
    long long iterations_per_thread = total_operations / num_threads;

    auto start = std::chrono::high_resolution_clock::now();
    std::vector<std::thread> threads;

    for (int i = 0; i < num_threads; ++i) {
        threads.emplace_back(worker_func, i, std::ref(bad_data[i].count), iterations_per_thread);
    }

    for (auto& t : threads) {
        t.join();
    }

    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> duration = end - start;

    return duration.count();
}

int main(int argc, char* argv[]) {
    if (argc < 3 || argc > 4) {
        std::cerr << "Usage: " << argv[0] << " <num_threads> <total_operations> [mode]" << std::endl;
        std::cerr << "Modes: 0=default, 1=same core (2 threads only), 2=same CCD different cores, 3=different CCDs" << std::endl;
        return 1;
    }

    int num_threads = std::stoi(argv[1]);
    long long total_operations = std::stoll(argv[2]);
    int mode = (argc == 4) ? std::stoi(argv[3]) : 0;

    // Define CPU mappings based on /sys topology (L3 cache sharing)
    std::vector<int> ccd0_cores = {0,1,2,3,4,5,12,13,14,15,16,17};
    std::vector<int> ccd1_cores = {6,7,8,9,10,11,18,19,20,21,22,23};

    // Set CPUs based on mode
    cpus.clear();
    if (mode == 0) {
        // Default: no specific affinity, use 0 to num_threads-1
        for (int i = 0; i < num_threads; ++i) cpus.push_back(i);
    } else if (mode == 1) {
        //if (num_threads != 2) {
        //    std::cerr << "Mode 1 only supported for 2 threads" << std::endl;
        //    return 1;
        //}
        cpus = {9, 21}; // Same core (core 9)
    } else if (mode == 2) {
        // Different cores in same CCD (CCD1)
        for (int i = 0; i < num_threads; ++i) {
            cpus.push_back(ccd1_cores[i % ccd1_cores.size()]);
        }
    } else if (mode == 3) {
        // Different CCDs
        for (int i = 0; i < num_threads; ++i) {
            if (i % 2 == 0) {
                cpus.push_back(ccd1_cores[(i / 2) % ccd1_cores.size()]);
            } else {
                cpus.push_back(ccd0_cores[(i / 2) % ccd0_cores.size()]);
            }
        }
    } else {
        std::cerr << "Invalid mode" << std::endl;
        return 1;
    }

    double time = run_false_sharing_test(num_threads, total_operations);
    std::cout << "Time for bad coherency (mode " << mode << "): " << time << " ms" << std::endl;

    return 0;
}