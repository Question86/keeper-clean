import re

# FIX: r-Präfix vor dem Pfad
input_file = r"C:\Users\ambas\Keeper_Run_4\paa_shredded_data.txt"
output_file = "paa_shredded_data_2.txt"

def shred_logic(text):
    # Trennung nach Satzzeichen, behält das Zeichen im Split-Ergebnis
    pattern = r'([,;:.?!])'
    parts = re.split(pattern, text)
    
    shredded = []
    # Falls der Text kein Satzzeichen am Ende hat, ist die Länge von parts ungerade
    for i in range(0, len(parts)-1, 2):
        fragment = (parts[i] + parts[i+1]).strip()
        if len(fragment) > 5:
            shredded.append(fragment + "\n")
            
    # Kleiner Catch für Textreste ohne abschließendes Satzzeichen
    if len(parts) % 2 != 0:
        last_part = parts[-1].strip()
        if len(last_part) > 5:
            shredded.append(last_part + "\n")
            
    return shredded

with open(input_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

all_shredded = []
for line in lines:
    all_shredded.extend(shred_logic(line))

with open(output_file, "w", encoding="utf-8") as f:
    f.writelines(all_shredded)

print(f"✅ Zertrümmerung abgeschlossen! Neue Anzahl: {len(all_shredded)} Fragmente.")