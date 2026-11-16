# sdd-workflow — Plugin de Spec-Driven Development para Hermes Agent (Nous Research)

> **A implementação oficial do padrão Spec-Driven Development (SDD Puro v2.1) para o ecossistema Hermes Agent.**

[![Standard: Pure SDD](https://img.shields.io/badge/Standard-Pure%20SDD%20v2.1-blue.svg)](https://github.com/sdd-standard/spec-driven-development)
[![Platform: Hermes Agent](https://img.shields.io/badge/Platform-Hermes%20Agent-00b894.svg)](https://hermes-agent.nousresearch.com/docs/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---

## Sobre o Projeto & Propósito

Este plugin operacionaliza no **Hermes Agent** ([NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)) o conjunto completo de princípios, sintaxes formais e gates do **Spec-Driven Development (SDD Puro v2.1)**.

Enquanto empresas e desenvolvedores utilizam o Hermes Agent em ambientes auto-hospedados (Docker, servidores Linux, Desktop OS Container) conectados a LLMs de ponta (Anthropic Claude, Google Gemini, OpenAI, OpenRouter), o **SDD Puro** fornece a governança de engenharia para que agentes autônomos construam software sem deriva de intenção, alucinação de escopo ou amnésia de contexto:

- **A Especificação é a Fonte da Verdade (P1/P2)**: Toda mudança começa na spec (`docs/sdd/`), governada pela `constitution.md` e formalizada em **Intent Blocks** e sintaxe **GEARS**.
- **Quality Gate 100% Passivo em 3 Camadas**:
  - **Camada 0 (Piso Mecânico Passivo):** Guarda determinística de IDs (`sdd_check_ids` em Python nativo) + **Say-Do Gate** (`sdd_say_do_audit`), que audita o ledger da sessão para comprovar que testes realmente rodaram com `exit code 0` após a última edição de código.
  - **Camadas 1 e 2 (`sdd-validator` 100% Read-Only):** Auditoria separada em **Estágio 1 (Conformidade Estrita GEARS e Anti-Scope-Creep)** e **Estágio 2 (Qualidade, Constitution e Infra Global)**. Nenhuma camada do gate edita arquivos — apenas reporta divergências para o implementador corrigir.
- **Entrevista Escopada, Baixa Fricção e Fatiamento de Escopo**: O entrevistador (`sdd-architect`) inspeciona **apenas** o código do domínio em pauta (jamais varre o repositório inteiro), realiza diagnóstico de `Validate-Gap`, faz poucas perguntas cirúrgicas com recomendação padrão e sugere fragmentar ou estreitar *changes* grandes demais.
- **Engenharia de Contexto com Paginação Elástica (P11)**: Injeção automática no início da sessão (`on_session_start`), teto de 150 linhas por arquivo com parágrafos curtos (máx. 4–5 linhas) e suporte nativo a transbordo estruturado (`10-validation-02.md`, `11-project-memory-02.md`) que se auto-exclui quando as dívidas são sanadas.
- **Blindagem contra Auto-Mutação do Learning Loop**: Impede via hook `pre_tool_call` que o ciclo de auto-aprendizado nativo do Hermes altere silenciosamente a `constitution.md` ou as skills canônicas do método.

> 📖 **Manifesto e Fundamentação Teórica:**  
> Para estudar os 11 Princípios Inegociáveis (P1–P11), a sintaxe GEARS, os Intent Blocks e a evolução via Delta Specs, visite o repositório central:  
> 👉 **[sdd-standard/spec-driven-development](https://github.com/sdd-standard/spec-driven-development)**

---

## Instalação no Hermes Agent

### Opção A — Instalação Direta via GitHub (Recomendado)
O gerenciador de plugins do Hermes instala diretamente a partir do repositório GitHub:

```bash
hermes plugins install sdd-standard/sdd-hermes --enable
```

### Opção B — Instalação Local (Desenvolvimento / Monorepo)
Se você clonou este repositório localmente:

```bash
hermes plugins install ./sdd-hermes --enable
# Ou copiando diretamente para a pasta de plugins do seu perfil Hermes:
mkdir -p ~/.hermes/plugins/sdd-workflow
cp -r ./sdd-hermes/* ~/.hermes/plugins/sdd-workflow/
```

---

### Opção C — Uso / Teste 100% Isolado via Docker (Zero Rastros no Windows/Host)
Se você está no Windows (ou qualquer host) e não deseja instalar o Hermes localmente, pode rodar o agente (ou o ambiente OS Desktop pré-configurado do Hermes) inteiramente via Docker:

#### 1. Container CLI / Gateway Enxuto (`nousresearch/hermes-agent`)
```powershell
# Teste descartável (--rm apaga o container ao sair) montando o plugin e o seu projeto:
docker run --rm -it `
  -v "${PWD}/sdd-hermes:/root/.hermes/plugins/sdd-workflow" `
  -v "${PWD}/meu-projeto:/workspace" `
  -w /workspace `
  nousresearch/hermes-agent:latest
```

#### 2. Container OS Desktop Pré-Configurado (`nousresearch/hermes-agent-desktop`)
Empacota um sistema operacional Linux/Ubuntu Desktop completo com Chrome embutido (acessível via navegador na porta `6080`) e API Gateway na porta `8642`:

```yaml
# docker-compose.yml
services:
  hermes-desktop:
    image: nousresearch/hermes-agent-desktop:latest
    container_name: hermes-sdd-desktop
    ports:
      - "6080:6080" # Interface visual Desktop (noVNC / Browser)
      - "8642:8642" # Hermes Gateway API
    volumes:
      - ./sdd-hermes:/opt/data/plugins/sdd-workflow
      - ./meu-projeto:/workspace
    environment:
      - VNC_PASSWORD=sddpassword
```

Para encerrar e remover qualquer vestígio da máquina host após o uso:
```powershell
docker compose down --rmi all --volumes
```

---

## O que vem no Pacote

| Componente | Conteúdo | Papel no SDD Puro v2.1 |
|---|---|---|
| `plugin.yaml` & `__init__.py` | Manifesto + `register(ctx)` | Registra as 8 skills, 8 slash commands, 2 tools passivas e 4 hooks no core do Hermes Agent. |
| `skills/` (8) | `sdd-init`, `sdd-adopt`, `sdd-specify`, `sdd-design`, `sdd-tasks`, `sdd-implement`, `sdd-change`, `sdd-validate` | As fases completas do método (Greenfield, Brownfield e Delta Specs). |
| `agents/` (4) | `sdd-architect` (`deep`), `sdd-implementer` (`balanced`), `sdd-validator` (`balanced`, **100% read-only**), `sdd-doc-writer` (`fast`) | Perfis de subagentes para `delegate_task` com roteamento de modelos e contextos isolados. |
| `rules/` | `sdd-core-rules.md` | Regras globais (P1–P11, GEARS, paginação elástica e proteção contra auto-mutação). |
| `scripts/` | `check_ids.py`, `check-ids.mjs`, `session_start.py`, `say_do_gate.py` | Guarda mecânica de IDs em Python nativo (sem depender de Node.js), injeção de sessão e auditoria passiva Say-Do. |
| `templates/` | `HERMES.md.template`, `constitution.md.template`, `specs/00..11` (incluindo `11-project-memory.md`), `changes/` e `archive/` | Esqueletos canônicos que `sdd-init` e `sdd-adopt` instanciam na estrutura flat `docs/sdd/`. |

---

## Como Usar (Slash Commands & Skills)

| Comando no Hermes | Fase / Função |
|---|---|
| `/sdd-init` | Inicia um novo projeto (Greenfield) com entrevista enxuta da Constitution, árvore `docs/sdd/` e `.hermes.md`. |
| `/sdd-adopt` | Adota o SDD em projetos existentes (Brownfield) via baseline *As-Built* mínima e *Spec-on-Touch*. |
| `/sdd-specify` | Conduz Brief, Discovery, Intent Blocks e Requisitos em sintaxe canônica **GEARS** com entrevista escopada. |
| `/sdd-design` | Executa diagnóstico `Validate-Gap` no domínio tocado, Domain Model (DDD), Design (`DES-xxx`) e Roadmap. |
| `/sdd-tasks` | Fatiamento em tarefas atômicas no ledger (`07-tasks.md`), critérios `AC-xxx` (`08`) e rastreabilidade (`09`). |
| `/sdd-implement` | Implementação guiada por tasks `In Progress` + **Quality Gate 100% Passivo em 3 Camadas** ao fechar milestone. |
| `/sdd-change` | Fluxo completo de Delta Specs (`proposal` ➔ `apply` ➔ `archive`) com fatiamento proativo de changes grandes. |
| `/sdd-validate` | Dispara manualmente o Quality Gate 100% Passivo em 3 Camadas (`sdd_check_ids` + `sdd_say_do_audit` + `sdd-validator`). |

---

## Arquitetura do Quality Gate 100% Passivo em 3 Camadas (v2.1)

No fechamento de cada milestone ou mudança (`/sdd-change`), o Gate opera em **1 único momento**, dividido internamente em **3 camadas estritamente passivas (`read-only`)** que apenas reportam divergências para o implementador corrigir:

1. **Camada 0 — Piso Mecânico Passivo (`sdd_check_ids` + `sdd_say_do_audit`)**:
   - `sdd_check_ids` (`python scripts/check_ids.py .`): Varre o repositório por exclusão e barra qualquer ID citado sem declaração em `docs/sdd/`.
   - `sdd_say_do_audit` (`scripts/say_do_gate.py`): Audita o ledger de ferramentas da sessão para comprovar mecanicamente que a suíte de testes/build foi executada com `exit_code == 0` após a última modificação de código.
2. **Camada 1 — Estágio 1 do `sdd-validator` (Conformidade Estrita GEARS)**:
   - Confronta cada cláusula `Where / While / When / shall` e cada `AC-xxx` contra `arquivo:linha` do código real e barra invenções fora da spec (*anti-scope-creep*).
3. **Camada 2 — Estágio 2 do `sdd-validator` (Qualidade, Constitution e Infra Global)**:
   - Audita aderência à `constitution.md`, segurança e interações com infraestrutura global (middlewares, rotas raiz, autenticação, banco de dados).

---

## Licença

Distribuído sob a licença [MIT](./LICENSE).
