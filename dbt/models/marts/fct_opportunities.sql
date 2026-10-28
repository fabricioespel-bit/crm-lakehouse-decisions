with opportunities as (
    select * from {{ ref('stg_opportunities') }}
),

account_mapping as (
    select * from {{ ref('int_account_id_mapping') }}
),

lead_links as (
    select * from {{ ref('int_lead_opportunities') }}
    where opportunity_id is not null
    -- mais de um Lead na mesma Opportunity: fica o que chegou primeiro (Lead sem aquisição por último)
    qualify row_number() over (
        partition by opportunity_id
        order by acquired_at nulls last, lead_id
    ) = 1
),

attribution as (
    select * from {{ ref('int_lead_attribution') }}
)

select
    opportunities.opportunity_id,
    account_mapping.master_account_id as account_id,
    opportunities.opportunity_name,
    opportunities.stage_name,
    opportunities.amount,
    opportunities.is_closed,
    opportunities.is_won,
    opportunities.created_at,
    opportunities.close_date,
    case
        when not opportunities.is_closed then 'open'
        when opportunities.is_won then 'won'
        else 'lost'
    end as outcome,
    -- ciclo só de Opportunity fechada; negativo é a sujeira de CloseDate < CreatedDate e fica fora das médias
    iff(opportunities.is_closed,
        datediff(day, opportunities.created_at::date, opportunities.close_date), null) as sales_cycle_days,
    iff(opportunities.is_closed, sales_cycle_days >= 0, null) as is_valid_sales_cycle,
    lead_links.lead_id,
    lead_links.opportunity_match_path,
    attribution.first_touch_campaign_id,
    attribution.last_touch_campaign_id,
    -- utm_only não tem data de aquisição, então cai em lead_untracked (não dá para validar a ordem no tempo)
    case
        when lead_links.lead_id is null then 'no_lead'
        when lead_links.acquired_at is null then 'lead_untracked'
        when lead_links.is_opportunity_after_acquisition then 'marketing_sourced'
        else 'marketing_influenced'
    end as opportunity_source
from opportunities
left join account_mapping
    on account_mapping.account_id = opportunities.account_id
left join lead_links
    on lead_links.opportunity_id = opportunities.opportunity_id
left join attribution
    on attribution.lead_id = lead_links.lead_id
