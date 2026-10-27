with clicks as ( 
    select * from {{ ref('stg_marketing_click_events') }}
),

conversions as ( 
    select * from {{ ref('int_marketing_conversions') }}
),

converted_visitors as (
    select distinct visitor_id from conversions
),

-- próximo envio do mesmo visitante depois do clique: é a conversão para a qual o clique contribuiu
next_conversion as ( 
    select 
        clicks.click_id,
        conversions.submission_id,
        conversions.submitted_at,
        conversions.lead_id,
        conversions.conversion_number,
        conversions.conversion_type
    from clicks
    inner join conversions
        on conversions.visitor_id = clicks.visitor_id
        and conversions.submitted_at > clicks.clicked_at
    qualify row_number() over(
        partition by clicks.click_id
        order by conversions.submitted_at, conversions.submission_id
    ) = 1
),

classified as(
    select
        clicks.click_id,
        clicks.visitor_id,
        clicks.campaign_id,
        clicks.clicked_at,
        next_conversion.submission_id,
        next_conversion.submitted_at,
        next_conversion.lead_id,
        next_conversion.conversion_number,
        next_conversion.conversion_type,
        case 
            when converted_visitors.visitor_id is null then 'no_conversion'
            when next_conversion.click_id is null then 'post_conversion'
            when next_conversion.submitted_at > dateadd(day, {{var('attribution_lookback_days')}}, clicks.clicked_at)
                then 'outside_window'
            else 'pre_conversion'
        end as touch_phase
    from clicks
    left join next_conversion
        on next_conversion.click_id = clicks.click_id
    left join converted_visitors
        on converted_visitors.visitor_id = clicks.visitor_id
),

-- só toques dentro da janela ficam ligados à conversão
attributed as (
    select
        click_id,
        visitor_id,
        campaign_id,
        clicked_at,
        touch_phase,
        iff(touch_phase = 'pre_conversion', submission_id, null) as submission_id,
        iff(touch_phase = 'pre_conversion', submitted_at, null) as submitted_at,
        iff(touch_phase = 'pre_conversion', lead_id, null) as lead_id,
        iff(touch_phase = 'pre_conversion', conversion_number, null) as conversion_number,
        iff(touch_phase = 'pre_conversion', conversion_type, null) as conversion_type
    from classified
),

positioned as ( 
    select
        *,
        iff(submission_id is not null,
            row_number() over (partition by submission_id order by clicked_at, click_id),
            null) as touch_number,
        iff(submission_id is not null,
            count(*) over (partition by submission_id),
            null) as touch_count
    from attributed
)

select
    *,
    touch_number = 1 as is_first_touch,
    touch_number  = touch_count as is_last_touch
from positioned

