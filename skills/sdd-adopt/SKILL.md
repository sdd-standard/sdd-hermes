---
name: sdd-adopt
description: Adota o SDD em um projeto existente (Brownfield) no Hermes Agent. Extrai a Constitution real, gera uma baseline As-Built mínima e prepara o fluxo Spec-on-Touch.
---

# SDD Adopt (Brownfield — v2.1)

Esta skill cria a fundação SDD em projetos existentes que ainda não possuíam especificação viva.

> **Princípio de Ouro Brownfield:** **NÃO faça retro-spec nem leia o código legado inteiro.** Crie apenas a baseline estrutural mínima (*As-Built*) + **Spec-on-Touch** (a especificação cresce organicamente apenas nas áreas tocadas por novas mudanças via `/sdd-change`).

## Fase 1 — Levantamento Estrutural Leve (Sem Varredura Massiva)
1. Inspecione apenas os arquivos de manifesto e configuração da raiz (`package.json`, `pyproject.toml`, `.sln`, `docker-compose.yml`, estrutura de diretórios de 1º/2º nível e pipelines de CI).
2. Identifique os macro-módulos/*bounded contexts* aparentes e integrações externas principais.
3. Liste em até 3 a 5 perguntas diretas (com recomendação padrão) apenas o que não é possível inferir dos manifestos (SLAs, regras de negócio críticas implícitas, modelos para roteamento no Hermes).

## Fase 2 — Constitution Extraída + Desejada
4. Gere `docs/sdd/constitution.md` dividida em duas partes:
   - **(a) Convenções OBSERVADAS** no projeto (stack, testes, estrutura) — confirme com o usuário;
   - **(b) Regras DESEJADAS** daqui em diante (qualidade, segurança, política de dependências, comando oficial de testes para o `Say-Do Gate`);
   - **(c) Calibração de criticidade do domínio** (seção 6): pergunte o que, neste negócio, eleva um achado automaticamente para `Critical` ou `High` (ex.: precisão financeira, PII/LGPD, auditoria regulatória) e o que é tolerado como `Medium`/`Low` nesta fase.

## Fase 3 — Baseline Mínima "As-Built" (Estrutura Flat em `docs/sdd/`)
5. Crie a estrutura enxuta em `docs/sdd/` utilizando os modelos de `templates/specs/` e `templates/archive/` (pastas da **raiz do plugin**, informada no cabeçalho deste comando; instalação padrão: `~/.hermes/plugins/sdd-workflow/`):
   - `constitution.md` — governança extraída + desejada (`templates/constitution.md.template`).
   - `00-project-brief.md` — o que o sistema é hoje e por que existe (`templates/specs/00-project-brief.md`).
   - `02-spec.md` — capacidades atuais em alto nível (seção `"As-Built"`, sem GEARS retroativo do sistema inteiro).
   - `04-domain-model.md` — mapa dos *bounded contexts* e linguagem ubíqua observada.
   - `05-design.md` — arquitetura macro atual + decisões conhecidas (marque decisões antigas como `"legado"`).
   - `07-tasks.md` — ledger vazio (`templates/specs/07-tasks.md`).
   - `10-validation.md` — dívidas e lacunas já conhecidas (`templates/specs/10-validation.md`, com suporte a paginação elástica `10-validation-02.md` ao atingir o gatilho de paginação).
   - `11-project-memory.md` — estado inicial (`templates/specs/11-project-memory.md`, com suporte a paginação elástica `11-project-memory-02.md`).
   - `changes/` — pasta vazia para futuras mudanças.
   - `archive/validation-log.md` e `archive/memory-history.md` — templates vazios de cold storage (`templates/archive/*`).
   - *Nota:* **NÃO** crie `01`, `03`, `06`, `08`, `09` retroativos para o sistema inteiro — eles nascerão sob demanda por mudança.
6. Gere ou atualize `.hermes.md` na raiz do projeto (via `templates/HERMES.md.template`), preservando quaisquer instruções pré-existentes do usuário.

## Fase 4 — Operação Contínua
7. A partir daqui, toda nova feature ou alteração entra via `/sdd-change` (Delta Specs com inspeção escopada apenas ao domínio tocado).
8. Se uma nova feature for grande demais para um único delta, oriente usar `/sdd-specify` escopado exclusivamente àquela feature (ou fatiar em múltiplas changes sequenciais).
