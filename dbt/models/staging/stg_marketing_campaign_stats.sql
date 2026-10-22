with source as (
    select * from {{ source('marketing', 'MARKETING_CAMPAIGN_STATS') }}
),
renamed as (
    select 
        CAMPAIGN_ID as campaign_id,
        IMPRESSIONS as impressions,
        CLICKS as clicks,
        COST as cost
    from source
)

select * from renamed