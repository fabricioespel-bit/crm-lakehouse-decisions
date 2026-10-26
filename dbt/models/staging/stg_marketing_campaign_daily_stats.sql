with source as (
    select * from {{ source('marketing', 'MARKETING_CAMPAIGN_DAILY_STATS') }}
), 
renamed as (
    select
        CAMPAIGN_ID as campaign_id,
        STAT_DATE as stat_date,
        IMPRESSIONS as impressions,
        CLICKS as clicks,
        COST as cost
    from source
)

select * from renamed