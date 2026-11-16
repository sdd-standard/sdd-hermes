---
trigger: always_on
description: Regras e Fundamentos do Spec-Driven Development (SDD Puro v2.1) para Hermes Agent.
---

# SDD Core Rules & Metodologia (Spec-Driven Development — v2.1)

Este projeto opera sob a metodologia **Spec-Driven Development (SDD Puro v2.1)**. A especificação é o artefato primário, versionado, vivo e central. Código, testes, tarefas, design e documentação são derivados dela.

---

## 1. Princípios Inegociáveis (P1 a P11)

- **P1 — A especificação é a fonte da verdade**: Mudanças começam sempre na spec (`docs/sdd/`), nunca no código.
- **P2 — Constitution vem antes da especificação**: Princípios inegociáveis (`constitution.md`) governam todas as fases do projeto.
- **P3 — A especificação deve ser viva**: Evolui com o projeto. Spec desatualizada é spec morta.
- **P4 — Rastreabilidade obrigatória**: Cadeia inquebrável: `Objetivo (Intent) → Requisito (GEARS) → Decisão de Design (DES) → Tarefa (TASK) → Critério de Aceite (AC) → Teste → Código`.
- **P5 — Requisitos verificáveis**: Nunca use termos vagos ("rápido", "simples"). Use métricas observáveis.
- **P6 — Ambiguidade tratada cedo**: Lacunas não resolvidas NUNCA são preenchidas com suposições — marque imediatamente como `PENDENTE DE DEFINIÇÃO` e registre em `10-validation.md`.
- **P7 — Design vem antes da execução**: Arquitetura, componentes e trade-offs justificados antes de tasks e código.
- **P8 — Tarefas derivam dos artefatos**: Nenhuma tarefa nasce do nada; cada task no `07-tasks.md` aponta para um requisito ou decisão.
- **P9 — Validação é gate contínuo e 100% passivo**: Cada fase é validada antes de avançar. Ao fechar milestones, o Quality Gate Passivo em 3 Camadas audita o código real sem jamais alterá-lo, reportando divergências para o implementador corrigir.
- **P10 — SDD não é Waterfall**: Especificar o suficiente para reduzir risco incrementalmente, aprender e consolidar.
- **P11 — Estado fora do chat (Engenharia de Contexto e Paginação Elástica)**: O chat é volátil. TODO o estado, decisões e tarefas residem em arquivos versionados (`docs/sdd/`). A memória entre sessões vive em `11-project-memory.md` e as dívidas ativas em `10-validation.md` (teto de 150 linhas por arquivo, máximo de 4–5 linhas por parágrafo, com paginação elástica `-02.md` quando necessário e auto-exclusão ao sanar pendências).

---

## 2. Sintaxes Formais

### Intent Block (Captura o PORQUÊ)
Usado em Discovery, Épicos e Visão Geral (`02-spec.md` ou `proposal.md`):
```text
Intent Block:
Goal:        <objetivo de negócio ou do usuário>
Expectation: <expectativa mensurável em alto nível>
Action:      <capacidade ou mudança que será construída>
Result:      <resultado observável ou valor entregue>
```

### GEARS — Generalized EARS (Formaliza O QUE deve acontecer)
Sintaxe canônica para todos os requisitos funcionais e não-funcionais (`03-requirements.md` e `delta-spec.md`).
**Regra rígida: Keywords SEMPRE em inglês, mesmo com conteúdo em português.**

```text
[Where <static precondition / feature flag / config>]
[While <stateful precondition / runtime state>]
[When <trigger / event>]
the <subject> shall <behavior observável>.
```

- `Where`: Pré-condição estática (ambiente, flag ativada).
- `While`: Pré-condição dinâmica de estado (ex: "While user account is locked").
- `When`: Gatilho ou evento (ex: "When the user submits valid credentials").
- `<subject>`: O componente, serviço ou ator específico (não apenas "o sistema").
- `shall`: Comportamento estrito e mensurável.

---

## 3. Matriz Canônica Universal de Severidades (`Critical | High | Medium | Low`)

Todo achado de validação (`VAL-xxx`) deve ser classificado combinando esta matriz universal com a seção de **Calibração de Criticidade do Domínio** definida na `docs/sdd/constitution.md` do projeto:

| Severidade | Efeito no Gate | Definição Objetiva no SDD Puro |
| :--- | :---: | :--- |
| **`Critical`** | **BLOQUEIA** | Violação direta da `constitution.md`, falha de segurança/dados (LGPD, vazamento, perda), quebra do Piso Mecânico (`check-ids` com órfãs ou testes falhando/não executados após edição), regressão que quebra funcionalidade existente ou cláusula principal `shall` de um `FR`/`NFR` não implementada/invertida. |
| **`High`** | **BLOQUEIA** | Omissão de cláusula condicional GEARS (`Where` estático, `While` estado ou `When` gatilho), falha de integração com a Infraestrutura Global (middleware, auth, rate-limit, rota raiz, banco), requisito `FR-xxx` sem teste automatizado exercitando seu `AC-xxx`, ou invenção de comportamento fora da spec (*scope creep*). |
| **`Medium`** | **NÃO BLOQUEIA** *(Vai para `10-validation.md`)* | Desvio parcial de Design (`DES-xxx`) sem quebrar o comportamento (`FR`/`AC`) nem a `constitution.md`, cobertura de testes ausente apenas para borda secundária, critério verificável somente em runtime/QA manual, ou dívida técnica/acoplamento restrito ao módulo local. |
| **`Low`** | **NÃO BLOQUEIA** *(Vai para `10-validation.md`)* | Divergência cosmética, nomenclatura interna menor, documentação secundária ou oportunidade de otimização acima do exigido pelo `NFR-xxx`. |

---

## 4. Regras Estritas de Execução e Governança (v2.1)

1. **NUNCA modifique código sem uma task `In Progress`**: O arquivo `docs/sdd/07-tasks.md` (ou `tasks.md` da delta-spec) é o ledger de execução. Não gere código se a tarefa não estiver formalmente ativa e rastreada a um requisito.
2. **Mudanças pós-baseline são Delta Specs**: Após a baseline inicial de specs (`00` a `10`), NUNCA edite diretamente os arquivos centrais. Use o ciclo de vida de mudanças (`sdd-change`):
   - `proposal.md` ➔ `delta-spec.md` (seções ADDED / MODIFIED / REMOVED em GEARS) ➔ `tasks.md` ➔ Implementação ➔ Gate Passivo ➔ Consolidação nas specs e arquivamento em `archive/`.
3. **Entrevista Escopada, Baixa Fricção e Fatiamento de Escopo**:
   - Em projetos existentes, o entrevistador (`sdd-architect`) inspeciona **apenas** os arquivos do domínio/módulo em pauta (jamais o repositório inteiro de uma vez).
   - Faz poucas perguntas cirúrgicas (máx. 3–5) sempre acompanhadas de uma opção recomendada.
   - Se detectar que a mudança solicitada é grande demais, sugere proativamente fragmentar em múltiplas changes ou estreitar a change atual e registrar o excedente como dívida ativa/escopo futuro em `10-validation.md` ou `06-roadmap.md`.
4. **Quality Gate 100% Passivo em 3 Camadas**:
   - **Camada 0 (Piso Mecânico Passivo):** `sdd_check_ids` (rastreabilidade de IDs) + `sdd_say_do_audit` (confirmação mecânica de testes executados na sessão).
   - **Camada 1 (Validador Passivo — Estágio 1):** Conformidade estrita GEARS e `AC-xxx` (sem omissões e sem *scope creep*).
   - **Camada 2 (Validador Passivo — Estágio 2):** Qualidade arquitetural, `constitution.md` e interações com infra global.
   - *Regra de Ouro:* Nenhuma das 3 camadas altera arquivos; todas apenas reportam divergências para o implementador corrigir.
5. **Paginação Elástica com Auto-Exclusão (*Overflow Sharding*)**:
   - Nunca crie parágrafos gigantescos de uma única linha para burlar o teto de 150 linhas de `10-validation.md` ou `11-project-memory.md`.
   - Se o volume de dívidas/memória ativa ultrapassar 150 linhas (com parágrafos de até 4–5 linhas), crie `10-validation-02.md` ou `11-project-memory-02.md`, referencie-o no topo do arquivo principal e **exclua o arquivo `-02.md` assim que as pendências forem sanadas** e o conteúdo voltar a caber no arquivo principal.
6. **Imutabilidade contra Auto-Mutação do Learning Loop**:
   - O *learning loop* nativo do Hermes Agent NUNCA deve editar silenciosamente `docs/sdd/constitution.md`, `rules/sdd-core-rules.md` ou as skills `sdd-*`. Aprendizados operacionais vão para `11-project-memory.md`.
7. **Confirmação de dependências**: SEMPRE peça permissão explícita ao usuário antes de adicionar bibliotecas ou dependências ao projeto.
