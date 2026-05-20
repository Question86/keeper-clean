import os
import random
import fitz  # PyMuPDF
from typing import List

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extrahiert sauberen Text aus PDFs."""
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text("text") + "\n\n"
    except Exception as e:
        print(f"⚠️ Fehler beim Lesen von {pdf_path}: {e}")
    return text

def build_paa_pdf_chains(input_folder: str, output_file: str, b=3, d=5):
    """
    Erstellt Ketten mit Tiefe d=5.
    Ziel: 5-Hop transitive Inferenz ermöglichen.
    """
    all_nodes = []
    
    # 1. EXTRACTION
    print(f"🔍 Scanne {input_folder} nach PDF-Material...")
    for filename in os.listdir(input_folder):
        if filename.endswith(".pdf"):
            path = os.path.join(input_folder, filename)
            raw_text = extract_text_from_pdf(path)
            
            # Semantic Chunking: Wir trennen strikter nach Absätzen
            paragraphs = [p.strip() for p in raw_text.split('\n\n') if len(p.strip()) > 80]
            all_nodes.extend(paragraphs)
            print(f"  - {filename}: {len(paragraphs)} Axiome gefunden.")

    if len(all_nodes) < d:
        print("❌ Zu wenig Daten für Tiefe d=5!")
        return

    # 2. TRANSITIVE CHAIN GENERATION (Complexity d=5)
    print(f"🧶 Webe transitive Ketten (Tiefe d={d}, Branching b={b})...")
    with open(output_file, 'w', encoding='utf-8') as out:
        # Wir generieren mehr Ketten, um die 52x Konnektivität zu nutzen
        for i in range(len(all_nodes) * 2): 
            current_chain = []
            # Zufälliger Startpunkt für jede Kette
            current_idx = random.randint(0, len(all_nodes) - 1)
            
            for step in range(d):
                # Säuberung für das Training (keine Zeilenumbrüche innerhalb eines Knotens)
                clean_node = all_nodes[current_idx].replace('\n', ' ').replace('\r', '')
                current_chain.append(clean_node)
                
                # Branching b=3: Wir springen im "Wissensnetz"
                # Erhöht die Wahrscheinlichkeit für weit entfernte Verknüpfungen
                jump = random.randint(1, b)
                current_idx = (current_idx + jump) % len(all_nodes)
            
            # Speichern im PAA-Format
            out.write(" |NEXT_STEP| ".join(current_chain) + "\n")

    print(f"✅ Success: {len(all_nodes) * 2} Ketten in {output_file} gespeichert.")

# AUSFÜHRUNG
if __name__ == "__main__":
    # Deine Pfade bleiben erhalten
    input_dir = r"D:\Keeper-Clean-Loop1\tests\deep-field\Test_v0.1+\prep_data_set\Raw_Content\Sample 1 - Period system content"
    output_path = r"D:\Keeper-Clean-Loop1\tests\deep-field\Test_v0.1+\prep_data_set\paa_pdf_training_data.txt"
    
    # Wir setzen d=5 für den optimalen Token-Sweet-Spot
    build_paa_pdf_chains(input_dir, output_path, b=3, d=7)