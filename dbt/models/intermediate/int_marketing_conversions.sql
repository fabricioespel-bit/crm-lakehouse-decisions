with submissions as (
    select * from {{ ref('stg_marketing_form_submissions') }}
),  
leads as (
    select
        lead_id,
        lower(trim(email)) as email
    from {{ ref('stg_leads') }}
),

matched as (
    select 
        submissions.submission_id,
        submissions.visitor_id,
        submissions.email,
        submissions.submitted_at,
        leads.lead_id
    from submissions
    left join leads
        on leads.email = submissions.email
),

-- numeração por Lead (pelo email, não pelo visitor_id: a pessoa pode voltar por outro dispositivo);
-- envio sem Lead é numerado pelo próprio email
numbered as (
    select 
        *, 
        row_number() over(
            partition by coalesce(lead_id, email)
            order by submitted_at, submission_id
        ) as conversion_number
    from matched
)

select 
    submission_id,
    visitor_id,
    email,
    submitted_at,
    lead_id,
    conversion_number,
    case 
        when lead_id is null then 'unmatched'
        when conversion_number = 1 then 'acquisition'
        else 'reengagement' 
    end as conversion_type    
from numbered

   
    