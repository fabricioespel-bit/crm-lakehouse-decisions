-- Grão do fato: um Lead × campanha
select lead_id, campaign_id, count(*) as row_count
from {{ ref('fct_lead_campaign_attribution') }}
group by lead_id, campaign_id
having count(*) > 1