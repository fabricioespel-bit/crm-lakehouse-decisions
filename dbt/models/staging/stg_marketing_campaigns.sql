with source as (
    select * from {{ source('marketing', 'MARKETING_CAMPAIGNS') }}
), 

renamed as (
    select
        CAMPAIGN_ID as campaign_id,
        UTM_SOURCE as utm_source,
        UTM_MEDIUM as utm_medium,
        UTM_CAMPAIGN as utm_campaign
    from source
)

select * from renamed