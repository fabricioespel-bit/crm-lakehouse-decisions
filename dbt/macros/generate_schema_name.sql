{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set base_schema = target.schema if custom_schema_name is none else custom_schema_name | trim -%}
    {#- no CI, cada PR grava em schemas próprios (CI_PR12_STAGING...), sem tocar nos objetos de verdade -#}
    {%- if target.name == 'ci' -%}
        {{ env_var('DBT_CI_SCHEMA_PREFIX') }}_{{ base_schema }}
    {%- else -%}
        {{ base_schema }}
    {%- endif -%}
{%- endmacro %}
