import torch
import torch.nn as nn
import json

# Reproduzierbarkeit
torch.manual_seed(42)

def force_instability(layer, target_rho=1.20):
    """Zwingt das System in den instabilen Bereich."""
    with torch.no_grad():
        current_rho = torch.linalg.matrix_norm(layer.weight, ord=2).item()
        layer.weight.data *= (target_rho / current_rho)

class ResilientStabilityValve:
    def __init__(self, optimizer, model, c_max=0.99):
        self.optimizer = optimizer
        self.model = model
        self.c_max = c_max

    def step(self):
        with torch.no_grad():
            # 1. Messung
            rho_t = torch.linalg.matrix_norm(self.model[0].weight, ord=2).item()
            
            # 2. HEILUNGS-LOGIK (Recovery)
            # Wenn wir über dem Limit sind, kontrahieren wir aktiv
            if rho_t > self.c_max:
                # Faktor berechnen, um sofort auf 98% von c_max zu kommen
                recovery_factor = (self.c_max * 0.98) / rho_t
                self.model[0].weight.data *= recovery_factor
                return "RECOVERED"

            # 3. PRÄVENTIONS-LOGIK (Normalbetrieb)
            # Hier greift dein normales Fischer-Ventil
            # (Für diesen Test halten wir es simpel: LR=0 bei Gefahr)
            return "STABLE"

# Setup
model = nn.Sequential(nn.Linear(10, 10, bias=False))
optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
force_instability(model[0], 1.20) # Wir starten im Chaos

valve = ResilientStabilityValve(optimizer, model)
results = []

for step in range(20):
    rho_before = torch.linalg.matrix_norm(model[0].weight, ord=2).item()
    
    # Ventil entscheidet: Heilen oder normales Update?
    status = valve.step()
    
    if status != "RECOVERED":
        # Nur wenn wir stabil sind, machen wir einen normalen Lernschritt
        x, y = torch.randn(1, 10), torch.zeros(1, 10)
        optimizer.zero_grad()
        loss = torch.mean((model(x) - y)**2)
        loss.backward()
        optimizer.step()
    
    rho_after = torch.linalg.matrix_norm(model[0].weight, ord=2).item()
    
    results.append({
        "step": step,
        "status": status,
        "rho_before": rho_before,
        "rho_after": rho_after
    })

with open("recovery_härte_test.json", "w") as f:
    json.dump(results, f, indent=2)

print("Härte-Test abgeschlossen. Schau in die Ergebnisse!")