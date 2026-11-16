---
name: sdd-init
description: Inicia um novo projeto SDD Greenfield no Hermes Agent. Entrevista o usuário para a Constitution e gera a baseline de arquivos em docs/sdd/ e .hermes.md.
---

# SDD Init (Greenfield — v2.1)

Esta skill inicia o workflow **Spec-Driven Development (SDD Puro v2.1)** do zero em um novo projeto no Hermes Agent.

## Passos:
1. **Verificação Inicial**: Confirme que `docs/sdd/` ainda não existe (se já existir, pare e oriente usar `/sdd-adopt` ou continuar de onde parou).
2. **Entrevista Concisa da Constitution (Baixa Fricção)**:
   - Faça uma entrevista enxuta e direta com o usuário (máx. 3 a 5 perguntas agrupadas com recomendações padrão) para definir:
     - Padrões de arquitetura e stack tecnológica fixa;
     - Política de testes e comando oficial de verificação (para o `Say-Do Gate`);
     - Regras de segurança/LGPD e git flow;
     - Modelos disponíveis no Hermes do usuário para o roteamento de subagentes (`deep` para `sdd-architect`, `balanced` para `sdd-implementer` e `sdd-validator`, `fast` para `sdd-doc-writer`).
3. **Criação da Árvore Canônica Flat (`docs/sdd/`)**:
   Copie os templates do plugin (`templates/specs/*` → `docs/sdd/` e `templates/archive/*` → `docs/sdd/archive/`) na raiz do projeto:
   - `docs/sdd/constitution.md` — baseado na entrevista (`templates/constitution.md.template`) e nos princípios P1 a P11 (protegido contra auto-mutação silenciosa).
   - `docs/sdd/00-project-brief.md` a `docs/sdd/09-traceability.md` — esqueletos canônicos (a partir de `templates/specs/`).
   - `docs/sdd/07-tasks.md` — ledger de execução inicial (vazio).
   - `docs/sdd/10-validation.md` — backlog vivo de dívida ativa (a partir de `templates/specs/10-validation.md`, com suporte a paginação elástica `-02.md`).
   - `docs/sdd/11-project-memory.md` — estado inicial de memória (a partir de `templates/specs/11-project-memory.md`, com suporte a paginação elástica `-02.md`).
   - `docs/sdd/changes/` — pasta vazia para futuras mudanças pós-baseline.
   - `docs/sdd/archive/validation-log.md` — cold storage append-only de débitos resolvidos.
   - `docs/sdd/archive/memory-history.md` — cold storage append-only de mudanças finalizadas.
4. **Contexto Nativo do Hermes (`.hermes.md`)**:
   - Instancie o arquivo `.hermes.md` na raiz do projeto a partir de `templates/HERMES.md.template`, preenchendo nome, descrição curta e stack do projeto.
5. **Próximo Passo**:
   - Oriente o usuário a avançar para `/sdd-specify`.

> [!IMPORTANT]
> Nunca pule a entrevista da `constitution.md` — ela governa todas as fases. Nunca modifique arquivos sem confirmar o plano inicial com o usuário.
