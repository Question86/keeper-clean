import torch

class UniversalPSIInjector:
    def __init__(self, model, tokenizer, bus_state):
        self.model = model
        self.tokenizer = tokenizer
        self.bus_state = bus_state
        # Wir nutzen einen hohen Index-Bereich für Injektionen
        self.injection_index_start = 170000 
        self.active_injections = {}

    def inject_statement(self, statement, custom_cost=5.0, custom_conf=0.1):
        """
        Legt ein Statement in den Bus und setzt die initialen CACR-Werte.
        """
        idx = self.injection_index_start + len(self.active_injections)
        self.active_injections[idx] = statement
        
        with torch.no_grad():
            # Wir setzen die Replacement Cost hoch (das Modell soll es ernst nehmen)
            # Aber die Confidence niedrig (es ist eine unsichere Hypothese)
            self.bus_state.replacement_cost[idx] = custom_cost
            self.bus_state.confidence[idx] = custom_conf
            self.bus_state.contradiction[idx] = 0.5 # Startet mit Dissonanz
            
        print(f"[*] Injected: '{statement[:50]}...' at Index {idx}")
        return idx

    def test_resonance(self, statement_idx):
        """
        Prüft, wie das Modell (Danube 3) auf das Statement reagiert,
        indem wir einen Forward-Pass mit PSI-Modulation machen.
        """
        text = self.active_injections[statement_idx]
        inputs = self.tokenizer(text, return_tensors="pt").to("cuda")
        indices = torch.tensor([[statement_idx]]).to("cuda")
        
        with torch.no_grad():
            outputs, stats = self.model(
                inputs['input_ids'], 
                fragment_indices=indices, 
                return_cacr_stats=True
            )
        
        return stats['mean_resonance'], stats['psi_params']