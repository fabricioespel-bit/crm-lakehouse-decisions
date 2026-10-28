-- Detalhe por campanha para a tabela do painel; CPL e ROAS já vêm calculados (e defensivos) do mart
select
    utm_campaign as campanha,
    utm_source as canal,
    cost as investimento,
    last_touch_leads as leads_last,
    last_touch_cpl as cpl_last,
    last_touch_revenue as receita_last,
    first_touch_roas as roas_first,
    last_touch_roas as roas_last,
    linear_roas as roas_linear
from CRM_LAKEHOUSE.MARTS.MART_CAMPAIGN_PERFORMANCE
order by receita_last desc, investimento desc