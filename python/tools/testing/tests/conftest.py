import builtins
import json
import importlib
import subprocess

# `requests` is a dependency of the project; import if available
try:
    import requests
except Exception:
    requests = None

# Inject into builtins so legacy tests that reference these names without imports succeed
builtins.json = json
builtins.importlib = importlib
builtins.subprocess = subprocess
builtins.requests = requests
