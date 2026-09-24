with source as (

    select * from {{ source('salesforce', 'ACCOUNT')}}
    where not ISDELETED
),

industry_mapping as (
    select * from {{ ref('industry_mapping')}}
),

renamed as (

    select 
        a.ID as account_id,
        a.NAME as account_name,
        coalesce(m.industry_standardized, a.INDUSTRY) as industry,
        a.INDUSTRY as industry_raw,
        a.BILLINGCITY as billing_city,
        a.BILLINGSTATECODE as billing_state_code,
        a.BILLINGCOUNTRYCODE as billing_country_code,
        a.PHONE as phone,
        a.WEBSITE as website,
        a.NUMBEROFEMPLOYEES as number_of_employees,
        a.CREATEDDATE as created_at,
        a.SYSTEMMODSTAMP as updated_at
    
    from source as a 
    left join industry_mapping as m 
        on a.industry = m.industry_raw
        
)

select * from renamed