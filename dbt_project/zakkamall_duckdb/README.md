Welcome to your new dbt project!

### Using the starter project

Try running the following commands:
- dbt run
- dbt test


### dbt codegen

packages.yml
```
packages:
  - package: dbt-labs/dbt_utils
    version: 1.4.1
  - package: dbt-labs/codegen
    version: 0.14.1
```

packages.yml編集後、下記の順で実行する。

```bash
TABLES=$(python -c "import duckdb,json; c=duckdb.connect('dbt_demo.duckdb',read_only=True); print(json.dumps([r[0] for r in c.sql(\"select table_name from information_schema.tables where table_schema='zakka_mall' order by 1\").fetchall()]))")
```

```bash
dbt --quiet run-operation generate_source --args "{\"schema_name\": \"zakka_mall\", \"generate_columns\": true, \"include_descriptions\": true, \"table_names\": $TABLES}" > "models/staging/_zakka_mall__models.yml"
```
