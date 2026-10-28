with campaigns as (
    select * from {{ ref('stg_marketing_campaigns') }}
),

daily_stats as (
    select
        campaign_id,
        sum(impressions) as impressions,
        sum(clicks) as platform_clicks,
        sum(cost) as cost
    from {{ ref('stg_marketing_campaign_daily_stats') }}
    group by campaign_id
),

-- cliques rastreados no site, inclusive os que não converteram (o caminho dos insucessos)
tracked as (
    select
        campaign_id,
        count(*) as tracked_clicks,
        count(distinct visitor_id) as visitors,
        count_if(touch_phase = 'pre_conversion') as converting_clicks,
        count_if(touch_phase = 'no_conversion') as non_converting_clicks
    from {{ ref('int_marketing_touches') }}
    group by campaign_id
),

attribution as (
    select 
        campaign_id,
        sum(first_touch_credit) as first_touch_leads,
        sum(last_touch_credit) as last_touch_leads,
        sum(linear_credit) as linear_leads,
        sum(first_touch_revenue) as first_touch_revenue,
        sum(last_touch_revenue) as last_touch_revenue,
        sum(linear_revenue) as linear_revenue
    from {{ ref('fct_lead_campaign_attribution') }}
    group by campaign_id
),

joined as (
    select
        campaigns.campaign_id,
        campaigns.utm_source,
        campaigns.utm_medium,
        campaigns.utm_campaign,
        campaigns.start_date,
        campaigns.end_date,
        coalesce(daily_stats.cost, 0) as cost,
        coalesce(daily_stats.impressions, 0) as impressions,
        coalesce(daily_stats.platform_clicks, 0) as platform_clicks,
        coalesce(tracked.tracked_clicks, 0) as tracked_clicks,
        coalesce(tracked.visitors, 0) as visitors,
        coalesce(tracked.converting_clicks, 0) as converting_clicks,
        coalesce(tracked.non_converting_clicks, 0) as non_converting_clicks,
        coalesce(attribution.first_touch_leads, 0) as first_touch_leads,
        coalesce(attribution.last_touch_leads, 0) as last_touch_leads,
        coalesce(attribution.linear_leads, 0) as linear_leads,
        coalesce(attribution.first_touch_revenue, 0) as first_touch_revenue,
        coalesce(attribution.last_touch_revenue, 0) as last_touch_revenue,
        coalesce(attribution.linear_revenue, 0) as linear_revenue
    from campaigns
    left join daily_stats
        on daily_stats.campaign_id = campaigns.campaign_id
    left join tracked
        on tracked.campaign_id = campaigns.campaign_id
    left join attribution
        on attribution.campaign_id = campaigns.campaign_id
)

select 
    *,
    -- divisão defensiva: sem lead -> CPL nulo; sem custo (newsletter) -> ROAS nulo, não infinito
    cost / nullif(first_touch_leads, 0) as first_touch_cpl,
    cost / nullif(last_touch_leads, 0) as last_touch_cpl,
    cost / nullif(linear_leads, 0) as linear_cpl,
    first_touch_revenue / nullif(cost, 0) as first_touch_roas,
    last_touch_revenue / nullif(cost, 0) as last_touch_roas,
    linear_revenue / nullif(cost, 0) as linear_roas
from joined