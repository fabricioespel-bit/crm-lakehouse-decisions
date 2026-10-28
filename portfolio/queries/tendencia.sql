-- Série mensal de Opportunities criadas e receita ganha, por origem
select
    date_trunc('month', created_at)::date as mes,
    opportunity_source,
    count(*) as opportunities,
    sum(iff(outcome = 'won', amount, 0)) as won_amount
from CRM_LAKEHOUSE.MARTS.FCT_OPPORTUNITIES
group by mes, opportunity_source
order by mes, opportunity_source