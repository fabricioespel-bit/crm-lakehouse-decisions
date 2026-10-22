-- A combinação dos três UTMs precisa identificar uma única campanha:
-- é a chave do stitching marketing ↔ Lead (2b). Duplicidade aqui tornaria
-- a atribuição ambígua já na origem.
select 
    utm_source,
    utm_medium,
    utm_campaign,
    count(*) as campaigns
from {{ ref('stg_marketing_campaigns') }}
group by 1,2,3
having count(*) > 1