---
name: sdd-tasks
description: Deriva tarefas atômicas no ledger (07-tasks.md), critérios de aceite Given/When/Then (08-acceptance.md) e a matriz de rastreabilidade (09-traceability.md).
---

# SDD Tasks (Fases 07 a 09 — v2.1)

Transforma as especificações GEARS (`03-requirements.md`) e as decisões de arquitetura (`05-design.md`) em tarefas atômicas, verificáveis e rastreáveis no ledger do projeto.

## Passos:
1. **Leitura de Base**: Analise `03-requirements.md`, `05-design.md` e `06-roadmap.md` (ou o `delta-spec.md` de uma mudança ativa).
2. **Geração do Ledger (`07-tasks.md`)**:
   - Quebre a implementação em tarefas pequenas e atômicas (máximo de ~1 dia de trabalho humano / 1 sessão focada de subagente por task).
   - Toda task DEVE conter os campos canônicos: `ID` (`TASK-xxx`), `Title`, `Goal`, `Inputs`, `Related Requirements` (`FR-xxx`, `DES-xxx`), `Done When`, `Recommended Agent`, `Dependencies` e `Status: Pending`.
3. **Critérios de Aceite (`08-acceptance.md`)**:
   - Derive critérios `AC-xxx` em formato `Given / When / Then` diretamente a partir dos requisitos GEARS (cobrindo caminho feliz, casos negativos e estados `While`/`Where`).
4. **Matriz de Rastreabilidade (`09-traceability.md`)**:
   - Conecte ponta a ponta: `Intent Block (IB-xxx) → Requisito (FR/NFR-xxx) → Design (DES-xxx) → Task (TASK-xxx) → Critério de Aceite (AC-xxx)`.
5. **Guarda Mecânica Pré-Implementação**:
   - Execute a tool `sdd_check_ids` (ou `python scripts/check_ids.py .`) para garantir que nenhum ID ficou órfão antes de iniciar o código.
   - Atualize `docs/sdd/11-project-memory.md` (respeitando o teto de 150 linhas e paginação elástica `-02.md`).

## Próximo Passo:
Oriente o usuário a iniciar a implementação com `/sdd-implement`.
