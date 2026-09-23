with source as (

    select * from {{ source('salesforce', 'ACCOUNT')}}
    where not ISDELETED
),

renamed as (

    select 
        ID as account_id,
        NAME as account_name,
        INDUSTRY as industry,
         BILLINGCITY as billing_city,
        BILLINGSTATECODE as billing_state_code,
        BILLINGCOUNTRYCODE as billing_country_code,
        PHONE as phone,
        WEBSITE as website,
        NUMBEROFEMPLOYEES as number_of_employees,
        CREATEDDATE as created_at,
        SYSTEMMODSTAMP as updated_at
    
    from source
        
)

select * from renamed