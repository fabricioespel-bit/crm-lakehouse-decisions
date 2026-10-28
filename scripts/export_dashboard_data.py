"""Exporta os dados do painel executivo do portfólio: roda cada portfolio/queries/*.sql no Snowflake e
grava um JSON só, com uma chave por arquivo (kpis.sql -> "kpis").

As consultas são agregação fina sobre os marts; regra de negócio nova vai para um model do dbt, não
para cá. Roda no deploy do site (dbt-docs.yml) com a credencial só leitura do CI. Credencial por
variável de ambiente, nunca em argumento:
  SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PRIVATE_KEY (PEM, conteúdo do .p8)
  SNOWFLAKE_ROLE (padrão DBT_CI_ROLE), SNOWFLAKE_WAREHOUSE (padrão CRM_LAKEHOUSE_WH)
"""
import argparse
import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import snowflake.connector
from cryptography.hazmat.primitives import serialization

REPO_DIR = Path(__file__).resolve().parent.parent


def connect():
    private_key = serialization.load_pem_private_key(
        os.environ["SNOWFLAKE_PRIVATE_KEY"].encode(), password=None
    )
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key=private_key,
        role=os.environ.get("SNOWFLAKE_ROLE", "DBT_CI_ROLE"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "CRM_LAKEHOUSE_WH"),
        database="CRM_LAKEHOUSE",
    )


def to_json_value(value):
    # Decimal vira float (o painel só formata, não soma centavo); datas em ISO
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def run_query(cursor, sql_path):
    cursor.execute(sql_path.read_text())
    # Snowflake devolve alias sem aspas em maiúsculas: o JSON usa snake_case minúsculo
    columns = [col[0].lower() for col in cursor.description]
    return [
        {col: to_json_value(val) for col, val in zip(columns, row)}
        for row in cursor.fetchall()
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--queries", type=Path, default=REPO_DIR / "portfolio" / "queries")
    parser.add_argument("--out", type=Path, default=REPO_DIR / "site" / "data" / "dashboard.json")
    args = parser.parse_args()

    sql_files = sorted(args.queries.glob("*.sql"))
    if not sql_files:
        raise SystemExit(f"nenhuma consulta em {args.queries}")

    data = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    with connect() as conn, conn.cursor() as cursor:
        for sql_path in sql_files:
            data[sql_path.stem] = run_query(cursor, sql_path)
            print(f"{sql_path.stem}: {len(data[sql_path.stem])} linha(s)")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"gravado em {args.out}")


if __name__ == "__main__":
    main()
