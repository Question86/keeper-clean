import torch
import torch.nn as nn
import time
import bitsandbytes.nn as bnb

# --- CONFIGURATION (Calibrated for 3060 Ti) ---
PAA_CONFIG = {
    "depth_d": 5,
    "branching_b": 3,
    "c_max": 0.99,
    "recovery_factor": 0.97,
}

class AxiomaticPatcher:
    def __init__(self, model, config=PAA_CONFIG):
        self.model = model
        self.config = config
        self.target_modules = ['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj']
        # We find all linear layers, including quantized ones
        self.layers = [(n, m) for n, m in model.named_modules() 
                       if any(t in n for t in self.target_modules)]
        
        # Filter for layers that actually have weight attributes (like Linear or Linear4bit)
        self.layers = [(n, m) for n, m in self.layers if hasattr(m, 'weight')]
        
        print(f"✅ PAA-Shield active on {len(self.layers)} layers.")
        print(f"📊 Mode: Depth-First (d={config['depth_d']})")

    @torch.no_grad()
    def enforce_axioms(self):
        healed_count = 0
        max_rho = 0.0
        
        for name, layer in self.layers:
            # 1. Get the weight. If it's a 4-bit layer, we must dequantize it for the norm calculation.
            if hasattr(layer, 'quant_state'): # This identifies a BitsAndBytes 4-bit layer
                # Temporary dequantization to FP16 for math
                w = bnb.functional.dequantize_4bit(layer.weight.data, layer.quant_state)
            else:
                w = layer.weight.data
            
            # 2. Calculate the Spectral Radius (2-norm)
            rho = torch.linalg.matrix_norm(w.to(torch.float32), ord=2).item()
            max_rho = max(max_rho, rho)
            
            # 3. Apply recovery if it exceeds the PAA threshold
            if rho > self.config["c_max"]:
                target_rho = self.config["c_max"] * self.config["recovery_factor"]
                scale = target_rho / rho
                
                # We apply the scale back to the raw weights
                layer.weight.data.mul_(scale)
                healed_count += 1
        
        return healed_count, max_rho

def log_status(step, loss, healed, max_rho):
    status = "OK" if healed == 0 else "🛠️ RECOVERED"
    print(f"[{time.strftime('%H:%M:%S')}] Step: {step:04d} | Loss: {loss:.4f} | Max-Rho: {max_rho:.3f} | {status} ({healed} Layers)")