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
  - **Risco identificado, ainda não testado:** Airbyte self-hosted normalmente roda via Docker, e o Docker
    Desktop já se mostrou incompatível com esta máquina (macOS) em pelo menos um projeto anterior
    (`amigurumi-agent`, que migrou pra Qdrant Cloud por causa disso). Se o mesmo acontecer aqui, o
    fallback é **Airbyte Cloud** (tem free tier) — a confirmar na prática antes de assumir qual caminho
    seguir.
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
  - [ ] Gerar/complementar dados de exemplo no CRM, com sujeira proposital (checklist na seção 7).
  - [ ] Desenhar e gerar a fonte sintética de eventos de marketing (volumes, taxa de propagação do
    click_id) — checklist na seção 7.
  - [ ] Criar conta trial do Snowflake (warehouse X-Small, databases/schemas).
  - [ ] Decidir Airbyte self-hosted vs. Cloud na prática.
- **Fase 1 — Ingestão:** conectar Airbyte (Salesforce → Snowflake) e o script Python de eventos de
  marketing (carga direta pro `raw`, ver seção 4); decidir e documentar estratégia de sincronização
  incremental (`SystemModstamp` no CRM, timestamp de evento no marketing).
- **Fase 2 — Transformação (dbt):** projeto dbt Core inicializado e versionado no Git.
  - **2a — staging:** tipagem, dedup, padronização de picklists, limpeza da sujeira proposital do CRM.
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

**Checklist para fechar a geração de dados e seguir para a Fase 1** (ponto de retomada entre sessões):

- [ ] Obter security token do Salesforce (Setup → "Reset My Security Token").
- [ ] `git init` do repositório + estrutura inicial de pastas (ex.: `scripts/`, `dbt/`,
  `.github/workflows/`).
- [ ] Criar ambiente virtual Python e instalar `simple-salesforce` + `Faker`.
- [ ] Decidir volumes/distribuição de dados sintéticos (nº de Accounts, Contacts por Account, Opportunities
  por estágio do funil, Leads).
- [ ] Decidir taxas de "corrupção" dos dados do CRM (% duplicidade, % picklist inconsistente, % Contact
  Role ausente, % LeadSource nulo/genérico, % datas ilógicas).
- [ ] Desenhar a fonte sintética de marketing: campanhas, volume de impressões/cliques por campanha, taxa
  de propagação do `click_id`/UTM pro Lead (ex.: 60–70%).
- [ ] Escrever o script de geração do CRM (ex.: `scripts/generate_sample_data.py`).
- [ ] Escrever o script da fonte de marketing, já com a carga direta pro `raw` do Snowflake (ex.:
  `scripts/generate_marketing_events.py`).
- [ ] Rodar os scripts e validar os registros criados na UI do Salesforce e no dataset de marketing.
- [ ] Documentar os dados como sintéticos (ex.: `data/GENERATED_DATA.md`), no mesmo espírito de
  transparência da camada sintética do `account-health-ml-service`.
- [ ] Seguir para a Fase 1 (Airbyte → Snowflake `raw`).
