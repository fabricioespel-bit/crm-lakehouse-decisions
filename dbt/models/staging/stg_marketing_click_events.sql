{{ config(
    materialized='incremental',
    unique_key='click_id',
    incremental_strategy='merge',
    on_schema_change='fail'
) }}

with source as (
    select * from {{ source('marketing', 'MARKETING_CLICK_EVENTS') }}
    {% if is_incremental() %}
    -- reprocessa os últimos dias: evento que chega atrasado (retry da tag, fila do tracking) entra pelo merge
    where EVENT_TIMESTAMP >= (
        select dateadd(day, -{{ var('click_events_lookback_days') }}, max(clicked_at)) from {{ this }}
    )
    {% endif %}
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