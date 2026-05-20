import torch
import time
import numpy as np
from typing import Tuple

torch.set_grad_enabled(False)
torch.set_num_threads(8)  # Use multiple threads

# Match the C++ struct
# struct CACRSlot { float confidence, age, contradiction, replacement; }

def compute_psi_resonance(y: torch.Tensor, psi: float, lambda_: torch.Tensor, delta: torch.Tensor) -> torch.Tensor:
    dist = y - psi
    eps = 1e-8
    resilience = torch.atan(dist / (delta + eps))
    exponent = -1.5 * (dist * dist)
    mask = exponent >= -50.0
    return torch.where(mask, torch.cos(lambda_ * resilience) * torch.exp(exponent), torch.zeros_like(exponent))

@torch.no_grad()
def psilong_cpu(attention_scores: torch.Tensor, bus_memory: torch.Tensor,
               history_indices: torch.Tensor, base_psi: float, base_lambda: float) -> torch.Tensor:
    n = attention_scores.shape[0]
    depth = history_indices.shape[0]
    max_fragments = bus_memory.shape[0]

    accumulated_R = torch.zeros_like(attention_scores)
    weight_sum = torch.zeros_like(attention_scores)

    for d in range(depth):
        frag_idx = history_indices[d]  # shape (n,)
        mask = (frag_idx >= 0) & (frag_idx < max_fragments)

        # Gather slots: bus_memory[frag_idx] but only for valid
        valid_idx = frag_idx[mask]
        if valid_idx.numel() > 0:
            slots = bus_memory[valid_idx]  # shape (num_valid, 4)
            dynamic_delta = 0.5 * (1.0 + slots[:, 2] * 4.0)  # contradiction
            dynamic_lambda = base_lambda * (1.0 + slots[:, 0])  # confidence

            current_scores_valid = attention_scores[mask]
            R_valid = compute_psi_resonance(current_scores_valid, base_psi, dynamic_lambda, dynamic_delta)

            t_weight = torch.exp(torch.tensor(-0.3 * d, dtype=torch.float32, device=attention_scores.device))
            accumulated_R[mask] += R_valid * t_weight
            weight_sum[mask] += t_weight

    # Compute final
    mask_ws = weight_sum > 0
    final_R = torch.zeros_like(accumulated_R)
    final_R[mask_ws] = accumulated_R[mask_ws] / weight_sum[mask_ws]
    final_R = torch.clamp(final_R, -0.9, 2.0)

    result = attention_scores * (1.0 + final_R)
    return result

def generate_test_data(n: int, depth: int, seed: int = 42) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    np.random.seed(seed)
    torch.manual_seed(seed)

    scores = torch.rand(n, dtype=torch.float32)
    bus = torch.rand(1000000, 4, dtype=torch.float32)  # confidence, age, contradiction, replacement
    history = torch.randint(0, 1000000, (depth, n), dtype=torch.int64)

    return scores, bus, history

def benchmark_cpu(n: int, depth: int, num_warmup: int = 20, num_runs: int = 100) -> dict:
    scores, bus, history = generate_test_data(n, depth)

    print(f"x: {scores.shape}, {scores.dtype}, {scores.device}, is_cuda: {scores.is_cuda}")

    # Warmup
    for _ in range(num_warmup):
        _ = psilong_cpu(scores.clone(), bus, history, 1.0, 0.5)

    times = []
    for _ in range(num_runs):
        scores_copy = scores.clone()
        t0 = time.perf_counter()
        result = psilong_cpu(scores_copy, bus, history, 1.0, 0.5)
        t1 = time.perf_counter()
        times.append(t1 - t0)

        assert not scores_copy.is_cuda and not result.is_cuda

    times = np.array(times)
    throughput = n / times  # elements per second

    return {
        'mean_time': np.mean(times),
        'std_time': np.std(times),
        'min_time': np.min(times),
        'max_time': np.max(times),
        'mean_throughput': np.mean(throughput),
        'times': times.tolist()
    }

if __name__ == "__main__":
    print("PyTorch CPU Baseline Test")
    print("Num threads:", torch.get_num_threads())

    # Benchmark
    configs = [(1024, 5), (4096, 5), (16384, 5), (65536, 5), (131072, 5), (262144, 5), (100000, 5), (1024, 10), (4096, 10), (16384, 10)]
    results = {}
    for n, depth in configs:
        print(f"Benchmarking n={n}, depth={depth}")
        res = benchmark_cpu(n, depth)
        results[(n, depth)] = res
        print(f"Mean time: {res['mean_time']:.4f} s, Throughput: {res['mean_throughput']:.0f} elem/s")

    # Save results
    import json
    results_str = {str(k): v for k, v in results.items()}
    with open('pytorch_cpu_results.json', 'w') as f:
        json.dump(results_str, f, indent=2)