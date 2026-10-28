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

**Conversão Lead → Opportunity (patch no RAW, 27/out/2026).** O gerador original não converteu nenhum
Lead e usou e-mails únicos para Leads e Contacts, então não havia elo Lead → Opportunity.
`scripts/generate_lead_conversions.py` (seed 44, reprodutível, não toca no Salesforce) lê o backup do
RAW e os envios de formulário e grava dois CSVs aplicados com `MERGE` no RAW, simulando o sync depois
do time de vendas trabalhar os Leads:
- `salesforce_lead_conversions.csv` — 20 Leads convertidos em Opportunities já abertas
  (`ISCONVERTED`, `CONVERTEDDATE`, `CONVERTED*ID`)
- `salesforce_contact_email_updates.csv` — 8 Contacts criados "à mão" pelo vendedor com o e-mail do
  Lead, sem conversão formal (elo só via e-mail → Contact Role); 4 com caixa diferente

Os dois saem dos 33 Leads `Closed - Converted`; 5 seguem sem elo nenhum. A Opportunity é criada 3–45
dias depois do envio de aquisição, exceto 1 Lead por caminho ligado a uma Opportunity aberta **antes**
da aquisição (sujeira proposital). 7 das 28 Opportunities ligadas são ganhas (1.170.154,71).

## Fonte 2 — Eventos de marketing

Gerado por `scripts/generate_marketing_events_v2.py` (26/out/2026), gravado em `data/` e carregado no
`RAW` via `COPY INTO`. Substitui o v1 (`generate_marketing_events.py`, mantido como histórico), que
ligava cada Lead a um único clique e não permitia atribuição multi-toque — ver PLANO.md seção 7.

Representa uma fonte de **tracking de primeira parte** (tipo GA4/GTM do próprio site), mais um export
diário de custo por campanha no formato que uma plataforma de anúncio entregaria. O v2 **não toca no
Salesforce**: lê os Leads e as 8 campanhas originais do backup do RAW de 16/out/2026.

**Volumes:**
| Dataset | Quantidade |
|---|---|
| Campanhas (`marketing_campaigns.csv`) | 10 (8 originais + newsletter + LinkedIn), com início/fim sobrepostos |
| Cliques (`marketing_click_events.csv`) | 12.120, de 6.099 visitantes (`visitor_id`); ~1,5% dos visitantes viram Lead |
| Envios de formulário (`marketing_form_submissions.csv`) | 113 (89 aquisições, 20 re-engajamentos de 14 Leads, 4 sem Lead no CRM) |
| Desempenho diário (`marketing_campaign_daily_stats.csv`) | 1.095 linhas (campanha × dia); custo total ~143,6 mil com CPC de B2B SaaS (Google 6–15, Meta 2,5–7, LinkedIn 10–22); newsletter com custo zero |

**Mecanismo de vínculo jornada → Lead (a parte mais importante de entender):**
1. Cada visitante tem uma jornada de 1–6 cliques em até 60 dias, cada clique numa campanha ativa naquela
   data — a jornada pode cruzar campanhas (34 jornadas com primeiro toque ≠ último toque)
2. O envio de formulário liga o `visitor_id` ao e-mail do Lead — é a chave do stitching
3. Os 59 Leads com UTM no Salesforce (`UTM_Source__c`, `UTM_Medium__c`, `UTM_Campaign__c`) têm o
   **último clique** na campanha do UTM — campo oculto de formulário captura o last-touch. Outros 30
   Leads sem UTM também vieram de marketing (perda de propagação: 59/89 ≈ 66%); o resto é orgânico
4. ~20% dos Leads de jornada voltam e enviam outro formulário (re-engajamento, até 2 vezes, 15–120 dias
   depois, com 0–3 cliques entre os envios). Gerado com seed separada (43), sem alterar as aquisições
5. A newsletter nunca é o primeiro clique de um visitante (só recebe quem já está na base): quando o
   sorteio cai nela, a campanha é trocada por outra ativa na data (seed separada, 45)

**Sujeira proposital:** e-mail do formulário com caixa/espaço diferente do CRM (~10%); troca de
dispositivo em ~10% das jornadas (primeiros toques em outro `visitor_id`, irrecuperáveis); envios sem
Lead no CRM (~5%); cliques depois da conversão (~20% dos visitantes que convertem); cliques da
plataforma 10–25% acima dos rastreados no site.

## Reprodutibilidade

Ambos os scripts usam `random.seed(42)`. No CRM, os IDs do Salesforce são sempre novos (não controlados
pela seed). O gerador de marketing v2 usa janela de datas fixa e UUIDs derivados da seed, então gera CSVs
idênticos a cada execução.

## Como regenerar

```bash
source venv/bin/activate
python3 scripts/generate_sample_data.py
python3 scripts/generate_marketing_events_v2.py   # não toca no Salesforce
python3 scripts/generate_lead_conversions.py      # depois do v2 (lê os envios); aplicar no RAW via MERGE
```

**Atenção:** o `generate_sample_data.py` (e o v1 de marketing) fazem `insert`/`update` direto na org Salesforce configurada no `.env` —
rodar de novo sem limpar a org antes duplica os dados.
