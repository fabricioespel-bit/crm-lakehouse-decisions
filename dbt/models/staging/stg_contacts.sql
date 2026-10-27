with source as (
    select *
    from {{ source('salesforce', 'CONTACT') }}
    where not ISDELETED
),

renamed as (

    select 
        ID as contact_id,
        ACCOUNTID as account_id,
        NAME as full_name,
        FIRSTNAME as first_name,
        LASTNAME as last_name,
        lower(trim(EMAIL)) as email,
        EMAIL as email_raw,
        PHONE as phone,
        TITLE as title,
        CREATEDDATE as created_at,
        SYSTEMMODSTAMP as updated_at
    
    from source
)

select * from renamed