## General Guidelines

1. Do not overengineer.
2. The statements in `/backend/database/schema.sql` should be idempotent like using `IF NOT EXISTS` for table/index create statements.
