"""SQL query repositories — thin per-entity modules (monorepo proposal tree).

Each function takes an open `sqlite3.Connection`; `SQLDatabaseManager`
supplies connections and orchestration. Rows map explicitly to core entities
(no bare dicts leak into services when an entity exists).
"""