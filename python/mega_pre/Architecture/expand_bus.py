import torch
import os

# --- PFADE ANPASSEN ---
# Wir gehen direkt in deinen Emergency-Stop Ordner
BASE_PATH = r"C:\Users\ambas\Keeper_Run_4\Checkpoints_Run_4_1\run4_1_emergency_stop"
BUS_FILE = "cacr_bus_state.pt"
BUS_PATH = os.path.join(BASE_PATH, BUS_FILE)

TARGET_SIZE = 1000000 # Upgrade auf 1 Million Slots für das neue Pulver

def patch_bus():
    if not os.path.exists(BUS_PATH):
        print(f"❌ FEHLER: Die Datei wurde nicht gefunden!")
        print(f"Gesuchter Pfad: {BUS_PATH}")
        return

    print(f"[*] Lade CACR-Bus am offenen Herzen: {BUS_PATH}")
    # map_location='cpu' stellt sicher, dass wir kein VRAM verbrauchen
    state = torch.load(BUS_PATH, map_location='cpu')
    
    new_state = {}
    for key, tensor in state.items():
        old_size = tensor.size(0)
        
        # Initialisierung der neuen Fläche mit Standardwerten (aus deiner cacr_bus.py)
        if "confidence" in key:
            new_tensor = torch.full((TARGET_SIZE,), 0.5)
        elif "replacement_cost" in key:
            new_tensor = torch.full((TARGET_SIZE,), 0.1)
        else: # age, contradiction
            new_tensor = torch.zeros(TARGET_SIZE)
            
        # Die alten Daten (deine Simons-Axiome etc.) rüberkopieren
        new_tensor[:old_size] = tensor
        new_state[key] = new_tensor
        print(f"    -> {key}: von {old_size} auf {TARGET_SIZE} Slots erweitert.")

    # Sicherheits-Backup erstellen
    backup_path = BUS_PATH + ".bak"
    if os.path.exists(BUS_PATH):
        os.rename(BUS_PATH, backup_path)
        print(f"[✓] Backup der alten Datei erstellt: {backup_path}")

    # Speichern der neuen, großen Datei
    torch.save(new_state, BUS_PATH)
    print(f"\n[✓] OPERATION ERFOLGREICH!")
    print(f"Der Bus hat jetzt Platz für 1.000.000 Fragmente.")
    print(f"Du kannst den Run jetzt mit dem neuen Pulver (650k) starten.")

if __name__ == "__main__":
    patch_bus()