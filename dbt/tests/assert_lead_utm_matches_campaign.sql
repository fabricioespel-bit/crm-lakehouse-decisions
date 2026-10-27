-- UTM gravado no Lead não corresponde a nenhuma campanha: sem este teste, o Lead
-- cairia silenciosamente em 'unattributed' no int_lead_attribution
select
    leads.lead_id,
    leads.utm_source,
    leads.utm_medium,
    leads.utm_campaign
from {{ref('stg_leads')}} as leads
left join {{ref('stg_marketing_campaigns')}} as campaigns
    on campaigns.utm_source = leads.utm_source
    and campaigns.utm_medium = leads.utm_medium
    and campaigns.utm_campaign = leads.utm_campaign
where coalesce(leads.utm_source, leads.utm_medium, leads.utm_campaign) is not null
    and campaigns.campaign_id is null