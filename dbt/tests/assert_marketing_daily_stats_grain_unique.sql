select 
    campaign_id,
    stat_date,
    count(*) as rows_per_day
from {{ ref('stg_marketing_campaign_daily_stats') }}
group by 1, 2
having count(*) > 1
