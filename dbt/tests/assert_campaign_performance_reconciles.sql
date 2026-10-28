-- O mart não pode perder nem duplicar crédito nos joins: os totais do mart batem com os do fato
with mart as (
    select sum(last_touch_leads) as leads, sum(last_touch_revenue) as revenue
    from {{ ref('mart_campaign_performance') }}
),

fct as (
    select sum(last_touch_credit) as leads, sum(last_touch_revenue) as revenue
    from {{ ref('fct_lead_campaign_attribution') }}
)

select mart.leads as mart_leads, fct.leads as fct_leads, mart.revenue as mart_revenue, fct.revenue as fct_revenue
from mart
cross join fct
where mart.leads <> fct.leads
    or abs(mart.revenue - fct.revenue) > 0.01