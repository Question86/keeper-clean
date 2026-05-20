# MODE: SCRIPT\n\n"""Run POC in real mode with specific environment variables set programmatically."""
import os
from tasks.poc_task_0022 import run

# Set desired model here
os.environ['OLLAMA_MODEL'] = os.environ.get('OLLAMA_MODEL', 'mixtral:8x7b')

rc = run(outdir='samples/task_0022_real_run6', mode='real')
print('POC exit code:', rc)
