import torch
import time
import numpy as np
from typing import Tuple

torch.set_grad_enabled(False)
torch.backends.cuda.matmul.allow_tf32 = False

# Match the C++ struct
# struct CACRSlot { float confidence, age, contradiction, replacement; }

def compute_psi_resonance(y: torch.Tensor, psi: float, lambda_: torch.Tensor, delta: torch.Tensor) -> torch.Tensor:
    dist = y - psi
    eps = 1e-8
    resilience = torch.atan(dist / (delta + eps))
    exponent = -1.5 * (dist * dist)
    mask = exponent >= -50.0
    return torch.where(mask, torch.cos(lambda_ * resilience) * torch.exp(exponent), torch.zeros_like(exponent))

@torch.jit.script
def psilong_pytorch_gpu(attention_scores: torch.Tensor, bus_memory: torch.Tensor,
                       history_indices: torch.Tensor, base_psi: float, base_lambda: float) -> torch.Tensor:
    n = attention_scores.shape[0]
    depth = history_indices.shape[0]
    max_fragments = bus_memory.shape[0]

    # Vectorize over all d and idx
    frag_idx_all = history_indices.flatten()  # (depth * n,)
    d_idx_all = torch.arange(depth * n, device=attention_scores.device) // n  # d for each position
    idx_all = torch.arange(depth * n, device=attention_scores.device) % n  # idx for each position

    mask_all = (frag_idx_all >= 0) & (frag_idx_all < max_fragments)

    frag_idx_valid = frag_idx_all[mask_all]
    d_valid = d_idx_all[mask_all]
    idx_valid = idx_all[mask_all]

    slots_valid = bus_memory[frag_idx_valid]  # (num_valid, 4)
    current_scores_valid = attention_scores[idx_valid]

    dynamic_delta = 0.5 * (1.0 + slots_valid[:, 2] * 4.0)  # contradiction
    dynamic_lambda = base_lambda * (1.0 + slots_valid[:, 0])  # confidence

    R_valid = compute_psi_resonance(current_scores_valid, base_psi, dynamic_lambda, dynamic_delta)

    t_weight_valid = torch.exp(-0.3 * d_valid.to(torch.float32))

    # Accumulate
    accumulated_R = torch.zeros_like(attention_scores)
    weight_sum = torch.zeros_like(attention_scores)

    accumulated_R.index_add_(0, idx_valid, R_valid * t_weight_valid)
    weight_sum.index_add_(0, idx_valid, t_weight_valid)

    # Compute final
    mask_ws = weight_sum > 0
    final_R = torch.zeros_like(accumulated_R)
    final_R[mask_ws] = accumulated_R[mask_ws] / weight_sum[mask_ws]
    final_R = torch.clamp(final_R, -0.9, 2.0)

    result = attention_scores * (1.0 + final_R)
    return result

def generate_fixed_test_data(n: int, depth: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    scores = torch.full((n,), 0.5, dtype=torch.float32, device='cuda')
    bus = torch.tensor([0.1, 0.2, 0.3, 0.4], dtype=torch.float32, device='cuda').repeat(1000000, 1)
    history = torch.zeros((depth, n), dtype=torch.int64, device='cuda')
    return scores, bus, history

def generate_test_data(n: int, depth: int, seed: int = 42, contiguous: bool = False) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    np.random.seed(seed)
    torch.manual_seed(seed)

    scores = torch.rand(n, dtype=torch.float32, device='cuda')
    bus = torch.rand(1000000, 4, dtype=torch.float32, device='cuda')  # confidence, age, contradiction, replacement
    if contiguous:
        # Make indices contiguous starting from 0
        max_idx = min(1000000, n * depth)
        indices_flat = torch.arange(max_idx, device='cuda', dtype=torch.int64)
        if len(indices_flat) < depth * n:
            indices_flat = torch.cat([indices_flat, torch.randint(0, 1000000, (depth * n - len(indices_flat),), device='cuda', dtype=torch.int64)])
        history = indices_flat[:depth * n].reshape(depth, n)
    else:
        history = torch.randint(0, 1000000, (depth, n), dtype=torch.int64, device='cuda')

    return scores, bus, history

def benchmark_pytorch_gpu(n: int, depth: int, num_warmup: int = 20, num_runs: int = 100, contiguous: bool = False) -> dict:
    scores, bus, history = generate_test_data(n, depth, contiguous=contiguous)

    print(f"x: {scores.shape}, {scores.dtype}, {scores.device}, is_cuda: {scores.is_cuda}")

    # Warmup
    for _ in range(num_warmup):
        _ = psilong_pytorch_gpu(scores.clone(), bus, history, 1.0, 0.5)

    torch.cuda.synchronize()

    times = []
    for _ in range(num_runs):
        scores_copy = scores.clone()
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        result = psilong_pytorch_gpu(scores_copy, bus, history, 1.0, 0.5)
        torch.cuda.synchronize()
        t1 = time.perf_counter()
        times.append(t1 - t0)

        assert scores_copy.is_cuda and result.is_cuda

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
    print("PyTorch GPU Baseline Test")
    print("cuda available:", torch.cuda.is_available())
    print("torch:", torch.__version__, "cuda:", torch.version.cuda)

    # Test correctness on fixed data
    n, depth = 1024, 5
    scores, bus, history = generate_fixed_test_data(n, depth)
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    result = psilong_pytorch_gpu(scores, bus, history, 1.0, 0.5)
    torch.cuda.synchronize()
    t1 = time.perf_counter()
    print("single call time:", t1-t0, "sec", "y0:", result.flatten()[0].item())
    print(f"y: {result.shape}, {result.dtype}, {result.device}, is_cuda: {result.is_cuda}")

    # Benchmark
    configs = [
        (256, 1, False), (256, 1, True), (256, 5, False), (256, 5, True),
        (1024, 1, False), (1024, 1, True), (1024, 5, False), (1024, 5, True),
        (4096, 1, False), (4096, 1, True), (4096, 5, False), (4096, 5, True),
        (16384, 5, False)
    ]
    results = {}
    for n, depth, contiguous in configs:
        print(f"Benchmarking n={n}, depth={depth}, contiguous={contiguous}")
        res = benchmark_pytorch_gpu(n, depth, contiguous=contiguous)
        results[(n, depth, contiguous)] = res
        print(f"Mean time: {res['mean_time']:.6f} s, Throughput: {res['mean_throughput']:.0f} elem/s")

    # Save results
    import json
    results_str = {str(k): v for k, v in results.items()}
    with open('pytorch_gpu_results_adversarial.json', 'w') as f:
        json.dump(results_str, f, indent=2)