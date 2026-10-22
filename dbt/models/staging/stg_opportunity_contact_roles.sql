with source as (
    select * from {{ source('salesforce', 'OPPORTUNITYCONTACTROLE') }}
    where not ISDELETED
),

renamed as (
    select
        ID as opportunity_contact_role_id,
        OPPORTUNITYID as opportunity_id,
        CONTACTID as contact_id,
        ROLE as role,
        ISPRIMARY as is_primary,
        CREATEDDATE as created_at,
        SYSTEMMODSTAMP as updated_at
    from source
)

select * from renamed

