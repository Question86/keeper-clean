# MODE: SCRIPT\n\n"""Wrapper to run the POC script with an explicit env var for OLLAMA_MODEL."""
import os
import subprocess

env = os.environ.copy()
env['OLLAMA_MODEL'] = env.get('OLLAMA_MODEL', 'mixtral:8x7b')
cmd = ['python', 'tasks/poc_task_0022.py', '--mode', 'real', '--outdir', 'samples/task_0022_real_run7']
print('Running:', ' '.join(cmd), 'with OLLAMA_MODEL=', env['OLLAMA_MODEL'])
proc = subprocess.run(cmd, env=env)
print('Exit code:', proc.returncode)
