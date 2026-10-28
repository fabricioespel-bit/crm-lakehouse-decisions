-- O mart não pode perder nem duplicar Opportunity: contagem e receita ganha batem com o staging
-- (protege contra fan-out no join com Leads do fct_opportunities)
with mart as (
    select sum(opportunities) as opportunities, sum(won_amount) as won_amount
    from {{ ref('mart_sales_funnel') }}
),

source as (
    select count(*) as opportunities, sum(iff(is_won, amount, 0)) as won_amount
    from {{ ref('stg_opportunities') }}
)

select
    mart.opportunities as mart_opportunities,
    source.opportunities as source_opportunities,
    mart.won_amount as mart_won_amount,
    source.won_amount as source_won_amount
from mart
cross join source
where mart.opportunities <> source.opportunities
    or abs(mart.won_amount - source.won_amount) > 0.01
