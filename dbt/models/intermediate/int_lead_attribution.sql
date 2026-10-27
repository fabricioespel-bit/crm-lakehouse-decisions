with leads as (
    select * from {{ ref('stg_leads') }}
),

campaigns as (
    select * from {{ ref('stg_marketing_campaigns') }}
),

conversions as (
    select * from {{ ref('int_marketing_conversions') }}
),

touches as (
    select * from {{ ref('int_marketing_touches') }}
),

acquisitions as (
    select * from conversions
    where conversion_type = 'acquisition'
),

acquisition_touches as (
    select
        submission_id,
        max(touch_count) as touch_count,
        count(distinct campaign_id) as distinct_campaign_count,
        max(iff(is_first_touch, campaign_id, null)) as first_touch_campaign_id,
        max(iff(is_last_touch, campaign_id, null)) as last_touch_campaign_id
    from touches
    where conversion_type = 'acquisition'
    group by submission_id
),

reengagements as (
    select
        lead_id,
        count(*) as reengagement_count
    from conversions
    where conversion_type = 'reengagement'
    group by lead_id
),

-- campanha indicada pelo UTM gravado no Lead (last-touch capturado pelo campo oculto do formulário)
utm_campaigns as (
    select
        leads.lead_id,
        campaigns.campaign_id as utm_campaign_id
    from leads
    inner join campaigns
        on  campaigns.utm_source   = leads.utm_source
        and campaigns.utm_medium   = leads.utm_medium
        and campaigns.utm_campaign = leads.utm_campaign
)

select
    leads.lead_id,
    case
        when acquisitions.lead_id is not null then 'journey'
        when utm_campaigns.lead_id is not null then 'utm_only'
        else 'unattributed'
    end as match_path,
    acquisitions.submission_id as acquisition_submission_id,
    acquisitions.visitor_id as acquisition_visitor_id,
    acquisitions.submitted_at as acquired_at,
    acquisition_touches.touch_count,
    acquisition_touches.distinct_campaign_count,
    -- utm_only: o UTM só registra o último toque, então o primeiro fica desconhecido (nulo)
    acquisition_touches.first_touch_campaign_id,
    coalesce(acquisition_touches.last_touch_campaign_id, utm_campaigns.utm_campaign_id) as last_touch_campaign_id,
    utm_campaigns.utm_campaign_id,
    coalesce(reengagements.reengagement_count, 0) as reengagement_count
from leads
left join acquisitions
    on acquisitions.lead_id = leads.lead_id
left join acquisition_touches
    on acquisition_touches.submission_id = acquisitions.submission_id
left join utm_campaigns
    on utm_campaigns.lead_id = leads.lead_id
left join reengagements
    on reengagements.lead_id = leads.lead_id
