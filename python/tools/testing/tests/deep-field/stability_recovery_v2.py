import torch

class AdaptiveStabilityValve:
    def __init__(self, optimizer, model, c_max=0.99, eps=1e-8):
        self.optimizer = optimizer
        self.model = model
        self.c_max = c_max
        self.eps = eps
        # Puffer, um nicht exakt auf der Kante zu tanzen (basierend auf Audit-Gap)
        self.safety_buffer = 0.98 

    def estimate_local_curvature(self):
        """
        Berechnet die Diagonale der Fisher-Information (FIM) als 
        empirische Sensitivität statt einer statischen Zahl.
        """
        total_curvature = 0.0
        for p in self.model.parameters():
            if p.grad is not None:
                # Das Quadrat des Gradienten ist ein Proxy für die FIM-Diagonale
                # Es misst, wie stark die Output-Verteilung auf dieses Gewicht reagiert
                diag_fim = torch.mean(p.grad**2)
                total_curvature += diag_fim.item()
        return total_curvature

    def step(self):
        # 1. Aktuellen Spektralradius messen (Axiom 3)
        # Für Deep Networks nutzen wir die Frobenius-Norm als Proxy oder Power Iteration
        with torch.no_grad():
            rho_t = torch.linalg.matrix_norm(self.model[0].weight, ord=2).item()

        # 2. Lokale Krümmung (Fischer) messen
        sensitivity = self.estimate_local_curvature()
        
        # 3. Das Adaptive Ventil
        for group in self.optimizer.param_groups:
            base_lr = group['lr']
            grad_norm = sum(p.grad.norm()**2 for p in self.model.parameters() if p.grad is not None)**0.5
            
            # Die Distanz zum Limit
            delta = self.c_max - rho_t
            
            if delta <= 0:
                group['lr'] = 0.0 # Absolute Notbremse
            else:
                # Dynamische Berechnung: Je höher die Fischer-Krümmung, 
                # desto kleiner muss die LR sein.
                max_safe_lr = delta / (sensitivity * grad_norm + self.eps)
                
                # Wir drosseln nur, wenn die base_lr das Risiko-Limit reißt
                if base_lr > max_safe_lr:
                    group['lr'] = max_safe_lr * self.safety_buffer
                    
        self.optimizer.step()

def test_adaptive_valve():
    """
    Testet das adaptive Ventil in einem simulierten Training.
    Ziel: Rho soll stabil unter c_max bleiben, auch bei aggressiven LRs.
    """
    import torch.nn as nn
    
    # Ein einfaches MLP
    model = nn.Sequential(
        nn.Linear(10, 10, bias=False),
        nn.Tanh()
    )
    
    # Seed initial spectral norm in 0.9-0.99 range
    with torch.no_grad():
        weight = model[0].weight
        current_norm = torch.linalg.matrix_norm(weight, ord=2)
        target_norm = torch.rand(1).item() * 0.09 + 0.9  # Random between 0.9 and 0.99
        weight.mul_(target_norm / current_norm)
    
    # Aggressive LR, um Instabilität zu provozieren
    optimizer = torch.optim.SGD(model.parameters(), lr=1.0)
    
    valve = AdaptiveStabilityValve(optimizer, model, c_max=0.99)
    
    results = []
    
    for step in range(50):
        # Simuliere einen Batch: Dummy-Input und Loss
        x = torch.randn(32, 10)
        y = torch.randn(32, 10)
        
        output = model(x)
        loss = torch.mean((output - y)**2)
        
        loss.backward()
        
        # Messung vor dem Schritt
        with torch.no_grad():
            rho_before = torch.linalg.matrix_norm(model[0].weight, ord=2).item()
        
        # Der adaptive Schritt
        valve.step()
        
        # Messung nach dem Schritt
        with torch.no_grad():
            rho_after = torch.linalg.matrix_norm(model[0].weight, ord=2).item()
        
        results.append({
            "step": step,
            "rho_before": rho_before,
            "rho_after": rho_after,
            "breach": rho_after > 0.99,
            "lr_used": optimizer.param_groups[0]['lr']
        })
        
        # Reset gradients
        optimizer.zero_grad()
    
    breaches = [r for r in results if r['breach']]
    print(f"Adaptive Valve Test: {len(breaches)} breaches in 50 steps")
    return results

if __name__ == "__main__":
    import sys
    output_file = sys.argv[1] if len(sys.argv) > 1 else 'stability_recovery_results.json'
    test_results = test_adaptive_valve()
    
    import json
    with open(output_file, 'w') as f:
        json.dump(test_results, f, indent=2)