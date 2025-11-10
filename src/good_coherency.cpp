#include <iostream>
#include <thread>
#include <vector>
#include <chrono>

struct AlignedCounter {
    alignas(64) volatile long long count = 0;
};

void worker_func(volatile long long& counter, long long iterations) {
    for (long long i = 0; i < iterations; ++i) {
        counter++;
    }
}

double run_good_coherency_test(int num_threads, long long total_operations) {
    if (num_threads <= 0) return 0.0;
    
    std::vector<AlignedCounter> good_data(num_threads);
    long long iterations_per_thread = total_operations / num_threads;

    auto start = std::chrono::high_resolution_clock::now();
    std::vector<std::thread> threads;

    for (int i = 0; i < num_threads; ++i) {
        threads.emplace_back(worker_func, std::ref(good_data[i].count), iterations_per_thread);
    }

    for (auto& t : threads) {
        t.join();
    }

    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> duration = end - start;

    return duration.count();
}

int main(int argc, char* argv[]) {
    if (argc != 3) {
        std::cerr << "Usage: " << argv[0] << " <num_threads> <total_operations>" << std::endl;
        return 1;
    }

    int num_threads = std::stoi(argv[1]);
    long long total_operations = std::stoll(argv[2]);

    double time = run_good_coherency_test(num_threads, total_operations);
    std::cout << "Time for good coherency: " << time << " ms" << std::endl;

    return 0;
}