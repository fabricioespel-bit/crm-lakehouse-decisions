with touches as (
    select * from {{ ref('int_marketing_touches') }}
    where touch_phase = 'pre_conversion'
        and conversion_type = 'acquisition'
),

leads as (
    select * from {{ ref('int_lead_attribution') }}
),

opportunities as (
    select * from {{ ref('int_lead_opportunities') }}
),

-- crédito por campanha dentro da jornada de aquisição: uma campanha pode aparecer em vários toques
journey_credits as (
    select
        lead_id,
        campaign_id,
        count(*) as campaign_touch_count,
        max(iff(is_first_touch, 1, 0)) as first_touch_credit,
        max(iff(is_last_touch, 1, 0)) as last_touch_credit,
        count(*) / max(touch_count) as linear_credit
    from touches
    group by lead_id, campaign_id
),

-- utm_only: o UTM só registra o último toque, então first-touch e linear ficam desconhecidos (nulos)
utm_credits as (
    select
        lead_id,
        last_touch_campaign_id as campaign_id,
        0 as campaign_touch_count,
        null as first_touch_credit,
        1 as last_touch_credit,
        null as linear_credit
    from leads
    where match_path = 'utm_only'
),

credits as (
    select * from journey_credits
    union all
    select * from utm_credits
)

select
    credits.lead_id,
    credits.campaign_id,
    leads.match_path,
    leads.acquired_at,
    credits.campaign_touch_count,
    credits.first_touch_credit,
    credits.last_touch_credit,
    credits.linear_credit,
    opportunities.opportunity_id,
    -- receita só de Opportunity ganha e criada depois da aquisição (aberta antes: marketing só influenciou;
    -- utm_only não tem data de aquisição para validar a ordem, então fica sem receita)
    iff(opportunities.is_won and opportunities.is_opportunity_after_acquisition,
        opportunities.amount, 0) as attributable_revenue,
    attributable_revenue * credits.first_touch_credit as first_touch_revenue,
    attributable_revenue * credits.last_touch_credit as last_touch_revenue,
    attributable_revenue * credits.linear_credit as linear_revenue
from credits
inner join leads
    on leads.lead_id = credits.lead_id
left join opportunities
    on opportunities.lead_id = credits.lead_id