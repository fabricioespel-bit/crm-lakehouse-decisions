with leads as (
    select
        lead_id,
        lower(trim(email)) as email,
        converted_opportunity_id
    from {{ ref('stg_leads') }}
),

contacts as (
    select * from {{ ref('stg_contacts') }}
),

contact_roles as (
    select * from {{ ref('stg_opportunity_contact_roles') }}
),

opportunities as (
    select * from {{ ref('stg_opportunities') }}
),

account_mapping as (
    select * from {{ ref('int_account_id_mapping') }}
),

attribution as (
    select lead_id, acquired_at from {{ ref('int_lead_attribution') }}
),

-- fallback: Lead não convertido cujo e-mail é de um Contact numa Opportunity (vendedor criou o Contact à mão)
contact_matches as (
    select
        leads.lead_id,
        contact_roles.opportunity_id
    from leads
    inner join contacts
        on contacts.email = leads.email
    inner join contact_roles
        on contact_roles.contact_id = contacts.contact_id
    inner join opportunities
        on opportunities.opportunity_id = contact_roles.opportunity_id
    where leads.converted_opportunity_id is null
    -- o mesmo Contact pode estar em mais de uma Opportunity: fica a primeira aberta
    qualify row_number() over (
        partition by leads.lead_id
        order by opportunities.created_at, opportunities.opportunity_id
    ) = 1
),

linked as (
    select
        leads.lead_id,
        coalesce(leads.converted_opportunity_id, contact_matches.opportunity_id) as opportunity_id,
        case
            when leads.converted_opportunity_id is not null then 'converted'
            when contact_matches.opportunity_id is not null then 'contact_match'
            else 'no_opportunity'
        end as opportunity_match_path
    from leads
    left join contact_matches
        on contact_matches.lead_id = leads.lead_id
)

select
    linked.lead_id,
    linked.opportunity_match_path,
    linked.opportunity_id,
    -- Account mestre (a Opportunity pode estar numa Account duplicada)
    account_mapping.master_account_id as account_id,
    opportunities.stage_name,
    opportunities.amount,
    opportunities.is_closed,
    opportunities.is_won,
    opportunities.created_at as opportunity_created_at,
    opportunities.close_date,
    attribution.acquired_at,
    -- false: a Opportunity já estava aberta antes da aquisição (marketing influenciou, não originou);
    -- nulo quando não há aquisição rastreada ou não há Opportunity
    iff(attribution.acquired_at is null or opportunities.opportunity_id is null, null,
        convert_timezone('UTC', opportunities.created_at)::timestamp_ntz >= attribution.acquired_at)
        as is_opportunity_after_acquisition
from linked
left join opportunities
    on opportunities.opportunity_id = linked.opportunity_id
left join account_mapping
    on account_mapping.account_id = opportunities.account_id
left join attribution
    on attribution.lead_id = linked.lead_id
