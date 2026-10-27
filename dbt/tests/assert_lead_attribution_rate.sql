{{config(severity='warn')}}
-- Taxa de Leads atribuídos a marketing (jornada ou UTM). Hoje ~71% (vs ~47% só com UTM);
-- queda abaixo de 60% indica degradação do tracking
select match_rate
from (
    select avg(iff(match_path <> 'unattributed', 1, 0)) as match_rate
    from {{ref('int_lead_attribution')}}
)
where match_rate < 0.60

