#!/usr/bin/env python3
"""
Autonomous VS Code Development Agent — CERN Scanner Pipeline
Liest AGENT_CONTEXT.md, baut fehlende Files, testet, debuggt.

LLM-Integration:
  - Primär:  Ollama (lokal, kostenlos) → Mistral / Codellama / etc.
  - Fallback: OpenAI API (gpt-4o-mini, günstig)
  - Kein LLM verfügbar → deterministischer Modus (wie bisher)

Env-Variablen:
  WORKSPACE        Projekt-Root (default: /workspace)
  OLLAMA_URL       Ollama API URL (default: http://localhost:11434)
  OLLAMA_MODEL     Modell-Name   (default: codellama)
  OPENAI_API_KEY   Falls OpenAI als Fallback genutzt werden soll
  LLM_DISABLED     Auf "1" setzen um LLM komplett zu deaktivieren
"""

import io
import os
import subprocess
import sys
import time
import textwrap
import logging
import traceback as tb
from datetime import datetime
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Reconfigure stdout to UTF-8 to handle Unicode characters properly
sys.stdout.reconfigure(encoding='utf-8')

# ── Konfiguration ─────────────────────────────────────────────────────────────
SCRIPT_DIR    = Path(__file__).resolve().parent
WORKSPACE     = Path(os.environ.get("WORKSPACE", str(SCRIPT_DIR)).strip('"'))
DATA_DIR      = Path(os.environ.get("DATA_DIR", str(WORKSPACE / "data")).strip('"'))
DATA_JOBS_DIR = DATA_DIR / "jobs"
CONTEXT_FILE  = WORKSPACE / "AGENT_CONTEXT.md"
API_PORT      = int(os.environ.get("API_PORT", "8000"))
API_URL       = f"http://localhost:{API_PORT}"

OLLAMA_URL    = os.environ.get("OLLAMA_URL",   "http://localhost:11434")
OLLAMA_MODEL  = os.environ.get("OLLAMA_MODEL", "codellama")
LLM_PRIMARY   = os.environ.get("LLM_PRIMARY", "ollama").strip().lower()
OPENAI_MODEL  = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
LLM_DISABLED  = os.environ.get("LLM_DISABLED", "0") == "1"


# ══════════════════════════════════════════════════════════════════════════════
# LLM-Backend
# ══════════════════════════════════════════════════════════════════════════════

class LLMBackend:
    """
    Einheitliches Interface für Ollama (lokal) und OpenAI (Fallback).
    Gibt immer einen String zurück – niemals Exception nach außen.
    """

    def __init__(self, log_fn):
        self._log = log_fn
        self._backend: str | None = None  # "ollama" | "openai" | None
        self._detected = False

    # ── Verfügbarkeit prüfen ──────────────────────────────────────────────────

    def _ollama_available(self) -> bool:
        try:
            r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
            if r.status_code != 200:
                return False
            models = [m["name"].split(":")[0] for m in r.json().get("models", [])]
            if any(OLLAMA_MODEL in m for m in models):
                return True
            self._log(
                f"⚠️  Ollama läuft, aber '{OLLAMA_MODEL}' fehlt. "
                f"Verfügbar: {models}  →  ollama pull {OLLAMA_MODEL}"
            )
        except requests.exceptions.RequestException:
            pass
        return False

    def _openai_available(self) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY"))

    def detect(self) -> str | None:
        """Erkennt verfügbares Backend. Wird beim ersten Aufruf gecacht."""
        if self._detected:
            return self._backend

        self._detected = True

        if LLM_DISABLED:
            self._log("ℹ️  LLM deaktiviert (LLM_DISABLED=1)")
            return None

        backend_order = ["ollama", "openai"]
        if LLM_PRIMARY == "openai":
            backend_order = ["openai", "ollama"]

        for backend in backend_order:
            if backend == "ollama" and self._ollama_available():
                self._log(f"🧠 LLM-Backend: Ollama ({OLLAMA_MODEL}) @ {OLLAMA_URL}")
                self._backend = "ollama"
                return "ollama"
            if backend == "openai" and self._openai_available():
                self._log(f"🧠 LLM-Backend: OpenAI ({OPENAI_MODEL})")
                self._backend = "openai"
                return "openai"

        self._log("ℹ️  Kein LLM verfügbar → deterministischer Modus")
        return None

    # ── Anfrage senden ────────────────────────────────────────────────────────

    def ask(self, prompt: str, max_tokens: int = 1024) -> str | None:
        """
        Sendet einen Prompt ans LLM. Gibt None zurück wenn nicht verfügbar.
        """
        if not self._detected:
            self.detect()
        if self._backend is None:
            return None

        try:
            if self._backend == "ollama":
                return self._ask_ollama(prompt, max_tokens)
            if self._backend == "openai":
                return self._ask_openai(prompt, max_tokens)
        except Exception as e:
            self._log(f"⚠️  LLM-Fehler ({self._backend}): {e}")
            # Backend zurücksetzen → nächster Aufruf versucht neu
            self._backend = None
            self._detected = False
        return None

    def _ask_ollama(self, prompt: str, max_tokens: int) -> str:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model":   OLLAMA_MODEL,
                "prompt":  prompt,
                "stream":  False,
                "options": {"num_predict": max_tokens},
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["response"].strip()

    def _ask_openai(self, prompt: str, max_tokens: int) -> str:
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("pip install openai")
        client = OpenAI()
        r = client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return r.choices[0].message.content.strip()

    def _resolve_path(self, candidates: list[str]) -> Path | None:
        for rel in candidates:
            path = self.workspace / rel
            if path.exists():
                return path
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Agent
# ══════════════════════════════════════════════════════════════════════════════

class AutonomousAgent:
    def __init__(self):
        self.workspace = WORKSPACE
        self.services: dict[str, subprocess.Popen] = {}
        self.llm = LLMBackend(self.log)
        self._context: str = ""  # gecachter Context-Inhalt
        self.continuous = False

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        try:
            print(f"[{ts}] [AGENT] {msg}")
        except UnicodeEncodeError:
            # Fallback: replace non-ASCII chars
            safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
            print(f"[{ts}] [AGENT] {safe_msg}")
        logger.info(msg)

    def run_command(
        self, cmd: str | list[str], cwd=None, timeout: int = 60, env_extra: dict = None
    ) -> tuple[bool, str]:
        env = os.environ.copy()
        env["DATA_DIR"]   = str(DATA_DIR)
        env["PYTHONPATH"] = str(self.workspace)
        if env_extra:
            env.update(env_extra)
        try:
            if isinstance(cmd, list):
                args = [sys.executable] + cmd
            elif cmd.startswith("python -c "):
                args = [sys.executable, "-c", cmd[10:]]
            else:
                args = cmd
                shell = True
            result = subprocess.run(
                args, shell=shell if 'shell' in locals() else False,
                cwd=cwd or self.workspace,
                capture_output=True, text=True,
                timeout=timeout, env=env,
            )
            if result.returncode != 0:
                self.log(f"❌ Fehler: {cmd}")
                self.log(f"   STDERR: {result.stderr.strip()[:300]}")
                return False, result.stderr
            return True, result.stdout
        except subprocess.TimeoutExpired:
            self.log(f"⏰ Timeout ({timeout}s): {cmd}")
            return False, "Timeout"
        except Exception as e:
            self.log(f"🔥 Exception: {cmd} — {e}")
            return False, str(e)

    # ── LLM-Hilfsmethoden ─────────────────────────────────────────────────────

    def _llm_analyze_error(self, error_output: str, context: str = "") -> str | None:
        """Schickt Fehler-Output ans LLM, gibt Analyse zurück."""
        ctx = (context or self._context)[:2000]
        prompt = textwrap.dedent(f"""
            Du bist ein Python-Debugging-Assistent für ein CERN-Datenanalyse-Projekt.

            PROJEKTSTRUKTUR:
            {ctx}

            FEHLER:
            {error_output[:3000]}

            Antworte NUR mit diesem Format:
            1. URSACHE: (ein Satz)
            2. DATEI: (welche Datei ändern, oder "keine")
            3. FIX: (konkreter Code-Snippet, max 15 Zeilen)
            4. BEFEHL: (Shell-Befehl zum Testen, oder "keine")

            Auf Deutsch. Konkret, kein Blabla.
        """).strip()

        self.log("🧠 LLM analysiert Fehler...")
        answer = self.llm.ask(prompt, max_tokens=512)
        if answer:
            self.log("💡 LLM-Analyse:")
            for line in answer.splitlines():
                self.log(f"   {line}")
        return answer

    def _llm_explain_failure(self, test_output: str) -> str | None:
        """Kurze menschenlesbare Zusammenfassung des Test-Outputs."""
        prompt = textwrap.dedent(f"""
            Fasse diesen pytest-Output in maximal 3 Sätzen auf Deutsch zusammen.
            Welche Tests schlagen fehl und was ist die wahrscheinliche Ursache?

            {test_output[:2000]}
        """).strip()
        return self.llm.ask(prompt, max_tokens=200)

    def _llm_suggest_fix(self, failing_tests: str, error_output: str) -> str | None:
        """Konkreter Fix-Vorschlag für fehlschlagende Tests."""
        prompt = textwrap.dedent(f"""
            Du bist ein Python-Experte. Diese Tests schlagen fehl:

            {failing_tests[:400]}

            FEHLER-OUTPUT:
            {error_output[:2000]}

            PROJEKTKONTEXT:
            {self._context[:1200]}

            Gib NUR den minimalen Fix zurück:
            DATEI: <relativer Pfad>
            ```python
            <code>
            ```
            ERKLAERUNG: <ein Satz>
        """).strip()

        self.log("🧠 LLM schlägt Fix vor...")
        answer = self.llm.ask(prompt, max_tokens=600)
        if answer:
            self.log(f"🔧 Fix-Vorschlag:\n{answer}")
        return answer

    # ── Context lesen ─────────────────────────────────────────────────────────

    def read_context(self) -> str:
        if not CONTEXT_FILE.exists():
            self.log(f"⚠️  Keine AGENT_CONTEXT.md unter {CONTEXT_FILE}")
            return ""
        content = CONTEXT_FILE.read_text(encoding='utf-8')
        self._context = content
        self.log(f"📖 AGENT_CONTEXT.md geladen ({len(content)} Zeichen)")
        todos = [
            line.strip() for line in content.splitlines()
            if "← NOCH ANLEGEN" in line or "PLACEHOLDER" in line.upper()
        ]
        if todos:
            self.log(f"📋 Offene TODOs ({len(todos)}):")
            for t in todos[:8]:
                self.log(f"   - {t}")
        else:
            self.log("✅ Keine offenen TODOs")
        return content

    # ── Pflicht-Files ─────────────────────────────────────────────────────────

    def ensure_required_files(self) -> bool:
        self.log("🔍 Prüfe Pflicht-Files...")

        api_main = self.workspace / "api_service" / "app" / "main.py"
        if not api_main.exists():
            self.log(f"📝 Erstelle {api_main.relative_to(self.workspace)}")
            api_main.parent.mkdir(parents=True, exist_ok=True)
            (api_main.parent / "__init__.py").touch(exist_ok=True)
            api_main.write_text(
                '"""API service entry point."""\n'
                "from app.api import app  # noqa: F401\n"
            )

        worker_main = self.workspace / "worker-service" / "app" / "main.py"
        if not worker_main.exists():
            self.log(f"📝 Erstelle {worker_main.relative_to(self.workspace)}")
            worker_main.parent.mkdir(parents=True, exist_ok=True)
            (worker_main.parent / "__init__.py").touch(exist_ok=True)
            worker_main.write_text(
                '"""Worker entry point."""\n'
                "import sys\nfrom pathlib import Path\n"
                "sys.path.insert(0, str(Path(__file__).parent.parent.parent))\n"
                "from worker.runner import main\n"
                'if __name__ == "__main__":\n    main()\n'
            )

        zee_path = self.workspace / "tests" / "data" / "zee.txt"
        if not zee_path.exists():
            self.log(f"📝 Erstelle {zee_path.relative_to(self.workspace)}")
            zee_path.parent.mkdir(parents=True, exist_ok=True)
            zee_path.write_text(
                "# m_zee weight\n"
                "88.5 1.0\n89.1 0.98\n90.2 1.02\n91.2 1.05\n91.5 1.03\n"
                "92.1 0.99\n93.4 0.97\n95.0 0.95\n98.2 0.93\n101.5 0.90\n"
                "105.0 0.88\n110.3 0.85\n115.0 0.83\n118.5 0.80\n"
                "88.0 1.0\n89.5 0.99\n90.8 1.01\n91.0 1.06\n91.3 1.04\n"
                "92.5 0.98\n94.0 0.96\n97.0 0.94\n100.0 0.91\n108.0 0.86\n"
            )

        if not (self.workspace / "pytest.ini").exists():
            (self.workspace / "pytest.ini").write_text(
                "[pytest]\nasyncio_mode = auto\ntestpaths = tests\n"
                "addopts = --tb=short -v\n"
            )

        for pkg_dir in [
            self.workspace / "worker",
            self.workspace / "worker" / "adapters",
        ]:
            init = pkg_dir / "__init__.py"
            if pkg_dir.exists() and not init.exists():
                init.touch()
                self.log(f"   ✅ {init.relative_to(self.workspace)}")

        DATA_JOBS_DIR.mkdir(parents=True, exist_ok=True)
        self.log("✅ Pflicht-Files OK")
        return True

    # ── Import-Check ──────────────────────────────────────────────────────────

    def verify_imports(self) -> bool:
        self.log("🔬 Prüfe Imports...")
        checks = [
            ("API app",      "from app.api import app",                          self.workspace / "api_service"),
            ("Models",       "from app.models import JobStatus",                 self.workspace / "api_service"),
            ("Storage",      "from app.storage import read_state",               self.workspace / "api_service"),
            ("Queue",        "from app.queue import enqueue",                    self.workspace / "api_service"),
            ("Base adapter", "from worker.adapters.base import BaseAdapter",     self.workspace),
            ("Inspector",    "from worker.adapters.inspector import inspect_and_parse", self.workspace),
            ("Canonical",    "from worker.canonical import save_canonical",      self.workspace),
            ("Pipeline",     "from worker.pipeline import run_scan",             self.workspace),
            ("Runner",       "from worker.runner import process_job",            self.workspace),
        ]

        failed = []
        for name, import_str, cwd in checks:
            ok, err = self.run_command(
                ["-c", f"{import_str}; print('OK')"],
                cwd=cwd, timeout=10,
            )
            self.log(f"   {'✅' if ok else '❌'} {name}")
            if not ok:
                failed.append((name, import_str, err))

        if failed:
            error_summary = "\n".join(
                f"'{imp}' schlägt fehl:\n{err[:200]}"
                for _, imp, err in failed
            )
            self._llm_analyze_error(error_summary)
            return False
        return True

    # ── Redis / API warten ────────────────────────────────────────────────────

    def _wait_for_redis(self, timeout: int = 20) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            r = subprocess.run(
                ["redis-cli", "-p", "6379", "ping"],
                capture_output=True, text=True
            )
            if r.stdout.strip() == "PONG":
                return True
            time.sleep(0.5)
        return False

    def _wait_for_api(self, timeout: int = 30) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if requests.get(f"{API_URL}/health", timeout=1).status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        return False

    # ── Services starten ──────────────────────────────────────────────────────

    def start_services(self) -> bool:
        self.log("🚀 Starte Services...")

        self.run_command("redis-server --daemonize yes --port 6379 --loglevel warning")
        if not self._wait_for_redis():
            self.log("❌ Redis startet nicht")
            self._llm_analyze_error("redis-server startet nicht oder reagiert nicht auf PING")
            return False
        self.log("✅ Redis bereit (PONG)")

        env = os.environ.copy()
        env.update({
            "DATA_DIR":   str(DATA_DIR),
            "PYTHONPATH": str(Path(self.workspace).parent.parent) + ";" + str(self.workspace),
            "REDIS_URL":  "redis://localhost:6379/0",
            "PYTHONIOENCODING": "utf-8",
        })

        api_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.api:app",
             "--host", "0.0.0.0", "--port", str(API_PORT),
             "--app-dir", str(Path(self.workspace).parent.parent / "api-service")],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(self.workspace), env=env, text=True, encoding='utf-8',
        )
        self.services["api"] = api_proc

        worker_main = self.workspace / "worker-service" / "app" / "main.py"
        self.services["worker"] = subprocess.Popen(
            [sys.executable, str(worker_main)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(self.workspace), env=env, text=True, encoding='utf-8',
        )

        if not self._wait_for_api(timeout=30):
            stderr = ""
            if api_proc.poll() is not None:
                _, stderr = api_proc.communicate(timeout=2)
            err_text = stderr
            self.log(f"❌ API startet nicht.\n{err_text[:400]}")
            self._llm_analyze_error(
                f"uvicorn startet nicht. STDERR:\n{err_text}",
                context=(
                    f"api_service liegt unter: {self.workspace}/api_service/app/\n"
                    f"Startbefehl: uvicorn app.main:app --app-dir {self.workspace}/api_service\n"
                    "Bekannte Tücke: Verzeichnisname 'api_service' hat Unterstrich → Python-Modul"
                )
            )
            return False

        self.log("✅ Alle Services laufen")
        return True

    # ── Tests ─────────────────────────────────────────────────────────────────

    def run_unit_tests(self) -> bool:
        self.log("🧪 Unit-Tests (kein Docker nötig)...")
        test_file = self._resolve_path(["tests/test_unit.py", "test_unit.py"])
        if not test_file:
            self.log("⚠️  Unit-Test-Datei nicht gefunden (tests/test_unit.py | test_unit.py)")
            return False
        ok, output = self.run_command(
            ["-m", "pytest", str(test_file), "-v", "--tb=short"],
            timeout=120
        )
        if ok:
            self.log("✅ Unit-Tests bestanden")
            return True

        self.log("❌ Unit-Tests fehlgeschlagen")
        summary = self._llm_explain_failure(output)
        if summary:
            self.log(f"📋 Zusammenfassung: {summary}")

        failing = [l for l in output.splitlines() if "FAILED" in l or "ERROR" in l]
        if failing:
            self._llm_suggest_fix("\n".join(failing[:3]), output)

        return False

    def run_smoke_test(self) -> bool:
        self.log("🎯 Smoke-Test...")
        smoke_file = self._resolve_path(["tests/smoke_test.py", "smoke_test.py"])
        if not smoke_file:
            self.log("⚠️  Smoke-Test-Datei nicht gefunden (tests/smoke_test.py | smoke_test.py)")
            return False
        ok, output = self.run_command(
            [str(smoke_file), "--api-url", API_URL],
            timeout=120
        )
        if ok:
            self.log("✅ Smoke-Test bestanden")
            return True

        self.log("❌ Smoke-Test fehlgeschlagen")
        self._llm_analyze_error(
            output,
            context=(
                "Smoke-Test schickt HTTP an FastAPI :8000. "
                "Testet: Job-Upload (zee.txt), Status-Polling, Results, Artifacts, run_id-Konsistenz."
            )
        )
        return False

    def run_integration_tests(self) -> bool:
        self.log("🔗 Integration-Tests...")
        test_file = self._resolve_path(["tests/test_full_workflow.py", "test_full_workflow.py"])
        if not test_file:
            self.log("⚠️  Integration-Test-Datei nicht gefunden")
            return False
        ok, output = self.run_command(
            ["-m", "pytest", str(test_file), "-v", "--tb=short"],
            timeout=180
        )
        if ok:
            self.log("✅ Integration-Tests bestanden")
            return True

        self.log("❌ Integration-Tests fehlgeschlagen")
        summary = self._llm_explain_failure(output)
        if summary:
            self.log(f"📋 {summary}")
        return False

    # ── Stop ──────────────────────────────────────────────────────────────────

    def stop_services(self):
        self.log("🛑 Stoppe Services...")
        for name, proc in self.services.items():
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        self.services = {}
        self.run_command("taskkill /F /FI \"IMAGENAME eq uvicorn.exe\"")
        self.run_command("taskkill /F /FI \"IMAGENAME eq python.exe\" /FI \"WINDOWTITLE eq worker-service*\"")

    # ── Context aktualisieren ─────────────────────────────────────────────────

    def update_context(self, completed_todos: list[str]):
        if not CONTEXT_FILE.exists() or not completed_todos:
            return
        content = CONTEXT_FILE.read_text(encoding='utf-8')
        for todo in completed_todos:
            content = content.replace(
                f"{todo}          ← NOCH ANLEGEN",
                f"{todo}          ✅ ERLEDIGT"
            )
        CONTEXT_FILE.write_text(content, encoding='utf-8')
        self.log(f"📝 AGENT_CONTEXT.md: {len(completed_todos)} TODOs erledigt")

    # ── Haupt-Cycle ───────────────────────────────────────────────────────────

    def full_cycle(self) -> bool:
        self.log("═" * 55)
        self.log("AUTONOMER DEVELOPMENT CYCLE")
        self.log("═" * 55)

        try:
            self.read_context()
            self.llm.detect()

            if not self.ensure_required_files():
                return False
            if not self.verify_imports():
                self.log("💥 Import-Check fehlgeschlagen")
                return False
            if not self.run_unit_tests():
                self.log("💥 Unit-Tests schlagen fehl – kein Service-Start")
                return False
            if not self.start_services():
                self.log("💥 Service-Start fehlgeschlagen")
                return False

            smoke_ok       = self.run_smoke_test()
            integration_ok = self.run_integration_tests()

            completed = [
                marker for marker, path in [
                    ("main.py (api)",    self.workspace / "api_service" / "app" / "main.py"),
                    ("main.py (worker)", self.workspace / "worker-service" / "app" / "main.py"),
                    ("zee.txt",          self.workspace / "tests" / "data" / "zee.txt"),
                ]
                if path.exists()
            ]
            self.update_context(completed)

            if smoke_ok and integration_ok:
                self.log("🎉 Alle Tests bestanden – System funktionsfähig!")
                return True

            self.log("⚠️  Nicht alle Tests bestanden")
            return False

        except KeyboardInterrupt:
            self.log("⏹️  Unterbrochen")
            return False
        except Exception as e:
            self.log(f"💥 Unerwarteter Fehler: {e}")
            buf = io.StringIO()
            tb.print_exc(file=buf)
            self._llm_analyze_error(buf.getvalue())
            return False
        finally:
            if not self.continuous:
                self.stop_services()

    def continuous_mode(self, interval: int = 60):
        self.continuous = True
        self.log("🔄 Continuous-Mode gestartet")
        cycle = 0
        while True:
            cycle += 1
            self.log(f"\n🔄 Cycle #{cycle}")
            success = self.full_cycle()
            self.log(f"Cycle #{cycle}: {'✅ OK' if success else '❌ fehlgeschlagen'}")
            self.log(f"⏳ Warte {interval}s...")
            time.sleep(interval)


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    agent = AutonomousAgent()

    if "--continuous" in sys.argv:
        idx = sys.argv.index("--continuous")
        interval = (
            int(sys.argv[idx + 1])
            if idx + 1 < len(sys.argv) and sys.argv[idx + 1].isdigit()
            else 60
        )
        agent.continuous_mode(interval=interval)
    else:
        success = agent.full_cycle()
        sys.exit(0 if success else 1)
