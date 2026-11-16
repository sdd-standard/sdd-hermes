#!/usr/bin/env python3
"""
say_do_gate.py — Auditoria Mecânica 100% Passiva de Execução (Camada 0 do Gate).

Regra de Ouro:
- Este módulo é ESTRITAMENTE PASSIVO (Read-Only em relação ao código e artefatos do projeto).
- Ele nunca altera código nem executa testes por conta própria.
- Apenas registra em memória os eventos `post_tool_call` da sessão e, quando consultado no Gate,
  informa se houve uma execução real de testes/build com `exit_code == 0` APÓS a última
  modificação de arquivo de código.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List

# Ledger efêmero em memória por session_id
_SESSION_LEDGERS: Dict[str, List[Dict[str, Any]]] = {}

TEST_OR_BUILD_RE = re.compile(
    r"\b(pytest|unittest|vitest|jest|mocha|ava|cargo\s+test|go\s+test|dotnet\s+test"
    r"|npm\s+test|npm\s+run\s+test|pnpm\s+(run\s+)?test|yarn\s+test|bun\s+test"
    r"|mvn\s+test|gradle\s+test|tsc|npm\s+run\s+build|pnpm\s+(run\s+)?build)\b",
    re.IGNORECASE,
)

CODE_WRITE_TOOLS = {"write_file", "edit_file", "patch", "apply_patch", "replace_in_file"}
TERMINAL_TOOLS = {"terminal", "bash", "run_command", "shell", "execute_command"}


def record_tool_event(
    session_id: str,
    tool_name: str,
    args: Dict[str, Any],
    result: Any,
) -> None:
    """Registra passivamente um evento de ferramenta no ledger da sessão."""
    ledger = _SESSION_LEDGERS.setdefault(session_id, [])
    t_name = tool_name.lower()

    entry: Dict[str, Any] = {
        "timestamp": time.time(),
        "tool": t_name,
    }

    if t_name in TERMINAL_TOOLS:
        cmd = str(args.get("command") or args.get("cmd") or args.get("CommandLine") or "")
        exit_code = _extract_exit_code(result)
        entry["kind"] = "terminal"
        entry["command"] = cmd
        entry["is_test_or_build"] = bool(TEST_OR_BUILD_RE.search(cmd))
        entry["exit_code"] = exit_code
        ledger.append(entry)
    elif t_name in CODE_WRITE_TOOLS:
        path = str(args.get("path") or args.get("file_path") or args.get("Path") or "")
        is_sdd_doc = "docs/sdd/" in path.replace("\\", "/")
        entry["kind"] = "doc_write" if is_sdd_doc else "code_write"
        entry["path"] = path
        ledger.append(entry)


def _extract_exit_code(result: Any) -> int | None:
    if isinstance(result, dict):
        for key in ("exit_code", "exitCode", "returncode", "code"):
            if key in result and isinstance(result[key], int):
                return result[key]
    if isinstance(result, str):
        m = re.search(r"exited with code (\d+)|exit_code[:=]\s*(\d+)", result, re.IGNORECASE)
        if m:
            return int(m.group(1) or m.group(2))
    return 0


def audit_session_ledger(session_id: str = "default") -> Dict[str, Any]:
    """
    Audita passivamente o ledger da sessão e retorna evidência mecânica para o Gate:
    - Quantos arquivos de código foram modificados na sessão.
    - Quais comandos de teste/build rodaram e seus exit codes.
    - Se existe pelo menos 1 execução de teste/build com exit_code == 0 posterior
      à última modificação de código (`verified_after_last_edit`).
    """
    events = _SESSION_LEDGERS.get(session_id, [])
    code_writes = [e for e in events if e.get("kind") == "code_write"]
    test_runs = [
        e for e in events
        if e.get("kind") == "terminal" and e.get("is_test_or_build")
    ]

    last_code_write_ts = code_writes[-1]["timestamp"] if code_writes else 0.0
    passing_tests_after_edit = [
        t for t in test_runs
        if t.get("exit_code") == 0 and t["timestamp"] >= last_code_write_ts
    ]
    failing_tests_after_edit = [
        t for t in test_runs
        if t.get("exit_code") not in (0, None) and t["timestamp"] >= last_code_write_ts
    ]

    if not code_writes:
        status = "NO_CODE_EDITS_IN_SESSION"
        passed = True
        message = (
            "Say-Do Gate (Passivo): Nenhuma modificação de arquivo de código registrada nesta sessão."
        )
    elif passing_tests_after_edit and not failing_tests_after_edit:
        status = "VERIFIED_PASS"
        passed = True
        last_cmd = passing_tests_after_edit[-1]["command"]
        message = (
            f"Say-Do Gate (Passivo): OK — Comando de verificação `{last_cmd}` "
            f"executado com exit_code=0 após a última edição de código."
        )
    elif failing_tests_after_edit:
        status = "FAILED_AFTER_EDIT"
        passed = False
        last_fail = failing_tests_after_edit[-1]
        message = (
            f"Say-Do Gate (Passivo): ALERTA — O comando `{last_fail['command']}` "
            f"falhou (exit_code={last_fail['exit_code']}) após a edição de código. "
            f"O implementador deve corrigir e re-executar antes de aprovar o gate."
        )
    else:
        status = "UNVERIFIED_CODE_EDIT"
        passed = False
        message = (
            f"Say-Do Gate (Passivo): ALERTA — {len(code_writes)} edição(ões) de código "
            f"registrada(s) na sessão sem nenhum comando de teste/build executado com exit_code=0 depois. "
            f"O implementador deve rodar a suíte de testes antes de avançar."
        )

    return {
        "passed": passed,
        "status": status,
        "message": message,
        "code_edits_count": len(code_writes),
        "test_runs_count": len(test_runs),
        "recent_test_commands": [
            {"command": t["command"], "exit_code": t["exit_code"]}
            for t in test_runs[-5:]
        ],
    }
