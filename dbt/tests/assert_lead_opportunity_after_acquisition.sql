{{ config(severity='warn') }}
-- Lead de marketing ligado a uma Opportunity aberta antes da aquisição: o marketing influenciou,
-- mas não originou o negócio, então não pode receber crédito de receita na 2c
select lead_id, opportunity_id, opportunity_match_path, acquired_at, opportunity_created_at
from {{ ref('int_lead_opportunities') }}
where not is_opportunity_after_acquisition