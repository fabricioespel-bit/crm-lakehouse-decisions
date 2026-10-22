with source as (
    select * from {{ source('salesforce', 'LEAD') }}
    where not ISDELETED
),

renamed as (
    select
        ID as lead_id,
        OWNERID as owner_id,
        COMPANY as company,
        FIRSTNAME as first_name,
        LASTNAME as last_name,
        EMAIL as email,
        PHONE as phone,
        LEADSOURCE as lead_source,
        STATUS as status,
        INDUSTRY as industry,
        UTM_SOURCE__C as utm_source,
        UTM_MEDIUM__C as utm_medium,
        UTM_CAMPAIGN__C as utm_campaign,
        ISCONVERTED as is_converted,
        CONVERTEDDATE as converted_date,
        CONVERTEDACCOUNTID as converted_account_id,
        CONVERTEDCONTACTID as converted_contact_id,
        CONVERTEDOPPORTUNITYID as converted_opportunity_id,
        CREATEDDATE as created_at,
        SYSTEMMODSTAMP as updated_at
    from source
)

select * from renamed