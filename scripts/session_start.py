#!/usr/bin/env python3
"""
session_start.py — Injetor determinístico de contexto SDD no início de sessão (P11).

Comportamento:
1. Se `docs/sdd/` não existir no workspace, permanece 100% silencioso (custo zero em projetos sem SDD).
2. Carrega `docs/sdd/11-project-memory.md` (Camada 1 — índice mestre de memória).
3. Avisa quando `11-project-memory.md` ou `10-validation.md` atingem o gatilho de Paginação Elástica:
   150 linhas OU o teto de caracteres do arquivo (o que vier primeiro). O gatilho não corta nada:
   indica que é hora de criar o shard `-02.md`.
4. Detecta automaticamente se existem arquivos de Paginação Elástica (`11-project-memory-02.md`,
   `10-validation-02.md`, etc.) e injeta um aviso de 1 linha para consulta sob demanda,
   sem inflar o contexto inicial com todos os shards.
5. Filtra `docs/sdd/07-tasks.md` trazendo apenas tasks ativas (`Pending`, `In Progress`, `Blocked`),
   limitadas a no máximo 15 itens. Aceita o formato canônico do template (`TASK-001` sozinho na linha
   + `Status: ...`) e a variante em Markdown (`### TASK-001` + `- **Status:** ...`).
6. Lista as changes ativas (`docs/sdd/changes/<nome>/`), uma linha por change, sem carregar o conteúdo.

ORÇAMENTO DE INJEÇÃO (limitação do Hermes, não do SDD): o Hermes limita o contexto devolvido por hook
a 10.000 caracteres por padrão; acima disso grava a saída em `$HERMES_HOME/hook_outputs/...` e entrega
só começo/fim + caminho (docs: developer-guide/plugins). Este injetor nunca depende desse corte:
  1. alertas, shards, tasks e changes (pequenos e com tamanho máximo) entram primeiro;
  2. a memória entra inteira se couber no que sobra do orçamento;
  3. se não couber, entram só as seções críticas (Estado Atual, Próximos Passos, Pendências) e uma
     instrução explícita para ler o arquivo inteiro antes de agir.
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import List, Tuple

INJECTION_BUDGET = 10000  # limite padrão do Hermes para o contexto devolvido por hook
SAFETY_MARGIN = 300
LINE_CAP = 150
# Gatilho de paginação (linhas OU caracteres, o que vier primeiro). Não corta nada: indica que é hora de
# rotacionar ou criar o shard `-02.md`. Memória: orçamento de 10.000 − ~3.000 reservados para alertas,
# tasks e changes. Validation: não é injetado; o teto é higiene de leitura do padrão.
CHAR_CAPS = {"11-project-memory.md": 7000, "10-validation.md": 16000}
MAX_TASKS = 15
MAX_CHANGES = 10
MAX_TITLE = 80
# Seções críticas da memória, em ordem de prioridade (títulos do template; aceita variações).
CRITICAL_SECTIONS = [
    re.compile(r"^(estado atual|current state)"),
    re.compile(r"^(proximos passos|next steps)"),
    re.compile(r"^(pendencias|open items|blockers)"),
]
RE_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")

RE_TASK_HEADER = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\*\*)?(TASK-[A-Za-z0-9_-]*\d)(?:\*\*)?\s*(?:[—–:-]\s*(.*))?$"
)
RE_FENCE = re.compile(r"^\s*```")


def _field_re(name: str) -> "re.Pattern[str]":
    # `Status: X`, `- **Status:** X` e `**Status**: X` — sem atravessar a quebra de linha
    return re.compile(rf"^\s*(?:[-*]\s+)?(?:\*\*)?{name}(?::\*\*|\*\*:|:)[ \t]*(.*)$", re.IGNORECASE)


RE_STATUS = _field_re("Status")
RE_TITLE = _field_re("Title")
RE_ACTIVE = re.compile(r"^(Pending|In Progress|Blocked)\b", re.IGNORECASE)


def parse_active_tasks(tasks_text: str) -> List[Tuple[str, str, str]]:
    """Retorna [(id, status, título)] das tasks ativas. Texto antes da primeira task é ignorado."""
    tasks: List[dict] = []
    current: dict | None = None
    fenced = False
    for line in tasks_text.splitlines():
        if RE_FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        header = RE_TASK_HEADER.match(line)
        if header:
            current = {"id": header.group(1), "title": (header.group(2) or "").strip(), "status": None}
            tasks.append(current)
            continue
        if current is None or line.lstrip().startswith(">"):
            continue
        if current["status"] is None:
            m_status = RE_STATUS.match(line)
            if m_status:
                current["status"] = m_status.group(1).strip().strip("*").strip()
                continue
        if not current["title"]:
            m_title = RE_TITLE.match(line)
            if m_title:
                current["title"] = m_title.group(1).strip()

    return [
        (t["id"], t["status"], t["title"] or "(sem título)")
        for t in tasks
        if t["status"] and RE_ACTIVE.match(t["status"])
    ]


def _clip(text: str, limit: int = MAX_TITLE) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _norm(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower().strip()


def critical_sections(md: str) -> str:
    """Recorta só as seções críticas da memória (título + corpo até o próximo título de mesmo nível ou acima)."""
    lines = md.splitlines()
    picked: List[str] = []
    for pattern in CRITICAL_SECTIONS:
        for i, line in enumerate(lines):
            h = RE_HEADING.match(line)
            if not h or not pattern.match(_norm(h.group(2))):
                continue
            j = i + 1
            while j < len(lines):
                n = RE_HEADING.match(lines[j])
                if n and len(n.group(1)) <= len(h.group(1)):
                    break
                j += 1
            picked.append("\n".join(lines[i:j]).rstrip())
            break
    return "\n\n".join(picked)


def _fit_lines(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[: max(0, limit)]
    nl = cut.rfind("\n")
    return cut[:nl] if nl > 0 else cut


def memory_within_budget(memory: str, budget: int) -> str:
    """Memória inteira se couber no orçamento; senão seções críticas + instrução explícita de leitura."""
    if len(memory) <= budget:
        return memory
    notice = (
        f"> MEMÓRIA INCOMPLETA NESTA INJEÇÃO: `docs/sdd/11-project-memory.md` tem {len(memory)} caracteres e "
        f"não cabe no orçamento de injeção do Hermes ({INJECTION_BUDGET}). Abaixo vão só as seções críticas. "
        "Leia o arquivo inteiro com a ferramenta de leitura antes de agir e aplique a higiene (rotação para "
        "`archive/memory-history.md` ou shard `-02.md`).\n\n"
    )
    core = critical_sections(memory) or memory
    return notice + _fit_lines(core, budget - len(notice))


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def over_cap_report(sdd_root: Path) -> List[str]:
    """Artefatos voláteis que atingiram o gatilho de paginação (150 linhas OU teto de caracteres)."""
    report = []
    for name, char_cap in CHAR_CAPS.items():
        text = _read(sdd_root / name)
        lines, chars = len(text.splitlines()), len(text)
        if lines > LINE_CAP or chars > char_cap:
            report.append(
                f"`docs/sdd/{name}` ({lines} linhas, {chars} caracteres; "
                f"teto {LINE_CAP} linhas ou {char_cap} caracteres)"
            )
    return report


def active_changes_report(sdd_root: Path) -> List[str]:
    changes_dir = sdd_root / "changes"
    if not changes_dir.is_dir():
        return []
    names = sorted(p.name for p in changes_dir.iterdir() if p.is_dir())
    lines = []
    for name in names[:MAX_CHANGES]:
        active = parse_active_tasks(_read(changes_dir / name / "tasks.md"))
        in_progress = sum(1 for _, status, _ in active if re.match(r"In Progress\b", status, re.IGNORECASE))
        label = _clip(name)
        if active:
            lines.append(f"- `changes/{label}/` — {len(active)} task(s) não concluída(s), {in_progress} In Progress")
        else:
            lines.append(f"- `changes/{label}/` — sem tasks ativas (verifique se falta o archive)")
    if len(names) > MAX_CHANGES:
        lines.append(f"(+{len(names) - MAX_CHANGES} changes não exibidas)")
    return lines


def build_session_context(workspace: str | Path = ".") -> str:
    root = Path(workspace).resolve()
    sdd_root = root / "docs" / "sdd"
    if not sdd_root.is_dir():
        return ""

    # Prioridade 1: alertas, shards, tasks e changes (tamanho limitado). A memória entra no que sobrar.
    parts: List[str] = []

    # 2. Gatilho de paginação dos artefatos voláteis (150 linhas OU teto de caracteres)
    over_cap = over_cap_report(sdd_root)
    if over_cap:
        parts.append(
            f"SDD Context — ALERTA de Paginação Elástica: {', '.join(over_cap)} ultrapassa(m) o teto. "
            "Antes de prosseguir, aplique a higiene: mova itens resolvidos/antigos para `docs/sdd/archive/` e, "
            "se o conteúdo ATIVO ainda não couber, crie o shard `-02.md` com índice no topo. "
            "Nunca resuma nem corte o conteúdo de uma dívida para caber."
        )

    # 3. Detecção de Paginação Elástica (Overflow Shards -02.md, -03.md)
    overflow_files = sorted(
        p.name
        for p in sdd_root.glob("*-0[2-9].md")
        if p.is_file()
    )
    if overflow_files:
        shards_list = ", ".join(f"`docs/sdd/{name}`" for name in overflow_files)
        parts.append(
            f"SDD Context — Paginação Elástica Ativa: "
            f"Existem arquivos complementares de memória/dívida ({shards_list}). "
            f"Consulte-os sob demanda se a tarefa atual tocar nos escopos indicados no cabeçalho principal."
        )

    # 4. Tasks Ativas do Ledger Principal (07-tasks.md — máx. 15)
    tasks_path = sdd_root / "07-tasks.md"
    if tasks_path.is_file():
        try:
            active = parse_active_tasks(tasks_path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            active = []
        if active:
            shown = active[:MAX_TASKS]
            joined = "\n".join(f"- {tid} [{status}] {_clip(title)}" for tid, status, title in shown)
            more = f"\n(+{len(active) - len(shown)} não exibidas)" if len(active) > len(shown) else ""
            parts.append(
                f"SDD Context — Tasks não concluídas ({len(active)}):\n"
                f"{joined}{more}\n\n"
                "Siga o protocolo SDD: confirme o estado atual e o próximo passo em até 5 linhas e prossiga com o pedido do usuário no mesmo turno (a confirmação não substitui a ação)."
            )

    # 5. Changes ativas (uma linha por change; o conteúdo é carregado sob demanda pelas skills)
    changes = active_changes_report(sdd_root)
    if changes:
        parts.append("SDD Context — Changes ativas:\n" + "\n".join(changes))

    # Prioridade 2: memória principal (11-project-memory.md) no orçamento restante, sempre primeiro no texto
    memory_path = sdd_root / "11-project-memory.md"
    if memory_path.is_file():
        prefix = "SDD Context — Estado de Memória Carregado (`docs/sdd/11-project-memory.md`):\n```markdown\n"
        suffix = "\n```"
        used = sum(len(x) for x in parts) + 2 * len(parts)
        budget = INJECTION_BUDGET - SAFETY_MARGIN - used - len(prefix) - len(suffix) - 2
        memory_content = _read(memory_path).strip()
        parts.insert(0, prefix + memory_within_budget(memory_content, budget) + suffix)

    return "\n\n".join(parts)


def main() -> int:
    workspace = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    context = build_session_context(workspace)
    print(json.dumps({"sdd_context": context, "active": bool(context)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
