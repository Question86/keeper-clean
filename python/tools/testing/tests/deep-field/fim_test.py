import torch
import torch.nn as nn
import numpy as np
import json

def get_spectral_radius(layer):
    # Echte Messung des Spektralradius via Singulärwertzerlegung
    return torch.linalg.matrix_norm(layer.weight, ord=2).item()

def run_empirical_audit(steps=100, nominal_sensitivity=10.0):
    """
    Misst die 'Axiom-Lücke': Die Differenz zwischen dem, was das 
    Ventil vorhersagt, und dem, was geometrisch wirklich passiert.
    """
    c_max = 0.99
    # Ein kleines MLP mit ReLU/Tanh ist perfekt, um Linearität zu brechen
    model = nn.Sequential(
        nn.Linear(20, 20, bias=False),
        nn.Tanh() 
    )
    
    # Startpunkt: Kurz vor der Instabilität
    with torch.no_grad():
        model[0].weight.copy_(torch.eye(20) * 0.90)

    results = []
    
    for i in range(steps):
        rho_t = get_spectral_radius(model[0])
        
        # Erzeuge einen zufälligen, aber starken Gradienten
        grad = torch.randn(20, 20) * 0.1
        model[0].weight.grad = grad
        grad_norm = torch.linalg.matrix_norm(grad, ord=2).item()

        # --- Die Axiom 3b Logik (Deine aktuelle Implementierung) ---
        # Wir berechnen die LR so, dass wir GLAUBEN, wir landen bei 0.985
        target_rho = 0.985
        delta_needed = target_rho - rho_t
        
        # Hier liegt die Tautologie: Wenn das Ventil 'nominal_sensitivity' nutzt,
        # aber die Schicht lokal 'aktiver' ist, schießt es über das Ziel hinaus.
        valve_lr = delta_needed / (nominal_sensitivity * grad_norm + 1e-8)
        
        # --- Der echte Schritt ---
        with torch.no_grad():
            model[0].weight -= valve_lr * grad
            
        # --- Die nackte Wahrheit ---
        rho_after = get_spectral_radius(model[0])
        
        # Messung der Abweichung
        prediction_error = rho_after - target_rho
        
        results.append({
            "step": i,
            "rho_before": rho_t,
            "rho_after": rho_after,
            "error": prediction_error,
            "breach": rho_after > c_max
        })
        
    return results

# Audit starten
audit_results = run_empirical_audit()
leaks = [r for r in audit_results if r['breach']]

# Save full results to JSON
with open('fim_audit_results.json', 'w') as f:
    json.dump(audit_results, f, indent=2)

print(f"Echte Kontraktions-Brüche trotz Ventil: {len(leaks)}")