"""pytest entry: runs the SVM+ harness (fake Discord, fake LocalAI server, fake docker) against ../bot.py."""
import ast, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_layers_and_ai_agent():
    p = subprocess.run([sys.executable, str(ROOT / "tests" / "harness_svm_plus.py"), str(ROOT / "bot.py")], capture_output=True, text=True, timeout=600)
    assert "CHECKS PASSED" in p.stdout, (p.stdout[-1500:] + p.stderr[-1500:])
    assert "FAIL:" not in p.stdout


def test_bot_compiles_and_runs_last():
    tree = ast.parse((ROOT / "bot.py").read_text())
    runs = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "run" and getattr(getattr(n.func, "value", None), "id", "") == "bot"]
    last_def = max(n.end_lineno for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
    assert runs and min(runs) > last_def


def test_motd_is_local_and_has_no_url():
    assert "curl -fsSL https://raw.githubusercontent.com" not in (ROOT / "bot.py").read_text()
    script = (ROOT / "motd" / "svm-motd-installer.sh").read_text()
    assert "curl" not in script and "wget" not in script


def test_installer_syntax():
    assert subprocess.run(["bash", "-n", str(ROOT / "install.sh")]).returncode == 0
