# Dados sintéticos deste projeto

Todos os dados neste projeto (Salesforce e eventos de marketing) são **gerados artificialmente**,
não coletados de nenhuma empresa ou pessoa real. Este documento existe por transparência — mesmo
princípio já usado na camada sintética de tickets do `account-health-ml-service`.

## Fonte 1 — CRM (Salesforce)

Gerado por `scripts/generate_sample_data.py`, usando `simple-salesforce` (autenticação) + `Faker`
(locale `pt_BR`, dados com nomes/endereços/telefones brasileiros fictícios).

**Volumes (seed fixa em 42, reprodutível):**
| Objeto | Quantidade |
|---|---|
| Account | 71 (65 originais + 6 duplicatas propositais) |
| Contact | 171 (1–4 por Account) |
| Lead | 125 |
| Opportunity | 200 |
| OpportunityContactRole | ~161 (200 − ~20% sem Contact Role, proposital) |

**Sujeira proposital injetada** (taxas configuráveis no topo do script, ver PLANO.md seção 4):
- Duplicidade de Account: ~9% (nome com variação — maiúsculas, sufixo "Ltda", espaço extra)
- Picklist `Industry` inconsistente: ~15% (ex. `"Tech"` em vez de `"Technology"`)
- Opportunity sem Contact Role: ~20%
- `LeadSource` nulo ou genérico (`"Other"`): ~25%
- Datas ilógicas (`CloseDate` anterior a `CreatedDate`, só em Opportunities fechadas): ~5%

Essa sujeira é intencional — simula problemas reais de qualidade de dado em CRM mal preenchido, e é
o que justifica a camada `staging` do dbt fazer limpeza de verdade, não só tipagem (ver PLANO.md
seção 2).

## Fonte 2 — Eventos de marketing

Gerado por `scripts/generate_marketing_events.py`, gravado em `data/marketing_campaigns.csv`,
`data/marketing_click_events.csv`, `data/marketing_campaign_stats.csv` — artefato intermediário até
a conta Snowflake existir (Fase 1 vai fazer `COPY INTO` desses arquivos pro schema `raw`).

Representa uma fonte de **tracking de primeira parte** (tipo GA4/GTM do próprio site), não uma API de
plataforma de anúncio — ver PLANO.md seção 4 pra a distinção entre as duas.

**Volumes:**
| Dataset | Quantidade |
|---|---|
| Campanhas | 8, em 4 canais (Google Ads, Meta Ads, LinkedIn, newsletter) |
| Eventos de clique | 1740 |
| Impressões (derivadas, CTR 1–3%) | ~86 mil (agregado por campanha) |
| Custo total (CPC por canal, newsletter = R$0) | ver `marketing_campaign_stats.csv` |

**Mecanismo de vínculo clique → Lead (a parte mais importante de entender):**
1. ~70% dos 125 Leads do Salesforce foram escolhidos como "vindos de marketing", cada um associado a
   um evento de clique com timestamp anterior à criação do Lead
2. Desses, só **~65%** (59 de 88, nessa geração) tiveram os UTMs gravados de volta no Salesforce
   (campos customizados `UTM_Source__c`, `UTM_Medium__c`, `UTM_Campaign__c` no Lead) — os outros ~35%
   simulam perda de rastreamento real (ad blocker, cookie limpo, troca de dispositivo)
3. O evento de clique original **continua existindo** no dataset de marketing mesmo quando o UTM não
   propagou pro Salesforce — é isso que cria o gap de atribuição que a Fase 2b (stitching) precisa
   medir honestamente, em vez de fingir 100% de match

## Reprodutibilidade

Ambos os scripts usam `random.seed(42)` — rodar de novo gera a mesma sequência de valores "aleatórios"
(embora IDs do Salesforce e UUIDs de clique sejam sempre novos, já que não são controlados pela seed).

## Como regenerar

```bash
source venv/bin/activate
python3 scripts/generate_sample_data.py
python3 scripts/generate_marketing_events.py
```

**Atenção:** os dois scripts fazem `insert`/`update` direto na org Salesforce configurada no `.env` —
rodar de novo sem limpar a org antes duplica os dados.
