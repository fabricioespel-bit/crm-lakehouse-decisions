{% macro drop_ci_schemas() %}
    {#- remove os schemas do PR no fim do CI; recusa rodar fora do target ci para nunca apagar schema de verdade -#}
    {% if target.name != 'ci' %}
        {{ exceptions.raise_compiler_error('drop_ci_schemas só roda no target ci') }}
    {% endif %}
    {% set prefix = env_var('DBT_CI_SCHEMA_PREFIX') | upper ~ '_' %}
    {% set schemas = run_query("select schema_name from " ~ target.database ~ ".information_schema.schemata") %}
    {% for row in schemas %}
        {#- startswith, não like: no like o '_' é curinga e CI_PR12_ casaria com CI_PR120_ -#}
        {% if row[0].startswith(prefix) %}
            {% do run_query('drop schema if exists ' ~ target.database ~ '.' ~ row[0] ~ ' cascade') %}
            {{ log('Schema removido: ' ~ row[0], info=True) }}
        {% endif %}
    {% endfor %}
{% endmacro %}