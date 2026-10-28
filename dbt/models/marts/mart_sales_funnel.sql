with opportunities as (
    select * from {{ ref('fct_opportunities') }}
)

select
    opportunity_source,
    count(*) as opportunities,
    count_if(outcome = 'open') as open_opportunities,
    count_if(outcome = 'won') as won_opportunities,
    count_if(outcome = 'lost') as lost_opportunities,
    -- win rate sobre as fechadas; sem nenhuma fechada fica nulo, não 0
    won_opportunities / nullif(won_opportunities + lost_opportunities, 0) as win_rate,
    sum(iff(outcome = 'open', amount, 0)) as open_pipeline_amount,
    sum(iff(outcome = 'won', amount, 0)) as won_amount,
    avg(iff(outcome = 'won', amount, null)) as avg_won_amount,
    -- ciclo de venda das ganhas, sem as datas ilógicas (CloseDate < CreatedDate)
    median(iff(outcome = 'won' and is_valid_sales_cycle, sales_cycle_days, null)) as median_won_cycle_days,
    avg(iff(outcome = 'won' and is_valid_sales_cycle, sales_cycle_days, null)) as avg_won_cycle_days,
    count_if(is_closed and not is_valid_sales_cycle) as invalid_cycle_count
from opportunities
group by opportunity_source
