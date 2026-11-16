"""
sdd-workflow — Plugin Oficial de Spec-Driven Development (SDD Puro v2.1) para Hermes Agent.

Registra no contexto do Hermes Agent (`ctx`):
1. As 8 Skills canônicas (`sdd-init`, `sdd-adopt`, `sdd-specify`, `sdd-design`,
   `sdd-tasks`, `sdd-implement`, `sdd-change`, `sdd-validate`).
2. Os 8 Slash Commands correspondentes (`/sdd-init`, `/sdd-adopt`, etc.).
3. As 2 Tools determinísticas e 100% passivas da Camada 0 do Quality Gate:
   - `sdd_check_ids`: Guarda mecânica de rastreabilidade de IDs (zero dependência de Node.js).
   - `sdd_say_do_audit`: Auditoria passiva do ledger de execução da sessão.
4. As regras núcleo (`rules/sdd-core-rules.md`) como seções do prompt de sistema
   (`register_system_prompt_section`), fonte única: o `.hermes.md` do projeto não as repete.
   Sem essa API (Hermes antigo), as regras vão no contexto do primeiro turno por um callback próprio.
5. Os 6 Hooks de ciclo de vida:
   - `on_session_start`: zera o estado de injeção da sessão (o Hermes ignora o retorno deste hook).
   - `pre_llm_call`: injeção enxuta de `11-project-memory.md`, ponteiros de paginação elástica
     (`-02.md`), tasks ativas (`07-tasks.md`) e changes ativas no primeiro turno, via `{"context": ...}`.
   - `pre_tool_call`: guarda determinística contra instalação não autorizada de pacotes
     (`guard-install`, portão humano), contra auto-mutação dos artefatos de governança
     (`constitution.md` → portão humano; skills/regras canônicas do plugin → bloqueio) e contra
     escrita por subagente `[sdd-validator]` (somente leitura).
   - `subagent_start` / `subagent_stop`: marcam e desmarcam a sessão do subagente `[sdd-validator]`.
   - `post_tool_call`: alimenta passivamente o ledger efêmero da sessão para o Say-Do Gate.

Contratos do Hermes usados aqui (docs: user-guide/features/hooks, features/plugins e
developer-guide/plugins):
- `pre_llm_call` injeta contexto retornando `{"context": "<texto>"}` (persistido com o turno).
- `register_system_prompt_section(id, conteúdo, position=..., max_chars=...)`: até 4.000 caracteres
  por seção e 8.000 somando todos os plugins.
- `subagent_start` recebe `child_session_id`, `child_subagent_id`, `child_role` e `child_goal`;
  `pre_tool_call` recebe `session_id` e `task_id`.
- `pre_tool_call` veta com `{"action": "block", "message": ...}` e escala para aprovação
  humana com `{"action": "approve", "message": ...}`. Qualquer outro retorno é ignorado.
- `post_tool_call` recebe `result` sempre como string JSON.
- Handlers de tool são chamados como `handler(params, **kwargs)` e retornam string JSON.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

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
CANONICAL_SKILL_NAMES = {name for name, _ in SKILLS_MANIFEST}

INSTALL_PATTERN = re.compile(
    r"\b(pnpm|npm|yarn|bun)\s+(add|install|i)\b(?!.*--frozen-lockfile)"
    r"|\bnpx\s+\S+@"
    r"|\bdotnet\s+add\s+package\b"
    r"|\bpip3?\s+install\b"
    r"|\buv\s+(pip\s+install|add)\b"
    r"|\bcargo\s+add\b"
    r"|\bpoetry\s+add\b"
    r"|\bgo\s+get\b"
    r"|\bcomposer\s+require\b"
    r"|\bgem\s+install\b",
    re.IGNORECASE,
)

TERMINAL_TOOL_NAMES = {"terminal", "bash", "run_command", "shell", "execute_command"}
FILE_WRITE_TOOL_NAMES = {"write_file", "patch", "edit_file", "apply_patch", "replace_in_file"}
SKILL_WRITE_TOOL_NAMES = {"skill_manage", "skill_edit", "skill_write"}

_PATCH_FILE_RE = re.compile(r"^\*\*\*\s+(?:Update|Add|Delete)\s+File:\s*(.+)$", re.MULTILINE)
_SHELL_SPLIT_RE = re.compile(r"\|\||&&|;|\||\n")
_REDIRECT_TARGET_RE = re.compile(r"(?<![0-9&>])>{1,2}\s*([^\s>&|;]+)")

MAX_TRACKED_SESSIONS = 200
# Sessões que já receberam injeção de memória (dict preserva ordem → descarte do mais antigo)
_INJECTED_SESSIONS: Dict[str, bool] = {}
# Sessões que já receberam as regras pelo caminho de fallback (Hermes sem system prompt sections)
_RULES_INJECTED_SESSIONS: Dict[str, bool] = {}
# Última sessão vista pelos hooks: é a sessão que `sdd_say_do_audit` audita por padrão
_ACTIVE_SESSION: Dict[str, str] = {"id": "default"}
# Identificadores (session_id / subagent_id) dos subagentes `[sdd-validator]` em execução
_READ_ONLY_IDS: Dict[str, bool] = {}

RULES_FILE = PLUGIN_ROOT / "rules" / "sdd-core-rules.md"
SECTION_MAX_CHARS = 4000
_SECTION_MARKER_RE = re.compile(r"<!-- section: ([a-z0-9-]+) -->\n")
VALIDATOR_MARKER = "[sdd-validator]"

# Subagente validador: ferramentas que escrevem ou delegam são vetadas; no terminal, só comandos de leitura.
READ_ONLY_BLOCKED_TOOLS = {"delegate_task", "execute_code", "memory", "send_message", "cronjob"}
_READ_ONLY_SHELL_HEADS = {
    "ls", "cat", "head", "tail", "grep", "rg", "find", "wc", "tree", "pwd", "diff", "file", "stat",
    "less", "more", "cut", "nl", "realpath", "dirname", "basename", "which", "echo",
}
_READ_ONLY_GIT_SUBCOMMANDS = {"diff", "log", "show", "status", "blame", "ls-files", "grep", "rev-parse", "branch"}
_FIND_WRITE_RE = re.compile(r"\s-(?:delete|exec|execdir|ok|okdir|fprint\w*|fls)\b")


def register(ctx: Any) -> None:
    """Ponto de entrada padrão invocado pelo Hermes Agent ao carregar o plugin."""

    # 1. Registro das 8 Skills canônicas
    if hasattr(ctx, "register_skill"):
        for skill_name, description in SKILLS_MANIFEST:
            skill_path = PLUGIN_ROOT / "skills" / skill_name / "SKILL.md"
            if not skill_path.is_file():
                continue
            try:
                ctx.register_skill(name=skill_name, path=skill_path, description=description)
            except TypeError:
                ctx.register_skill(skill_name, skill_path)

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
                    "Audita o ledger de comandos executados para comprovar mecanicamente se testes ou builds "
                    "foram executados com exit code 0 após a última alteração de código. "
                    "Status possíveis: VERIFIED_PASS (aprovado), FAILED_AFTER_EDIT, UNVERIFIED_CODE_EDIT e "
                    "NO_EVIDENCE (sem evidência — NÃO é aprovação)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "ID opcional da sessão (padrão: sessão ativa).",
                        },
                        "all_sessions": {
                            "type": "boolean",
                            "description": (
                                "Se verdadeiro, funde os eventos de todas as sessões do processo "
                                "(use quando o código foi editado por subagente via delegate_task)."
                            ),
                        },
                    },
                },
            },
            handler=_handle_say_do_tool,
        )

    # 4. Regras núcleo no prompt de sistema (fonte única; o `.hermes.md` do projeto não as repete)
    rules_in_system_prompt = _register_rule_sections(ctx)

    # 5. Registro dos Hooks de Ciclo de Vida
    if hasattr(ctx, "register_hook"):
        ctx.register_hook("on_session_start", _on_session_start)
        ctx.register_hook("pre_llm_call", _on_pre_llm_call)
        if not rules_in_system_prompt:
            # Callback separado: a memória e as regras não disputam o mesmo teto de contexto por hook.
            ctx.register_hook("pre_llm_call", _on_pre_llm_call_rules_fallback)
        ctx.register_hook("pre_tool_call", _on_pre_tool_call)
        ctx.register_hook("post_tool_call", _on_post_tool_call)
        ctx.register_hook("subagent_start", _on_subagent_start)
        ctx.register_hook("subagent_stop", _on_subagent_stop)


def load_rule_sections() -> List[tuple]:
    """[(id, texto)] das seções de `rules/sdd-core-rules.md`, com `{PLUGIN_ROOT}` resolvido."""
    try:
        raw = RULES_FILE.read_text(encoding="utf-8")
    except OSError:
        return []
    pieces = _SECTION_MARKER_RE.split(raw)
    root = PLUGIN_ROOT.as_posix()
    return [
        (pieces[i], pieces[i + 1].replace("{PLUGIN_ROOT}", root).strip())
        for i in range(1, len(pieces) - 1, 2)
    ]


def _register_rule_sections(ctx: Any) -> bool:
    register = getattr(ctx, "register_system_prompt_section", None)
    sections = load_rule_sections()
    if register is None or not sections:
        return False
    try:
        for section_id, text in sections:
            try:
                register(section_id, text, position="after_memory", max_chars=SECTION_MAX_CHARS)
            except TypeError:
                register(section_id, text)
        return True
    except Exception:  # API presente mas com contrato diferente: cai no fallback via pre_llm_call
        return False


def _make_command_handler(skill_name: str):
    def _handler(args: str = "", **_kwargs: Any) -> str:
        skill_file = PLUGIN_ROOT / "skills" / skill_name / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8") if skill_file.is_file() else ""
        extra = f"\n\nArgumentos/Contexto do usuário: {args}" if args else ""
        return (
            f"[SDD Workflow — Ativando skill `{skill_name}`]\n"
            f"Raiz do plugin: `{PLUGIN_ROOT.as_posix()}` — os caminhos `templates/...` e `scripts/...` "
            "citados abaixo são relativos a ESTA pasta (não à raiz do projeto do usuário).\n\n"
            f"{content}{extra}"
        )

    return _handler


def _as_tool_result(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _handle_check_ids_tool(params: Dict[str, Any] | None = None, **_kwargs: Any) -> str:
    params = params or {}
    root = params.get("root") or _session_cwd()
    strict = bool(params.get("strict", False))
    extra_raw = params.get("extra_prefixes") or ""
    extra = [p.strip() for p in str(extra_raw).split(",") if p.strip()]
    return _as_tool_result(run_check_ids(root=root, strict=strict, extra_prefixes=extra))


def _handle_say_do_tool(params: Dict[str, Any] | None = None, **kwargs: Any) -> str:
    params = params or {}
    session_id = str(
        params.get("session_id") or kwargs.get("session_id") or _ACTIVE_SESSION["id"] or "default"
    )
    all_sessions = bool(params.get("all_sessions", False))
    return _as_tool_result(audit_session_ledger(session_id=session_id, all_sessions=all_sessions))


def _session_cwd() -> str:
    """Diretório de trabalho DA SESSÃO, não do processo.

    No gateway do Hermes (usado também pelo `hermes -z` e pelas plataformas de mensagem) o processo roda em
    `/run/hermes-service/...`; o diretório do projeto vem da sessão (`TERMINAL_CWD` / cwd da sessão).
    A doc de plugins manda usar `agent.runtime_cwd.resolve_agent_cwd()`; `os.getcwd()` só como fallback.
    """
    try:
        from agent.runtime_cwd import resolve_agent_cwd

        return str(resolve_agent_cwd())
    except Exception:
        return os.getcwd()


def _touch_session(kwargs: Dict[str, Any]) -> str:
    session_id = str(kwargs.get("session_id") or "default")
    _ACTIVE_SESSION["id"] = session_id
    return session_id


def _workspace_from(kwargs: Dict[str, Any]) -> str:
    return str(kwargs.get("workspace") or kwargs.get("cwd") or _session_cwd())


def _on_session_start(**kwargs: Any) -> None:
    # O Hermes ignora o retorno de `on_session_start`: a injeção acontece em `pre_llm_call`.
    session_id = _touch_session(kwargs)
    _INJECTED_SESSIONS.pop(session_id, None)
    return None


def _on_pre_llm_call(**kwargs: Any) -> Dict[str, str] | None:
    session_id = _touch_session(kwargs)
    is_first_turn = bool(kwargs.get("is_first_turn", False))
    if session_id in _INJECTED_SESSIONS and not is_first_turn:
        return None

    context_text = build_session_context(_workspace_from(kwargs))
    _INJECTED_SESSIONS[session_id] = True
    while len(_INJECTED_SESSIONS) > MAX_TRACKED_SESSIONS:
        _INJECTED_SESSIONS.pop(next(iter(_INJECTED_SESSIONS)))
    if not context_text:
        return None
    return {"context": context_text}


def _on_pre_llm_call_rules_fallback(**kwargs: Any) -> Dict[str, str] | None:
    session_id = str(kwargs.get("session_id") or "default")
    if session_id in _RULES_INJECTED_SESSIONS and not kwargs.get("is_first_turn", False):
        return None
    _RULES_INJECTED_SESSIONS[session_id] = True
    while len(_RULES_INJECTED_SESSIONS) > MAX_TRACKED_SESSIONS:
        _RULES_INJECTED_SESSIONS.pop(next(iter(_RULES_INJECTED_SESSIONS)))
    text = "\n\n".join(body for _, body in load_rule_sections())
    return {"context": text} if text else None


def _on_subagent_start(**kwargs: Any) -> None:
    goal = str(kwargs.get("child_goal") or "")
    role = str(kwargs.get("child_role") or "")
    if VALIDATOR_MARKER not in goal.lower() and "sdd-validator" not in role.lower():
        return None
    for key in ("child_session_id", "child_subagent_id"):
        if kwargs.get(key):
            _READ_ONLY_IDS[str(kwargs[key])] = True
    while len(_READ_ONLY_IDS) > MAX_TRACKED_SESSIONS:
        _READ_ONLY_IDS.pop(next(iter(_READ_ONLY_IDS)))
    return None


def _on_subagent_stop(**kwargs: Any) -> None:
    for key in ("child_session_id", "child_subagent_id"):
        if kwargs.get(key):
            _READ_ONLY_IDS.pop(str(kwargs[key]), None)
    return None


def _is_read_only_caller(kwargs: Dict[str, Any]) -> bool:
    return any(str(kwargs.get(k) or "") in _READ_ONLY_IDS for k in ("session_id", "task_id", "subagent_id"))


def _is_read_only_command(cmd: str) -> bool:
    """Allow-list (fail-closed): cada segmento precisa ser um comando de leitura e nada pode ser escrito."""
    if _shell_write_targets(cmd):
        return False
    for segment in _SHELL_SPLIT_RE.split(cmd):
        tokens = segment.strip().split()
        if not tokens:
            continue
        head = tokens[0].lower().rsplit("/", 1)[-1]
        if head == "git":
            sub = next((t for t in tokens[1:] if not t.startswith("-")), "")
            if sub not in _READ_ONLY_GIT_SUBCOMMANDS:
                return False
        elif head == "find":
            if _FIND_WRITE_RE.search(segment):
                return False
        elif head not in _READ_ONLY_SHELL_HEADS:
            return False
    return True


_BLOCK_READ_ONLY = {
    "action": "block",
    "message": (
        "SDD Quality Gate: o subagente sdd-validator é 100% passivo (read-only). Ele só lê arquivos, "
        "roda comandos de leitura e as tools sdd_check_ids / sdd_say_do_audit; correções ficam com o implementador."
    ),
}


def _candidate_paths(args: Dict[str, Any]) -> List[str]:
    paths = [str(args[k]) for k in ("path", "file_path", "Path", "target_file") if args.get(k)]
    for key in ("patch", "diff", "content"):
        value = args.get(key)
        if isinstance(value, str) and "*** " in value:
            paths.extend(m.strip() for m in _PATCH_FILE_RE.findall(value))
    return paths


def _shell_write_targets(cmd: str) -> List[str]:
    """
    Caminhos que um comando de shell ESCREVE (não os que apenas lê): alvos de redirecionamento,
    de `tee`/`rm`/`truncate`/`mv`, de `sed -i`/`perl -i` e o destino de `cp`.
    Ler ou copiar A PARTIR do plugin (ex.: templates no `sdd-init`) continua permitido.
    """
    targets: List[str] = []
    for segment in _SHELL_SPLIT_RE.split(cmd):
        targets.extend(_REDIRECT_TARGET_RE.findall(segment))
        tokens = _REDIRECT_TARGET_RE.sub("", segment).split()
        if not tokens:
            continue
        head = tokens[0].lower().rsplit("/", 1)[-1]
        operands = [t for t in tokens[1:] if not t.startswith("-")]
        flags = [t for t in tokens[1:] if t.startswith("-")]
        if head in {"tee", "rm", "truncate", "mv"}:
            targets.extend(operands)
        elif head == "cp" and operands:
            targets.append(operands[-1])
        elif head in {"sed", "perl"} and any("i" in f.lstrip("-") for f in flags):
            targets.extend(operands)
    return [t.strip("\"'").replace("\\", "/") for t in targets]


def _is_inside_plugin(raw_path: str) -> bool:
    try:
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            candidate = Path(_session_cwd()) / candidate
        candidate.resolve().relative_to(PLUGIN_ROOT)
        return True
    except (ValueError, OSError):
        return False


def _is_constitution(raw_path: str) -> bool:
    return raw_path.replace("\\", "/").rstrip("/").endswith("docs/sdd/constitution.md")


_BLOCK_PLUGIN = {
    "action": "block",
    "message": (
        "SDD Governança: as skills canônicas e as regras núcleo do plugin SDD são protegidas contra "
        "auto-mutação (Learning Loop). Registre aprendizados do projeto em docs/sdd/11-project-memory.md "
        "ou proponha a mudança ao usuário."
    ),
}
_APPROVE_CONSTITUTION = {
    "action": "approve",
    "rule_key": "sdd:constitution-edit",
    "message": (
        "SDD Governança: docs/sdd/constitution.md só muda por decisão explícita do usuário, "
        "registrada com justificativa e data. Confirme esta alteração."
    ),
}


def _on_pre_tool_call(**kwargs: Any) -> Dict[str, Any] | None:
    _touch_session(kwargs)
    tool_name = str(kwargs.get("tool_name") or "").lower()
    args = kwargs.get("args") or kwargs.get("params") or {}
    if not isinstance(args, dict):
        return None

    # 0. Subagente `[sdd-validator]`: somente leitura, imposto pelo plugin (não só pelo prompt)
    if _is_read_only_caller(kwargs):
        if tool_name in FILE_WRITE_TOOL_NAMES | SKILL_WRITE_TOOL_NAMES | READ_ONLY_BLOCKED_TOOLS:
            return dict(_BLOCK_READ_ONLY)
        if tool_name in TERMINAL_TOOL_NAMES:
            cmd = str(args.get("command") or args.get("cmd") or args.get("CommandLine") or "")
            if not _is_read_only_command(cmd):
                return dict(_BLOCK_READ_ONLY)
            return None

    if tool_name in TERMINAL_TOOL_NAMES:
        cmd = str(args.get("command") or args.get("cmd") or args.get("CommandLine") or "")

        # 1. Governança: edição de artefatos protegidos feita pelo terminal
        for target in _shell_write_targets(cmd):
            if _is_inside_plugin(target):
                return dict(_BLOCK_PLUGIN)
            if _is_constitution(target):
                return dict(_APPROVE_CONSTITUTION)

        # 2. Guard-Install: portão humano antes de instalar novas dependências
        if INSTALL_PATTERN.search(cmd):
            return {
                "action": "approve",
                "rule_key": "sdd:guard-install",
                "message": (
                    "SDD Constitution (Guard-Install): instalar dependências novas exige confirmação "
                    "explícita do usuário. Confirme a versão pinada e a necessidade real."
                ),
            }
        return None

    # 3. Protege skills canônicas (Learning Loop do Hermes edita skills via tool própria)
    if tool_name in SKILL_WRITE_TOOL_NAMES:
        skill_ref = str(args.get("name") or args.get("skill") or args.get("skill_name") or "")
        if skill_ref.split(":")[-1].strip() in CANONICAL_SKILL_NAMES:
            return dict(_BLOCK_PLUGIN)
        return None

    # 4. Protege arquivos de governança contra escrita direta
    if tool_name in FILE_WRITE_TOOL_NAMES:
        for raw_path in _candidate_paths(args):
            if _is_inside_plugin(raw_path):
                return dict(_BLOCK_PLUGIN)
            if _is_constitution(raw_path):
                return dict(_APPROVE_CONSTITUTION)

    return None


def _on_post_tool_call(**kwargs: Any) -> None:
    session_id = _touch_session(kwargs)
    args = kwargs.get("args") or kwargs.get("params") or {}
    record_tool_event(
        session_id=session_id,
        tool_name=str(kwargs.get("tool_name") or ""),
        args=args if isinstance(args, dict) else {},
        result=kwargs.get("result"),
    )
