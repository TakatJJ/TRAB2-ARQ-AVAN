#include <iostream>
#include <thread>
#include <vector>
#include <chrono>
#include <sched.h>
#include <string>

std::vector<int> cpus;

struct UnalignedCounter {
    volatile long long count = 0;
};

inline unsigned int fast_rand(unsigned int& state) {
    state = state * 1103515245 + 12345;
    return (state / 65536) % 32768;
}

void worker_func(int id, volatile long long& counter, long long iterations, bool stress_uarch) {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(cpus[id], &cpuset);
    sched_setaffinity(0, sizeof(cpu_set_t), &cpuset);

    unsigned int seed = id + 1;

    for (long long i = 0; i < iterations; ++i) {
        if (stress_uarch) {
            // Case 4: Bad Memory & Bad uArch
            // The branch depends on 'counter' (which is False Shared/Slow).
            // The CPU speculates, but can't know if it's right until 'counter' arrives.
            // When it arrives, we force a misprediction (randomness).
            // Result: Pipeline stalls waiting for memory + Wasted speculative work.
            if ((fast_rand(seed) ^ counter) & 1) {
                counter++;
            } else {
                counter++;
            }
        } else {
            // Case 3: Bad Memory Only (Predictable Branch)
            counter++;
        }
    }
}

double run_false_sharing_test(int num_threads, long long total_operations, bool stress_uarch) {
    if (num_threads <= 0) return 0.0;
    
    std::vector<UnalignedCounter> bad_data(num_threads);
    long long iterations_per_thread = total_operations / num_threads;

    auto start = std::chrono::high_resolution_clock::now();
    std::vector<std::thread> threads;

    for (int i = 0; i < num_threads; ++i) {
        threads.emplace_back(worker_func, i, std::ref(bad_data[i].count), iterations_per_thread, stress_uarch);
    }

    for (auto& t : threads) {
        t.join();
    }

    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> duration = end - start;

    return duration.count();
}

int main(int argc, char* argv[]) {
    if (argc < 3 || argc > 5) {
        std::cerr << "Usage: " << argv[0] << " <num_threads> <total_operations> [mode] [stress_uarch]" << std::endl;
        return 1;
    }

    int num_threads = std::stoi(argv[1]);
    long long total_operations = std::stoll(argv[2]);
    int mode = (argc >= 4) ? std::stoi(argv[3]) : 0;
    bool stress_uarch = (argc == 5) ? (std::stoi(argv[4]) != 0) : false;

    // Define CPU mappings based on /sys topology
    std::vector<int> ccd0_cores = {0,1,2,3,4,5,12,13,14,15,16,17};
    std::vector<int> ccd1_cores = {6,7,8,9,10,11,18,19,20,21,22,23};

    cpus.clear();
    if (mode == 0) {
        for (int i = 0; i < num_threads; ++i) cpus.push_back(i);
    } else if (mode == 1) {
        cpus = {9, 21};
    } else if (mode == 2) {
        for (int i = 0; i < num_threads; ++i) cpus.push_back(ccd1_cores[i % ccd1_cores.size()]);
    } else if (mode == 3) {
        for (int i = 0; i < num_threads; ++i) {
            if (i % 2 == 0) cpus.push_back(ccd1_cores[(i / 2) % ccd1_cores.size()]);
            else cpus.push_back(ccd0_cores[(i / 2) % ccd0_cores.size()]);
        }
    } else {
        std::cerr << "Invalid mode" << std::endl;
        return 1;
    }

    double time = run_false_sharing_test(num_threads, total_operations, stress_uarch);
    std::cout << "Time for bad coherency (mode " << mode << ", stress " << stress_uarch << "): " << time << " ms" << std::endl;

    return 0;
}
