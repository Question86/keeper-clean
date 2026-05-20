import torch
from torch.utils.cpp_extension import load_inline

cuda_source = '''
__global__ void test_psi_kernel(float* d_out, float y, float psi, float delta) {
    d_out[0] = atanf((y - psi) / (delta + 1e-8f));
}

torch::Tensor launch_psi(float y, float psi, float delta) {
    auto options = torch::TensorOptions().dtype(torch::kFloat32).device(torch::kCUDA);
    torch::Tensor out = torch::empty({1}, options);
    test_psi_kernel<<<1, 1>>>(out.data_ptr<float>(), y, psi, delta);
    return out;
}
'''

cpp_source = "torch::Tensor launch_psi(float y, float psi, float delta);"

print("[*] Kompiliere PSI-Kernel via PyTorch JIT...")
try:
    psi_module = load_inline(
        name='psi_test_jit',
        cpp_sources=cpp_source,
        cuda_sources=cuda_source,
        functions=['launch_psi'],
        verbose=True
    )
    
    result = psi_module.launch_psi(2.0, 1.0, 0.5)
    print(f"\n[✓] PSI-Resultat von GPU: {result.item():.4f}")
    print(">>> STATUS: 3060 Ti kommuniziert fehlerfrei mit dem PSI-Kernel! <<<")

except Exception as e:
    print(f"\n[!] JIT-Fehler: {e}")