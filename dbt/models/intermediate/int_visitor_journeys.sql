with touches as (
    select * from {{ ref('int_marketing_touches') }}
),

conversions as (
    select * from {{ ref('int_marketing_conversions') }}
),

visitor_clicks as (
    select
        visitor_id,
        count(*) as click_count,
        count(distinct campaign_id) as distinct_campaign_count,
        sum(iff(touch_phase = 'pre_conversion', 1, 0)) as pre_conversion_click_count,
        min(clicked_at) as first_click_at,
        max(clicked_at) as last_click_at,
        min_by(campaign_id, clicked_at) as first_campaign_id,
        max_by(campaign_id, clicked_at) as last_campaign_id
    from touches
    group by visitor_id
),

visitor_conversions as (
    select
        visitor_id,
        count(*) as conversion_count,
        min(submitted_at) as first_conversion_at,
        -- nos dados atuais um visitante leva no máximo a um Lead (sem computador compartilhado)
        max(lead_id) as lead_id
    from conversions
    group by visitor_id
)

select
    visitor_clicks.*,
    coalesce(visitor_conversions.conversion_count, 0) as conversion_count,
    visitor_conversions.first_conversion_at,
    visitor_conversions.lead_id,
    case
        when visitor_conversions.lead_id is not null then 'converted_lead'
        when visitor_conversions.visitor_id is not null then 'converted_no_lead'
        else 'not_converted'
    end as journey_outcome
from visitor_clicks
left join visitor_conversions
    on visitor_conversions.visitor_id = visitor_clicks.visitor_id
