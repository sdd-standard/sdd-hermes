---
name: sdd-implement
description: Executa as tarefas ativas (In Progress) do ledger SDD e aciona ao final de cada milestone o Quality Gate 100% Passivo em 3 Camadas (Camada 0 Mecânica + Estágios 1 e 2 do sdd-validator).
---

# SDD Implement (Execução Guiada & Gate Passivo em 3 Camadas — v2.1)

A fase de código real. Só altere código de produção através desta skill e com uma task formalmente marcada como `In Progress`.

## Ciclo de Execução por Task:
1. **Protocolo de Sessão**: Leia `constitution.md` → `11-project-memory.md` → `10-validation.md` → ledger ativo:
   - **Baseline (Greenfield)**: `docs/sdd/07-tasks.md`.
   - **Mudança ativa (Delta)**: `11-project-memory.md` indica qual change está em `apply` → leia **apenas** `docs/sdd/changes/<ativa>/tasks.md` (e verifique se há avisos de paginação elástica `10-validation-02.md` ou `11-project-memory-02.md`).
2. **Seleção da Task**: Selecione a task `In Progress` existente, ou a primeira `Pending` sem dependências bloqueadas. Confirme com o usuário em 1 linha.
3. **Gate de Entrada**: A task possui `Related Requirements` e `Done When`? Há achado `Critical`/`High` aberto **sem** `Risk Acceptance` do usuário no `10-validation.md`? Se sim → pare e reporte. Dívidas aceitas pelo usuário e dívidas de maturidade (`Medium`) não bloqueiam.
4. **Ativação e Implementação**:
   - Marque `Status: In Progress` no ledger **antes** de tocar no código.
   - Implemente o código e os testes automatizados seguindo estritamente os `FR-xxx` e `DES-xxx` vinculados (delegando ao perfil `sdd-implementer` via `delegate_task` quando aplicável).
5. **Gate de Saída da Task (Evidência para o Say-Do Gate)**:
   - **Execute a suíte de testes no terminal** após a última edição de código e confirme `exit code 0`.
   - Com `Done When` satisfeito e testes verdes, mude para `Status: Done` e atualize `11-project-memory.md` no mesmo turno.
   - Se a task concluir uma funcionalidade visível ao usuário, acione o `sdd-doc-writer` (`README.md` + `docs/features/`).

---

## Quality Gate de Milestone (100% Passivo em 3 Camadas)

Ao concluir a última task de um milestone (ou a última task de uma mudança ativa em `changes/<nome>/tasks.md`):

> **Regra Inegociável de Passividade:** Todas as 3 camadas do Gate abaixo são **100% PASSIVAS (`read-only`)**. Elas apenas inspecionam e reportam divergências/erros para que **você (o implementador/orquestrador)** realize as correções.

### Passo 6 — Camada 0: Piso Mecânico Passivo (`sdd_check_ids` + `sdd_say_do_audit`)
1. Execute a verificação mecânica de IDs:
   - Chame a tool `sdd_check_ids`.
   - Se houver siglas órfãs (`exit 1`), **corrija antes de chamar o validador**.
2. Execute a auditoria mecânica de execução (`sdd_say_do_audit`):
   - Confirma no ledger da sessão que um comando de teste/build realmente rodou com `exit_code == 0` após a última edição de código.
   - Só `VERIFIED_PASS` libera o gate. Se acusar `UNVERIFIED_CODE_EDIT` ou `FAILED_AFTER_EDIT`, **rode/corrija os testes antes de chamar o validador**.
   - `NO_EVIDENCE` **não é aprovação** (ledger vazio: sessão nova ou código editado em outra sessão): rode o comando oficial de testes (constitution §3) e re-audite. Se o código foi editado por subagente via `delegate_task`, audite com `all_sessions: true`.

### Passo 7 — Camadas 1 e 2: Acione o Subagente `sdd-validator` (100% Passivo / Read-Only)
Com a Camada 0 limpa, acione o `sdd-validator` via `delegate_task` (`goal` começando com `[sdd-validator]`, `context` = `agents/sdd-validator.md` da raiz do plugin + escopo do milestone; o plugin trava esse subagente em somente leitura). Ele re-executa por conta própria as duas tools passivas da Camada 0 (a prova não depende do relato de quem implementou), lê o código real (`arquivo:linha`) sem editar nada e emite seu relatório em dois estágios:
- **Camada 1 (Estágio 1 — Conformidade Estrita GEARS & Escopo):** Verifica cobertura de cada `FR-xxx`, `NFR-xxx`, `AC-xxx` e ausência de invenção fora da spec (*anti-scope-creep*).
- **Camada 2 (Estágio 2 — Qualidade, Constitution e Infra Global):** Verifica aderência à `constitution.md`, segurança e interações com infra global (middlewares, rotas raiz, auth, banco).

### Passo 8 — Correção pelo Implementador e Destino dos Achados
- **Achados `Critical`/`High` apontados pelo validador**:
  - Se a correção for tornar o código conforme a spec já aprovada → **o implementador corrige o código no mesmo gate**, re-roda os testes e re-valida.
  - Se exigir mudar a spec ou decisão de produto → só passa como **`APROVADO COM RESSALVAS`** com **Aceite de Risco do usuário** (sempre confirme antes; nunca o agente): a severidade original é mantida e a `VAL` no `10-validation.md` recebe `Risk Acceptance: <quem>, <data> — <justificativa> — revisão: <data ou gatilho>`. Falha da Camada 0 nunca é aceitável; aceitar violação da `constitution.md` exige registrar a exceção na seção 8 dela. Sem aceite → **`BLOQUEADO`**; o milestone não avança.
- **Registro em Duas Camadas**:
  - Adicione o bloco `"Registro do gate Mn"` no ledger (`07-tasks.md`). Achado **corrigido no gate** vive apenas nesse bloco.
  - **Todo achado que permanecer ABERTO** (qualquer severidade) deve ser registrado também em `docs/sdd/10-validation.md` como dívida ativa (`VAL-nnn`, com ponteiro cruzado).

### Passo 9 — Higiene de Dívida, Memória e Paginação Elástica (*Overflow Sharding*)
1. **Dívidas Sanadas → Cold Storage**: Se este milestone resolveu dívidas de `10-validation.md` (ou `10-validation-02.md`), **MOVA** essas entradas para `docs/sdd/archive/validation-log.md` (append-only).
2. **Rotação de Memória**: Mantenha apenas os ~5 milestones/changes mais recentes em `11-project-memory.md`, movendo os anteriores para `docs/sdd/archive/memory-history.md`.
3. **Paginação Elástica e Auto-Exclusão (`-02.md`)**:
   - Se `10-validation.md` ou `11-project-memory.md` passar de **150 linhas ou do teto de caracteres** (7.000 no memory, 16.000 no validation), crie `10-validation-02.md` ou `11-project-memory-02.md` e linke no topo do arquivo principal. Nunca resuma nem corte uma dívida para caber.
   - Se, após sanar dívidas ou rotacionar memória, os itens de um arquivo `-02.md` voltarem a caber no arquivo principal (dentro dos dois tetos), **repatrie os itens para o arquivo principal, remova o link do cabeçalho e EXCLUA o arquivo `-02.md`**.

### Passo 10 — Fechamento
- Se esta era a última task de uma mudança ativa (`changes/<nome>/tasks.md`), conduza o passo de **Archive** da skill `/sdd-change`.
- Apresente o resultado ao usuário e aguarde aprovação manual antes de iniciar o próximo milestone ou realizar commit.
