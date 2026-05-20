import os, time, math
import torch
from torch.utils.cpp_extension import load

torch.set_grad_enabled(False)

# ---------- CONFIG ----------
SRC = os.path.join(os.path.dirname(__file__), "final_kernel.cu")  # passe an falls anders
EXT_NAME = "psi_ext"
DTYPE = torch.float32
DEVICE = "cuda"

# test matrix
Ns = [256, 1024, 4096, 16384, 65536, 131072, 262144]
DEPTHS = [1, 5, 10]
WARMUP = 20
RUNS = 100

# kernel parameters (MUST match kernel defaults/usage you intend)
psi = 1.0
base_lambda = 12.0
delta = 0.05
alpha = 1.5
beta = 1.0
eps = 1e-8
decay = 0.3
clip_lo, clip_hi = -0.9, 2.0

# ---------- BUILD/LOAD EXT ----------
# This assumes final_kernel.cu exposes a binding `launch_psilong(...)`
# If your binding name differs, adjust below.
module = load(
    name=EXT_NAME,
    sources=[SRC],
    extra_cuda_cflags=["-O3", "--use_fast_math", "-lineinfo"],
    extra_cflags=["-O3"],
    with_cuda=True,
    verbose=False,
)

# ---------- HELPERS ----------
def make_inputs(n, depth, contiguous=False, seed=0):
    g = torch.Generator(device=DEVICE)
    g.manual_seed(seed)

    # attention scores
    scores = torch.randn(n, device=DEVICE, dtype=DTYPE, generator=g)

    # bus memory: [Nbus, 4] floats -> confidence, contradiction, age, replacement_cost
    # Choose a moderate bus size; increase if your kernel expects 1e6
    Nbus = 1_000_000
    bus = torch.empty((Nbus, 4), device=DEVICE, dtype=DTYPE)
    bus[:, 0] = torch.rand(Nbus, device=DEVICE, dtype=DTYPE, generator=g)          # confidence in [0,1]
    bus[:, 1] = torch.rand(Nbus, device=DEVICE, dtype=DTYPE, generator=g)          # contradiction in [0,1]
    bus[:, 2] = torch.rand(Nbus, device=DEVICE, dtype=DTYPE, generator=g) * 100.0  # age
    bus[:, 3] = torch.rand(Nbus, device=DEVICE, dtype=DTYPE, generator=g)          # replacement cost

    # history indices: [depth, n] long indices into bus
    if contiguous:
        base = torch.randint(0, Nbus - depth - 1, (n,), device=DEVICE, generator=g)
        hist = torch.stack([base + d for d in range(depth)], dim=0).to(torch.int64)
    else:
        hist = torch.randint(0, Nbus, (depth, n), device=DEVICE, generator=g, dtype=torch.int64)

    return scores, bus, hist


def resonance_node(y, conf, contr):
    # lambda_d, delta_d (must match kernel)
    lam_d = base_lambda * (1.0 + conf)
    del_d = 0.5 * (1.0 + 4.0 * contr)

    z = (y - psi) / (del_d + eps)
    phase = lam_d * torch.atan(z)
    # envelope in kernel description: exp(-1.5*(y-psi)^2)
    # if your kernel uses (y-psi)^2 without /beta etc, match that. Adjust if needed.
    env = torch.exp(-alpha * (y - psi) * (y - psi))

    # cutoff like "if exponent < -50 => 0" (apply to env)
    env = torch.where((-alpha * (y - psi) * (y - psi)) < -50.0, torch.zeros_like(env), env)

    return torch.cos(phase) * env


def pytorch_baseline(scores_in, bus, hist):
    # Match kernel in-place: scores *= (1 + final_R)
    # Compute final_R as weighted avg across depth using bus metadata.
    depth, n = hist.shape
    y = scores_in

    # gather confidence/contradiction per depth
    # bus[frag, 0] = confidence, bus[frag, 1] = contradiction
    frags = hist  # [D, n]
    conf = bus[frags, 0]   # [D, n]
    contr = bus[frags, 1]  # [D, n]

    R = resonance_node(y.unsqueeze(0).expand(depth, n), conf, contr)  # [D, n]

    w = torch.exp(-decay * torch.arange(depth, device=DEVICE, dtype=DTYPE)).unsqueeze(1)  # [D,1]
    num = (R * w).sum(dim=0)
    den = w.sum(dim=0)  # scalar broadcast
    final_R = num / den

    final_R = torch.clamp(final_R, clip_lo, clip_hi)

    out = scores_in * (1.0 + final_R)
    return out


def time_cuda(fn, *args):
    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record()
    fn(*args)
    end.record()
    torch.cuda.synchronize()
    return start.elapsed_time(end) / 1000.0  # seconds


# ---------- MAIN ----------
print("GPU:", torch.cuda.get_device_name(0))
print("Torch:", torch.__version__, "CUDA:", torch.version.cuda)
print("Using:", DEVICE, DTYPE)

# 1) Correctness gate: compare kernel output vs pytorch baseline
# We assume kernel function signature:
# module.launch_psilong(scores, bus, hist, depth, psi, base_lambda)
# Adjust if your binding differs.
def run_kernel(scores, bus, hist):
    # kernel updates scores in-place
    module.launch_psilong(scores, bus, hist, int(hist.shape[0]), float(psi), float(base_lambda))

for n in [1024, 16384]:
    for depth in [1, 5, 10]:
        scores, bus, hist = make_inputs(n, depth, contiguous=False, seed=123)
        scores_k = scores.clone()
        scores_t = scores.clone()

        # kernel
        run_kernel(scores_k, bus, hist)

        # torch baseline
        out_t = pytorch_baseline(scores_t, bus, hist)

        max_abs = (scores_k - out_t).abs().max().item()
        max_rel = ((scores_k - out_t).abs() / (out_t.abs() + 1e-12)).max().item()
        print(f"[CORRECT] n={n} depth={depth} max_abs={max_abs:.3e} max_rel={max_rel:.3e}")

        if not (max_abs <= 1e-5 and max_rel <= 1e-5):
            raise SystemExit("FAIL: Baseline does not match kernel. Fix baseline/kernel mapping before benchmarking.")

print("Correctness gate: PASS")

# 2) Benchmark matrix
rows = []
for contiguous in [False, True]:
    for depth in DEPTHS:
        for n in Ns:
            scores, bus, hist = make_inputs(n, depth, contiguous=contiguous, seed=7)

            # warmup
            for _ in range(WARMUP):
                s = scores.clone()
                run_kernel(s, bus, hist)
            for _ in range(WARMUP):
                _ = pytorch_baseline(scores, bus, hist)
            torch.cuda.synchronize()

            # kernel timing
            tk = []
            for _ in range(RUNS):
                s = scores.clone()
                tk.append(time_cuda(run_kernel, s, bus, hist))
            t_kernel = sum(tk)/len(tk)

            # torch timing
            tt = []
            for _ in range(RUNS):
                tt.append(time_cuda(pytorch_baseline, scores, bus, hist))
            t_torch = sum(tt)/len(tt)

            thr_k = n / t_kernel / 1e6
            thr_t = n / t_torch / 1e6

            rows.append((n, depth, contiguous, t_kernel, thr_k, t_torch, thr_t, t_torch / t_kernel))

            print(
                f"n={n:7d} depth={depth:2d} contig={str(contiguous):5s} | "
                f"kernel {t_kernel:.6e}s ({thr_k:8.2f} M/s) | "
                f"torch {t_torch:.6e}s ({thr_t:8.2f} M/s) | "
                f"speedup torch/kernel={t_torch/t_kernel:6.2f}x"
            )

print("DONE")
