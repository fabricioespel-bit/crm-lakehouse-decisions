-- As duplicatas propositais do gerador são 6 (9% de 65, ver GENERATED_DATA.md).
-- Se a regra de identidade quebrar (ex.: a regex não remover "LTDA"), a contagem muda
-- e este teste acusa — os testes de integridade (unique/not_null) não pegam esse caso.
select count(*) as duplicatas_resolvidas
from {{ ref('int_account_id_mapping') }}
where not is_master
having count(*) != 6    

