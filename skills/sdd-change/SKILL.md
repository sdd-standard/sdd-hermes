---
name: sdd-change
description: Ciclo completo de Delta Specs (proposal → apply → archive) com Inspeção Escopada ao domínio, Entrevista de Baixa Fricção, Fatiamento Proativo de Changes Grandes, Validate-Gap e Paginação Elástica.
---

# SDD Change (Delta Specs — Ciclo Completo v2.1)

O fluxo `/sdd-change` governa toda evolução contínua pós-baseline (especialmente em projetos **Brownfield**).
**Regra de Ouro:** Nunca edite diretamente os artefatos centrais em `docs/sdd/00..09` após o baseline; toda alteração passa pela máquina de 3 estados: **`proposal` → `apply` → `archive`**.

---

## Estado 1 — Proposal (Com Inspeção Escopada e Fatiamento Proativo)

1. **Inspeção Estritamente Escopada (*Scoped Inspection*)**:
   - Ao ouvir o objetivo da mudança do usuário, **NUNCA leia ou escaneie o código legado inteiro do repositório**.
   - Localize e leia **apenas os arquivos/módulos do domínio que será modificado ou discutido**, além de `constitution.md`, `11-project-memory.md` e `10-validation.md` (verificando se já existem dívidas ativas daquele domínio).
2. **Detecção de Change Grande Demais (*Scope Slicing*)**:
   - Se você detectar que a mudança pedida pelo usuário é muito extensa (ex.: altera múltiplos *bounded contexts*, mistura grande refatoração com nova feature ou geraria dezenas de tasks), **pare antes de criar arquivos e proponha ao usuário**:
     - **Opção A (Fragmentar):** Dividir em múltiplas changes menores e sequenciais (`changes/<parte-1>/`, `changes/<parte-2>/`); ou
     - **Opção B (Estreitar + Registrar Dívida/Futuro):** Focar a change atual apenas no núcleo imediato e registrar as demais modificações solicitadas como **dívidas ativas / escopo futuro** em `docs/sdd/10-validation.md` (ou `06-roadmap.md`).
3. **Entrevista de Estresse de Baixa Fricção (Anti-Burocracia)**:
   - Com base no que você viu no código do domínio tocado, faça no máximo **3 a 5 perguntas cirúrgicas** sobre aspectos que o usuário não previu (contratos quebrados, migração de dados, falhas, segurança), **sempre sugerindo uma opção recomendada**.
4. **Geração e Aprovação da Proposal**:
   - Crie `docs/sdd/changes/<nome-da-mudanca>/proposal.md` contendo: `Intent Block`, `Why`, `What`, `Scope (Inclui / Fora de escopo)`, `Success Criteria` e `Artefatos impactados`.
   - Peça aprovação explícita da `proposal.md` ao usuário.

---

## Estado 2 — Validate-Gap, Delta Spec e Tasks

5. **Diagnóstico `Validate-Gap` (Brownfield)**:
   - Confronte o código atual do módulo tocado com a proposta aprovada, identificando o que já existe (*as-built*) vs. o que será adicionado/modificado/removido.
   - **Spec-on-Touch**: Se a área tocada nunca havia sido especificada antes, a seção `ADDED` do delta incluirá a especificação mínima daquela área.
6. **Escrita do `delta-spec.md`**:
   - Escreva `docs/sdd/changes/<nome-da-mudanca>/delta-spec.md` com as seções `ADDED`, `MODIFIED` e `REMOVED`.
   - Todo requisito funcional/não-funcional DEVE usar a sintaxe **GEARS** canônica (`[Where] [While] [When] the <subject> shall <behavior>`, com keywords em inglês) e decisões de design usam `DES-xxx`.
   - Peça aprovação do `delta-spec.md` ao usuário.
7. **Ledger da Mudança (`tasks.md`) e Gate Pré-Apply Passivo**:
   - Quebre a mudança em tarefas atômicas em `docs/sdd/changes/<nome-da-mudanca>/tasks.md` (`ID`, `Title`, `Goal`, `Related Requirements`, `Done When`, `Status: Pending`).
   - Acione o **`sdd-validator` (100% passivo / read-only)** para auditar a consistência do delta contra a `constitution.md` antes de liberar o código.

---

## Estado 3 — Apply (Implementação via `/sdd-implement`)

8. Oriente ou execute a implementação das tasks ativas via `/sdd-implement` lendo `docs/sdd/changes/<nome-da-mudanca>/tasks.md`.
   - **Nova subtarefa técnica descoberta no Apply** (mesmo requisito): declare primeiro em `tasks.md` e informe o usuário antes de codificar.
   - **Novo comportamento de negócio descoberto no Apply**: atualize o `delta-spec.md` primeiro (em GEARS), obtenha aprovação do usuário e só então crie a task.

---

## Estado 4 — Archive (Gate Passivo em 3 Camadas + Consolidação + Higiene Elástica)

Ao concluir todas as tasks da mudança:

9. **Quality Gate Final Passivo em 3 Camadas**:
   - Rode a **Camada 0 Passiva**: `sdd_check_ids` (`python scripts/check_ids.py .`) + `sdd_say_do_audit` (comprovando testes verdes após a última edição).
   - Acione o **`sdd-validator` (100% passivo)** para auditar em 2 estágios (`1. Conformidade GEARS` e `2. Qualidade & Infra Global`). Qualquer divergência reportada é corrigida pelo implementador antes de consolidar.
10. **Consolidação na Baseline (`docs/sdd/`)**:
    - Incorpore as seções `ADDED`, `MODIFIED` e `REMOVED` do `delta-spec.md` nos artefatos centrais (`02-spec.md`, `03-requirements.md`, `04-domain-model.md`, `05-design.md`, `08-acceptance.md` e `09-traceability.md`).
11. **Higiene de Dívidas e Paginação Elástica (*Overflow Sharding*)**:
    - Dívidas do `10-validation.md` (ou `10-validation-02.md`) resolvidas por esta change devem ser **MOVIDAS** para `docs/sdd/archive/validation-log.md` com `"Fechado por: sdd-change <nome>"`.
    - Se novos achados abertos fizerem `10-validation.md` passar de 150 linhas, crie/atualize `10-validation-02.md` e linke no topo.
    - Se, após sanar dívidas, o conteúdo de `10-validation-02.md` voltar a caber no `10-validation.md` principal (`≤ 150 linhas`), **consolide no arquivo principal, remova o link e EXCLUA o arquivo `10-validation-02.md`**.
12. **Arquivamento e Rotação de Memória**:
    - Mova a pasta `docs/sdd/changes/<nome-da-mudanca>/` inteira para `docs/sdd/archive/<nome-da-mudanca>/`.
    - Atualize `docs/sdd/11-project-memory.md` mantendo apenas as ~5 mudanças mais recentes e movendo o resumo das mais antigas para `docs/sdd/archive/memory-history.md` (compactando e excluindo `11-project-memory-02.md` se não for mais necessário).
