#!/usr/bin/env python3
"""
NOVA MCP Server Launcher
Findet automatisch die richtige venv und startet den Server.
Erstellt venv automatisch wenn nicht vorhanden.
"""

import os
import sys
import subprocess
import time
import json
import re
from pathlib import Path


def log(level: str, message: str) -> None:
    """Einheitliches Logging auf stderr."""
    print(f"[{level}] NOVA: {message}", file=sys.stderr, flush=True)


def run_cmd(
    args: list[str],
    cwd: Path | None = None,
    timeout: int | None = None,
    retries: int = 0,
    retry_delay: float = 1.0,
    description: str = "command",
    capture_output: bool = False,
    text: bool = False,
) -> subprocess.CompletedProcess | None:
    """
    Fuehrt einen Prozess robust aus.
    Gibt bei Erfolg CompletedProcess, sonst None zurueck.
    """
    attempt = 0
    while True:
        try:
            return subprocess.run(
                args,
                cwd=cwd,
                timeout=timeout,
                capture_output=capture_output,
                text=text,
            )
        except FileNotFoundError:
            log("ERROR", f"{description} fehlgeschlagen: Datei/Programm nicht gefunden ({args[0]})")
            return None
        except subprocess.TimeoutExpired:
            log("ERROR", f"{description} Timeout nach {timeout}s")
        except OSError as exc:
            log("ERROR", f"{description} fehlgeschlagen: {exc}")

        if attempt >= retries:
            return None

        attempt += 1
        sleep_for = retry_delay * attempt
        log("WARN", f"{description} wird erneut versucht ({attempt}/{retries}) in {sleep_for:.1f}s")
        time.sleep(sleep_for)


def find_venv_python() -> Path | None:
    """Findet den Python-Interpreter in der venv."""
    script_dir = Path(__file__).parent

    # Windows
    windows_python = script_dir / ".venv" / "Scripts" / "python.exe"
    if windows_python.exists():
        return windows_python

    # Linux/macOS
    unix_python = script_dir / ".venv" / "bin" / "python"
    if unix_python.exists():
        return unix_python

    return None


def create_venv() -> bool:
    """Erstellt venv und installiert Dependencies. Gibt True bei Erfolg zurueck."""
    script_dir = Path(__file__).parent
    venv_path = script_dir / ".venv"
    requirements_path = script_dir / "requirements.txt"
    
    log("INFO", "Erstelle .venv...")

    # venv erstellen
    result = run_cmd(
        [sys.executable, "-m", "venv", str(venv_path)],
        cwd=script_dir,
        timeout=300,
        description="venv erstellen",
    )
    if result is None or result.returncode != 0:
        log("ERROR", "venv konnte nicht erstellt werden.")
        return False

    log("OK", ".venv erstellt")

    # pip path bestimmen
    if sys.platform == "win32":
        pip_path = venv_path / "Scripts" / "pip.exe"
    else:
        pip_path = venv_path / "bin" / "pip"

    if not pip_path.exists():
        log("ERROR", f"pip nicht gefunden: {pip_path}")
        return False

    # pip upgrade
    log("INFO", "Upgrade pip...")
    run_cmd(
        [str(pip_path), "install", "--upgrade", "pip", "--quiet"],
        cwd=script_dir,
        timeout=300,
        retries=1,
        retry_delay=2.0,
        description="pip upgrade",
    )

    # Dependencies installieren
    if requirements_path.exists():
        log("INFO", "Installiere Dependencies...")
        result = run_cmd(
            [str(pip_path), "install", "-r", str(requirements_path)],
            cwd=script_dir,
            timeout=900,
            retries=1,
            retry_delay=2.0,
            description="Dependency-Installation",
        )
        if result is None or result.returncode != 0:
            log("ERROR", "Dependencies konnten nicht installiert werden.")
            return False
        log("OK", "Dependencies installiert")
    else:
        log("WARN", "requirements.txt fehlt - starte ohne Dependency-Installation")

    log("OK", "Setup abgeschlossen")
    return True


def check_config() -> None:
    """Prüft ob nova.toml existiert und gibt Hinweis aus."""
    script_dir = Path(__file__).parent
    nova_root = script_dir.parent
    
    config_locations = [
        nova_root / "nova.toml",
        script_dir / "nova.toml",
    ]
    
    for config_path in config_locations:
        if config_path.exists():
            return  # Config gefunden, alles ok

    # Keine Config gefunden - Hinweis ausgeben
    setup_path = script_dir / "setup.py"
    if setup_path.exists():
        log("INFO", "Keine nova.toml gefunden.")
        log("INFO", "Tipp: python nova-core/setup.py fuer interaktives Setup")
    # Weiter mit Defaults - kein harter Fehler


def _extract_core_root_from_cmdline(cmdline: str) -> Path | None:
    """
    Extrahiert <...>/nova-core aus einem Prozess-Commandline-String, wenn
    dieser auf mcp/nova_mcp_core_server.py zeigt.
    """
    patterns = [
        r'([A-Za-z]:[^\n\r"]*?[\\/]+mcp[\\/]+nova_mcp_core_server\.py)',
        r'(/[^"\s]*?/mcp/nova_mcp_core_server\.py)',
    ]
    for pattern in patterns:
        match = re.search(pattern, cmdline, flags=re.IGNORECASE)
        if not match:
            continue
        try:
            server_path = Path(match.group(1).strip().strip('"')).resolve()
            return server_path.parent.parent
        except Exception:
            return None
    return None


def _list_running_mcp_servers() -> list[dict]:
    """
    Listet laufende Python-Prozesse mit NOVA MCP Core Server-Skript.
    Rueckgabe: [{"pid": int, "commandline": str, "core_root": Path|None}, ...]
    """
    if sys.platform != "win32":
        return []

    current_pid = os.getpid()
    ps_cmd = (
        "$procs = Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -match '^python(\\\\.exe)?$' -and $_.CommandLine -match 'mcp[\\\\\\\\/]nova_mcp_core_server\\\\.py' }; "
        "$procs | Select-Object ProcessId, CommandLine | ConvertTo-Json -Compress"
    )
    result = run_cmd(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        timeout=10,
        description="MCP-Prozesssuche",
        capture_output=True,
        text=True,
    )
    if result is None or result.returncode != 0 or not result.stdout:
        return []

    raw = result.stdout.strip()
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []

    servers: list[dict] = []
    for item in data:
        try:
            pid = int(item.get("ProcessId"))
        except Exception:
            continue
        if pid == current_pid:
            continue
        commandline = str(item.get("CommandLine") or "")
        core_root = _extract_core_root_from_cmdline(commandline)
        servers.append({
            "pid": pid,
            "commandline": commandline,
            "core_root": core_root,
        })
    return servers


def _build_close_command(pids: list[int]) -> str | None:
    """Baut copy-paste close-command fuer gefundene Fremdprozesse."""
    if not pids:
        return None
    if sys.platform == "win32":
        pid_list = ",".join(str(pid) for pid in sorted(set(pids)))
        return f"Stop-Process -Id {pid_list} -Force"
    pid_list = " ".join(str(pid) for pid in sorted(set(pids)))
    return f"kill -9 {pid_list}"


def _stop_processes(pids: list[int]) -> bool:
    """Stoppt Prozesse best-effort, ohne Launcher-Start zu blockieren."""
    if not pids:
        return True
    dedup = sorted(set(int(pid) for pid in pids))
    if sys.platform == "win32":
        pid_list = ",".join(str(pid) for pid in dedup)
        result = run_cmd(
            ["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {pid_list} -Force"],
            timeout=10,
            description="Fremde MCP-Prozesse stoppen",
        )
        return result is not None and result.returncode == 0
    result = run_cmd(
        ["kill", "-9", *[str(pid) for pid in dedup]],
        timeout=10,
        description="Fremde MCP-Prozesse stoppen",
    )
    return result is not None and result.returncode == 0


def main() -> int:
    current_core_root = Path(__file__).parent.resolve()
    expected_workspace = Path.cwd().resolve()
    os.environ["NOVA_EXPECTED_WORKSPACE_ROOT"] = str(expected_workspace)
    os.environ["NOVA_LAUNCHER_CORE_ROOT"] = str(current_core_root)

    running_servers = _list_running_mcp_servers()
    foreign_servers = [
        srv for srv in running_servers
        if srv.get("core_root") is not None and srv["core_root"] != current_core_root
    ]
    if foreign_servers:
        log("WARN", "CAUTION: different workspace MCP already running")
        for srv in sorted(foreign_servers, key=lambda x: x["pid"]):
            log("WARN", f"PID={srv['pid']} running={srv['core_root']}")
            log("WARN", f"expected={current_core_root}")
        foreign_pids = [srv["pid"] for srv in foreign_servers]
        close_cmd = _build_close_command(foreign_pids)
        if close_cmd:
            log("WARN", f"close with command: {close_cmd}")
        if _stop_processes(foreign_pids):
            log("OK", f"foreign MCP processes stopped: {','.join(str(p) for p in sorted(set(foreign_pids)))}")
        else:
            log("WARN", "automatic stop failed; run close command manually")

    venv_python = find_venv_python()

    if venv_python is None:
        log("INFO", "Keine .venv gefunden. Starte Setup...")

        if create_venv():
            venv_python = find_venv_python()

        if venv_python is None:
            log("ERROR", "Setup fehlgeschlagen.")
            return 1

    # Config-Check (nur Hinweis, kein Abbruch)
    check_config()

    # Starte den eigentlichen MCP Server mit venv Python
    server_dir = Path(__file__).parent / "mcp"
    server_path = server_dir / "nova_mcp_core_server.py"
    if not server_path.exists():
        log("ERROR", f"Server-Datei nicht gefunden: {server_path}")
        return 1

    args = [str(venv_python), str(server_path), *sys.argv[1:]]
    try:
        result = subprocess.run(
            args,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        return result.returncode
    except KeyboardInterrupt:
        log("INFO", "Launcher durch Benutzer abgebrochen.")
        return 130
    except OSError as exc:
        log("ERROR", f"Server konnte nicht gestartet werden: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
