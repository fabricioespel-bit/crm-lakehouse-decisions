-- Um canal por linha, com os três modelos de atribuição lado a lado: o mesmo canal muda de ROAS
-- conforme o modelo, e é esse contraste que o gráfico mostra
select
    utm_source as canal,
    sum(cost) as investimento,
    sum(tracked_clicks) as cliques_rastreados,
    sum(first_touch_leads) as leads_first,
    sum(last_touch_leads) as leads_last,
    sum(linear_leads) as leads_linear,
    sum(first_touch_revenue) as receita_first,
    sum(last_touch_revenue) as receita_last,
    sum(linear_revenue) as receita_linear,
    -- newsletter não tem custo: ROAS nulo, não infinito
    sum(first_touch_revenue) / nullif(sum(cost), 0) as roas_first,
    sum(last_touch_revenue) / nullif(sum(cost), 0) as roas_last,
    sum(linear_revenue) / nullif(sum(cost), 0) as roas_linear
from CRM_LAKEHOUSE.MARTS.MART_CAMPAIGN_PERFORMANCE
group by utm_source
order by investimento desc