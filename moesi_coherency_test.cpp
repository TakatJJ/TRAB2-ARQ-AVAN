#include <iostream>
#include <thread>
#include <vector>
#include <chrono>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <stdexcept>

// Total operations for the entire test
const long long TOTAL_OPERATIONS = 500000000; // 500 million operations

// =========================================================================
// DATA STRUCTURES FOR N THREADS
// =========================================================================

// For GOOD Coherency: Each counter is padded to fit exactly one 64-byte cache line.
// This prevents False Sharing, as each thread modifies its own line.
struct AlignedCounter {
    // The volatile keyword is used to prevent the compiler from caching the counter in a register,
    // ensuring every update is a memory access (which then hits the L1 cache).
    alignas(64) volatile long long count = 0; 
};

// For BAD Coherency: Counters are packed tightly (8 bytes each).
// This maximizes the chance that multiple adjacent counters are on the same 64-byte cache line,
// causing False Sharing and MOESI thrashing.
struct UnalignedCounter {
    volatile long long count = 0;
};

// =========================================================================
// WORKER FUNCTION
// =========================================================================

// Generic function executed by every thread
void worker_func(volatile long long& counter, long long iterations) {
    for (long long i = 0; i < iterations; ++i) {
        counter++;
    }
}

// =========================================================================
// SCENARIO 1: BAD COHERENCY (FALSE SHARING)
// =========================================================================

double run_false_sharing_test(int num_threads) {
    if (num_threads <= 0) return 0.0;
    
    // Allocate N counters contiguously
    std::vector<UnalignedCounter> bad_data(num_threads);
    long long iterations_per_thread = TOTAL_OPERATIONS / num_threads;

    auto start = std::chrono::high_resolution_clock::now();
    std::vector<std::thread> threads;

    // Launch N threads, each updating its own adjacent counter
    for (int i = 0; i < num_threads; ++i) {
        threads.emplace_back(worker_func, std::ref(bad_data[i].count), iterations_per_thread);
    }

    for (auto& t : threads) {
        t.join();
    }

    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> duration = end - start;

    long long total_increments = 0;
    for (const auto& item : bad_data) {
        total_increments += item.count;
    }

    std::cout << "\n--- SCENARIO 1: BAD COHERENCY (FALSE SHARING) ---" << std::endl;
    std::cout << "Description: " << num_threads << " threads update adjacent counters, causing MOESI cache line thrashing." << std::endl;
    std::cout << "Total time: " << duration.count() << " ms" << std::endl;
    std::cout << "Total increments: " << total_increments << std::endl;

    return duration.count();
}

// =========================================================================
// SCENARIO 2: GOOD COHERENCY (AVOIDING FALSE SHARING)
// =========================================================================

double run_good_coherency_test(int num_threads) {
    if (num_threads <= 0) return 0.0;
    
    // Allocate N aligned counters, guaranteeing no False Sharing
    std::vector<AlignedCounter> good_data(num_threads);
    long long iterations_per_thread = TOTAL_OPERATIONS / num_threads;

    auto start = std::chrono::high_resolution_clock::now();
    std::vector<std::thread> threads;

    // Launch N threads, each updating its own cache-aligned counter
    for (int i = 0; i < num_threads; ++i) {
        threads.emplace_back(worker_func, std::ref(good_data[i].count), iterations_per_thread);
    }

    for (auto& t : threads) {
        t.join();
    }

    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> duration = end - start;

    long long total_increments = 0;
    for (const auto& item : good_data) {
        total_increments += item.count;
    }

    std::cout << "\n--- SCENARIO 2: GOOD COHERENCY (ALIGNED DATA) ---" << std::endl;
    std::cout << "Description: " << num_threads << " threads update cache-aligned counters, minimizing MOESI traffic." << std::endl;
    std::cout << "Total time: " << duration.count() << " ms" << std::endl;
    std::cout << "Total increments: " << total_increments << std::endl;

    return duration.count();
}

// =========================================================================
// MAIN FUNCTION (Handles User Input)
// =========================================================================

int main() {
    int num_threads;
    int max_threads = static_cast<int>(std::thread::hardware_concurrency());

    std::cout << "Detected hardware concurrency (max cores/threads): " << max_threads << std::endl;
    std::cout << "Enter the number of threads (N) to use for the test: ";
    
    if (!(std::cin >> num_threads) || num_threads <= 0) {
        std::cerr << "Invalid input. Please enter a positive integer." << std::endl;
        return 1;
    }
    
    std::cout << "Running MOESI Cache Coherency Exploration with N = " << num_threads << " threads." << std::endl;

    // Run tests
    double bad_time = run_false_sharing_test(num_threads);
    double good_time = run_good_coherency_test(num_threads);

    // Calculate and display comparison
    double speedup = bad_time / good_time;
    double performance_factor = (bad_time - good_time) / bad_time * 100.0;
    
    std::cout << "\n=========================================================" << std::endl;
    std::cout << "                      COMPARISON                         " << std::endl;
    std::cout << "=========================================================" << std::endl;
    std::cout << "Threads used: " << num_threads << std::endl;
    std::cout << "Time (False Sharing/Bad Coherency): " << bad_time << " ms" << std::endl;
    std::cout << "Time (Aligned Data/Good Coherency): " << good_time << " ms" << std::endl;
    std::cout << "SPEEDUP: The good coherency case is " << speedup << "x faster." << std::endl;
    std::cout << "The MOESI overhead reduced performance by " << performance_factor << " %." << std::endl;
    std::cout << "=========================================================" << std::endl;
    
    // For visualization, you would generate a bar chart comparing bad_time vs good_time.
    
    return 0;
}