with source as (
    select * from {{ source('salesforce', 'OPPORTUNITY') }}
    where not ISDELETED
),

renamed as (
    select
        ID as opportunity_id,
        ACCOUNTID as account_id,
        CONTACTID as primary_contact_id,
        OWNERID as owner_id,
        NAME as opportunity_name,
        STAGENAME as stage_name,
        AMOUNT::number(18, 2) as amount,
        PROBABILITY as probability,
        CLOSEDATE as close_date,
        ISCLOSED as is_closed,
        ISWON as is_won,
        FORECASTCATEGORY as forecast_category,
        LEADSOURCE as lead_source,
        CAMPAIGNID as campaign_id,
        CREATEDDATE as created_at,
        SYSTEMMODSTAMP as updated_at
    from source
)

select * from renamed
