import torch
import time
import numpy as np
from torch.utils.cpp_extension import load_inline

# Load the final_kernel.cu
cuda_source = '''
#include <cuda_runtime.h>
#include <math.h>
#include <torch/extension.h>

struct CACRSlot {
    float confidence;
    float age;
    float contradiction;
    float replacement;
};

// Device-only Resonanz-Logik mit numerischem Schutz
__device__ float compute_psi_resonance(float y, float psi, float lambda, float delta) {
    float dist = y - psi;
    // epsilon gegen Division durch Null
    float eps = 1e-8f;
    float resilience = atanf(dist / (delta + eps));

    // Gauß-Envelope mit Begrenzung gegen Überlauf
    float exponent = -1.5f * (dist * dist);
    if (exponent < -50.0f) return 0.0f; // Zu weit weg -> Resonanz Null

    return cosf(lambda * resilience) * expf(exponent);
}

__global__ void psilong_deep_inference_kernel(
    float* __restrict__ attention_scores,
    const CACRSlot* __restrict__ bus_memory,
    const int* __restrict__ history_indices,
    int n,               // Anzahl der Elemente (numel)
    int depth,           // Aktuelle History-Tiefe
    int max_fragments,   // Bus-Limit (meist 1.000.000)
    float base_psi,
    float base_lambda
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;

    float accumulated_R = 0.0f;
    float weight_sum = 0.0f;
    float current_score = attention_scores[idx];

    // Deep Inference Loop
    for (int d = 0; d < depth; d++) {
        // Sicherer Index-Zugriff: d * n + idx
        int frag_idx = history_indices[d * n + idx];

        if (frag_idx >= 0 && frag_idx < max_fragments) {
            CACRSlot slot = bus_memory[frag_idx];

            // PSI-Modulation basierend auf Bus-Zustand
            float dynamic_delta = 0.5f * (1.0f + slot.contradiction * 4.0f);
            float dynamic_lambda = base_lambda * (1.0f + slot.confidence);

            float R = compute_psi_resonance(current_score, base_psi, dynamic_lambda, dynamic_delta);

            // Temporal Decay: Neuere Fragmente zählen mehr
            float t_weight = expf(-0.3f * (float)d);
            accumulated_R += R * t_weight;
            weight_sum += t_weight;
        }
    }

    // Finale In-Place Anwendung
    if (weight_sum > 0.0f) {
        float final_R = accumulated_R / weight_sum;
        // Sicherheits-Clip für die Resonanz (verhindert Modell-Explosion)
        if (final_R > 2.0f) final_R = 2.0f;
        if (final_R < -0.9f) final_R = -0.9f;

        attention_scores[idx] *= (1.0f + final_R);
    }
}

// --- C++ Wrapper ---
torch::Tensor launch_psilong(
    torch::Tensor scores,
    torch::Tensor bus_tensor,
    torch::Tensor history_indices,
    int depth,
    float base_psi,
    float base_lambda
) {
    const int n = scores.numel();
    const int max_fragments = 1000000; // Hard-coded Limit vom Bus
    const int threads = 256;
    const int blocks = (n + threads - 1) / threads;

    psilong_deep_inference_kernel<<<blocks, threads>>>(
        scores.data_ptr<float>(),
        (const CACRSlot*)bus_tensor.data_ptr<float>(),
        history_indices.data_ptr<int>(),
        n,
        depth,
        max_fragments,
        base_psi,
        base_lambda
    );

    return scores;
}
'''

cpp_source = "torch::Tensor launch_psilong(torch::Tensor scores, torch::Tensor bus_tensor, torch::Tensor history_indices, int depth, float base_psi, float base_lambda);"

print("Compiling final_kernel.cu...")
module = load_inline(
    name='final_kernel',
    cpp_sources=cpp_source,
    cuda_sources=cuda_source,
    functions=['launch_psilong'],
    verbose=False
)

def benchmark_kernel(n, depth, num_warmup=20, num_runs=100):
    # Create test tensors
    scores = torch.randn(n, device='cuda', dtype=torch.float32)
    bus_memory = torch.randn(1000000, 4, device='cuda', dtype=torch.float32)  # 4 floats per CACRSlot
    history_indices = torch.randint(0, 1000000, (depth, n), device='cuda', dtype=torch.int32)

    # Preallocate buffer
    scores_buffer = scores.clone()

    # Warmup
    for _ in range(num_warmup):
        scores_buffer.copy_(scores)
        module.launch_psilong(scores_buffer, bus_memory, history_indices, depth, 1.0, 0.5)

    torch.cuda.synchronize()

    times = []
    for _ in range(num_runs):
        scores_buffer.copy_(scores)
        start_event = torch.cuda.Event(enable_timing=True)
        end_event = torch.cuda.Event(enable_timing=True)

        start_event.record()
        module.launch_psilong(scores_buffer, bus_memory, history_indices, depth, 1.0, 0.5)
        end_event.record()

        torch.cuda.synchronize()
        times.append(start_event.elapsed_time(end_event) / 1000.0)  # to seconds

    times = np.array(times)
    throughput = n / times  # elements per second

    return {
        'mean_time': np.mean(times),
        'std_time': np.std(times),
        'min_time': np.min(times),
        'max_time': np.max(times),
        'mean_throughput': np.mean(throughput),
        'times': times
    }

if __name__ == "__main__":
    print("Benchmarking final_kernel.cu performance")
    print("=" * 50)

    test_configs = [
        (1024, 5),
        (1024*4, 5),
        (1024*16, 5),
        (1024*64, 5),
        (1024*256, 5),
        (1024, 10),
        (1024*4, 10),
        (1024*16, 10),
    ]

    for n, depth in test_configs:
        result = benchmark_kernel(n, depth)
        print(f"n={n}, depth={depth}: mean_time={result['mean_time']:.6f}s, throughput={result['mean_throughput']/1e6:.2f}M elem/s")

    print("\nBenchmark complete!")