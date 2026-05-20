import torch
import torch.nn as nn
from bitsandbytes.nn import Params4bit
import bitsandbytes.functional as bnb_f

# 1. Nano-Architektur (Simulation eines Layers)
class NanoLayer(nn.Module):
    def __init__(self):
        super().__init__()
        # 16x16 Gewichte = 256 Parameter (+ Bias = ca. 500)
        self.weight = Params4bit(
            torch.randn(16, 16) * 10, # Provokation: Hohe Werte für hohes Rho
            requires_grad=False,
            quant_type="nf4"
        ).cuda()

# 2. Mini-Patcher Logik
def patch_nano(model, recovery_factor=0.40):
    print("\n--- PAA NANO-TEST ---")
    w = model.weight
    
    # Rho berechnen (Stellvertretend für deine Logik)
    # Dequantisieren zum Messen
    w_float = bnb_f.dequantize_4bit(w.data, w.quant_state)
    rho = torch.norm(w_float).item()
    print(f"Rho BEFORE: {rho:.4f}")

    if rho > 1.0:
        print(f"Targeting Layer... Factor: {recovery_factor}")
        # DER KRITISCHE PUNKT: Skalieren im Float-Raum
        new_float = w_float * recovery_factor
        
        # Zurück-Quantisieren (Force Overwrite)
        new_quantized, new_state = bnb_f.quantize_4bit(
            new_float, 
            quant_type="nf4"
        )
        
        # Physisches Update des Speichers
        w.data.copy_(new_quantized)
        w.quant_state = new_state
        
    # Re-Check
    w_final = bnb_f.dequantize_4bit(w.data, w.quant_state)
    rho_after = torch.norm(w_final).item()
    print(f"Rho AFTER:  {rho_after:.4f}")

# Testlauf
nano = NanoLayer()
patch_nano(nano)