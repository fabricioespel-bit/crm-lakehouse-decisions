with accounts as (
    select * from {{ ref('stg_accounts') }}
),

keyed as (

    select 
        account_id,
        created_at,
        lower(trim(regexp_replace(account_name, '\\s+ltda\\.?$', '', 1, 1, 'i'))) as name_key,
        phone,
        website
    from accounts
),
ranked as (
    select 
        account_id,
        first_value(account_id) over (
            partition by name_key, phone, website
            order by created_at, account_id
        ) as master_account_id
    from keyed
)

select 
    account_id,
    master_account_id,
    account_id = master_account_id as is_master
from ranked