import torch
import time
import numpy as np
from typing import Tuple

# Disable TF32 for fairness
torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False

def compute_psi_resonance_torch(y: torch.Tensor, psi: float, lambda_: float, delta: float) -> torch.Tensor:
    """PyTorch implementation of compute_psi_resonance"""
    dist = y - psi
    eps = 1e-8
    resilience = torch.atan(dist / (delta + eps))
    exponent = -1.5 * (dist ** 2)
    mask = exponent < -50.0
    result = torch.cos(lambda_ * resilience) * torch.exp(exponent)
    result = torch.where(mask, torch.zeros_like(result), result)
    return result

def psilong_pytorch_gpu(attention_scores: torch.Tensor,
                       bus_memory: torch.Tensor,
                       history_indices: torch.Tensor,
                       base_psi: float,
                       base_lambda: float) -> torch.Tensor:
    """
    PyTorch GPU baseline implementation
    """
    n = attention_scores.shape[0]
    depth = history_indices.shape[0]

    # Clone to avoid modifying input
    scores = attention_scores.clone()

    for idx in range(n):
        current_score = scores[idx]
        accumulated_R = 0.0
        weight_sum = 0.0

        for d in range(depth):
            frag_idx = history_indices[d, idx].item()
            if frag_idx >= 0 and frag_idx < bus_memory.shape[0]:
                slot = bus_memory[frag_idx]
                contradiction = slot[2]  # index 2 is contradiction
                confidence = slot[0]     # index 0 is confidence

                dynamic_delta = 0.5 * (1.0 + contradiction * 4.0)
                dynamic_lambda = base_lambda * (1.0 + confidence)

                R = compute_psi_resonance_torch(current_score, base_psi, dynamic_lambda, dynamic_delta)
                t_weight = torch.exp(torch.tensor(-0.3 * d, device=scores.device, dtype=scores.dtype))
                accumulated_R += R * t_weight
                weight_sum += t_weight

        if weight_sum > 0.0:
            final_R = accumulated_R / weight_sum
            final_R = torch.clamp(final_R, -0.9, 2.0)
            scores[idx] *= (1.0 + final_R)

    return scores

def generate_test_data(n: int, depth: int, seed: int = 42) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Generate test data matching the C++ test suite"""
    np.random.seed(seed)
    torch.manual_seed(seed)

    scores = torch.rand(n, dtype=torch.float32)

    max_fragments = 1000000
    bus = torch.rand(max_fragments, 4, dtype=torch.float32)

    history = torch.randint(0, max_fragments, (depth, n), dtype=torch.int32)

    return scores.cuda(), bus.cuda(), history.cuda()

def benchmark_pytorch_gpu(n: int, depth: int, num_warmup: int = 20, num_runs: int = 100) -> Tuple[float, float, float, float]:
    """Benchmark PyTorch GPU baseline"""
    scores, bus, history = generate_test_data(n, depth)

    # Warmup
    for _ in range(num_warmup):
        _ = psilong_pytorch_gpu(scores, bus, history, 1.0, 0.5)
        torch.cuda.synchronize()

    times = []
    for _ in range(num_runs):
        torch.cuda.synchronize()
        start = time.perf_counter()
        _ = psilong_pytorch_gpu(scores, bus, history, 1.0, 0.5)
        torch.cuda.synchronize()
        end = time.perf_counter()
        times.append(end - start)

    times = np.array(times)
    return times.mean(), times.std(), times.min(), times.max()

if __name__ == "__main__":
    # Test correctness
    print("Testing PyTorch GPU baseline correctness...")
    n, depth = 1024, 5
    scores, bus, history = generate_test_data(n, depth)
    result = psilong_pytorch_gpu(scores, bus, history, 1.0, 0.5)
    print(f"PyTorch result[0]: {result[0].item():.6f}")

    # Benchmark
    print("Benchmarking PyTorch GPU baseline...")
    configs = [(1024, 5), (4096, 5), (16384, 5), (65536, 5), (1024, 10), (4096, 10), (16384, 10)]
    for n, depth in configs:
        mean_t, std_t, min_t, max_t = benchmark_pytorch_gpu(n, depth)
        print(f"n={n}, depth={depth}: mean={mean_t:.6e}s, std={std_t:.6e}s")