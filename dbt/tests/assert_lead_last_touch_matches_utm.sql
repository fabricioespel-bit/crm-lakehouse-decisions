-- O UTM gravado no Lead é o last-touch capturado pelo formulário na aquisição: quando o
-- Lead tem jornada e UTM, o último toque precisa ser a mesma campanha. Divergência indica
-- erro no stitching (e-mail ligado ao Lead errado ou ordenação de toques)
select
    lead_id,
    last_touch_campaign_id,
    utm_campaign_id
from {{ ref('int_lead_attribution') }}
where match_path = 'journey'
    and utm_campaign_id is not null
    and last_touch_campaign_id <> utm_campaign_id
