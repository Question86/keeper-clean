import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from AxiomaticPatcher import AxiomaticPatcher, log_status

# 1. SETUP: Load Mistral in 4-bit (Essential for 8GB VRAM)
model_path = "./your_mistral_folder" # UPDATE THIS TO YOUR MODEL PATH
tokenizer = AutoTokenizer.from_pretrained(model_path)

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_quant_type="nf4"
)

print("⏳ Loading model into VRAM...")
model = AutoModelForCausalLM.from_pretrained(
    model_path, 
    quantization_config=bnb_config,
    device_map="auto"
)

# 2. INITIALIZE: Activate the Axiomatic Shield
patcher = AxiomaticPatcher(model)

# 3. TEST DATA: Load your generated chains
with open("paa_pdf_training_data.txt", "r", encoding="utf-8") as f:
    test_chains = f.readlines()

# 4. EXECUTE: The "Dry Run"
print("🚀 Starting Axiomatic Stress Test...")
model.train() # Set to train mode to activate gradients

for i, chain in enumerate(test_chains[:10]): # Start with 10 chains
    # Tokenize the chain
    inputs = tokenizer(chain, return_tensors="pt", truncation=True, max_length=1024).to("cuda")
    
    # Forward pass
    outputs = model(**inputs, labels=inputs["input_ids"])
    loss = outputs.loss
    
    # Backward pass (This generates the 'heat' in the weights)
    loss.backward()
    
    # --- THE AXIOMATIC CHECK ---
    healed, max_rho = patcher.enforce_axioms()
    
    # Visual Studio Log
    log_status(i, loss.item(), healed, max_rho)
    
    # Clean up for next step
    model.zero_grad()