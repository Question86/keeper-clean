import sys
import os
import importlib.util

# Import from parent directory
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Load the module from the parent directory
spec = importlib.util.spec_from_file_location("local_mistral_agent", os.path.join(parent_dir, "local_mistral_agent.py"))
mistral_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mistral_module)

LocalMistralAgent = mistral_module.LocalMistralAgent

agent = LocalMistralAgent()
response = agent.generate("Analyze the data in D:\\Keeper-Clean-Loop1\\breadcrumb_data_analysis")
print(response)