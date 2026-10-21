# Windows setup for disposable MySQL staging

**Preparation only. Migration execution is blocked until the staging database is confirmed disposable and the project owner explicitly approves testing.** Neither migration has been run or verified on MySQL. Do not use production credentials or data.

## Prepare an isolated instance and empty database

1. Use a dedicated local MySQL instance or an approved isolated staging instance. Never point these steps at production. If MySQL or its client is not already available, stop and arrange an approved staging environment; this guide does not install software.
2. In PowerShell, identify an existing client or local service. These commands only inspect the machine:

   ```powershell
   Get-Command mysql.exe -ErrorAction SilentlyContinue
   Get-Service | Where-Object { $_.Name -match 'mysql' -or $_.DisplayName -match 'mysql' } | Select-Object Name, DisplayName, Status
   ```

   Do not start a service as part of preparation. Later, after approval, start only the service confirmed to be disposable, using Windows Services or the administrator's approved procedure.
3. After approval, connect to the confirmed staging instance with its approved MySQL client. This PowerShell command template prompts for the password instead of placing it in the command line; replace the quoted placeholders first:

   ```powershell
   mysql.exe --host "<STAGING_HOST>" --port "<STAGING_PORT>" --user "<STAGING_ADMIN_USER>" --password
   ```

4. Have the staging administrator create a **new, separate, empty** database using an approved charset and collation for the target MySQL version. Replace placeholders before use; they are not literal SQL. Do not assume the production or server defaults are appropriate:

   ```sql
   CREATE DATABASE `<STAGING_DATABASE>`
     CHARACTER SET <APPROVED_CHARSET>
     COLLATE <APPROVED_COLLATION>;
   ```

5. Have the administrator create a dedicated staging migration account, with only the permissions needed for the reviewed DDL and schema inspection, scoped to this staging database. Do not use `GRANT ALL` or reuse a production account. Store its values only in the approved secret store or local backend environment.
6. Confirm the database is empty before any future fresh-install test:

   ```sql
   SELECT COUNT(*) AS base_table_count
   FROM information_schema.TABLES
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_TYPE = 'BASE TABLE';
   ```

   Expected result for the fresh-install starting point: `0`.

The backend reads either `DATABASE_URL` or `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME`. When using `DATABASE_URL`, use the project's SQLAlchemy/PyMySQL URL scheme `mysql+pymysql://...`, as configured in `backend/database.py`; use placeholders only in documentation. The `mysql.exe` commands below use administrative client flags and do not take a SQLAlchemy URL. For any later staging-only application check, configure the supported names in the backend's separate local environment using placeholders such as `<STAGING_HOST>` and `<STAGING_PASSWORD>`. Do not copy production values. `AUTO_CREATE_TABLES` must remain disabled. The frontend's `VITE_API_URL` is not needed for migration checks. Do not put real credentials, API keys, or JWT secrets in this document.

## Check MySQL compatibility before migrations

Run these read-only checks only after an approved connection to the disposable staging instance. Record results without credentials or personal data:

```sql
SELECT VERSION() AS mysql_version,
       @@default_storage_engine AS default_storage_engine,
       @@character_set_server AS server_charset,
       @@collation_server AS server_collation,
       @@sql_mode AS sql_mode;
```

After tables exist, confirm each actual table engine, row format, and collation. The baseline does not declare an engine or charset; `001_agent_events.sql` declares InnoDB and utf8mb4 for `agent_events` only.

```sql
SELECT TABLE_NAME, ENGINE, ROW_FORMAT, TABLE_COLLATION
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
ORDER BY TABLE_NAME;
```

Before proceeding, explicitly verify all of the following against the selected version and settings:

- Before migration `000` in the fresh-install path, verify that the planned unique index on `users.email VARCHAR(255)` fits the target MySQL version, storage engine, charset, and row format, including its maximum index-key length. After migration `000`, inspect the created column definition and actual unique-index metadata; confirm the index is unique (`NON_UNIQUE` is `0`). For existing-database adoption, inspect the actual schema only after confirming the database identity and migration history.
- The target supports the `JSON` columns and the generated `DEFAULT now()` expressions. Inspect `SHOW CREATE TABLE` output after a future staging run, including `service_requests` for JSON and a `now()` default.
- Tables use an engine that enforces foreign keys, and the chosen charset/collation policy is recorded and consistent with the intended deployment.
- Every expected foreign key, delete rule, primary key, unique rule, and index exists. `001` has four nullable foreign keys with `ON DELETE SET NULL` and two composite indexes.

Example read-only metadata checks for later staging use:

```sql
SELECT COLUMN_TYPE, CHARACTER_MAXIMUM_LENGTH, CHARACTER_SET_NAME, COLLATION_NAME
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'users'
  AND COLUMN_NAME = 'email';

SELECT INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME, SUB_PART
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'users'
  AND COLUMN_NAME = 'email';

SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND DATA_TYPE = 'json';

SHOW CREATE TABLE users;
SHOW CREATE TABLE service_requests;
SHOW CREATE TABLE agent_events;
```

## Fresh-install test: `000` then `001`

This path is only for the new empty staging database above. After compatibility review and explicit approval:

1. Apply the exact reviewed `database/sql/migrations/000_core_schema_baseline.sql` using approved MySQL tooling. It proposes 15 ORM tables and does not create `agent_events`.
2. Inspect the result before continuing. Stop on any error, warning, missing constraint, unexpected default, or schema difference.
3. Only after `000` passes inspection, apply the existing `database/sql/migrations/001_agent_events.sql`.
4. Verify the final schema against the models and `database/SCHEMA_MIGRATION_PLAN.md`: 16 ORM tables total, including `agent_events`; correct columns, nullability, defaults, indexes, foreign keys, and delete rules; no application data inserted.

The project has no migration runner documented. Do not start the application or substitute automatic table creation for these scripts. These instructions do not claim either migration has been tested or is production-safe.

## Existing-database adoption: separate path

Do not use the fresh-install sequence on an existing database. First compare its actual schema with the ORM and confirm migration history from a reliable ledger or deployment records. Treat it as populated. If history is missing or unreliable, stop until a documented schema comparison and an explicitly approved baseline/adoption procedure establish its starting state.

Never retroactively apply or record `000_core_schema_baseline.sql` after `001_agent_events.sql` has been applied. Do not rerun `001` to repair drift; `IF NOT EXISTS` does not reconcile an existing table. Select a reviewed forward migration only after the latest applied migration is confirmed. Migration execution remains blocked until staging identity, schema, history, MySQL settings, and unresolved constraints are verified and the owner explicitly approves the staging test.

## Backup, verification, and recovery

- For an existing-schema staging copy, take a consistent backup, restore it to a separate disposable target, and verify the restore before testing. Record pre-test schema metadata and row counts.
- Compare `SHOW CREATE TABLE` and `information_schema` metadata after the test. For an existing copy, verify row counts are unchanged and check for orphaned foreign keys, duplicate unique values, and unexpected nulls.
- On any unexpected result, stop and preserve the staging copy for review. MySQL DDL can implicitly commit, so do not rely on transaction rollback.
- For a failed fresh test, have the authorized operator discard and recreate only the confirmed disposable empty staging database, then restart after reviewing the failure. For an existing-schema test, restore the verified backup to a separate recovery target or use a reviewed compensating migration. Do not run destructive rollback steps against production.

No instance was started, database created, connection made, SQL executed, or migration run while preparing this document.
