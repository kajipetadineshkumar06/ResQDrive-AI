# Staging migration checklist

Use this checklist only in a separately approved, disposable MySQL staging environment. The proposed `000_core_schema_baseline.sql` and existing `001_agent_events.sql` have not been executed or verified against MySQL. Do not use production credentials or data.

## Before testing

- [ ] Confirm the target is an empty, disposable MySQL database for the fresh-install test. Use a dedicated least-privilege staging account with only the permissions needed to create the reviewed tables, indexes, and foreign keys.
- [ ] Confirm the project configuration names: `DATABASE_URL`, or `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME`. Supply staging-only values through the approved secret store or local backend environment; do not put credentials in this checklist, shell history, or logs.
- [ ] Keep `AUTO_CREATE_TABLES` disabled. The project has no migration runner documented; apply no application startup command as a substitute for migrations.
- [ ] For an existing-schema test, take a consistent backup, restore it to a separate disposable staging database, and verify the restore before testing.
- [ ] Record the staging server version and settings. Using the approved MySQL client or console, these read-only queries report server defaults:

```sql
SELECT VERSION() AS mysql_version,
       @@default_storage_engine AS default_storage_engine,
       @@character_set_server AS server_charset,
       @@collation_server AS server_collation,
       @@sql_mode AS sql_mode;
```

After the schema is created, inspect actual table engine, row format, and collation:

```sql
SELECT TABLE_NAME, ENGINE, ROW_FORMAT, TABLE_COLLATION
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
ORDER BY TABLE_NAME;
```

## Fresh, empty database test

1. Confirm the database contains no application tables. Test only a genuinely empty database.
2. Review `000_core_schema_baseline.sql` for the target server before applying it. It is proposed to create 15 ORM tables; it does not create `agent_events`.
3. Apply the exact reviewed `000_core_schema_baseline.sql` using approved staging MySQL tooling. Do not infer an execution command from the application: no project migration runner is documented.
4. Verify its result before continuing. Check all table definitions, columns, nullability, defaults, primary keys, unique rules, indexes, and foreign keys against the ORM and plan. In particular:
   - Confirm the unique index on `users.email` (`VARCHAR(255)`) fits the target MySQL version, storage engine, charset, and row format.
   - Confirm the target supports the `JSON` columns and the emitted `DEFAULT now()` expressions.
   - Confirm the tables use an engine that enforces foreign keys and record the actual charset/collation; the ORM does not declare engine or charset.
   - Confirm every foreign-key parent exists first and all expected indexes and constraints were created.
5. Only after `000` passes inspection, apply the existing `001_agent_events.sql`. It should create `agent_events` after its four parent tables exist. Check its four nullable foreign keys and `ON DELETE SET NULL` rules, two composite indexes, and declared InnoDB/utf8mb4 settings. `IF NOT EXISTS` does not repair drift.
6. Verify the expected fresh result: 16 ORM tables total, including `agent_events`, no application data inserted, and schema metadata consistent with the reviewed files. Do not call this a successful MySQL test until it has actually been performed in staging.

Useful read-only checks after applying the scripts:

```sql
SHOW CREATE TABLE users;
SHOW CREATE TABLE service_requests;
SHOW CREATE TABLE agent_events;

SELECT INDEX_NAME, NON_UNIQUE, COLUMN_NAME, SEQ_IN_INDEX
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'users'
  AND COLUMN_NAME = 'email';

SELECT COUNT(*) AS duplicate_email_groups
FROM (
    SELECT email
    FROM users
    GROUP BY email
    HAVING COUNT(*) > 1
) AS duplicate_groups;

SELECT TABLE_NAME, CONSTRAINT_NAME, COLUMN_NAME,
       REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE CONSTRAINT_SCHEMA = DATABASE()
  AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME, CONSTRAINT_NAME, ORDINAL_POSITION;
```

The email check reports duplicate group count only, not email values. Inspect `SHOW CREATE TABLE` and information schema output locally; do not include personal data or credentials in shared logs.

## Existing database adoption (separate path)

- [ ] Do not treat an existing database as empty. Inspect its schema and confirm migration history from a reliable ledger or deployment records before selecting a migration.
- [ ] If history is absent or unreliable, stop. Produce a documented schema comparison and obtain explicit approval for a baseline/adoption procedure before any migration runs.
- [ ] Never retroactively apply or record `000_core_schema_baseline.sql` after `001_agent_events.sql` has already been applied. Do not rerun `001` to repair drift. Select only a reviewed forward migration after the latest confirmed migration; stop if that state is unknown.
- [ ] Compare the restored staging schema with the ORM and proposed target. Check existing foreign-key orphans, unique-key duplicates, nulls, types, engine, charset, row format, indexes, and constraint names before preparing any forward change.
- [ ] Migration execution remains blocked until the deployed schema, migration history, target MySQL settings, and unresolved table/constraint questions have been verified in disposable staging.

## Expected results, failure handling, and rollback

- [ ] Save the pre-test schema metadata and row counts. After testing, compare `SHOW CREATE TABLE` and `information_schema` metadata with the approved expected schema. Verify foreign-key integrity, uniqueness, and unchanged row counts for an existing-schema copy.
- [ ] On any unexpected warning, error, missing constraint, or type/default difference, stop. Record the error without secrets, preserve the staging copy for investigation, and do not proceed to another environment.
- [ ] MySQL DDL may implicitly commit; do not rely on transaction rollback. For a failed fresh-database test, discard and recreate only the disposable empty staging database through the approved operator process, then restart from the reviewed sequence.
- [ ] For an existing-schema test, restore the verified backup to a separate recovery target or use a reviewed compensating migration. Do not run destructive rollback SQL or automatic inverse migrations against production. Reverify schema and row counts after recovery.

No database has been created or contacted as part of preparing this checklist.
