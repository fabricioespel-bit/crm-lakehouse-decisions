{{ config(severity='warn') }}

-- Oportunidades com data de fechamento menor que a data de criação. Oportunidade inválida.
select 
    opportunity_id, 
    opportunity_name, 
    close_date, 
    created_at
from {{ ref('stg_opportunities') }}
where close_date < created_at::date