#include <iostream>
#include <thread>
#include <vector>
#include <chrono>
#include <sched.h>
#include <string>
#include <cstdlib>
#include <new>

std::vector<int> cpus;

static constexpr std::size_t cache_line_size = 64;

#ifdef ALIGNED_COUNTER
struct Counter {
    alignas(64) volatile long long count = 0;
};
#else
struct Counter {
    volatile long long count = 0;
};
#endif

template <typename T>
struct AlignedAllocator {
    using value_type = T;

    AlignedAllocator() = default;

    template <class U>
    constexpr AlignedAllocator(const AlignedAllocator<U>&) noexcept {}

    T* allocate(std::size_t n) {
        if (n > std::size_t(-1) / sizeof(T)) throw std::bad_alloc();

        // Calculate size: must be a multiple of alignment (64)
        std::size_t alignment = cache_line_size;
        std::size_t bytes = n * sizeof(T);
        std::size_t aligned_size = (bytes + alignment - 1) & ~(alignment - 1);

        void* ptr = std::aligned_alloc(alignment, aligned_size);
        if (!ptr) throw std::bad_alloc();

        return static_cast<T*>(ptr);
    }

    void deallocate(T* p, std::size_t) noexcept {
        std::free(p);
    }
};

template <class T, class U>
bool operator==(const AlignedAllocator<T>&, const AlignedAllocator<U>&) { return true; }

template <class T, class U>
bool operator!=(const AlignedAllocator<T>&, const AlignedAllocator<U>&) { return false; }


// Fast Linear Congruential Generator for low-overhead randomness
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

    // Critical Loop
    for (long long i = 0; i < iterations; ++i) {
        // 1. Always pay the cost of the random number calculation.
        // This equalizes the instruction count overhead (multiplication/add) 
        // between the two modes.
        unsigned int rand_val = fast_rand(seed);

        if (stress_uarch) {
            // Case 2 & 4: Bad uArch (Random Branching)
            // Uses the random value to determine the path. 
            // The CPU cannot predict this, causing frequent pipeline flushes.
            if (rand_val & 1) {
                counter++;
            } else {
                counter++;
            }
        } else {
            // Case 1 & 3: Good uArch (Predictable Branching)
            // We introduce a branch here to match the instruction structure 
            // of the 'Bad' case (test + jump).
            // However, we use 'i & 1' (alternating 0, 1, 0, 1...) which is 
            // trivial for the Branch Predictor to learn.
            // Result: Similar instruction count, but near-zero mispredictions.
            if (i & 1) {
                counter++;
            } else {
                counter++;
            }
        }
    }
}

double run_test(int num_threads, long long total_operations, bool stress_uarch) {
    if (num_threads <= 0) return 0.0;

    std::vector<Counter, AlignedAllocator<Counter>> counters(num_threads);
    long long iterations_per_thread = total_operations / num_threads;

    auto start = std::chrono::high_resolution_clock::now();
    std::vector<std::thread> threads;

    for (int i = 0; i < num_threads; ++i) {
        threads.emplace_back(worker_func, i, std::ref(counters[i].count), iterations_per_thread, stress_uarch);
    }

    for (auto& t : threads) {
        t.join();
    }

    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> duration = end - start;

    return duration.count();
}

int main(int argc, char* argv[]) {
    // Updated usage to accept optional 4th argument
    if (argc < 3 || argc > 5) {
        std::cerr << "Usage: " << argv[0] << " <num_threads> <total_operations> [mode] [stress_uarch]" << std::endl;
        std::cerr << "Modes: 0=default, 1=same core, 2=same CCD, 3=different CCDs" << std::endl;
        std::cerr << "Stress uArch: 0=Disabled (default), 1=Enabled" << std::endl;
        return 1;
    }

    int num_threads = std::stoi(argv[1]);
    long long total_operations = std::stoll(argv[2]);
    int mode = (argc >= 4) ? std::stoi(argv[3]) : 0;
    bool stress_uarch = (argc == 5) ? (std::stoi(argv[4]) != 0) : false;

    // Define CPU mappings based on /sys topology
    std::vector<int> ccd0_cores = {1,2,3,4,5,13,14,15,16,17};
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

    double time = run_test(num_threads, total_operations, stress_uarch);
    #ifdef ALIGNED_COUNTER
        std::cout << "Time for good coherency (mode " << mode << ", stress " << stress_uarch << "): " << time << " ms" << std::endl;
    #else
        std::cout << "Time for bad coherency (mode " << mode << ", stress " << stress_uarch << "): " << time << " ms" << std::endl;
    #endif

    return 0;
}
