import torch
import torch.nn as nn
from Test_v0.1+\AxiomaticPatcher import AxiomaticPatcher, log_status

# Create a simple model to test the patcher (since full Mistral is large)
model = nn.Sequential(
    nn.Linear(10, 10),
    nn.ReLU(),
    nn.Linear(10, 10)
)

# Dummy optimizer
optimizer = torch.optim.SGD(model.parameters(), lr=0.01)

# Initialize patcher
patcher = AxiomaticPatcher(model)

# Simulate a few training steps
for step in range(10):
    # Dummy forward pass
    x = torch.randn(32, 10)
    y = torch.randn(32, 10)
    output = model(x)
    loss = torch.mean((output - y)**2)
    
    loss.backward()
    
    # Enforce axioms before optimizer step
    healed, max_rho = patcher.enforce_axioms()
    
    # Log status
    log_status(step, loss.item(), healed, max_rho)
    
    optimizer.step()
    optimizer.zero_grad()

print("Test completed!")