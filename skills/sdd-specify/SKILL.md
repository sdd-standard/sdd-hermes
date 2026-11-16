---
name: sdd-specify
description: Conduz as fases de especificação SDD (00→03) — Project Brief, Discovery, Spec (Intent Blocks) e Requirements (GEARS) — utilizando entrevista escopada de baixa fricção.
---

# SDD Specify (Fases 00 a 03 — v2.1)

Esta skill guia a captura estruturada de intenção de negócio e a formalização de requisitos verificáveis, delegando ao perfil `sdd-architect` (`delegate_task` quando aplicável).

## Pré-condições:
- `docs/sdd/constitution.md` deve existir. Se não existir, oriente o usuário a rodar `/sdd-init` ou `/sdd-adopt` primeiro.
- Leia `11-project-memory.md` e verifique o estado dos artefatos `00` a `03`.

## Protocolo de Entrevista Escopada e Baixa Fricção:
1. **Escopo Estrito de Leitura**: Se este `specify` estiver sendo executado para uma feature em um projeto existente, inspecione **apenas os arquivos do domínio/módulo relacionado à feature** (nunca leia o repositório inteiro).
2. **Detecção de Escopo Excessivo (*Scope Slicing*)**: Se perceber que o escopo pedido pelo usuário abrange múltiplos domínios grandes de uma vez, proponha dividir em fases/milestones menores ou estreitar o escopo imediato e registrar o restante como escopo futuro em `10-validation.md` / `06-roadmap.md`.
3. **Poucas Perguntas Cirúrgicas**: Faça no máximo **3 a 5 perguntas objetivas por vez**, sempre trazendo uma **opção recomendada** baseada na `constitution.md` para não burocratizar a experiência do usuário.

## Passos por Artefato (`00-project-brief.md` → `01-discovery.md` → `02-spec.md` → `03-requirements.md`):
1. Conduza **um artefato por vez** a partir do mais antigo incompleto:
   - **a.** Resuma em poucas linhas seu entendimento do contexto atual.
   - **b.** Conduza a entrevista enxuta de pontos cegos (segurança, LGPD, NFRs, RTO/RPO, casos de falha).
   - **c.** Gere o artefato em `docs/sdd/`.
2. Valide cada artefato com o usuário antes de avançar (`Status: Draft → Reviewed → Approved`).
3. Acione o check passivo do **`sdd-validator`** sobre o artefato concluído e atualize `docs/sdd/11-project-memory.md` (respeitando o teto de 150 linhas e paginação elástica `-02.md`).

## Regras de Sintaxe Canônica:
- **Intent Blocks** no `02-spec.md`: captura o PORQUÊ (`Goal / Expectation / Action / Result`).
- **GEARS** no `03-requirements.md`: formaliza O QUE deve acontecer (keywords `Where` / `While` / `When` / `shall` **sempre em inglês**):
  - `Where` = pré-condição estática (ambiente, flag, configuração).
  - `While` = pré-condição dinâmica de estado em runtime.
  - `When` = gatilho ou evento de entrada.
- Lacunas críticas não decididas → marque explicitamente `PENDENTE DE DEFINIÇÃO` e registre em `10-validation.md`.
- Termos vagos viram métricas observáveis ("rápido" → latência; "seguro" → mecanismo; "disponível" → SLA).

## Próximo Passo:
Ao aprovar `03-requirements.md`, oriente o usuário a avançar para `/sdd-design` (fases `04` a `06`).
