# Changelog

All notable changes to `sdd-hermes` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [2.1.0] - 2026-11-15

### Added
- **Initial official release for Hermes Agent (`NousResearch/hermes-agent`)** aligned with **Pure SDD Standard v2.1**:
  - `plugin.yaml` & `__init__.py` (`register(ctx)`) wiring 8 skills, 8 slash commands, 2 passive mechanical tools (`sdd_check_ids`, `sdd_say_do_audit`), and 4 lifecycle hooks (`on_session_start`, `pre_llm_call`, `pre_tool_call`, `post_tool_call`).
  - **8 Canonical Skills**: `sdd-init`, `sdd-adopt`, `sdd-specify`, `sdd-design`, `sdd-tasks`, `sdd-implement`, `sdd-change`, `sdd-validate`.
  - **4 Subagent Profiles (`agents/`)**: `sdd-architect` (`deep`), `sdd-implementer` (`balanced`), `sdd-validator` (`balanced`, 100% passive read-only), `sdd-doc-writer` (`fast`).
  - **Native Python Mechanical ID Guard (`scripts/check_ids.py`)**: Zero-config, grammar-based (`PREFIX[-SCOPE][-Mn]-NUMBER`), exclusion-scoped ID verifier running on Python 3 standard library without requiring Node.js (alongside `scripts/check-ids.mjs` for Node/CI compatibility).
  - **Passive Layer-0 Say-Do Gate (`scripts/say_do_gate.py` — `DÍVIDA-SDD-01`)**: Passively tracks session terminal commands and file writes via `post_tool_call` to mechanically verify that tests/builds ran with `exit_code == 0` after the latest code edit.
  - **Pre-Design `Validate-Gap` Check (`DÍVIDA-SDD-02`)**: Integrated into `sdd-design` and `sdd-change` for brownfield domain comparison before creating `DES-xxx` decisions.
  - **3-Layer 100% Passive Quality Gate (`DÍVIDA-SDD-03`)**: Unified milestone gate combining Layer 0 mechanical checks with a two-stage passive `sdd-validator` report (`Stage 1: Strict GEARS & Scope Compliance` → `Stage 2: Constitution, Security & Global Infra Quality`).
  - **Learning Loop Governance Guard (`DÍVIDA-SDD-04`)**: `pre_tool_call` protection preventing autonomous self-learning loops from silently mutating `constitution.md` or canonical SDD skills.
  - **Scoped Low-Friction Interview & Proactive Scope Slicing (`DÍVIDA-SDD-05`)**: `sdd-architect`, `sdd-specify`, and `sdd-change` restrict code reading strictly to the touched domain, ask at most 3–5 focused questions with recommended defaults, and proactively propose splitting or narrowing oversized changes.
  - **Elastic Pagination with Auto-Compaction (`-02.md` — `DÍVIDA-SDD-06`)**: Enforces the 150-line file cap + 4–5 line paragraph density limit while supporting `10-validation-02.md` and `11-project-memory-02.md` overflow shards that are automatically linked in the main header and deleted once debts/active fronts are resolved.
  - **Deterministic Severity Taxonomy & Domain Calibration (`DÍVIDA-SDD-07`)**: Embeds the Universal SDD Severity Matrix (`Critical | High | Medium | Low`) inline in `rules/sdd-core-rules.md`, `HERMES.md.template`, `agents/sdd-validator.md`, and `templates/specs/10-validation.md`, paired with project-specific risk calibration in `templates/constitution.md.template`.
  - Full canonical template suite (`HERMES.md.template`, `constitution.md.template`, `specs/00..11` including `11-project-memory.md`, `changes/`, `archive/`).
