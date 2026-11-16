#!/usr/bin/env python3
"""
session_start.py — Injetor determinístico de contexto SDD no início de sessão (P11).

Comportamento:
1. Se `docs/sdd/` não existir no workspace, permanece 100% silencioso (custo zero em projetos sem SDD).
2. Carrega `docs/sdd/11-project-memory.md` (Camada 1 — índice mestre de memória).
3. Detecta automaticamente se existem arquivos de Paginação Elástica (`11-project-memory-02.md`,
   `10-validation-02.md`, etc.) e injeta um aviso de 1 linha para consulta sob demanda,
   sem inflar o contexto inicial com todos os shards.
4. Filtra `docs/sdd/07-tasks.md` trazendo apenas tasks ativas (`Pending`, `In Progress`, `Blocked`),
   limitadas a no máximo 15 itens.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import List

RE_TASK_SPLIT = re.compile(r"\n(?=TASK-)")
RE_ACTIVE_STATUS = re.compile(r"Status:\s*(Pending|In Progress|Blocked)", re.IGNORECASE)
RE_TASK_ID = re.compile(r"TASK-[A-Za-z0-9_-]+")
RE_TASK_TITLE = re.compile(r"Title:\s*(.+)")
RE_TASK_STATUS = re.compile(r"Status:\s*(.+)")


def build_session_context(workspace: str | Path = ".") -> str:
    root = Path(workspace).resolve()
    sdd_root = root / "docs" / "sdd"
    if not sdd_root.is_dir():
        return ""

    parts: List[str] = []

    # 1. Memória Principal (11-project-memory.md)
    memory_path = sdd_root / "11-project-memory.md"
    if memory_path.is_file():
        try:
            memory_content = memory_path.read_text(encoding="utf-8").strip()
            parts.append(
                "SDD Context — Estado de Memória Carregado (`docs/sdd/11-project-memory.md`):\n"
                f"```markdown\n{memory_content}\n```"
            )
        except OSError:
            pass

    # 2. Detecção de Paginação Elástica (Overflow Shards -02.md, -03.md)
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

    # 3. Tasks Ativas do Ledger Principal (07-tasks.md — máx. 15)
    tasks_path = sdd_root / "07-tasks.md"
    if tasks_path.is_file():
        try:
            tasks_text = tasks_path.read_text(encoding="utf-8")
            blocks = RE_TASK_SPLIT.split(tasks_text)
            active_lines: List[str] = []
            for block in blocks:
                if not RE_ACTIVE_STATUS.search(block):
                    continue
                tid_m = RE_TASK_ID.search(block)
                title_m = RE_TASK_TITLE.search(block)
                status_m = RE_TASK_STATUS.search(block)
                tid = tid_m.group(0) if tid_m else "?"
                title = title_m.group(1).strip() if title_m else "?"
                status = status_m.group(1).strip() if status_m else "?"
                active_lines.append(f"- {tid} [{status}] {title}")
                if len(active_lines) >= 15:
                    break

            if active_lines:
                joined = "\n".join(active_lines)
                parts.append(
                    f"SDD Context — Tasks não concluídas ({len(active_lines)}):\n"
                    f"{joined}\n\n"
                    "Siga o protocolo SDD: confirme o estado atual e o próximo passo em até 5 linhas antes de agir."
                )
        except OSError:
            pass

    return "\n\n".join(parts)


def main() -> int:
    workspace = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    context = build_session_context(workspace)
    print(json.dumps({"sdd_context": context, "active": bool(context)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
