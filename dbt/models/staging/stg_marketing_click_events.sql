with source as (
    select * from {{ source('marketing', 'MARKETING_CLICK_EVENTS') }}
),
renamed as (
    select
        CLICK_ID as click_id,
        VISITOR_ID as visitor_id,
        CAMPAIGN_ID as campaign_id,
        UTM_SOURCE as utm_source,
        UTM_MEDIUM as utm_medium,
        UTM_CAMPAIGN as utm_campaign,
        EVENT_TIMESTAMP as clicked_at
    from source
)

select * from renamed