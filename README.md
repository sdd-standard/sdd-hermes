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
  - **Camadas 1 e 2 (`sdd-validator` 100% Read-Only):** Auditoria separada em **Estágio 1 (Conformidade Estrita GEARS e Anti-Scope-Creep)** e **Estágio 2 (Qualidade, Constitution e Infra Global)**. Nenhuma camada do gate edita arquivos — apenas reporta divergências para o implementador corrigir. O subagente delegado com `goal` iniciado por `[sdd-validator]` é travado em somente leitura pelo próprio plugin (`subagent_start` + `pre_tool_call`), não só pelo prompt.
- **Entrevista Escopada, Baixa Fricção e Fatiamento de Escopo**: O entrevistador (`sdd-architect`) inspeciona **apenas** o código do domínio em pauta (jamais varre o repositório inteiro), realiza diagnóstico de `Validate-Gap`, faz poucas perguntas cirúrgicas com recomendação padrão e sugere fragmentar ou estreitar *changes* grandes demais.
- **Engenharia de Contexto com Paginação Elástica (P11)**: Injeção automática da memória, das tasks e das changes ativas no primeiro turno (`pre_llm_call`), gatilho de paginação de 150 linhas ou 7.000/16.000 caracteres por arquivo (sem cortar o conteúdo das dívidas) e suporte nativo a transbordo estruturado (`10-validation-02.md`, `11-project-memory-02.md`) que se auto-exclui quando as dívidas são sanadas.
- **Regras núcleo sempre na versão do plugin**: `rules/sdd-core-rules.md` é injetado no prompt de sistema de cada sessão nova (`register_system_prompt_section`); o `.hermes.md` do projeto guarda só o que é específico do projeto, sem duplicar as regras.
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

### Opção C — Uso / Teste Isolado via Docker (imagem oficial `nousresearch/hermes-agent`)
Roteiro validado com o Hermes Agent v0.23.1. Todo o estado do Hermes fica no volume `/opt/data`. Use um **volume nomeado**: uma pasta do Windows montada ali chega com permissão `0777` e o Hermes se recusa a usá-la (`unsafe_control_permissions`).

```powershell
# 1. Container de trabalho com o projeto montado em /workspace
docker volume create hermes-data
# HERMES_WRITE_SAFE_ROOT: a imagem só permite escrever em /opt/data; inclua /workspace (lista separada por ":")
docker run -d --name hermes -e HERMES_WRITE_SAFE_ROOT=/opt/data:/workspace -v hermes-data:/opt/data -v "${PWD}/meu-projeto:/workspace" nousresearch/hermes-agent:stable sleep infinity

# 2. Plugin direto do GitHub (mesmo comando da Opção A)
docker exec -u hermes hermes hermes plugins install sdd-standard/sdd-hermes --enable
docker exec -u hermes hermes hermes plugins validate /opt/data/plugins/sdd-workflow

# 3. Sessão interativa no projeto
docker exec -it -u hermes -w /workspace hermes hermes
```

Modelo local com Ollama no host: o Hermes exige **pelo menos 64.000 tokens de contexto** (configure no servidor Ollama, por exemplo `OLLAMA_CONTEXT_LENGTH=65536`) e alcança o host por `http://host.docker.internal:11434/v1`:

```powershell
docker exec -u hermes hermes hermes config set model.provider custom
docker exec -u hermes hermes hermes config set model.base_url http://host.docker.internal:11434/v1
docker exec -u hermes hermes hermes config set model.default <modelo-com-suporte-a-tools>
docker exec -u hermes hermes hermes config set model.context_length 65536
```

Para remover tudo depois do uso:
```powershell
docker rm -f hermes
docker volume rm hermes-data
docker rmi nousresearch/hermes-agent:stable
```

### Aprovações humanas e o modo `hermes -z`
O guard-install e a edição da `constitution.md` pedem **aprovação humana** (`{"action": "approve"}`). O Hermes decide como esse pedido é respondido conforme o modo de execução:

| Modo | O que acontece com um pedido de aprovação do plugin |
|---|---|
| Chat interativo (`hermes`, TUI) e gateways com canal de aprovação | O usuário é perguntado. |
| `hermes chat -q ... --oneshot` | Bloqueado (fail-closed), a menos que `approvals.single_query_mode: approve`. |
| `hermes -z ...` | **Aprovado automaticamente** — por desenho do Hermes, o `-z` roda sem ninguém para responder e libera todo pedido de aprovação. |

**Não use `hermes -z` para trabalho SDD que possa instalar dependências ou alterar a constitution.** Os bloqueios do plugin (`{"action": "block"}`: skills e regras canônicas, subagente `[sdd-validator]` somente leitura) continuam valendo em todos os modos.

---

## O que vem no Pacote

| Componente | Conteúdo | Papel no SDD Puro v2.1 |
|---|---|---|
| `plugin.yaml` & `__init__.py` | Manifesto + `register(ctx)` | Registra as 8 skills, 8 slash commands, 2 tools passivas, 2 seções de prompt de sistema e 6 hooks no core do Hermes Agent. |
| `skills/` (8) | `sdd-init`, `sdd-adopt`, `sdd-specify`, `sdd-design`, `sdd-tasks`, `sdd-implement`, `sdd-change`, `sdd-validate` | As fases completas do método (Greenfield, Brownfield e Delta Specs). |
| `agents/` (4) | `sdd-architect` (`deep`), `sdd-implementer` (`balanced`), `sdd-validator` (`balanced`, **100% read-only**), `sdd-doc-writer` (`fast`) | Perfis de subagente: o orquestrador passa o arquivo como `context` do `delegate_task`, com `goal` iniciado por `[<perfil>]`. A rota de modelo sugerida depende da configuração de delegação do Hermes do usuário. |
| `rules/` | `sdd-core-rules.md` | Fonte única das regras núcleo (P1–P11, GEARS, maturidade, gate, severidades, aceite de risco, paginação e delegação), injetada no prompt de sistema pelo plugin. |
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

## Orçamento de injeção de contexto (limitação do Hermes Agent)

O Hermes limita, **por padrão**, o contexto devolvido por um hook a **10.000 caracteres**; acima disso grava a saída em `$HERMES_HOME/hook_outputs/` e entrega ao modelo só o começo, o fim e o caminho do arquivo ([guia de plugins](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins)). As regras núcleo vão por outro canal (seções do prompt de sistema, até 4.000 caracteres cada e 8.000 no total). Essas são limitações da plataforma, não do SDD.

O hook de início de sessão nunca depende desse corte. Ele monta a injeção por prioridade, dentro de **10.000 caracteres**:

1. alertas de paginação, shards `-02.md`, tasks ativas (até 15, títulos com até 80 caracteres) e changes ativas (até 10) — juntos, no máximo cerca de 3.000 caracteres;
2. o `11-project-memory.md` **inteiro**, se couber no que sobrou;
3. se não couber: só as seções **Estado Atual**, **Próximos Passos Imediatos** e **Pendências em Aberto**, precedidas do aviso `MEMÓRIA INCOMPLETA NESTA INJEÇÃO`, que manda o agente ler o arquivo inteiro antes de agir e aplicar a higiene (rotação ou shard `-02.md`).

Por isso o gatilho de paginação da memória neste plugin é **150 linhas ou 7.000 caracteres** (10.000 menos a reserva de ~3.000). O `10-validation.md` não é injetado (o hook só cita os shards) e segue o gatilho canônico de 150 linhas ou 16.000 caracteres. A `constitution.md` não é injetada por hook: o agente a lê inteira com a ferramenta de leitura, sem limite.

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
