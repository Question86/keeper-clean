import torch
import os

# --- PFADE ---
base_path = r"C:\Users\ambas\Keeper_Run_4"
# Wir nehmen den Checkpoint von Step 140.000
bus_path = os.path.join(base_path, "Checkpoints_Run_4_1", "run4_1_step_140000", "cacr_bus_state.pt")
data_path = os.path.join(base_path, "paa_shredded_data.txt")

def scan_keeper_knowledge(top_n=50):
    # 1. Daten laden
    print(f"[*] Lade Fragmente aus {data_path}...")
    with open(data_path, "r", encoding="utf-8") as f:
        all_fragments = [line.strip() for line in f.readlines()]

    # 2. Bus-State laden
    print(f"[*] Lade CACR-Bus-State aus {bus_path}...")
    state = torch.load(bus_path, map_location="cpu")
    
    # Extraktion der Tensoren aus dem State-Dict
    costs = state['replacement_cost']
    conf = state['confidence']
    contra = state['contradiction']
    age = state['age']

    # 3. Top-Dogmen finden (Höchste Replacement Cost = "Heiligkeit")
    print(f"\n" + "="*60)
    print(f"🔥 DIE {top_n} DOGMEN (EBENE 2) - UNANTASTBARES WISSEN")
    print("="*60)
    
    values, indices = torch.topk(costs, top_n)
    
    for i in range(top_n):
        idx = indices[i].item()
        text = all_fragments[idx] if idx < len(all_fragments) else "[INDEX OUT OF RANGE]"
        print(f"#{i+1:02d} | Index: {idx:6d} | Cost: {costs[idx]:.4f} | Conf: {conf[idx]:.4f}")
        print(f"   > Inhalt: {text}\n")

    # 4. Krisenherde finden (Höchste Contradiction = Logische Reibung)
    print("\n" + "="*60)
    print(f"⚠️ DIE {top_n} KRISENHERDE - LOGISCHE DISSONANZ")
    print("="*60)
    
    c_values, c_indices = torch.topk(contra, top_n)
    
    for i in range(top_n):
        idx = c_indices[i].item()
        text = all_fragments[idx] if idx < len(all_fragments) else "[INDEX OUT OF RANGE]"
        print(f"#{i+1:02d} | Index: {idx:6d} | Contra: {contra[idx]:.4f} | Age: {age[idx]:.1f}")
        print(f"   > Inhalt: {text}\n")

if __name__ == "__main__":
    scan_keeper_knowledge()