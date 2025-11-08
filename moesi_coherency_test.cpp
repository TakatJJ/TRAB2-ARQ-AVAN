#include <iostream>
#include <thread>
#include <vector>
#include <mutex>
#include <chrono>
#include <cmath>
#include <algorithm>

// Define the number of operations each thread will perform
// Using a large number to ensure execution time is long enough to measure coherency overhead
const long long NUM_ITERATIONS = 500000000; // 500 million operations

// =========================================================================
// SCENARIO 1: BAD COHERENCY (FALSE SHARING)
// =========================================================================

// Independent variables located close in memory, likely sharing a 64-byte cache line.
struct FalseSharedData {
    long long c1; // Accessed by Thread 1
    long long c2; // Accessed by Thread 2
    // Both c1 and c2 are in the same cache line, causing 'ping-pong' cache traffic.
};

FalseSharedData false_shared_data = {0, 0};

void false_sharing_thread_1() {
    for (long long i = 0; i < NUM_ITERATIONS; ++i) {
        false_shared_data.c1++;
    }
}

void false_sharing_thread_2() {
    for (long long i = 0; i < NUM_ITERATIONS; ++i) {
        false_shared_data.c2++;
    }
}

double run_false_sharing_test() {
    // Reset data for the test
    false_shared_data = {0, 0};
    
    auto start = std::chrono::high_resolution_clock::now();

    std::thread t1(false_sharing_thread_1);
    std::thread t2(false_sharing_thread_2);

    t1.join();
    t2.join();

    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> duration = end - start;

    std::cout << "\n--- SCENARIO 1: BAD COHERENCY (FALSE SHARING) ---" << std::endl;
    std::cout << "Description: Two threads update different variables on the same 64-byte cache line." << std::endl;
    std::cout << "MOESI Thrashing: Causes frequent transitions between M, I, and O states, resulting in high interconnect traffic." << std::endl;
    std::cout << "Total time: " << duration.count() << " ms" << std::endl;
    std::cout << "Total increments: " << false_shared_data.c1 + false_shared_data.c2 << std::endl;

    return duration.count();
}

// =========================================================================
// SCENARIO 2: GOOD COHERENCY (AVOIDING FALSE SHARING)
// =========================================================================

// alignas(64) forces the subsequent variable to start on a new 64-byte boundary.
// This is the standard cache line size on x86/AMD architectures.
struct AlignedData {
    alignas(64) long long c1; // Forced onto its own cache line
    alignas(64) long long c2; // Forced onto its own cache line
};

AlignedData aligned_data = {0, 0};

void good_coherency_thread_1() {
    for (long long i = 0; i < NUM_ITERATIONS; ++i) {
        aligned_data.c1++;
    }
}

void good_coherency_thread_2() {
    for (long long i = 0; i < NUM_ITERATIONS; ++i) {
        aligned_data.c2++;
    }
}

double run_good_coherency_test() {
    // Reset data for the test
    aligned_data = {0, 0};
    
    auto start = std::chrono::high_resolution_clock::now();

    std::thread t1(good_coherency_thread_1);
    std::thread t2(good_coherency_thread_2);

    t1.join();
    t2.join();

    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> duration = end - start;

    std::cout << "\n--- SCENARIO 2: GOOD COHERENCY (ALIGNED DATA) ---" << std::endl;
    std::cout << "Description: Two threads update different variables, each forced onto a separate 64-byte cache line." << std::endl;
    std::cout << "MOESI Optimization: Each core holds its line in the Exclusive (E) or Modified (M) state without interference, minimizing bus traffic." << std::endl;
    std::cout << "Total time: " << duration.count() << " ms" << std::endl;
    std::cout << "Total increments: " << aligned_data.c1 + aligned_data.c2 << std::endl;

    return duration.count();
}

// =========================================================================
// MAIN FUNCTION AND RESULTS VISUALIZATION
// =========================================================================

int main() {
    std::cout << "Starting MOESI Cache Coherency Exploration on " << std::thread::hardware_concurrency() << " cores." << std::endl;
    
    // Run tests
    double bad_time = run_false_sharing_test();
    double good_time = run_good_coherency_test();

    // Calculate and display comparison
    double speedup = bad_time / good_time;
    double performance_factor = (bad_time - good_time) / bad_time * 100.0;
    
    std::cout << "\n=========================================================" << std::endl;
    std::cout << "                      COMPARISON                         " << std::endl;
    std::cout << "=========================================================" << std::endl;
    std::cout << "Time (False Sharing/Bad Coherency): " << bad_time << " ms" << std::endl;
    std::cout << "Time (Aligned Data/Good Coherency): " << good_time << " ms" << std::endl;
    std::cout << "SPEEDUP: The good coherency case is " << speedup << "x faster." << std::endl;
    std::cout << "The MOESI overhead reduced performance by " << performance_factor << " %." << std::endl;
    std::cout << "=========================================================" << std::endl;
    
    // You would typically use a plotting library to generate the graphs based on these times
    // For visualization, consider generating a bar chart comparing bad_time vs good_time.
    
    return 0;
}