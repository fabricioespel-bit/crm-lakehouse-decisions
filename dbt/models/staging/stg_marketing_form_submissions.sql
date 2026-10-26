with source as (
    select * from {{ source('marketing', 'MARKETING_FORM_SUBMISSIONS') }}
), 
renamed as (
    select
        SUBMISSION_ID as submission_id,
        VISITOR_ID as visitor_id,
        lower(trim(EMAIL)) as email,
        EMAIL as email_raw,
        SUBMITTED_AT as submitted_at
    from source
)

select * from renamed