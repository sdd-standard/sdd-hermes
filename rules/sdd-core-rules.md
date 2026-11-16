<!--
Regras núcleo do SDD Puro v2.1 para o Hermes Agent.
Fonte única: o plugin injeta este arquivo no prompt de sistema de cada sessão nova
(`ctx.register_system_prompt_section`, até 4.000 caracteres por seção e 8.000 no total), dividido
nos marcadores de seção abaixo. O `.hermes.md` do projeto NÃO repete estas regras: guarda só o
que é específico do projeto. `{PLUGIN_ROOT}` é substituído em tempo de execução.
Ao editar, rode o teste de tamanho do harness: cada seção deve ficar abaixo de 3.900 caracteres.
-->
<!-- section: sdd-core-principles -->
# SDD Puro v2.1 — regras núcleo (plugin sdd-workflow)
Raiz do plugin nesta máquina: `{PLUGIN_ROOT}`. Os caminhos `templates/`, `scripts/` e `agents/` citados pelas skills são relativos a ela. Não grave este caminho em arquivos do projeto.

## Princípios P1–P11
P1 a spec (`docs/sdd/`) é a fonte da verdade: toda mudança começa nela. P2 `constitution.md` governa todas as fases. P3 spec viva. P4 rastreabilidade `Intent → GEARS → DES → TASK → AC → Teste → Código`. P5 requisitos verificáveis (métrica, nunca "rápido"). P6 lacuna nunca vira suposição: marque `PENDENTE DE DEFINIÇÃO` (equivale a `PENDING DEFINITION`) e registre em `10-validation.md`. P7 design antes do código. P8 toda task deriva de um artefato. P9 validação em gates 100% passivos. P10 não é waterfall. P11 estado fora do chat.

## Sintaxes
Intent Block: `Goal / Expectation / Action / Result`.
GEARS, keywords sempre em inglês: `[Where <estático>] [While <estado>] [When <gatilho>] the <subject> shall <comportamento observável>.`

## Protocolo de sessão
Leia `constitution.md` → `11-project-memory.md` (injetado) → `10-validation.md` → tasks e changes ativas (injetadas). Confirme estado e próximo passo em até 5 linhas e prossiga com o pedido do usuário no mesmo turno (a confirmação não substitui a ação).

## Maturidade `Draft → Reviewed → Approved`
- Só o usuário muda o `Status` de um artefato; pode aprovar vários de uma vez. O agente nunca se autopromove.
- Nenhuma fase avança sobre artefato abaixo de `Reviewed`. Consumir artefato `Reviewed` ainda não `Approved` abre dívida de maturidade (`VAL`, `Medium`) com snapshot dos IDs e do texto consumidos. Na aprovação: snapshot igual → fecha; diferente → revalide os dependentes antes de fechar.
- Um item (`FR`, `NFR`, `DES`, `AC`, item de delta) só pode ser `Auto-Approved` se: não toca as seções 4 (Segurança) e 6 (Calibração de Criticidade) da constitution; deriva 1:1 de item aprovado pelo usuário ou aplica convenção escrita na constitution; traz `Motivo:`. Liste os `Auto-Approved` ao pedir a aprovação do artefato.

## Fluxo
`/sdd-init` · `/sdd-adopt` bootstrap · `/sdd-specify` 00→03 · `/sdd-design` Validate-Gap → 04→06 · `/sdd-tasks` 07→09 · `/sdd-implement` task + gate · `/sdd-validate` gate manual · `/sdd-change` proposal → apply → archive.
<!-- section: sdd-core-governance -->
## Execução e governança
1. Zero código sem task `In Progress` em `07-tasks.md` ou `changes/<nome>/tasks.md`.
2. Após a baseline, `00–06`, `08` e `09` só mudam por change (`proposal → delta-spec → tasks → apply → gate → archive`). Não existe hotfix. `07`, `10` e `11` são voláteis.
3. Entrevista escopada: leia só o domínio em pauta; no máximo 3–5 perguntas, cada uma com recomendação; proponha fatiar change grande demais.
4. Dependência nova só com confirmação do usuário.
5. O learning loop nunca altera `constitution.md`, estas regras nem as skills `sdd-*`; aprendizados vão para `11-project-memory.md`.

## Quality Gate passivo em 3 camadas
Camada 0: `sdd_check_ids` + `sdd_say_do_audit`; só `VERIFIED_PASS` libera (`NO_EVIDENCE` não é aprovação). Com a Camada 0 falhando, não acione o validador. Camadas 1 (GEARS/AC, anti-scope-creep) e 2 (constitution, segurança, infra global): subagente `sdd-validator`. Nenhuma camada edita arquivos.

## Severidades (calibradas pela seção 6 da constitution)
- `Critical` bloqueia: viola a constitution, falha de segurança/dados, Camada 0 falhando, regressão, `shall` principal ausente.
- `High` bloqueia: condição `Where/While/When` omitida, falha na infra global, `FR` sem teste do seu `AC`, scope creep.
- `Medium`/`Low` não bloqueiam e vão para `10-validation.md`: desvio parcial de `DES`, borda secundária sem teste, QA manual; cosmético.

## Aceite de risco pelo usuário
Só o usuário aceita `Critical`/`High` aberto. A severidade não muda; o registro traz quem, data, justificativa e gatilho de revisão. Falha da Camada 0 não é aceitável. Aceitar violação da constitution exige registrar a exceção na seção 8 dela. Dívida aceita não bloqueia o `/sdd-implement`.

## Dívidas e paginação elástica
Cada `VAL` traz o quê, evidência `arquivo:linha`, impacto, recomendação, critério de fechamento e histórico datado. Nunca resuma para caber: fragmente em `VAL` filhas (`Parent:`). Shard `-02.md` ao passar de 150 linhas OU 7.000 caracteres (`11-project-memory.md`) / 16.000 (`10-validation.md`); exclua o shard quando esvaziar.

## Delegação (`delegate_task`)
Para usar um perfil (`sdd-architect`, `sdd-implementer`, `sdd-validator`, `sdd-doc-writer`): `goal` começa com `[<perfil>]` e `context` traz o conteúdo de `{PLUGIN_ROOT}/agents/<perfil>.md` mais o escopo. O plugin trava em somente leitura o subagente `[sdd-validator]`.
