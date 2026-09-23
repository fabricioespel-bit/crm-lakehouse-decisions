# Plano de Arquitetura — CRM Lakehouse Decisions (Snowflake + dbt)

`crm-lakehouse-decisions` — projeto de portfólio para fechar o gap técnico de dbt com prática real
(não só o argumento de equivalência via Dataform), ganhar experiência hands-on em Snowflake, e aplicar
CI/CD de verdade a um pipeline de engenharia de dados — algo que Fabricio identificou não ter sido feito
com rigor em projetos anteriores.

Fabricio Espel · v1 (18/set/2026), escopo de integração marketing+CRM incorporado em 19/set/2026

## 0. Modo de trabalho

Mesma regra já estabelecida no projeto irmão `account-health-ml-service` (registrada lá em 08/set/2026),
aplicada aqui pelo mesmo motivo: o objetivo é fechar um gap técnico real através de prática, então **o
Claude não deve executar comandos nem escrever scripts por conta própria**. O papel do Claude é orientar
— explicar o quê e o porquê, sugerir o comando ou o trecho de código — e Fabricio é quem executa e roda,
com a orientação do Claude. Vale para todas as fases (setup Salesforce/Snowflake/Airbyte, modelos dbt,
pipeline de CI/CD), não só para operações destrutivas. Atualizar este plano (`PLANO.md`) em si é exceção —
é documentação viva do projeto, não execução técnica, e o Claude mantém esse arquivo atualizado.

**Se isso não for o que você quer para este projeto, ajuste esta seção antes de seguir** — é um valor
herdado do projeto anterior, não uma decisão nova tomada especificamente aqui.

## 1. Contexto e objetivo

Em 18/set/2026, surgiu uma possível oportunidade de emprego numa empresa que usa Snowflake como data
lake, integrando dados de várias fontes, incluindo Salesforce. Isso motivou este projeto, que persegue dois
objetivos que se reforçam:

1. **Fechar de vez o gap de dbt** — pendente desde 05/ago/2026 (ver `novas-oportunidades/CLAUDE.md`,
   seção "Gaps técnicos"). Até aqui, o argumento em entrevista era "Dataform é funcionalmente equivalente
   ao dbt" — verdadeiro, mas não é a mesma coisa que ter rodado dbt de verdade. Este projeto substitui o
   argumento por prática real.
2. **Ganhar experiência real em Snowflake e aplicar CI/CD com rigor** a um pipeline de dados — prática que,
   segundo o próprio Fabricio, não foi aplicada de verdade em projetos anteriores de engenharia de dados
   (diferente do `account-health-ml-service`, que já tem CI/CD real, mas do lado de ML/serviço, não de
   transformação analítica).

Diferente do `data-lake-engineering-decisions` (BigQuery + Dataform, domínio genérico de SaaS), este
projeto usa **Snowflake + dbt Core**, com **Salesforce real** como fonte — mesma disciplina de arquitetura
em camadas e decisões documentadas, ferramentas e domínio diferentes, para ampliar a superfície de prova
técnica em vez de repetir o mesmo projeto com nome trocado.

**Escopo ampliado em 19/set/2026:** um funil de CRM sozinho é um problema relativamente limpo e não
captura duas dores reais e comuns em empresas que geram leads via marketing — (1) a qualidade de dado
dentro do CRM costuma ser ruim (preenchimento manual inconsistente, duplicidade, campos mal usados), e (2)
conectar a jornada online (qual campanha gerou o lead) ao que acontece dentro do CRM (conversão em
Opportunity, Closed Won) pra calcular ROAS é um problema de integração de dados real e mal resolvido na
maioria das empresas. O projeto passou a simular esses dois problemas de propósito e a implementar a
solução de qualidade/integração no lakehouse — ver detalhes nas seções 2 e 3. Isso também diferencia mais
este projeto do `data-lake-engineering-decisions` do que um funil limpo diferenciaria.

**Sem cronograma formal** — decisão explícita de Fabricio (18/set), diferente do projeto anterior. O trial
gratuito do Snowflake (30 dias corridos, ~US$400 de crédito) impõe um teto de tempo natural mesmo sem
prazo escrito; vale ter isso em mente ao decidir o ritmo de trabalho.

## 2. Escopo e domínio

**Problema de negócio (ilustrativo):** duas perguntas conectadas, que juntas cobrem uma dor comum em
empresas que geram leads via marketing e fecham venda via CRM:

1. **Saúde do funil de vendas** — win rate por estágio, duração do ciclo de venda, saúde do pipeline por
   período — a partir de Accounts, Contacts, Opportunities e Leads do Salesforce.
2. **ROAS e atribuição de marketing** — qual campanha gerou qual lead, e como essa jornada online se
   conecta ao que acontece dentro do CRM (conversão em Opportunity, Closed Won). Problema clássico de
   integração marketing↔CRM, que a maioria das empresas resolve mal ou pela metade.

**Fonte de dados #1 (CRM) — decisão fechada (18/set/2026):** **Salesforce Developer Edition real** (org
gratuita e permanente, criada em developer.salesforce.com), não um dataset público nem dado 100%
sintético. Fabricio escolheu isso deliberadamente por realismo de extração via API, mesmo custando mais
tempo de setup do que as alternativas consideradas (dataset público tipo CRM do Kaggle, ou dados
sintéticos gerados localmente). Os dados de exemplo que o Salesforce carrega por padrão numa org nova são
poucos — o volume é complementado via script/API (Salesforce REST/Bulk API), **documentado explicitamente
como dado gerado, não coletado**, seguindo o mesmo princípio de transparência já usado na camada sintética
de tickets de suporte do `account-health-ml-service`.

**Sujeira proposital no CRM — decisão fechada (19/set/2026):** o script de geração injeta, com taxas de
"corrupção" configuráveis (não aleatório sem controle), os problemas de qualidade de dado típicos de CRM
mal implementado/mal preenchido: Accounts duplicadas, valores de picklist inconsistentes (ex.: `"Tech"` vs
`"Technology"` vs `"tech "`), Opportunities sem Contact Role, `LeadSource` nulo ou genérico demais
(`"Other"`), datas ilógicas (CloseDate anterior a CreatedDate). Isso é o que justifica a camada `staging`
existir de verdade — não só tipagem, mas limpeza de qualidade de dado documentada e testada.

**Fonte de dados #2 (marketing) — decisão fechada (19/set/2026):** segunda fonte sintética, fora do
Salesforce, simulando eventos de campanha (impressões/cliques, com UTM e um `click_id`). Esse identificador
só se propaga pro Lead do Salesforce de forma **probabilística** (ex.: 60–70% dos casos) — simulando
tracking quebrado, ad blocker, ou lead entrando por um canal diferente do que gerou o clique original. Essa
perda parcial é proposital: é o que cria o problema de identity resolution/atribuição que a Fase 2b
resolve (parcialmente, como no mundo real — ver seção 4).

**Fora de escopo, de propósito:** nenhum componente de IA/agente/RAG neste projeto — esses gaps já
estão fechados em outros repositórios do portfólio (`amigurumi-agent`, `rag-quality-assurance`,
`multi-agent-analytics`). O foco aqui é 100% engenharia de dados: ingestão de duas fontes, resolução de
identidade, transformação, testes, CI/CD.

## 3. Arquitetura

```
Salesforce Developer Edition              Eventos de marketing (sintético)
(Accounts, Contacts,                      (impressões/cliques por campanha,
 Opportunities, Leads)                     UTM + click_id)
   │  Airbyte (conector Salesforce)          │  script Python direto pro raw
   ▼                                         ▼
Snowflake — schema RAW
   (uma tabela por objeto/fonte; incremental via SystemModstamp no CRM,
    via timestamp de evento no lado de marketing)
   │
   │  dbt Core — staging: tipagem, dedup, padronização de picklists,
   │             limpeza da sujeira proposital (seção 2)
   ▼
Snowflake — schema STAGING
   │
   │  dbt Core — stitching: join de touchpoints de marketing a Lead/Opportunity
   │             via UTM/click_id, com fallback e taxa de match documentada
   │             como métrica de qualidade (não força 100% de atribuição)
   ▼
Snowflake — schema INTERMEDIATE  (jornada unificada: touchpoint → Lead → Opportunity)
   │
   │  dbt Core — marts: funil de oportunidades, win rate, ciclo de venda,
   │             ROAS por campanha com modelo de atribuição explícito (ex. first-touch)
   ▼
Snowflake — schema MARTS
   │
   ▼
dbt docs (catálogo de dados, publicado como site estático — GitHub Pages)
```

CI/CD: GitHub Actions dispara `dbt build` + `dbt test` a cada push/PR que toque nos modelos dbt.

## 4. Decisões já fechadas (18/set/2026)

- **Ingestão via Airbyte**, não Fivetran — reaproveita a ferramenta já usada no
  `data-lake-engineering-decisions`, mantém o portfólio consistente em vez de introduzir mais uma
  ferramenta paga.
  - **Risco confirmado em 22/set/2026:** Docker Desktop não roda nessa máquina (mesmo problema já visto
    no `amigurumi-agent`, que migrou pra Qdrant Cloud por causa disso) — Airbyte self-hosted descartado.
    **Decisão fechada: Airbyte Cloud** (free tier).
- **Transformação via dbt Core** (não dbt Cloud) — CLI, versionado no Git, sem depender de um serviço
  gerenciado pago além do necessário; reforça a demonstração de CI/CD próprio em vez de usar o CI
  embutido do dbt Cloud.
- **Autenticação do CI/CD no Snowflake via key-pair** (par de chaves RSA), não OIDC federado — o Snowflake
  não tem o mesmo modelo de federação de identidade usado no Azure (`account-health-ml-service`). Isso é
  uma diferença de plataforma a documentar conscientemente no README final, não uma lacuna de
  execução.
- **Nome do repositório:** `crm-lakehouse-decisions`, mantendo o padrão de nomenclatura do
  `data-lake-engineering-decisions` (sufixo "-decisions" = documentar decisões de engenharia, não só
  código).
- **Geração de dados sintéticos via script Python** (`simple-salesforce` + `Faker`), não via Data Import
  Wizard (CSV/UI) nem criação manual pela interface — decisão tomada em 18/set/2026 entre essas três opções
  por ser a que mais reforça prática de API/autenticação (alinhado ao objetivo do projeto) e por gerar um
  artefato versionável (o script fica no repo, documentando como o dado foi produzido).
- **Autenticação do script de geração via username/senha + security token** (fluxo simples do
  `simple-salesforce`), não Connected App — a Connected App (OAuth) fica reservada para a Fase 1, quando o
  Airbyte precisar de fato de um fluxo OAuth para extrair os dados.
- **Duas fontes sintéticas, com sujeira e desalinhamento propositais** (19/set/2026) — Salesforce com
  problemas de qualidade de dado configuráveis (seção 2) e uma segunda fonte de eventos de marketing
  (UTM/click_id) que só se propaga pro Salesforce probabilisticamente. Decisão tomada porque o objetivo do
  projeto deixou de ser "modelar um funil limpo" e passou a ser "integrar e resolver (parcialmente) duas
  fontes desalinhadas" — cenário mais realista e mais raro no portfólio do que um pipeline com dado limpo.
- **Modelo de atribuição explícito e documentado, não "resolver 100%"** (19/set/2026) — a camada de
  stitching deixa claro o percentual de Opportunities sem atribuição completa à campanha de origem, em vez
  de forçar um match artificial de 100%. O valor de portfólio está em mostrar como lidar honestamente com
  a limitação (igual aconteceria numa empresa real), não em fingir que o problema foi resolvido por
  completo.

- **Ingestão da fonte de marketing via script Python direto pro schema `raw`** (19/set/2026) — não via
  Airbyte. Diferente do Salesforce (fonte real, faz sentido testar um conector de verdade), a fonte de
  marketing é sintética desde a origem, então não há API real pra um conector do Airbyte simular — o
  script que gera os eventos já escreve direto no `raw` (ex.: via Snowflake Connector for Python ou
  `COPY INTO` a partir de um arquivo gerado). Fecha a decisão em aberto da v1.1 deste plano.

## 5. Fases

- **Fase 0 — Setup:**
  - [x] Criar org Salesforce Developer Edition (18/set/2026) — confirmado vazia (0 registros em
    Accounts/Contacts/Opportunities/Leads), decisão de geração de dados via script tomada (ver seção 4).
  - [x] Gerar/complementar dados de exemplo no CRM, com sujeira proposital (21/set/2026, checklist
    detalhado na seção 7).
  - [x] Desenhar e gerar a fonte sintética de eventos de marketing (21/set/2026, checklist detalhado
    na seção 7).
  - [x] Criar conta trial do Snowflake (21/set/2026) — conta criada via "Sign up with Google"
    (AWS, região/edição escolhidas no fluxo "Snowflake CoCo"). **Obstáculos reais resolvidos (22/set):**
    (1) login social via Google não é integração SAML de verdade — `--authenticator externalbrowser`
    falha com erro de SAML; (2) autenticação de CLI/scripts exige **key-pair (RSA)**, já que não existe
    senha tradicional numa conta criada via Google — gerada localmente (`~/.snowflake_keys/`, fora do
    repo) e registrada via `ALTER USER ... SET RSA_PUBLIC_KEY=...` no Snowsight; (3) `snow connection
    add` inicialmente deu "JWT token is invalid" porque o `--user` deve usar o **`LOGIN_NAME`** do
    usuário (`FABRICIOESPEL@GMAIL.COM`, via `DESCRIBE USER`), não o `NAME` (`fabricioespel`). Conexão
    `devsnowflake` funcionando com `snow connection test`. Instalado também o **Salesforce CLI** (`sf`,
    `npm install --global @salesforce/cli`) nessa sessão, usado pra validar os dados gerados via SOQL
    em vez de só a UI. Warehouse `CRM_LAKEHOUSE_WH` (X-Small, `AUTO_SUSPEND=60`), database
    `CRM_LAKEHOUSE` e os 4 schemas da arquitetura (`RAW`, `STAGING`, `INTERMEDIATE`, `MARTS`) criados
    e configurados como default da conexão `devsnowflake`.
  - [x] Decidir Airbyte self-hosted vs. Cloud na prática (22/set/2026) — **Airbyte Cloud** (free tier),
    confirmando o risco já identificado na seção 4: Docker Desktop não roda nessa máquina, mesmo
    problema já visto no `amigurumi-agent`. Fase 0 completa.
- **Fase 1 — Ingestão** (iniciada 22/set/2026, conta Airbyte Cloud já criada — trial de 30 dias conta a
  partir da primeira sincronização): conectar Airbyte (Salesforce → Snowflake) e o script Python de
  eventos de marketing (carga direta pro `raw`, ver seção 4); decidir e documentar estratégia de
  sincronização incremental (`SystemModstamp` no CRM, timestamp de evento no marketing).
  - [x] ~~Criar Connected App no Salesforce~~ — não necessário no Airbyte **Cloud** (diferente do
    Open Source): o source Salesforce autentica via botão "Authenticate your account" (OAuth
    automático, redireciona pro login do Salesforce), sem setup manual prévio (confirmado 22/set/2026
    via docs.airbyte.com/integrations/sources/salesforce).
  - [x] Criar usuário/role dedicado no Snowflake pro Airbyte (22/set/2026) — `AIRBYTE_ROLE` +
    `AIRBYTE_USER` (tipo `service`, key-pair própria em `~/.snowflake_keys/airbyte_rsa_key.p8`,
    fora do repo), reaproveitando `CRM_LAKEHOUSE_WH`/`CRM_LAKEHOUSE` em vez de criar
    warehouse/database dedicados (diferente do script padrão da doc do Airbyte). `OWNERSHIP`
    concedida só no schema `RAW`, não no database inteiro — `STAGING`/`INTERMEDIATE`/`MARTS`
    ficam reservados pro role do dbt (Fase 2).
  - [x] Configurar Source Salesforce no Airbyte Cloud (22/set/2026) — OAuth via "Authenticate your
    account", sem Connected App manual (confirmado antes).
  - [x] Configurar Destination Snowflake no Airbyte Cloud (22/set/2026) — usuário `AIRBYTE_USER`,
    key-pair, schema padrão `RAW`. **Obstáculo resolvido:** primeira tentativa de sync falhou com
    "AIRBYTE_ROLE must have CREATE SCHEMA granted on DATABASE" — a `OWNERSHIP` no schema `RAW` não é
    suficiente, o Airbyte também precisa criar schemas auxiliares próprios; resolvido com
    `grant CREATE SCHEMA on database CRM_LAKEHOUSE to role AIRBYTE_ROLE`.
  - [x] Criar Connection (22/set/2026) — streams Account, Contact, Lead, Opportunity,
    OpportunityContactRole (removidos os defaults fora de escopo: OpportunityStage, Task, User);
    sync incremental via `SystemModstamp`/`Id` (detectado automaticamente pelo Airbyte, sem ajuste
    manual); sync mode "Manual" (não agendado, por causa do teto de tempo dos trials); namespace
    "Destination default" (tudo em `RAW`). **Primeiro sync rodado com sucesso.**
  - **Achado importante (22/set/2026):** o Airbyte sincroniza também registros **deletados** do
    Salesforce (`ISDELETED = TRUE`, via `queryAll`/Lixeira) — por isso as contagens em `RAW` vieram
    maiores que o esperado à primeira vista (ex. 90 Accounts em vez de 71). Conferido e explicado:
    a diferença bate exatamente com os registros de teste/demo que foram deletados ao longo da sessão
    (smoke tests do CRM + dataset padrão do Salesforce). **Implicação pra Fase 2a:** a camada
    `staging` precisa filtrar `WHERE ISDELETED = FALSE` explicitamente — isso também é, coincidentemente,
    uma boa lição real de engenharia de dados (histórico completo no `raw`, estado "vivo" só na
    `staging`), não um problema a esconder.
  - [x] Rodar `COPY INTO` dos CSVs de marketing pro `raw` (22/set/2026) — 3 tabelas criadas em
    `CRM_LAKEHOUSE.RAW` (`MARKETING_CAMPAIGNS`, `MARKETING_CLICK_EVENTS`, `MARKETING_CAMPAIGN_STATS`),
    carga via stage interno (`snow stage copy` + `COPY INTO`), 8 campanhas + 1740 cliques + 8 linhas de
    stats, sem erro. **Fase 1 completa.**
- **Fase 2 — Transformação (dbt)** (iniciada 23/set/2026):
  - [x] Instalar `dbt-core` + `dbt-snowflake` no venv (23/set/2026) — `dbt-core==1.12.5`,
    `dbt-snowflake==1.12.1`. **Obstáculo resolvido:** erro de certificado SSL ao instalar
    (`dbt-core-experimental-parser` baixa um binário direto do GitHub, fora do índice do PyPI) —
    resolvido rodando o `pip install` com `SSL_CERT_FILE=$(python3 -m certifi)`. Aviso não-bloqueante:
    conflito de versão de `click`/`protobuf` com o `snowflake-cli` (ambos os CLIs continuam funcionais).
  - [x] Criar usuário/role dedicado no Snowflake pro dbt (23/set/2026) — `DBT_ROLE`/`DBT_USER`
    (key-pair própria em `~/.snowflake_keys/dbt_rsa_key.p8`), leitura (`USAGE`+`SELECT`, incluindo
    `FUTURE TABLES`) no schema `RAW`, `OWNERSHIP` em `STAGING`/`INTERMEDIATE`/`MARTS`.
  - [x] Inicializar projeto dbt manualmente em `dbt/` (23/set/2026, sem `dbt init` interativo — prompts
    multi-etapa não funcionam nesse terminal) — `dbt_project.yml`, estrutura de pastas
    (`models/{staging,intermediate,marts}`, `seeds`, `tests`, `macros`), `~/.dbt/profiles.yml` (fora do
    repo, key-pair do `DBT_USER`). **Decisão de design:** macro `generate_schema_name` sobrescrita
    (`dbt/macros/generate_schema_name.sql`) pra usar o `+schema` de cada pasta diretamente, sem
    concatenar com o schema do profile (comportamento padrão do dbt, pensado pra múltiplos devs
    compartilhando conta — não se aplica aqui, projeto de uma pessoa só com schemas já fixados).
  - [x] `dbt debug` — todos os checks passando, incluindo teste de conexão real via key-pair.
  - **2a — staging:** tipagem, dedup, padronização de picklists, limpeza da sujeira proposital do CRM
    (inclui filtro `WHERE ISDELETED = FALSE`, achado da Fase 1 — ver seção 7).
    - [x] `stg_accounts` — versão básica (tipagem + filtro `WHERE ISDELETED = FALSE`, sem dedup/limpeza
      de picklist ainda), com `source()` declarado em `_staging__sources.yml`. Rodado com
      `dbt run --select stg_accounts`, 71 linhas em `STAGING.STG_ACCOUNTS` (bate com o total de
      Accounts ativas). **Pendente:** testes (`_staging__models.yml` com `unique`/`not_null` em
      `account_id`, `not_null` em `account_name`) já propostos, ainda não confirmados rodando
      (`dbt test --select stg_accounts`) — próximo passo ao retomar.
    - [ ] Adicionar padronização de picklist (`Industry`) e dedup das Accounts duplicadas propositais
      em `stg_accounts`.
    - [ ] `stg_contacts`, `stg_leads`, `stg_opportunities`, `stg_opportunity_contact_roles`.
  - **2b — stitching (novo):** join de touchpoints de marketing a Lead/Opportunity via UTM/click_id, com
    fallback e taxa de match exposta como métrica de qualidade (schema `intermediate`).
  - **2c — marts:** funil de oportunidades (win rate, ciclo de venda) e ROAS por campanha com modelo de
    atribuição explícito.
  - Testes dbt em todas as camadas (not-null, unique, relationships, customizados — incluindo teste que
    monitora a taxa de atribuição do stitching); pelo menos um model `materialized='incremental'`.
- **Fase 3 — CI/CD:** pipeline GitHub Actions (`dbt build`/`dbt test` em PR); autenticação via key-pair;
  `dbt docs generate` publicado via GitHub Pages.
- **Fase 4 (stretch, opcional):** avaliar se vale expor alguma forma de consumo (ex.: descrições de
  tabela/coluna pensadas pra consumo por agente de IA, no mesmo espírito do `data-lake-engineering-decisions`)
  — só entra se sobrar tempo dentro da janela do trial, não é objetivo central do projeto.

## 6. Como retomar numa sessão nova

Este arquivo é o plano vivo do projeto — atualizar conforme cada fase avança, incluindo obstáculos reais
encontrados e como foram resolvidos (mesmo padrão dos outros repositórios do portfólio: a documentação
honesta do processo é parte do valor do projeto, não só o resultado final). Ao abrir uma sessão nova neste
diretório, começar confirmando: (1) se a seção 0 (modo de trabalho) ainda reflete o que Fabricio quer; (2)
em que fase o projeto está; (3) se algum dos riscos já identificados (Airbyte/Docker) já se confirmou. Para
o estado detalhado e a fila de próximos passos, ver a seção 7.

## 7. Log de progresso e próximos passos imediatos

**18/set/2026:** Org Salesforce Developer Edition criada e confirmada vazia (0 registros em
Accounts/Contacts/Opportunities/Leads). Decidido gerar o volume de dados via script Python
(`simple-salesforce` + `Faker`), autenticando por username/senha + security token, sem Connected App por
enquanto (ver decisões na seção 4).

**19/set/2026:** Escopo ampliado para incorporar integração marketing+CRM — sujeira proposital nos dados
do Salesforce e uma segunda fonte sintética de eventos de marketing (UTM/click_id com propagação
probabilística), com camada de stitching/atribuição explícita no dbt (ver seções 2, 3 e 4). Decidido que a
fonte de marketing entra no `raw` via script Python direto (não Airbyte) — ver seção 4.

**21/set/2026:** Security token do Salesforce obtido e `git init` feito (repositório local, ainda sem
remoto/push para o GitHub) — detalhes no checklist abaixo. Próximo passo: ambiente virtual Python +
`simple-salesforce` + `Faker`.

**21/set/2026 — obstáculos reais encontrados ao escrever `scripts/generate_sample_data.py`:**
- **SOAP API login() desabilitado por padrão** nessa org (mudança recente de segurança da Salesforce,
  retirada gradual do SOAP login até Summer '27) — o `simple-salesforce` usa SOAP por padrão pra
  autenticar. Resolvido em duas partes: (1) Setup → "User Interface" → ativar o toggle
  "Enable SOAP API login()"; (2) criar um **Permission Set** (não dá pra editar direto no Profile
  "Administrador do sistema", por ser perfil padrão) com a permissão "Use Any API Auth" ("Usar qualquer
  autorização de API") e atribuir ao usuário usado pelo script.
- **`CreatedDate` não gravável via API por padrão** — necessário pra distribuir as datas de criação das
  Opportunities ao longo de 18 meses (em vez de tudo "criado hoje"). Resolvido ativando o toggle "Enable
  'Set Audit Fields upon Record Creation'..." em Setup → "User Interface", e então habilitando a
  permissão "Set Audit Fields upon Record Creation" — nesse caso não funcionou via Permission Set no
  perfil padrão, foi preciso **clonar/editar um Profile customizado** com essa permissão marcada.
- **Bug próprio no script (não da Salesforce):** unidades de tempo do Faker em `date_between` — `M`
  maiúsculo = meses, `m` minúsculo = minutos. Usar `"-18m"` gerava datas praticamente iguais a "hoje"
  (janela de minutos, não meses). Corrigido para `"-18M"`/`"-1M"`.
- **Correção de registro:** a confirmação de "org vazia" feita em 18/set/2026 estava incompleta — na
  prática a org tinha o dataset de demonstração padrão do Salesforce Developer Edition (13 Accounts tipo
  "Edge Communications"/"GenePoint"/"United Oil & Gas", 26 Opportunities, 26 Cases, 20 Contacts, 22
  Leads, 1 Entitlement), só descoberto ao consultar via SOQL em 21/set. Limpo por completo antes da
  geração real (ordem que funcionou: Case → Opportunity → Account teve cascade nos Contacts restantes;
  Lead à parte; a "Sample Account for Entitlements" só liberou depois de apagar o Entitlement vinculado).
  Confirmado com `SELECT Id FROM <objeto>` retornando 0 nos cinco objetos.

**Checklist para fechar a geração de dados e seguir para a Fase 1** (ponto de retomada entre sessões):

- [x] Obter security token do Salesforce (21/set/2026) — nessa org, o item aparece traduzido como
  "Redefinir minha chave de segurança" em vez de "token", em Configurações pessoais (não no Setup
  admin) → "Minhas informações pessoais".
- [x] `git init` do repositório + estrutura inicial de pastas (21/set/2026) — `scripts/`, `dbt/`,
  `.github/workflows/`, `data/` criadas; branch renomeada para `main`; `.gitignore` cobrindo `.env`,
  `venv/`, `__pycache__/`, artefatos do dbt; primeiro commit feito.
- [x] Criar ambiente virtual Python e instalar `simple-salesforce` + `Faker` (21/set/2026) —
  `simple-salesforce==1.12.10`, `Faker==40.39.0`, congelado em `requirements.txt`.
- [x] Decidir volumes/distribuição de dados sintéticos (21/set/2026): ~65 Accounts, 1–4 Contacts por
  Account (variável), ~200 Opportunities distribuídas de forma não-uniforme pelo funil, ~125 Leads.
- [x] Decidir taxas de "corrupção" dos dados do CRM (21/set/2026):
  - Duplicidade de Accounts: ~8–10%
  - Picklist inconsistente (ex. `Industry`): ~15%
  - Opportunities sem Contact Role: ~20%
  - `LeadSource` nulo ou genérico (`"Other"`): ~25% (taxa mais alta de propósito — é o que mais
    pesa na atribuição de marketing da Fase 2b)
  - Datas ilógicas (`CloseDate` < `CreatedDate`): ~5%
  - Taxas ficam como parâmetros configuráveis no topo de `scripts/generate_sample_data.py`, não
    hardcoded, e documentadas em `data/GENERATED_DATA.md`.
- [x] Desenhar a fonte sintética de marketing (21/set/2026):
  - ~6–10 campanhas, misturando canais (Google Ads, Meta Ads, LinkedIn, e-mail marketing)
  - Volume maior no topo do funil: milhares de impressões, centenas de cliques por campanha
    (CTR realista, ~1–3%)
  - Taxa de propagação pro Lead fechada em **65%** (ponto médio da faixa 60–70% já decidida)
  - Timestamp do evento sempre anterior à criação do Lead correspondente (ordem cronológica
    importa pro stitching e pro modelo de atribuição first-touch da Fase 2c)
  - **Refinado em 21/set/2026 (mecanismo de vínculo clique → Lead):** distinção entre duas
    fontes de marketing reais que não devem ser confundidas — **Fonte A** (API de plataforma
    de anúncio, ex. conector Airbyte do Google/Meta Ads) entrega dado **agregado por
    campanha/dia** (impressões, cliques, custo — sem granularidade de clique individual, sem
    `click_id` nem UTM por pessoa); **Fonte B** (tracking de primeira parte do próprio site,
    tipo GA4/GTM/script próprio) é onde `click_id` e UTMs por pessoa existem de verdade. A
    fonte sintética deste projeto modela a **Fonte B**, não a A (coerente com a decisão já
    fechada de não simular um conector real). Mecanismo final: `click_id` existe só dentro do
    dataset de marketing (uso interno, nunca gravado no Salesforce); os três campos UTM
    (`UTM_Source__c`, `UTM_Medium__c`, `UTM_Campaign__c`, campos customizados no Lead) são o
    que potencialmente chega no CRM via campo oculto de formulário, com a perda de 65% — join
    da Fase 2b vira combinação dos três UTMs + proximidade de tempo (pode ser ambíguo, é o
    problema real de identity resolution). Se no futuro fizer sentido simular a Fonte A pro
    lado de custo do ROAS, entra como tabela separada (`campaign_performance`, grão
    `campaign_id + date`), decisão adiada.
  - **Custo/investimento (21/set/2026, a pedido do Fabricio):** `campaign_stats` também carrega
    `cost` por campanha, derivado de CPC por canal (google/meta/linkedin pagos, faixas diferentes de
    custo por clique cada um; newsletter com custo zero, canal próprio) — necessário pro cálculo de
    ROAS na Fase 2c. Custo zero em campanha orgânica é proposital, cria o caso real de divisão por
    zero que o SQL/dbt vai precisar tratar explicitamente.
  - **Destino dos dados (21/set/2026):** como a conta Snowflake ainda não existe, o script grava os
    três datasets como CSV em `data/` (`marketing_campaigns.csv`, `marketing_click_events.csv`,
    `marketing_campaign_stats.csv`) em vez de carregar direto no `raw` — artefato intermediário que a
    Fase 1 vai `COPY INTO` quando o Snowflake existir.
- [x] Escrever o script de geração do CRM (`scripts/generate_sample_data.py`, 21/set/2026) — Accounts →
  Contacts → Leads → Opportunities → OpportunityContactRole via Bulk API. Rodado com volumes reais:
  71 Accounts (65 + 6 duplicatas), 171 Contacts, 125 Leads, 200 Opportunities, sem erro.
- [x] Escrever o script da fonte de marketing (`scripts/generate_marketing_events.py`, 21/set/2026) —
  gera campanhas, cliques (com UTM) e estatísticas agregadas (impressões/cliques/custo por campanha);
  seleciona ~70% dos Leads existentes como "vindos de marketing" e grava UTM de volta no Salesforce só
  pra ~65% deles (perda de rastreamento). Como a conta Snowflake ainda não existe, os três datasets
  (`marketing_campaigns.csv`, `marketing_click_events.csv`, `marketing_campaign_stats.csv`) ficam em
  `data/` por enquanto — é o artefato que vira `COPY INTO` no `raw` quando a Fase 1 começar. Rodado com
  volumes reais: 8 campanhas, 1740 cliques, 88 Leads associados a um clique, 58 com UTM propagado
  (~66%, perto do alvo de 65%).
- [x] Rodar os scripts e validar os registros (21/set/2026) — validado via **Salesforce CLI**
  (`sf data query`, instalado nessa sessão: `npm install --global @salesforce/cli`, autenticado com
  `sf org login web`) em vez de só a UI. Taxas de corrupção conferidas contra os alvos configurados:
  Industry sujo ~21% (alvo 15%, dentro da variação esperada), estágios de Opportunity batendo com os
  pesos do funil, LeadSource nulo/"Other" ~22% (alvo 25%), Opportunities sem Contact Role ~19,5% (alvo
  20%, quase exato), Leads com UTM propagado 59/125. CSVs de marketing conferidos (8 campanhas, 1740
  cliques, estrutura correta).
- [x] Documentar os dados como sintéticos (21/set/2026) — `data/GENERATED_DATA.md`.
- [ ] Seguir para a Fase 1 (Airbyte → Snowflake `raw`).
