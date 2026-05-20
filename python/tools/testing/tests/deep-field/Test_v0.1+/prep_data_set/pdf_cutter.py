import os
import random
import fitz  # PyMuPDF
from typing import List

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts clean text from PDF using PyMuPDF."""
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text("text") + "\n\n" # Preserve page breaks
    return text

def build_paa_pdf_chains(input_folder: str, output_file: str, b=3, d=5):
    all_nodes = []
    
    # 1. EXTRACTION & SEMANTIC CHUNKING
    print(f"🔍 Scanning {input_folder} for PDFs...")
    for filename in os.listdir(input_folder):
        if filename.endswith(".pdf"):
            path = os.path.join(input_folder, filename)
            raw_text = extract_text_from_pdf(path)
            
            # Split by double newlines to keep paragraphs (Axioms) together
            paragraphs = [p.strip() for p in raw_text.split('\n\n') if len(p.strip()) > 50]
            all_nodes.extend(paragraphs)
            print(f"  - Processed {filename}: Found {len(paragraphs)} nodes.")

    if not all_nodes:
        print("❌ No text found. Check if your PDFs are OCR-readable (not just images).")
        return

    # 2. CHAIN GENERATION (d=5 Random Walk)
    print(f"🧶 Weaving {len(all_nodes)} nodes into chains...")
    with open(output_file, 'w', encoding='utf-8') as out:
        for i in range(len(all_nodes)):
            current_chain = []
            current_idx = i
            
            for step in range(d):
                # Clean the text to keep it on one line for the training file
                clean_node = all_nodes[current_idx].replace('\n', ' ')
                current_chain.append(clean_node)
                
                # Branching b=3: Leap to a nearby node
                current_idx = (current_idx + random.randint(1, b)) % len(all_nodes)
            
            # Output format for your AxiomaticTrainer
            out.write(" |NEXT_STEP| ".join(current_chain) + "\n")

    print(f"✅ Success: Saved PAA chains to {output_file}")

# Execution
if __name__ == "__main__":
    input_folder = r"D:\Keeper-Clean-Loop1\tests\deep-field\Test_v0.1+\prep_data_set\Raw_Content\Sample 1 - Period system content"
    output_file = r"D:\Keeper-Clean-Loop1\tests\deep-field\Test_v0.1+\prep_data_set\paa_pdf_training_data.txt"
    build_paa_pdf_chains(input_folder, output_file)