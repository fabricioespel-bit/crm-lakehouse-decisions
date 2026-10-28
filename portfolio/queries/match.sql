-- Taxa de atribuição por caminho de match + o baseline "só UTM", que é o que se teria sem a jornada
-- por visitor_id. A diferença entre os dois é o argumento da integração marketing ↔ CRM.
with leads as (
    select match_path, utm_campaign_id
    from CRM_LAKEHOUSE.INTERMEDIATE.INT_LEAD_ATTRIBUTION
),

total as (
    select count(*) as total_leads from leads
),

por_caminho as (
    select
        match_path,
        count(*) as leads
    from leads
    group by match_path

    union all

    select
        'baseline_utm' as match_path,
        count_if(utm_campaign_id is not null) as leads
    from leads
)

select
    por_caminho.match_path,
    por_caminho.leads,
    por_caminho.leads / total.total_leads as pct
from por_caminho
cross join total
order by case por_caminho.match_path
    when 'journey' then 1
    when 'utm_only' then 2
    when 'unattributed' then 3
    when 'baseline_utm' then 4
end