-- KPIs do topo do painel: uma linha. Cada CTE agrega um mart no próprio grão e o cross join junta tudo.
with marketing as (
    select
        sum(cost) as investimento,
        sum(last_touch_leads) as leads_atribuidos,
        sum(last_touch_revenue) as receita_atribuida
    from CRM_LAKEHOUSE.MARTS.MART_CAMPAIGN_PERFORMANCE
),

funil as (
    select
        sum(won_amount) as receita_ganha_total,
        sum(iff(opportunity_source = 'marketing_sourced', won_amount, 0)) as receita_marketing,
        sum(won_opportunities) as ganhas,
        sum(lost_opportunities) as perdidas,
        sum(open_pipeline_amount) as pipeline_aberto
    from CRM_LAKEHOUSE.MARTS.MART_SALES_FUNNEL
),

-- mediana não se agrega a partir das medianas por origem: calcula direto no fato
ciclo as (
    select median(sales_cycle_days) as ciclo_mediano_dias
    from CRM_LAKEHOUSE.MARTS.FCT_OPPORTUNITIES
    where outcome = 'won'
        and is_valid_sales_cycle
)

select
    marketing.investimento,
    marketing.leads_atribuidos,
    marketing.investimento / nullif(marketing.leads_atribuidos, 0) as cpl,
    marketing.receita_atribuida,
    marketing.receita_atribuida / nullif(marketing.investimento, 0) as roas,
    funil.receita_ganha_total,
    funil.receita_marketing / nullif(funil.receita_ganha_total, 0) as share_receita_marketing,
    funil.ganhas / nullif(funil.ganhas + funil.perdidas, 0) as win_rate,
    funil.pipeline_aberto,
    ciclo.ciclo_mediano_dias
from marketing
cross join funil
cross join ciclo