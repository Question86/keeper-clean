import torch


class AxiomaticPatcher:
    def __init__(self, model, config=None):
        self.model = model
        self.config = config or {"c_max": 48.0, "recovery_factor": 0.96}
        self.layers = [(n, m) for n, m in model.named_modules() if isinstance(m, torch.nn.Linear)]
        self._apply_attention_patch()
        print(f"🔍 PSI-Patcher: {len(self.layers)} Weight-Layer & Attention-Hooks aktiv.")

    def _apply_attention_patch(self):
        """Injiziert den Deep-Inference CUDA-Kernel in alle Attention-Layer."""
        for name, module in self.model.named_modules():
            if "self_attn" in name:
                original_forward = module.forward

                def patched_forward(*args, original_f=original_forward, **kwargs):
                    import psilong_extension as psi_cuda
                    outputs = original_f(*args, **kwargs)
                    
                    # Überprüfung: Hat der Layer Attention Weights (outputs[1])?
                    if isinstance(outputs, tuple) and len(outputs) > 1 and outputs[1] is not None:
                        # 1. Konvertierung für CUDA (Kernel braucht float32)
                        attn_weights = outputs[1].to(torch.float32)
                        
                        # 2. History-Check: Nutzen wir die zeitlichen Ketten?
                        if hasattr(self.model, 'index_history') and len(self.model.index_history) > 0:
                            # Wir stacken die History zu [Depth, N]. 
                            # .contiguous() ist KRITISCH für den linearen Speicherzugriff im Kernel!
                            history_tensor = torch.stack(list(self.model.index_history)).to(torch.int32).cuda().contiguous()
                            
                            depth = history_tensor.size(0)
                            bus_tensor = self.model.cacr_bus.get_full_state().to(torch.float32)
                            
                            # 3. Aufruf des Deep-Kernels
                            # Die Signatur entspricht jetzt: (scores, bus, history, depth, psi, lambda)
                            psi_cuda.launch_psilong(
                                attn_weights,
                                bus_tensor,
                                history_tensor,
                                depth,
                                1.0,  # base_psi
                                3.14  # base_lambda
                            )
                            
                            # 4. Zurück in den Modell-Dtype konvertieren und Re-Injektion
                            new_outputs = list(outputs)
                            new_outputs[1] = attn_weights.to(torch.bfloat16)
                            outputs = tuple(new_outputs)
                            
                    return outputs

                module.forward = patched_forward

    @torch.no_grad()
    def enforce_axioms(self):
        # ... (Dein bisheriger Weight-Clipping Code bleibt gleich) ...
        healed_count = 0
        max_rho = 0.0
        for name, layer in self.layers:
            w = layer.weight.detach().to(device="cuda", dtype=torch.float32)
            rho = torch.linalg.matrix_norm(w, ord='fro').item()
            if rho > self.config["c_max"]:
                scale = (self.config["c_max"] * self.config["recovery_factor"]) / rho
                layer.weight.data.mul_(scale)
                healed_count += 1
                rho = self.config["c_max"] * self.config["recovery_factor"]
            if rho > max_rho: max_rho = rho
        return healed_count, max_rho, 0.0