import torch
import torch.nn as nn
import json

# --- FIXIERUNG DES EXPERIMENTS ---
torch.manual_seed(42) # Absolute Wiederholbarkeit

def set_initial_rho(layer, target_rho):
    with torch.no_grad():
        # Wir messen den aktuellen Radius
        current_rho = torch.linalg.matrix_norm(layer.weight, ord=2).item()
        # Wir skalieren die Gewichte exakt auf den Startpunkt
        layer.weight.data *= (target_rho / current_rho)

# Modell-Setup
model = nn.Sequential(nn.Linear(10, 10, bias=False))
optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
# Start in deiner "interessanten Zone"
set_initial_rho(model[0], 0.95) 

from stability_recovery_v2 import AdaptiveStabilityValve

valve = AdaptiveStabilityValve(optimizer, model, c_max=0.99)
results = []

for step in range(50):
    # Konstante Test-Daten (kein Rauschen zwischen den Runs)
    x = torch.ones(1, 10) 
    y = torch.zeros(1, 10)
    
    optimizer.zero_grad()
    loss = torch.mean((model(x) - y)**2)
    loss.backward()
    
    rho_before = torch.linalg.matrix_norm(model[0].weight, ord=2).item()
    
    # Ventil-Eingriff
    valve.step()
    
    rho_after = torch.linalg.matrix_norm(model[0].weight, ord=2).item()
    
    results.append({
        "step": step,
        "rho_before": rho_before,
        "rho_after": rho_after,
        "lr_used": optimizer.param_groups[0]['lr'],
        "delta": rho_after - rho_before
    })

# Speichern für den Vergleich
with open("seeded_frontier_test.json", "w") as f:
    json.dump(results, f, indent=2)

# Print summary
breaches = [r for r in results if r['rho_after'] > 0.99]
print(f"Seeded Frontier Test: {len(breaches)} breaches in 50 steps")
print(f"Final rho: {results[-1]['rho_after']:.4f}")