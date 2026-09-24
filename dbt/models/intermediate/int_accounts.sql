with accounts as (
    select * from {{ ref('stg_accounts') }}
),

mapping as (
    select * from {{ ref('int_account_id_mapping') }}
)


select a.* 
from accounts as a 
inner join mapping as m 
    on a.account_id = m.account_id 
where m.is_master