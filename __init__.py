"""
sdd-workflow — Plugin Oficial de Spec-Driven Development (SDD Puro v2.1) para Hermes Agent.

Registra no contexto do Hermes Agent (`ctx`):
1. As 8 Skills canônicas (`sdd-init`, `sdd-adopt`, `sdd-specify`, `sdd-design`,
   `sdd-tasks`, `sdd-implement`, `sdd-change`, `sdd-validate`).
2. Os 8 Slash Commands correspondentes (`/sdd-init`, `/sdd-adopt`, etc.).
3. As 2 Tools determinísticas e 100% passivas da Camada 0 do Quality Gate:
   - `sdd_check_ids`: Guarda mecânica de rastreabilidade de IDs (zero dependência de Node.js).
   - `sdd_say_do_audit`: Auditoria passiva do ledger de execução da sessão.
4. Os 4 Hooks de ciclo de vida:
   - `on_session_start` / `pre_llm_call`: Injeção enxuta de `11-project-memory.md`,
     ponteiros de paginação elástica (`-02.md`) e tasks ativas (`07-tasks.md`).
   - `pre_tool_call`: Guarda determinística contra instalação não autorizada de pacotes
     (`guard-install`) e contra auto-mutação silenciosa de artefatos de governança.
   - `post_tool_call`: Alimenta passivamente o ledger efêmero da sessão para o Say-Do Gate.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict

from .scripts.check_ids import run_check_ids
from .scripts.say_do_gate import audit_session_ledger, record_tool_event
from .scripts.session_start import build_session_context

PLUGIN_ROOT = Path(__file__).resolve().parent

SKILLS_MANIFEST = [
    (
        "sdd-init",
        "Inicia um novo projeto SDD Greenfield (entrevista da Constitution, árvore docs/sdd/ e .hermes.md).",
    ),
    (
        "sdd-adopt",
        "Adota o SDD em projeto existente (Brownfield) via baseline As-Built mínima e Spec-on-Touch.",
    ),
    (
        "sdd-specify",
        "Conduz as fases 00→03 (Brief, Discovery, Spec com Intent Blocks e Requirements em GEARS) com entrevista escopada.",
    ),
    (
        "sdd-design",
        "Conduz as fases 04→06 (Domain Model, Design DES-xxx e Roadmap) com check prévio de Validate-Gap.",
    ),
    (
        "sdd-tasks",
        "Fatia o design aprovado em tarefas atômicas no ledger (07-tasks.md), critérios AC-xxx (08) e matriz (09).",
    ),
    (
        "sdd-implement",
        "Executa tasks ativas (In Progress) com Quality Gate 100% passivo em 3 camadas no fechamento de milestone.",
    ),
    (
        "sdd-change",
        "Ciclo completo de Delta Specs (proposal → apply → archive) com entrevista escopada e fatiamento proativo.",
    ),
    (
        "sdd-validate",
        "Aciona manualmente o Quality Gate 100% passivo em 3 camadas (Camada 0 Mecânica + Estágios 1 e 2 do sdd-validator).",
    ),
]

INSTALL_PATTERN = re.compile(
    r"\b(pnpm|npm|yarn|bun)\s+(add|install|i)\b(?!.*--frozen-lockfile)"
    r"|\bnpx\s+\S+@"
    r"|\bdotnet\s+add\s+package\b"
    r"|\bpip3?\s+install\b"
    r"|\buv\s+(pip\s+install|add)\b"
    r"|\bcargo\s+add\b",
    re.IGNORECASE,
)

# Sessões que já receberam injeção de memória para evitar duplicação em cada turno
_INJECTED_SESSIONS: set[str] = set()


def register(ctx: Any) -> None:
    """Ponto de entrada padrão invocado pelo Hermes Agent ao carregar o plugin."""

    # 1. Registro das 8 Skills canônicas
    for skill_name, description in SKILLS_MANIFEST:
        skill_path = PLUGIN_ROOT / "skills" / skill_name / "SKILL.md"
        if hasattr(ctx, "register_skill") and skill_path.is_file():
            ctx.register_skill(
                name=skill_name,
                path=skill_path,
                description=description,
            )

    # 2. Registro dos Slash Commands (/sdd-init, /sdd-change, etc.)
    if hasattr(ctx, "register_command"):
        for skill_name, description in SKILLS_MANIFEST:
            ctx.register_command(
                name=skill_name,
                handler=_make_command_handler(skill_name),
                description=description,
            )

    # 3. Registro das Tools determinísticas e passivas (Camada 0 do Gate)
    if hasattr(ctx, "register_tool"):
        ctx.register_tool(
            name="sdd_check_ids",
            toolset="sdd_workflow",
            schema={
                "name": "sdd_check_ids",
                "description": (
                    "Guarda mecânica passiva (read-only) de identificadores SDD. "
                    "Varre o repositório por exclusão e detecta IDs órfãos (citados sem declaração em docs/sdd/) "
                    "e declarações nunca citadas."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "root": {
                            "type": "string",
                            "description": "Caminho raiz do projeto (padrão: diretório atual '.').",
                        },
                        "strict": {
                            "type": "boolean",
                            "description": "Se verdadeiro, falha também quando houver declarações nunca citadas.",
                        },
                        "extra_prefixes": {
                            "type": "string",
                            "description": "Prefixos adicionais separados por vírgula (ex.: 'ADR,REQ').",
                        },
                    },
                },
            },
            handler=_handle_check_ids_tool,
        )

        ctx.register_tool(
            name="sdd_say_do_audit",
            toolset="sdd_workflow",
            schema={
                "name": "sdd_say_do_audit",
                "description": (
                    "Say-Do Gate passivo (read-only). "
                    "Audita o ledger de comandos executados na sessão atual para comprovar mecanicamente "
                    "se testes ou builds foram executados com exit code 0 após a última alteração de código."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "ID opcional da sessão (padrão: sessão ativa).",
                        }
                    },
                },
            },
            handler=_handle_say_do_tool,
        )

    # 4. Registro dos Hooks de Ciclo de Vida
    if hasattr(ctx, "register_hook"):
        ctx.register_hook("on_session_start", _on_session_start)
        ctx.register_hook("pre_llm_call", _on_pre_llm_call)
        ctx.register_hook("pre_tool_call", _on_pre_tool_call)
        ctx.register_hook("post_tool_call", _on_post_tool_call)


def _make_command_handler(skill_name: str):
    def _handler(args: str = "") -> str:
        skill_file = PLUGIN_ROOT / "skills" / skill_name / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8") if skill_file.is_file() else ""
        extra = f"\n\nArgumentos/Contexto do usuário: {args}" if args else ""
        return (
            f"[SDD Workflow — Ativando skill `{skill_name}`]\n\n"
            f"{content}{extra}"
        )

    return _handler


def _handle_check_ids_tool(params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    params = params or {}
    root = params.get("root") or os.getcwd()
    strict = bool(params.get("strict", False))
    extra_raw = params.get("extra_prefixes") or ""
    extra = [p.strip() for p in extra_raw.split(",") if p.strip()]
    return run_check_ids(root=root, strict=strict, extra_prefixes=extra)


def _handle_say_do_tool(params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    params = params or {}
    session_id = params.get("session_id") or "default"
    return audit_session_ledger(session_id=session_id)


def _on_session_start(**kwargs: Any) -> Dict[str, Any] | None:
    session_id = str(kwargs.get("session_id") or "default")
    workspace = str(kwargs.get("workspace") or os.getcwd())
    context_text = build_session_context(workspace)
    if context_text:
        _INJECTED_SESSIONS.add(session_id)
        return {"system_message": context_text}
    return None


def _on_pre_llm_call(**kwargs: Any) -> None:
    session_id = str(kwargs.get("session_id") or "default")
    if session_id in _INJECTED_SESSIONS:
        return
    workspace = str(kwargs.get("workspace") or os.getcwd())
    context_text = build_session_context(workspace)
    if not context_text:
        return
    messages = kwargs.get("messages")
    if isinstance(messages, list):
        messages.insert(0, {"role": "system", "content": context_text})
        _INJECTED_SESSIONS.add(session_id)


def _on_pre_tool_call(**kwargs: Any) -> Dict[str, Any] | None:
    tool_name = str(kwargs.get("tool_name") or "").lower()
    args = kwargs.get("args") or kwargs.get("params") or {}

    # 1. Guard-Install: pede confirmação explícita antes de instalar novas dependências
    if tool_name in {"terminal", "bash", "run_command", "shell"}:
        cmd = str(args.get("command") or args.get("cmd") or "")
        if INSTALL_PATTERN.search(cmd):
            return {
                "decision": "ask",
                "reason": (
                    "SDD Constitution (Guard-Install): instalar dependências novas exige "
                    "confirmação explícita do usuário. Confirme a versão pinada e a necessidade real."
                ),
            }

    # 2. Protege Skills canônicas SDD contra auto-mutação do Learning Loop do Hermes
    if tool_name in {"write_file", "patch", "edit_file", "skill_edit", "skill_write"}:
        target_path = str(args.get("path") or args.get("file_path") or args.get("name") or "")
        if "sdd-workflow" in target_path or "sdd-hermes" in target_path or "sdd-core-rules.md" in target_path:
            return {
                "decision": "block",
                "reason": (
                    "SDD Governança: As skills canônicas e regras núcleo do SDD Puro "
                    "são protegidas contra auto-mutação pelo Learning Loop. Registre aprendizados "
                    "do projeto em docs/sdd/11-project-memory.md."
                ),
            }

    return None


def _on_post_tool_call(**kwargs: Any) -> None:
    session_id = str(kwargs.get("session_id") or "default")
    tool_name = str(kwargs.get("tool_name") or "")
    args = kwargs.get("args") or kwargs.get("params") or {}
    result = kwargs.get("result")
    record_tool_event(
        session_id=session_id,
        tool_name=tool_name,
        args=args if isinstance(args, dict) else {},
        result=result,
    )
