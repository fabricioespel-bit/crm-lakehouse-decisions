-- O mart já está no grão do gráfico (uma linha por origem); aqui só fixa a ordem de exibição
select *
from CRM_LAKEHOUSE.MARTS.MART_SALES_FUNNEL
order by case opportunity_source
    when 'marketing_sourced' then 1
    when 'marketing_influenced' then 2
    when 'lead_untracked' then 3
    when 'no_lead' then 4
end