---
name: sdd-design
description: Conduz as fases de Design SDD (04→06) — Diagnóstico Validate-Gap, Domain Model (DDD), Design Técnico (DES-xxx) e Roadmap a partir dos requisitos GEARS aprovados.
---

# SDD Design (Fases 04 a 06 — v2.1)

O Requisito (GEARS) define **O QUE** o sistema deve fazer; o Design define **COMO** ele vai atingir isso respeitando a `constitution.md`.

## Pré-condição:
- `02-spec.md` e `03-requirements.md` (ou `delta-spec.md` ativo) devem estar pelo menos em estado `Reviewed`/`Approved`. Se a base estiver só em `Reviewed`, registre antes a dívida de maturidade (`Type: Maturity`, com snapshot dos IDs e do texto consumidos) no `10-validation.md`; o `Status` dos artefatos só muda por decisão do usuário.

## Passos:
1. **Diagnóstico Pré-Design Escopado (`Validate-Gap`)**:
   - Se o projeto já possuir código existente no módulo/domínio afetado, inspecione **apenas os arquivos daquele domínio** (jamais o repositório inteiro).
   - Compare o estado atual (*as-built*) com os novos requisitos GEARS (*to-be*), listando brevemente: (a) o que será reaproveitado; (b) o que precisa ser alterado/estendido; (c) possíveis colisões de contrato ou schema.
2. **Entrevista de Trade-offs de Baixa Fricção**:
   - Quando houver mais de um caminho arquitetural relevante, apresente ao usuário em poucas linhas com uma **opção recomendada** clara antes de travar a decisão.
3. **Geração dos Artefatos**:
   - **`04-domain-model.md`**: *Bounded contexts*, entidades, agregados, Value Objects, eventos de domínio, invariantes e linguagem ubíqua (ACLs quando houver integração externa).
   - **`05-design.md`**: Arquitetura, componentes, fluxos e decisões enumeradas como `DES-xxx` (cada uma com `Related Requirements: FR-xxx` e `Rationale` justificando o trade-off).
   - **`06-roadmap.md`**: Fatiamento em MVP e milestones sequenciais com critérios claros de avanço.
4. **Validação Passiva e Memória**:
   - Submeta o design ao check passivo do **`sdd-validator`** (verificando se nenhum requisito ficou órfão de design e se não há violação da `constitution.md`).
   - Atualize `docs/sdd/11-project-memory.md` (respeitando o gatilho de paginação (150 linhas ou 7.000 caracteres) e a Paginação Elástica `-02.md`).

## Próximo Passo:
Oriente o usuário a usar `/sdd-tasks` para derivar o ledger de execução (`07-tasks.md`), critérios de aceite (`08-acceptance.md`) e matriz de rastreabilidade (`09-traceability.md`).
