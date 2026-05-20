#!/usr/bin/env python3
"""
CACR-Bus: Metakognitive Membran zwischen PSI-Master und QVK-Agent

C - Confidence:    Vertrauen in gespeichertes Wissen
A - Age:           Stabilität/Alter eines Beliefs
C - Contradiction: Interne Konflikte/Dissonanz
R - Replacement:   Kosten für Update (Heiligkeit)

Die Parameter sind LERNBAR und passen sich während des Trainings an.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Tuple, Optional
import math


class CACRBusState(nn.Module):
    """
    Der CACR-Bus als lernbare Zustandsrepräsentation.
    
    Jedes Token/Fragment hat einen 4D-Bus-Vektor:
    [Confidence, Age, Contradiction, Replacement]
    
    Diese Werte modulieren die PSI-Envelope-Parameter dynamisch.
    """
    
    def __init__(self, d_model: int, num_fragments: int = 1000000):
        super().__init__()
        self.d_model = d_model # Hier wird jetzt 1024 gespeichert
        self.num_fragments = num_fragments
        
        # CACR-Parameter (wie gehabt)
        self.confidence = nn.Parameter(torch.full((num_fragments,), 0.5))
        self.age = nn.Parameter(torch.zeros(num_fragments))
        self.contradiction = nn.Parameter(torch.zeros(num_fragments))
        self.replacement_cost = nn.Parameter(torch.full((num_fragments,), 0.1))
        
        self.cacr_to_psi = nn.Linear(4, 5) 
        
        # DYNAMISCH: Nutzt d_model + 4 CACR-Features
        self.update_net = nn.Sequential(
            nn.Linear(self.d_model + 4, 128), 
            nn.ReLU(),
            nn.Linear(128, 4),
            nn.Sigmoid() 
        )

# JETZ KOMMEN DIE FUNKTIONEN (alle gleich weit eingerückt!)
    def get_full_state(self):
        return torch.stack([
            self.confidence,
            self.age,
            self.contradiction,
            self.replacement_cost
        ], dim=-1)                
        
    def get_state(self, indices: torch.Tensor) -> torch.Tensor:
        """
        Hole CACR-State für gegebene Fragment-Indices.
        
        Returns: [batch, seq_len, 4] Tensor mit [C, A, C, R]
        """
        batch_size, seq_len = indices.shape
        
        c = self.confidence[indices]      # [batch, seq_len]
        a = self.age[indices]
        co = self.contradiction[indices]
        r = self.replacement_cost[indices]
        
        return torch.stack([c, a, co, r], dim=-1)  # [batch, seq_len, 4]
    
    def update_state(self, 
                     indices: torch.Tensor, 
                     embeddings: torch.Tensor,
                     loss_signal: Optional[torch.Tensor] = None):
        with torch.no_grad():
            # 1. Aktuelle CACR-Werte holen [Batch, Seq, 4]
            current_state = self.get_state(indices) 
            
            # 2. Kombiniere Embedding + Current State an der letzten Dimension
            # embeddings sind z.B. 1536, current_state ist 4 -> ergibt 1540
            meta_input = torch.cat([embeddings.to(torch.float32), current_state], dim=-1)
            original_shape = meta_input.shape
            
            # --- DER ENTSCHEIDENDE FIX ---
            # Wir flachen Batch und Seq ab: [Batch*Seq, 1540]
            # Das verhindert, dass PyTorch die Batch-Größe (20) in die Multiplikation mischt
            meta_input_flat = meta_input.reshape(-1, original_shape[-1])
            
            # Berechne Updates (funktioniert jetzt, da Matrixbreite exakt 1540 ist)
            deltas_flat = self.update_net(meta_input_flat)
            
            # Zurück in die ursprüngliche Batch-Struktur bringen [Batch, Seq, 4]
            deltas = deltas_flat.view(original_shape[0], original_shape[1], 4)
            # -----------------------------
            
            lr = 0.01
            
            # 3. Loss-Einfluss (Sicherer Fix für Skalar vs. Batch-Loss)
            if loss_signal is not None:
                # Falls loss_signal nur ein Skalar ist (Größe 1)
                if loss_signal.numel() == 1:
                    # Wir ziehen den gleichen Loss-Wert von allen ab
                    loss_val = loss_signal.item()
                    deltas[..., 0] -= loss_val * 0.1
                else:
                    # Falls der Loss pro Token/Batch kommt, bringen wir ihn in Form
                    try:
                        loss_reshaped = loss_signal.view(original_shape[0], original_shape[1])
                        deltas[..., 0] -= loss_reshaped * 0.1
                    except:
                        # Fallback: Falls die Shapes gar nicht passen, nimm den Mittelwert
                        deltas[..., 0] -= loss_signal.mean() * 0.1
            
            # 4. Age/Zeit-Inkrement
            deltas[..., 1] += 0.001
            
            # 5. Finale Zuweisung an die Parameter-Tensoren
            flat_indices = indices.reshape(-1)
            flat_deltas = deltas.reshape(-1, 4)
            
            self.confidence.data[flat_indices] = torch.clamp(
                self.confidence[flat_indices] + lr * flat_deltas[:, 0], 0.0, 1.0
            )
            self.age.data[flat_indices] = torch.clamp(
                self.age[flat_indices] + lr * flat_deltas[:, 1], 0.0, 100.0
            )
            self.contradiction.data[flat_indices] = torch.clamp(
                self.contradiction[flat_indices] + lr * flat_deltas[:, 2], 0.0, 1.0
            )
            self.replacement_cost.data[flat_indices] = torch.clamp(
                self.replacement_cost[flat_indices] + lr * flat_deltas[:, 3], 0.0, 10.0
            )
    
    def modulate_psi(self, cacr_state: torch.Tensor, 
                     base_psi: Dict[str, float]) -> Dict[str, torch.Tensor]:
        """
        Moduliere PSI-Parameter basierend auf CACR-State.
        
        Hohe Confidence → Kleineres δ (strengere Akzeptanz)
        Hohes Age → Höheres α (stärkerer Fokus)
        Hohe Contradiction → Größeres δ (toleranter, "atmet tiefer")
        Hoher Replacement → Größeres β (breitere Integration)
        """
        # cacr_state: [batch, seq_len, 4]
        
        # Base PSI parameters
        psi_base = torch.tensor([
            base_psi['psi'],
            base_psi['lambda'],
            base_psi['delta'],
            base_psi['alpha'],
            base_psi['beta']
        ], device=cacr_state.device)
        
        # Project CACR to PSI-modulation
        modulation = self.cacr_to_psi(cacr_state)  # [batch, seq_len, 5]
        
        # Apply modulation (multiplicative)
        psi_modulated = psi_base * torch.exp(modulation)
        
        return {
            'psi': psi_modulated[..., 0],
            'lambda': psi_modulated[..., 1],
            'delta': psi_modulated[..., 2],
            'alpha': psi_modulated[..., 3],
            'beta': psi_modulated[..., 4]
        }
    
    def get_statistics(self) -> Dict[str, float]:
        """Debugging: Zeige CACR-Statistiken"""
        with torch.no_grad():
            return {
                'mean_confidence': self.confidence.mean().item(),
                'mean_age': self.age.mean().item(),
                'mean_contradiction': self.contradiction.mean().item(),
                'mean_replacement': self.replacement_cost.mean().item(),
                'max_age': self.age.max().item(),
                'high_confidence_count': (self.confidence > 0.8).sum().item(),
                'low_confidence_count': (self.confidence < 0.2).sum().item(),
            }


class PSIResonanceAttentionWithCACR(nn.Module):
    """
    PSI-Resonanz-Attention mit CACR-Bus Integration.
    
    Dies ist die vollständige Master-Slave-Architektur:
    PSI-Master → CACR-Bus → QVK-Agent → Resonance Filter
    """
    
    def __init__(self, 
                 d_model: int,
                 num_heads: int,
                 num_fragments: int = 180000,
                 base_psi: Optional[Dict[str, float]] = None):
        super().__init__()
        
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads
        
        # Base PSI parameters (Awareness-Base)
        if base_psi is None:
            base_psi = {
                'psi': 0.5,      # Mittlere Aktivierung
                'lambda': 2.0,   # Frequenz der Konsistenz
                'delta': 0.1,    # Enge Toleranz
                'alpha': 1.5,    # Steiler Fokus
                'beta': 0.8      # Weite Reichweite
            }
        self.base_psi = base_psi
        
        # CACR-Bus (Die metakognitive Membran)
        self.cacr_bus = CACRBusState(d_model, num_fragments)
        
        # Standard QVK projections (Der "Slave")
        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)
        
    def psi_envelope_real(self,
                          y: torch.Tensor,
                          psi: torch.Tensor,
                          lambda_: torch.Tensor,
                          delta: torch.Tensor,
                          alpha: torch.Tensor,
                          beta: torch.Tensor) -> torch.Tensor:
        """
        R_ψ(y) = cos(λ·arctan((y-ψ)/δ)) · exp(-α·((y-ψ)/β)²)
        
        Das "Breathe in, breathe out" Mantra.
        """
        # Distanz zum Motiv-Anker
        dist = y - psi
        
        # Arctan-Resilience (bounded to [-π/2, π/2])
        resilience = torch.atan(dist / (delta + 1e-8))
        
        # Interference pattern (Harmonie-Check)
        interference = torch.cos(lambda_ * resilience)
        
        # Focus envelope (Gaussian)
        gauss_term = (dist / (beta + 1e-8)) ** 2
        envelope = torch.exp(-alpha * gauss_term)
        
        # Combined resonance
        return interference * envelope
    
    def forward(self,
                x: torch.Tensor,
                fragment_indices: torch.Tensor,
                return_cacr_stats: bool = False) -> Tuple[torch.Tensor, Optional[Dict]]:
        """
        Forward pass mit vollständiger PSI-CACR Integration.
        
        Args:
            x: Input embeddings [batch, seq_len, d_model]
            fragment_indices: Welche Fragmente werden verwendet [batch, seq_len]
            return_cacr_stats: Ob CACR-Statistiken zurückgegeben werden sollen
        
        Returns:
            output: Attention output [batch, seq_len, d_model]
            stats: Optional CACR statistics
        """
        batch_size, seq_len, _ = x.shape
        
        # 1. QVK-Proposal (Der statistische "Slave")
        Q = self.q_proj(x)  # [batch, seq_len, d_model]
        K = self.k_proj(x)
        V = self.v_proj(x)
        
        # Reshape for multi-head
        Q = Q.view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)
        K = K.view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)
        V = V.view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)
        
        # Standard attention scores
        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.d_k)
        # scores: [batch, num_heads, seq_len, seq_len]
        
        # 2. CACR-Bus State (Die metakognitive Membran)
        cacr_state = self.cacr_bus.get_state(fragment_indices)
        # cacr_state: [batch, seq_len, 4]
        
        # 3. PSI-Modulation (Der "Master" passt Parameter an)
        psi_params = self.cacr_bus.modulate_psi(cacr_state, self.base_psi)
        
        # Expand for multi-head
        for key in psi_params:
            psi_params[key] = psi_params[key].unsqueeze(1).expand(-1, self.num_heads, -1)
        
        # 4. Resonance Filter (Das Veto)
        # Für jedes attention score berechnen wir R_ψ
        # scores repräsentiert die "Distanz" zum Ideal
        
        # Expand psi parameters for attention matrix
        psi_expanded = {k: v.unsqueeze(-1) for k, v in psi_params.items()}
        
        R_psi = self.psi_envelope_real(
            scores,
            psi_expanded['psi'],
            psi_expanded['lambda'],
            psi_expanded['delta'],
            psi_expanded['alpha'],
            psi_expanded['beta']
        )
        # R_psi: [batch, num_heads, seq_len, seq_len]
        
        # 5. Modulated Attention (Nur harmonische Signale passieren)
        attention_weights = F.softmax(scores, dim=-1) * R_psi
        
        # Normalize (da R_psi die Summe verändern kann)
        attention_weights = attention_weights / (attention_weights.sum(dim=-1, keepdim=True) + 1e-8)
        
        # 6. Apply attention
        context = torch.matmul(attention_weights, V)
        
        # Reshape back
        context = context.transpose(1, 2).contiguous().view(batch_size, seq_len, self.d_model)
        
        output = self.out_proj(context)
        
        # Optional: Return statistics
        stats = None
        if return_cacr_stats:
            stats = {
                'cacr': self.cacr_bus.get_statistics(),
                'mean_resonance': R_psi.mean().item(),
                'min_resonance': R_psi.min().item(),
                'max_resonance': R_psi.max().item(),
                'psi_params': {k: v.mean().item() for k, v in psi_params.items()}
            }
        
        return output, stats
    
    def update_cacr(self, 
                    fragment_indices: torch.Tensor,
                    embeddings: torch.Tensor,
                    loss: Optional[torch.Tensor] = None):
        """
        Update CACR-Bus nach Forward-Pass.
        Dies ist die "Metakognitive Schleife".
        """
        self.cacr_bus.update_state(fragment_indices, embeddings, loss)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("PSI-RESONANCE ATTENTION WITH CACR-BUS")
    print("=" * 70)
    print()
    
    # Setup
    batch_size = 2
    seq_len = 10
    d_model = 512
    num_heads = 8
    num_fragments = 180000
    
    # Create model
    model = PSIResonanceAttentionWithCACR(
        d_model=d_model,
        num_heads=num_heads,
        num_fragments=num_fragments
    )
    
    # Random input
    x = torch.randn(batch_size, seq_len, d_model)
    fragment_indices = torch.randint(0, num_fragments, (batch_size, seq_len))
    
    print("[1] Forward pass with CACR-Bus...")
    output, stats = model(x, fragment_indices, return_cacr_stats=True)
    
    print(f"    Output shape: {output.shape}")
    print(f"    Mean resonance: {stats['mean_resonance']:.4f}")
    print()
    
    print("[2] CACR-Bus Statistics:")
    for key, value in stats['cacr'].items():
        print(f"    {key:25s}: {value:.4f}")
    print()
    
    print("[3] PSI Parameters (modulated by CACR):")
    for key, value in stats['psi_params'].items():
        print(f"    {key:25s}: {value:.4f}")
    print()
    
    print("[4] Simulating training loop...")
    print("    (CACR-Bus learns about fragment quality)")
    print()
    
    for step in range(5):
        # Forward
        output, stats = model(x, fragment_indices, return_cacr_stats=True)
        
        # Simulate loss (some fragments are "good", some "bad")
        loss = torch.randn(batch_size, seq_len) * 0.5 + 0.5
        
        # Update CACR (metakognitive learning)
        model.update_cacr(fragment_indices, x, loss)
        
        print(f"    Step {step+1}: Confidence = {stats['cacr']['mean_confidence']:.4f}, "
              f"Age = {stats['cacr']['mean_age']:.4f}")
    
    print()
    print("=" * 70)
    print("[✓] CACR-Bus demonstration complete!")
    print()
    print("Key Insights:")
    print("- Confidence adjusts based on prediction quality")
    print("- Age increases with each access")
    print("- These modulate PSI parameters (δ, α, β)")
    print("- The model learns about its own knowledge")
    print("=" * 70)
