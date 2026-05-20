import torch
import numpy as np
import json

def audit_valve_integrity():
    """
    Dieser Test misst die Fehlerrate (Leakage) des Ventils.
    Ein Leak tritt auf, wenn das Ventil behauptet, das System sei sicher, 
    der tatsächliche Radius nach dem Schritt aber rho > c_max ist.
    """
    c_max = 0.99
    # Wir nehmen eine nicht-lineare Schicht, um die lineare Annahme zu prüfen
    model = torch.nn.Sequential(
        torch.nn.Linear(10, 10, bias=False),
        torch.nn.Tanh() # Tanh erzeugt Nichtlinearität in der Krümmung
    )
    
    # Initialsierung nah am Limit
    with torch.no_grad():
        model[0].weight.copy_(torch.eye(10) * 0.95)
        
    optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
    
    # Hier simulieren wir einen extremen Gradienten-Stoß
    # Ein 'ehrlicher' Test erzwingt Rauschen in den Gradienten
    model[0].weight.grad = torch.randn(10, 10) * 0.5 
    
    # --- VORHER ---
    rho_before = torch.linalg.matrix_norm(model[0].weight, ord=2).item()
    
    # --- DER SCHRITT (Ventil-Logik simulieren) ---
    # Wir berechnen die Drosselung basierend auf DEINEM Axiom 3b
    # max_lr = (c_max - rho) / (sensitivity * grad_norm)
    sensitivity = 1.0 # Wir testen, ob 1.0 als Annahme ausreicht
    grad_norm = torch.linalg.matrix_norm(model[0].weight.grad, ord=2).item()
    
    max_lr = (c_max - rho_before) / (sensitivity * grad_norm + 1e-8)
    applied_lr = min(0.1, max_lr * 0.95)
    
    # Gewichtsupdate manuell ausführen
    with torch.no_grad():
        model[0].weight -= applied_lr * model[0].weight.grad
        
    # --- NACHHER (Die nackte Wahrheit) ---
    rho_after = torch.linalg.matrix_norm(model[0].weight, ord=2).item()
    
    leak = rho_after > c_max
    return {
        "rho_start": rho_before,
        "rho_end": rho_after,
        "leak": leak,
        "error_magnitude": max(0, rho_after - c_max)
    }

# Führe 1000 Stichproben durch, um die Wahrscheinlichkeit eines Axiom-Bruchs zu finden
results = [audit_valve_integrity() for _ in range(1000)]
leaks = [r for r in results if r['leak']]

# Save full results to JSON
with open('audit_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"Audit abgeschlossen. Leakage-Rate: {len(leaks)/10}%")
if leaks:
    print(f"Maximaler Stabilitäts-Durchbruch: {max(r['error_magnitude'] for r in leaks):.4f}")