{{ config(severity = 'warn') }}

-- Status de Lead 'Closed - Converted' sem a conversão real no Salesforce 
-- (IsConverted = false, sem Opportunity). Inconsistência proposital dos dados sintéticos:
-- o status foi gravado via API sem passar pelo processo de conversão.
select lead_id, status, is_converted
from {{ ref('stg_leads') }}
where status = 'Closed - Converted'
and not is_converted