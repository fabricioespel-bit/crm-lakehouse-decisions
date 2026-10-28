-- Cada Lead atribuído distribui exatamente 1 Lead de crédito em cada modelo (o linear com tolerância de
-- arredondamento: 1/3 + 1/3 + 1/3 = 0,999999). utm_only só tem last_touch
select
    lead_id,
    match_path,
    sum(first_touch_credit) as first_total,
    sum(last_touch_credit) as last_total,
    sum(linear_credit) as linear_total
from {{ ref('fct_lead_campaign_attribution') }}
group by lead_id, match_path
having last_total <> 1
    or (match_path = 'journey' and (first_total <> 1 or abs(linear_total -1) > 0.001))