#!/usr/bin/env python3
"""
say_do_gate.py — Auditoria Mecânica 100% Passiva de Execução (Camada 0 do Gate).

Regra de Ouro:
- Este módulo é ESTRITAMENTE PASSIVO (Read-Only em relação ao código e artefatos do projeto).
- Ele nunca altera código nem executa testes por conta própria.
- Apenas registra em memória os eventos `post_tool_call` da sessão e, quando consultado no Gate,
  informa se houve uma execução real de testes/build com `exit_code == 0` APÓS a última
  modificação de arquivo de código.

Princípio de segurança (fail-closed): ausência de evidência NUNCA é aprovação.
- Exit code indeterminado → o comando não conta como prova.
- Ledger vazio (sessão nova, processo reiniciado, hook não disparou) → `NO_EVIDENCE`, não `passed`.
- Comando de teste mascarado (`|| true`, pipe sem `pipefail`, `--help`, `--collect-only`) → não conta.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

MAX_EVENTS_PER_SESSION = 500
MAX_SESSIONS = 50

# Ledger efêmero em memória por session_id (ordem de inserção = ordem cronológica)
_SESSION_LEDGERS: Dict[str, List[Dict[str, Any]]] = {}
_SEQ = 0

CODE_WRITE_TOOLS = {"write_file", "edit_file", "patch", "apply_patch", "replace_in_file"}
TERMINAL_TOOLS = {"terminal", "bash", "run_command", "shell", "execute_command"}

# Prefixos que apenas embrulham o comando real (não mudam o que é executado)
_WRAPPER_RE = re.compile(
    r"^(?:(?:sudo|time|command|exec|npx|bunx|pnpx)\s+(?:-\S+\s+)*"
    r"|(?:pnpm|yarn|bun)\s+(?:exec|dlx)\s+"
    r"|(?:uv|poetry|pipenv|hatch|pdm|bundle)\s+(?:run|exec)\s+"
    r"|python[\d.]*\s+-m\s+"
    r"|\./)",
    re.IGNORECASE,
)
_ENV_ASSIGN_RE = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)+")

# O runner precisa ser a CABEÇA do segmento de comando (não basta aparecer no texto).
_TEST_HEAD_RE = re.compile(
    r"^(?:pytest|unittest|tox|nox|vitest|jest|mocha|ava|tsc|phpunit|rspec|ctest"
    r"|(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?(?:test|build|typecheck|check)(?:[:\w-]*)"
    r"|cargo\s+(?:test|build|check)"
    r"|go\s+(?:test|build|vet)"
    r"|dotnet\s+(?:test|build)"
    r"|deno\s+test"
    r"|mvnw?\s+(?:\S+\s+)*(?:test|verify|package|install)"
    r"|gradlew?\s+(?:\S+\s+)*(?:test|build|check)"
    r"|make\s+(?:test|check|build)"
    r"|(?:rake|mix)\s+test)\b",
    re.IGNORECASE,
)
_DRY_RUN_RE = re.compile(
    r"(?:^|\s)(?:--help|-h|--version|--collect-only|--co|--listTests|--list|--dry-run|--no-run)(?:\s|$)",
    re.IGNORECASE,
)
# Edição de arquivo feita pelo terminal (heurística conservadora: na dúvida, exige re-rodar os testes)
_TERMINAL_MUTATION_RE = re.compile(
    r"\bsed\s+(?:-\S+\s+)*-i|\bperl\s+-\S*i|\btee\s+(?!/dev/null)"
    r"|\bgit\s+(?:apply|checkout|restore|merge|rebase|cherry-pick|revert|stash\s+(?:pop|apply)|reset\s+--hard)\b"
    r"|\bpatch\s+-p|(?<![0-9&>])>{1,2}\s*(?!/dev/null|&)[^\s>&|]",
    re.IGNORECASE,
)


def _split_segments(cmd: str) -> List[Dict[str, str]]:
    """Divide o comando nos operadores de shell, guardando qual operador vem DEPOIS de cada segmento."""
    parts = re.split(r"(\|\||&&|;|\||\n)", cmd)
    segments: List[Dict[str, str]] = []
    for i in range(0, len(parts), 2):
        text = parts[i].strip()
        op_after = parts[i + 1] if i + 1 < len(parts) else ""
        if text:
            segments.append({"text": text, "op_after": op_after})
    return segments


def _strip_wrappers(segment: str) -> str:
    text = segment.strip().lstrip("(").strip()
    text = _ENV_ASSIGN_RE.sub("", text)
    for _ in range(4):
        new_text = _WRAPPER_RE.sub("", text, count=1).strip()
        if new_text == text:
            break
        text = new_text
    return text


def classify_command(cmd: str) -> Dict[str, Any]:
    """
    Classifica um comando de terminal:
    - is_test_or_build: algum segmento tem um runner de teste/build como cabeça.
    - masked: o exit code do comando composto não prova o resultado do teste
      (`|| ...`, pipe sem `pipefail`, flags de dry-run/help).
    - mutates_files: o comando provavelmente editou arquivos (conta como edição de código).
    """
    has_pipefail = "pipefail" in cmd
    is_test = False
    masked = False
    for seg in _split_segments(cmd):
        head = _strip_wrappers(seg["text"])
        if not _TEST_HEAD_RE.match(head):
            continue
        is_test = True
        if seg["op_after"] == "||" or _DRY_RUN_RE.search(head):
            masked = True
        if seg["op_after"] == "|" and not has_pipefail:
            masked = True
    return {
        "is_test_or_build": is_test,
        "masked": masked,
        "mutates_files": (not is_test) and bool(_TERMINAL_MUTATION_RE.search(cmd)),
    }


def _extract_exit_code(result: Any) -> Optional[int]:
    """
    Extrai o exit code do resultado de uma tool de terminal.
    Retorna None quando não é possível determinar — e None NUNCA conta como sucesso.
    (No Hermes, `result` chega sempre como string JSON: {"output": ..., "exit_code": ..., "error": ...}.)
    """
    if isinstance(result, (str, bytes)):
        raw = result.decode("utf-8", "replace") if isinstance(result, bytes) else result
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            parsed = None
        if isinstance(parsed, dict):
            result = parsed
        else:
            m = re.search(
                r"exited with code (-?\d+)|[\"']?(?:exit_code|exitCode|returncode)[\"']?\s*[:=]\s*(-?\d+)",
                raw,
                re.IGNORECASE,
            )
            return int(m.group(1) or m.group(2)) if m else None

    if isinstance(result, dict):
        for key in ("exit_code", "exitCode", "returncode", "return_code", "code"):
            value = result.get(key)
            if isinstance(value, bool):
                continue
            if isinstance(value, int):
                return value
            if isinstance(value, str) and re.fullmatch(r"-?\d+", value.strip()):
                return int(value.strip())
    return None


def _trim(ledger: List[Dict[str, Any]]) -> None:
    if len(ledger) > MAX_EVENTS_PER_SESSION:
        del ledger[: len(ledger) - MAX_EVENTS_PER_SESSION]
    while len(_SESSION_LEDGERS) > MAX_SESSIONS:
        _SESSION_LEDGERS.pop(next(iter(_SESSION_LEDGERS)))


def record_tool_event(
    session_id: str,
    tool_name: str,
    args: Dict[str, Any],
    result: Any,
) -> None:
    """Registra passivamente um evento de ferramenta no ledger da sessão."""
    global _SEQ
    t_name = (tool_name or "").lower()
    entry: Dict[str, Any] = {"tool": t_name}

    if t_name in TERMINAL_TOOLS:
        cmd = str(args.get("command") or args.get("cmd") or args.get("CommandLine") or "")
        info = classify_command(cmd)
        entry.update(
            kind="code_write" if info["mutates_files"] else "terminal",
            command=cmd,
            path="(via terminal)" if info["mutates_files"] else "",
            is_test_or_build=info["is_test_or_build"],
            masked=info["masked"],
            exit_code=_extract_exit_code(result),
        )
    elif t_name in CODE_WRITE_TOOLS:
        path = str(args.get("path") or args.get("file_path") or args.get("Path") or "")
        is_sdd_doc = "docs/sdd/" in path.replace("\\", "/")
        entry.update(kind="doc_write" if is_sdd_doc else "code_write", path=path)
    else:
        return

    _SEQ += 1
    entry["seq"] = _SEQ
    ledger = _SESSION_LEDGERS.setdefault(session_id, [])
    ledger.append(entry)
    _trim(ledger)


def known_sessions() -> List[str]:
    return list(_SESSION_LEDGERS.keys())


def audit_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Avalia uma lista de eventos (já em ordem cronológica) e devolve o veredito mecânico."""
    code_writes = [e for e in events if e.get("kind") == "code_write"]
    last_write_seq = code_writes[-1]["seq"] if code_writes else 0
    runs_after = [
        e for e in events
        if e.get("kind") == "terminal" and e.get("is_test_or_build") and e["seq"] > last_write_seq
    ]

    # Vale a ÚLTIMA execução de cada comando distinto (falhou e depois passou = passou).
    latest: Dict[str, Dict[str, Any]] = {}
    for run in runs_after:
        latest[" ".join(run["command"].split())] = run

    proven = [r for r in latest.values() if r.get("exit_code") == 0 and not r.get("masked")]
    failed = [r for r in latest.values() if r.get("exit_code") not in (0, None)]
    unproven = [r for r in latest.values() if r not in proven and r not in failed]

    if failed:
        status, passed = "FAILED_AFTER_EDIT", False
        bad = failed[-1]
        message = (
            f"Say-Do Gate (Passivo): ALERTA — `{bad['command']}` falhou (exit_code={bad['exit_code']}) "
            "após a última edição de código. O implementador deve corrigir e re-executar."
        )
    elif proven:
        status, passed = "VERIFIED_PASS", True
        message = (
            f"Say-Do Gate (Passivo): OK — `{proven[-1]['command']}` executado com exit_code=0 "
            "após a última edição de código registrada."
        )
    elif code_writes:
        status, passed = "UNVERIFIED_CODE_EDIT", False
        detail = ""
        if unproven:
            detail = (
                " Houve execução de teste/build, mas ela não serve de prova "
                "(exit code indeterminado ou comando mascarado por `||`, pipe ou flag de dry-run)."
            )
        message = (
            f"Say-Do Gate (Passivo): ALERTA — {len(code_writes)} edição(ões) de código sem execução "
            f"comprovada de teste/build com exit_code=0 depois.{detail} "
            "O implementador deve rodar o comando oficial de testes (constitution §3) e re-auditar."
        )
    else:
        status, passed = "NO_EVIDENCE", None
        message = (
            "Say-Do Gate (Passivo): SEM EVIDÊNCIA — o ledger não registra edição de código nem execução "
            "comprovada de testes (sessão nova, processo reiniciado ou trabalho feito em outra sessão/subagente). "
            "Ausência de evidência NÃO é aprovação: se o escopo auditado alterou código, rode agora o comando "
            "oficial de testes (constitution §3) e re-audite."
        )

    return {
        "passed": passed,
        "status": status,
        "message": message,
        "code_edits_count": len(code_writes),
        "test_runs_after_last_edit": len(runs_after),
        "recent_test_commands": [
            {"command": r["command"], "exit_code": r.get("exit_code"), "masked": bool(r.get("masked"))}
            for r in runs_after[-5:]
        ],
    }


def audit_session_ledger(session_id: str = "default", all_sessions: bool = False) -> Dict[str, Any]:
    """
    Audita passivamente o ledger e retorna evidência mecânica para o Gate.
    - `session_id`: sessão a auditar.
    - `all_sessions`: funde os eventos de todas as sessões do processo (útil quando o código foi
      editado por um subagente via `delegate_task`, que roda em sessão própria).
    """
    if all_sessions:
        events = sorted(
            (e for ledger in _SESSION_LEDGERS.values() for e in ledger),
            key=lambda e: e["seq"],
        )
    else:
        events = list(_SESSION_LEDGERS.get(session_id, []))

    report = audit_events(events)
    report["session_id"] = "*" if all_sessions else session_id

    others = [s for s in _SESSION_LEDGERS if s != session_id and _SESSION_LEDGERS[s]]
    if not all_sessions and report["status"] == "NO_EVIDENCE" and others:
        report["message"] += (
            f" Há eventos em {len(others)} outra(s) sessão(ões) deste processo "
            "(possíveis subagentes): re-audite com `all_sessions=true`."
        )
    return report
