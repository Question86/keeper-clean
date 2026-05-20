import torch
import time
import os
import sys
import gc
from torch.utils.cpp_extension import load
from transformers import AutoModelForCausalLM, AutoTokenizer
from AxiomaticPatcher import AxiomaticPatcher
from cacr_bus import CACRBusState

# --- 1. CUDA COMPILER SETUP ---
msvc_path = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64"
ninja_path = r"C:\Users\ambas\AppData\Roaming\Python\Python313\Scripts"
os.environ["PATH"] += os.pathsep + msvc_path + os.pathsep + ninja_path

# --- SETUP PFADE & AUTOMATISIERUNG ---
base_path = r"C:\Users\ambas\Keeper_Run_4"
checkpoint_dir = r"C:\Users\ambas\Keeper_Run_4\Checkpoints_Run_4_1\Y_1"
os.makedirs(checkpoint_dir, exist_ok=True)

data_path = os.path.join(base_path, "paa_shredded_data_physics.txt")
# FIX 1: Pfad zum Kernel wieder rein!
final_kernel_path = os.path.join(base_path, "Kernel", "final_kernel.cu") 

def get_latest_checkpoint(folder):
    files = [f for f in os.listdir(folder) if f.startswith("cacr_checkpoint_step_") and f.endswith(".pt")]
    if not files: return None
    files.sort(key=lambda x: int(x.split('_')[-1].split('.')[0]), reverse=True)
    return os.path.join(folder, files[0])

latest_ckpt = get_latest_checkpoint(checkpoint_dir)

if latest_ckpt:
    print(f"🎯 Biest gefunden! Lade Hybrid-Checkpoint: {latest_ckpt}")
    model_id = checkpoint_dir 
    is_resume = True
else:
    model_id = r"C:\Users\ambas\Keeper_Run_4\Checkpoints_Run_4_1\run4_1_emergency_stop"
    print(f"⚠️ Kein Hybrid-Checkpoint gefunden. Starte von: {model_id}")
    is_resume = False

# ==============================================================================
# AB HIER ERSETZEN (Alles von JIT KERNEL bis OPTIMIZER)
# ==============================================================================

# --- 2. JIT KERNEL LOADING ---
print("[*] Kompiliere & Lade PSI-Master-Kernel...")
try:
    psi_cuda = load(
        name="psilong_extension",
        sources=[final_kernel_path],
        verbose=True
    )
    print("✅ PSI-Kernel erfolgreich geladen.")
except Exception as e:
    print(f"❌ CUDA-Fehler beim Laden: {e}")
    sys.exit(1)

# --- HYPERPARAMETER & GLOBALS ---
ema_alpha = 0.01      # Der Glättungsfaktor (bleibt konstant)
ema_loss = None       # Wird beim ersten Step nach dem Laden initialisiert
start_step = 1        # Standardwert, wird gleich vom Checkpoint überschrieben

# --- MODELL & BUS LADEN ---
# Wir laden das Skelett immer von hier, damit HuggingFace nicht meckert:
base_model_path = r"C:\Users\ambas\Keeper_Run_4\Checkpoints_Run_4_1\run4_1_emergency_stop"

print(f"🏗️ Lade Modell-Architektur von: {base_model_path}")

model = AutoModelForCausalLM.from_pretrained(
    base_model_path, 
    torch_dtype=torch.bfloat16, 
    device_map="auto",
    attn_implementation="eager", 
    local_files_only=True
)

tokenizer = AutoTokenizer.from_pretrained(base_model_path)

# Jetzt das Biest injizieren, falls vorhanden
if is_resume:
    print(f"🧠 Biest-Injektion: Überschreibe Gewichte mit {latest_ckpt}...")
    checkpoint = torch.load(latest_ckpt, map_location="cuda")
    
    # FIX: strict=False erlaubt es, die Modell-Gewichte zu laden, 
    # auch wenn die Bus-Gewichte im File "zu viel" sind.
    model.load_state_dict(checkpoint['model_state_dict'], strict=False)
    start_step = checkpoint.get('step', 0) + 1

actual_d_model = model.config.hidden_size 
print(f"📏 Detektierte Hidden-Size: {actual_d_model}")

# Bus erstellen (Ebene 3)
bus = CACRBusState(d_model=actual_d_model, num_fragments=1000000)

if is_resume:
    print("✅ Lade Bus-Status direkt aus dem Hybrid-Checkpoint...")
    bus.load_state_dict(checkpoint['cacr_bus_state'])
    start_step = checkpoint['step'] + 1
else:
    # Nur wenn wir KEIN Biest haben, suchen wir die alte kleine Datei
    cacr_bus_state_path = os.path.join(model_id, "cacr_bus_state.pt")
    if os.path.exists(cacr_bus_state_path):
        state = torch.load(cacr_bus_state_path, map_location="cpu")
        bus.load_state_dict(state, strict=False)
        print("✅ Alte Bus-Parameter geladen.")
    start_step = 1

# Bus auf GPU und ans Modell binden
bus = bus.to("cuda")
model.cacr_bus = bus

# 4. Patcher und Optimizer
patcher = AxiomaticPatcher(model)
optimizer = torch.optim.AdamW(model.parameters(), lr=5e-6)

# Optimizer-Zustand wiederherstellen
if is_resume:
    optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    print(f"🚀 Optimizer bereit. Fortsetzung bei Step {start_step}")

# ==============================================================================
# AB HIER GEHT DEIN ALTER CODE WEITER (DATEN LADEN etc.)
# ==============================================================================

# --- DATEN LADEN MIT SHUFFLE-GARANTIE ---
import random

with open(data_path, "r", encoding="utf-8") as f:
    # Wir filtern und laden alles
    test_chains = [line.strip() for line in f if len(line.strip()) > 5]

# Wir setzen einen Seed, damit die "Zufälligkeit" bei jedem Resume gleich bleibt
# Sonst würde das Modell bei Step 50k nach einem Neustart andere Daten sehen als vorher
random.seed(42) 
random.shuffle(test_chains)

print(f"🎲 Würfel gefallen: {len(test_chains)} Snippets wurden geshuffelt.")

# --- HIER EINFÜGEN ---
history_depth = 5 
index_history = []
# ---------------------

print(f"\n🚀 KEEPER RUN 4.1 STARTET (CUDA ACCELERATED)")
print("-" * 50)

def save_metacognitive_checkpoint(model, optimizer, step, rho_val, checkpoint_dir):
    """
    Speichert das Modell inklusive der lernbaren CACR-Bus Parameter.
    """
    path = os.path.join(checkpoint_dir, f"cacr_checkpoint_step_{step}.pt")
    
    checkpoint = {
        'step': step,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        # Wir speichern den gesamten state_dict des Bus, da dieser 
        # die gelernten Parameter (confidence, age, etc.) enthält.
        'cacr_bus_state': model.cacr_bus.state_dict(), 
        'rho_val': rho_val,
    }
    
    temp_path = path + ".tmp"
    torch.save(checkpoint, temp_path)
    os.replace(temp_path, path)
    print(f"💾 Metakognitiver Checkpoint gesichert: Step {step} | Rho: {rho_val:.4f}")

MAX_SEQ_LEN = 64 # Wichtig für das Padding

# --- PROFESSIONELLES LOGGING INITIALISIEREN ---
log_file_path = "keeper_run_4_1_metrics.txt"

# Falls die Datei noch nicht existiert, Header schreiben
if not os.path.exists(log_file_path):
    with open(log_file_path, "w", encoding="utf-8") as f:
        f.write("Timestamp;Step;EMA_Loss;Bus_Confidence;Rho_Alignment\n")

def log_metrics(step, loss, conf, rho):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp};{step};{loss:.4f};{conf:.4f};{rho:.4f}\n"
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(log_line)
try:
    for i, chain in enumerate(test_chains[start_step-1:], start=start_step):
        t0 = time.time()
        
        # 1. Tokenizer mit fester max_length für die History-Stabilität
        inputs = tokenizer(chain, return_tensors="pt", truncation=True, max_length=MAX_SEQ_LEN).to("cuda")
        if inputs["input_ids"].size(1) < 2: continue

        # 2. Fragment-Indices berechnen
        fragment_indices = inputs["input_ids"] % 700000
        actual_len = fragment_indices.shape[1] # Wie lang ist der aktuelle Satz?

        # --- NEU: PADDING LOGIK (Damit der Crash aufhört) ---
        if actual_len < MAX_SEQ_LEN:
            pad_size = MAX_SEQ_LEN - actual_len
            padding = fragment_indices[:, -1:].expand(1, pad_size)
            indices_padded = torch.cat([fragment_indices, padding], dim=1)
        else:
            indices_padded = fragment_indices

        # 3. In die History speichern
        index_history.append(indices_padded.float())
        if len(index_history) > history_depth:
            index_history.pop(0)
            
        # 4. Durchschnitt berechnen (Ebene 3)
        # Dank Padding sind jetzt alle Tensors in der History [1, 64] groß -> Kein Crash mehr!
        effective_indices_padded = torch.mean(torch.stack(index_history), dim=0).long()

        # 5. Zurückschneiden auf die echte Satzlänge für das Modell
        effective_indices = effective_indices_padded[:, :actual_len]

        # 6. Sicherheits-Clamp & Zuweisung
        safe_indices = torch.clamp(effective_indices, 0, 999999).to(torch.int32).to("cuda")
        model.current_indices = safe_indices
        
        # --- FORWARD PASS ---
        outputs = model(**inputs, labels=inputs["input_ids"], 
                        output_attentions=True, 
                        output_hidden_states=True)
        loss = outputs.loss

        # --- BUS-UPDATE ---
        real_embeddings = outputs.hidden_states[-1].detach()
        # safe_indices und real_embeddings haben jetzt beide die Länge 'actual_len'
        model.cacr_bus.update_state(safe_indices, real_embeddings, loss.detach())   
        
        last_indices = fragment_indices.detach().cpu()

        # Backward & Optimization
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=0.5)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        
        healed, max_rho, _ = patcher.enforce_axioms()
        ema_loss = loss.item() if (ema_loss is None) else (1 - ema_alpha) * ema_loss + ema_alpha * loss.item()
        
        # REGULÄRES SPEICHERN (Alle 15000 Steps)
        if i % 15000 == 0:
            save_metacognitive_checkpoint(model, optimizer, i, max_rho, checkpoint_dir)
        
        if i % 10 == 0:
            avg_conf = model.cacr_bus.confidence[safe_indices.long()].mean().item()
            # In die Konsole
            print(f"Step {i} | EMA-Loss: {ema_loss:.4f} | Bus-Conf: {avg_conf:.4f} | Rho: {max_rho:.2f}")
            # In die Datei
            log_metrics(i, ema_loss, avg_conf, max_rho)

except KeyboardInterrupt:
    print("\n[!] Emergency Stop.")
    save_metacognitive_checkpoint(model, optimizer, i, max_rho, checkpoint_dir)
    print("💾 Letzter Checkpoint gesichert vor dem Stopp.")