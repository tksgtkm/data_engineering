uv python list --only-installed
uv run python --version
uv python install 3.12
uv venv --python 3.12
source .venv/bin/activate
uv pip install dbt-duckdb
dbt --version
dbt init sql_patterns

dbt run

dbt --quiet run-operation codegen.generate_model_yaml \
  --args '{"model_names": ["comments", "users", "votes", "posts_answers", "post_history", "posts_questions"], "upstream_descriptions": true}' \
  > models/bronze/_bronze.yml

duckdb sqlpatterns.duckdb < sql_code_list/list_1_1.sql