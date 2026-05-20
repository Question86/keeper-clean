import os
import sys

# --- DEIN KORRIGIERTER PFAD ---
msvc_path = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64"
ninja_path = r"C:\Users\ambas\AppData\Roaming\Python\Python313\Scripts"

print("[*] Initialisiere Environment-Check mit MSVC 14.44...")

# 1. Ninja-Pfad hinzufügen
if os.path.exists(ninja_path):
    os.environ["PATH"] += os.pathsep + ninja_path
    print(f"[✓] Ninja gefunden.")
else:
    print(f"[!] Warnung: Ninja nicht gefunden unter {ninja_path}")

# 2. MSVC-Pfad hinzufügen & Umgebung vorbereiten
if os.path.exists(msvc_path):
    os.environ["PATH"] += os.pathsep + msvc_path
    
    # Wichtig für den Compiler: Wir setzen auch INCLUDE und LIB Pfade automatisch
    parent = os.path.dirname(os.path.dirname(os.path.dirname(msvc_path)))
    os.environ["INCLUDE"] = os.path.join(parent, "include")
    os.environ["LIB"] = os.path.join(parent, "lib", "x64")
    print(f"[✓] MSVC 14.44 (cl.exe) erfolgreich lokalisiert.")
else:
    print(f"[!] KRITISCH: Pfad nicht gefunden! Bitte prüfen: {msvc_path}")
    sys.exit()

import torch
from torch.utils.cpp_extension import load_inline

# --- TEST KERNEL SOURCE ---
cuda_source = '''
__global__ void test_psi_kernel(float* d_out, float y, float psi, float delta) {
    // PSI-Resonanz Test-Berechnung
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

print("\n[*] Starte JIT-Kompilierung (3060 Ti wird vorbereitet)...")
try:
    # Das hier ruft jetzt Ninja und deinen cl.exe Compiler auf
    psi_module = load_inline(
        name='psi_test_jit',
        cpp_sources=cpp_source,
        cuda_sources=cuda_source,
        functions=['launch_psi'],
        verbose=True
    )
    
    # Test-Lauf
    result = psi_module.launch_psi(2.0, 1.0, 0.5)
    print(f"\n[✓] PSI-Resultat von GPU: {result.item():.4f}")
    
    if 1.1070 <= result.item() <= 1.1072:
        print(">>> STATUS: 3060 Ti IST PSI-READY! <<<")
    else:
        print(">>> STATUS: Hardware-Check erfolgreich, aber Präzisions-Abweichung. <<<")

except Exception as e:
    print(f"\n[!] JIT-Fehler: {e}")