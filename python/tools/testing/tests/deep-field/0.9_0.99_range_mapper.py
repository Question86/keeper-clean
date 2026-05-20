import numpy as np
import pandas as pd

def scan_dynamic_range(c_max=0.99, sensitivity=10.0, grad_norm=1.0):
    results = []
    # Wir scannen den Bereich von 0.5 bis 1.05 in feinen Schritten
    rho_range = np.arange(0.5, 1.05, 0.005)
    
    for rho_t in rho_range:
        # Formel aus deinem axiom3b:
        # max_permissible = (c_max - rho_t) / (sensitivity * grad_norm)
        delta = c_max - rho_t
        if delta <= 0:
            status = "BREACH"
            attenuation = 0.0 # Kompletter Stopp
        else:
            max_permissible = delta / (sensitivity * grad_norm + 1e-8)
            # Wir nehmen eine Standard-LR von 0.1 an
            attenuation = min(1.0, max_permissible / 0.1)
            status = "ACTIVE" if attenuation < 1.0 else "STABLE"
            
        results.append({
            "rho": rho_t,
            "efficiency": attenuation * 100, # In Prozent
            "status": status
        })
    return pd.DataFrame(results)

# Daten generieren
df = scan_dynamic_range()
print(df)