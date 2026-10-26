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
| Cliques (`marketing_click_events.csv`) | 2.052, de 999 visitantes (`visitor_id`) |
| Envios de formulário (`marketing_form_submissions.csv`) | 93 (89 com Lead no CRM, 4 sem) |
| Desempenho diário (`marketing_campaign_daily_stats.csv`) | 1.095 linhas (campanha × dia); newsletter com custo zero |

**Mecanismo de vínculo jornada → Lead (a parte mais importante de entender):**
1. Cada visitante tem uma jornada de 1–6 cliques em até 60 dias, cada clique numa campanha ativa naquela
   data — a jornada pode cruzar campanhas (34 jornadas com primeiro toque ≠ último toque)
2. O envio de formulário liga o `visitor_id` ao e-mail do Lead — é a chave do stitching
3. Os 59 Leads com UTM no Salesforce (`UTM_Source__c`, `UTM_Medium__c`, `UTM_Campaign__c`) têm o
   **último clique** na campanha do UTM — campo oculto de formulário captura o last-touch. Outros 30
   Leads sem UTM também vieram de marketing (perda de propagação: 59/89 ≈ 66%); o resto é orgânico

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
```

**Atenção:** o `generate_sample_data.py` (e o v1 de marketing) fazem `insert`/`update` direto na org Salesforce configurada no `.env` —
rodar de novo sem limpar a org antes duplica os dados.
