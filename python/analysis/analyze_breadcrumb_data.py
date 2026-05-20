import sys
import os

# Add parent directory to path to import from there
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from local_mistral_agent import LocalMistralAgent

agent = LocalMistralAgent()
response = agent.generate("Analyze the data in D:\\Keeper-Clean-Loop1\\breadcrumb_data_analysis")
print(response)