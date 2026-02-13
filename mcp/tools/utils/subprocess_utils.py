"""
Zentrale subprocess-Wrapper mit Timeout und Error Handling.
Alle Tools die externe Prozesse starten nutzen diese Funktionen.
"""

import asyncio
import subprocess
from dataclasses import dataclass
from typing import Optional

DEFAULT_TIMEOUT = 60  # Sekunden


@dataclass
class ProcessResult:
    """Ergebnis eines Subprocess-Aufrufs."""
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    error: Optional[str] = None
    
    @property
    def success(self) -> bool:
        return self.returncode == 0 and not self.timed_out and not self.error
    
    @property
    def output(self) -> str:
        """Kombinierter Output."""
        out = self.stdout
        if self.stderr:
            out += f"\n\nSTDERR:\n{self.stderr}"
        return out


def run_sync(
    cmd: list[str],
    cwd: str | None = None,
    timeout: int = DEFAULT_TIMEOUT
) -> ProcessResult:
    """
    Synchroner subprocess mit Timeout.
    Für einfache Fälle wo async nicht nötig ist.
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout
        )
        return ProcessResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr
        )
    except subprocess.TimeoutExpired:
        return ProcessResult(
            returncode=-1,
            stdout="",
            stderr="",
            timed_out=True,
            error=f"Process timed out after {timeout}s"
        )
    except FileNotFoundError as e:
        return ProcessResult(
            returncode=-1,
            stdout="",
            stderr="",
            error=f"Command not found: {e}"
        )
    except Exception as e:
        return ProcessResult(
            returncode=-1,
            stdout="",
            stderr="",
            error=f"{type(e).__name__}: {e}"
        )


async def run_async(
    cmd: list[str],
    cwd: str | None = None,
    timeout: int = DEFAULT_TIMEOUT
) -> ProcessResult:
    """
    Async subprocess mit Timeout.
    Blockiert nicht den Event Loop.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout
        )
        return ProcessResult(
            returncode=proc.returncode,
            stdout=stdout.decode(),
            stderr=stderr.decode()
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return ProcessResult(
            returncode=-1,
            stdout="",
            stderr="",
            timed_out=True,
            error=f"Process timed out after {timeout}s"
        )
    except FileNotFoundError as e:
        return ProcessResult(
            returncode=-1,
            stdout="",
            stderr="",
            error=f"Command not found: {e}"
        )
    except Exception as e:
        return ProcessResult(
            returncode=-1,
            stdout="",
            stderr="",
            error=f"{type(e).__name__}: {e}"
        )
