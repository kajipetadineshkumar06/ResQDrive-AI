# ResQDrive AI schema migration plan

## Scope and evidence

This is a planning document accompanying the proposed fresh-database baseline `database/sql/migrations/000_core_schema_baseline.sql`. The proposed SQL was generated offline from the SQLAlchemy model classes and has not been executed or verified against a MySQL server; no database was contacted. The inventory is based on `backend/models/`, `backend/database.py`, and the pre-existing `database/sql/migrations/001_agent_events.sql` in this checkout.

The model inventory defines 16 tables. Before this proposal, the only existing migration file was for `agent_events`; the proposed `000` baseline now covers the other 15 model tables for a fresh database only. A search of `backend/` and `database/` found no Alembic configuration or migration runner; the repository has SQL migration files, not a complete migration framework. Confirm whether deployment tooling outside those directories tracks applied migration versions before choosing the final tracking process.

### Reading the model inventory

- `PK` means the model declares a primary key. Integer primary keys are expected to auto-increment under the MySQL dialect, but the models do not set `autoincrement` explicitly; verify the emitted MySQL DDL.
- `NN` means `nullable=False` is explicit or the column is a primary key. `NULL` means explicitly nullable. `NULL*` means `nullable` is omitted; SQLAlchemy normally treats a non-primary-key `Column` as nullable in that case. Verify actual DDL, especially for a deployed schema.
- Defaults are identified as `Python default` (applied by SQLAlchemy when inserting) or `server default` (database-side). No default is inferred when none is shown.
- `index=True` is recorded where declared. Primary keys are indexed by the database; verify whether the model also emits a redundant secondary index for a primary key marked `index=True`.
- A foreign key without an explicit `ondelete` has no delete action specified in the model. The resulting database behavior must be verified; do not assume cascade behavior.

## ORM tables and columns

Types below are the SQLAlchemy types as declared in source; exact MySQL physical types, enum representation, timestamp behavior, charset, collation, and engine must be confirmed against generated DDL and the target MySQL version.

### `admins` — `backend/models/admin.py`

| Column | Type | Nullability | Keys / rules | Default |
|---|---|---|---|---|
| `admin_id` | `Integer` | PK / NN | `primary_key=True`, `index=True` | MySQL auto-increment inferred; verify |
| `name` | `String(100)` | NN | — | — |
| `email` | `String(100)` | NN | unique | — |
| `password` | `String(255)` | NN | — | — |
| `is_active` | `Boolean` | `NULL*` | — | Python `True` |
| `created_at` | `TIMESTAMP` | `NULL*` | — | server `func.now()` |

The model's 255-character password width is not evidence of the deployed column width. Verify the actual staging/deployed definition before relying on current or future password hashes.

### `agent_events` — `backend/models/agent_event.py`

| Column | Type | Nullability | Keys / rules | Default |
|---|---|---|---|---|
| `event_id` | `Integer` | PK / NN | primary key; no separate `index=True` in model | MySQL auto-increment inferred; verify |
| `emergency_id` | `Integer` | NULL | FK → `emergencies.emergency_id`, `ON DELETE SET NULL` | — |
| `request_id` | `Integer` | NULL | FK → `service_requests.request_id`, `ON DELETE SET NULL` | — |
| `actor_user_id` | `Integer` | NULL | FK → `users.user_id`, `ON DELETE SET NULL` | — |
| `provider_id` | `Integer` | NULL | FK → `service_providers.provider_id`, `ON DELETE SET NULL` | — |
| `event_type` | `String(80)` | NN | — | — |
| `event_status` | `String(30)` | NN | — | Python `"recorded"`; server `"recorded"` |
| `details` | `JSON` | NULL | — | — |
| `created_at` | `DateTime` | NN | — | server `CURRENT_TIMESTAMP` |

Model indexes: `ix_agent_events_emergency_created (emergency_id, created_at)` and `ix_agent_events_request_created (request_id, created_at)`.

### `coupons` — `backend/models/coupon.py`

| Column | Type | Nullability | Keys / rules | Default |
|---|---|---|---|---|
| `coupon_id` | `Integer` | PK / NN | primary key, `index=True` | MySQL auto-increment inferred; verify |
| `coupon_code` | `String(50)` | NN | unique | — |
| `description` | `String(255)` | NULL* | — | — |
| `discount_type` | `Enum('percentage', 'fixed')` | NN | enum name `coupon_discount_type` | — |
| `discount_value` | `DECIMAL(10, 2)` | NN | — | — |
| `minimum_amount` | `DECIMAL(10, 2)` | NULL* | — | Python `0` |
| `maximum_discount` | `DECIMAL(10, 2)` | NULL | — | — |
| `expiry_date` | `DateTime` | NN | — | — |
| `is_active` | `Boolean` | NULL* | — | Python `True` |
| `created_at` | `TIMESTAMP` | NULL* | — | server `func.now()` |

### `emergencies` — `backend/models/emergency.py`

| Column | Type | Nullability | Keys / rules | Default |
|---|---|---|---|---|
| `emergency_id` | `Integer` | PK / NN | primary key, `index=True` | MySQL auto-increment inferred; verify |
| `user_id` | `Integer` | NN | FK → `users.user_id` | — |
| `vehicle_id` | `Integer` | NULL | FK → `vehicles.vehicle_id` | — |
| `emergency_type` | `String(100)` | NN | — | — |
| `description` | `String(500)` | NULL | — | — |
| `location_lat` | `Float` | NN | — | — |
| `location_lng` | `Float` | NN | — | — |
| `status` | `String(30)` | NULL* | — | Python `"Pending"` |
| `priority` | `String(20)` | NULL* | — | Python `"Medium"` |
| `recommended_service` | `String(100)` | NULL | — | — |
| `created_at` | `TIMESTAMP` | NULL* | — | server `func.now()` |
| `resolved_at` | `TIMESTAMP` | NULL | — | — |

### `fcm_tokens` — `backend/models/fcm_token.py`

| Column | Type | Nullability | Keys / rules | Default |
|---|---|---|---|---|
| `token_id` | `Integer` | PK / NN | primary key, `index=True` | MySQL auto-increment inferred; verify |
| `user_id` | `Integer` | NN | FK → `users.user_id`; unique | — |
| `token` | `String(500)` | NN | unique | — |

### `invoices` — `backend/models/invoice.py`

| Column | Type | Nullability | Keys / rules | Default |
|---|---|---|---|---|
| `invoice_id` | `Integer` | PK / NN | primary key, `index=True` | MySQL auto-increment inferred; verify |
| `payment_id` | `Integer` | NN | FK → `payments.payment_id` | — |
| `invoice_number` | `String(100)` | NN | unique | — |
| `invoice_date` | `TIMESTAMP` | NULL* | — | server `func.now()` |
| `total_amount` | `DECIMAL(10, 2)` | NN | — | — |
| `tax_amount` | `DECIMAL(10, 2)` | NULL* | — | Python `0.0` |
| `discount_amount` | `DECIMAL(10, 2)` | NULL* | — | Python `0.0` |
| `final_amount` | `DECIMAL(10, 2)` | NN | — | — |
| `pdf_path` | `String(255)` | NULL | — | — |

### `notifications` — `backend/models/notification.py`

| Column | Type | Nullability | Keys / rules | Default |
|---|---|---|---|---|
| `notification_id` | `Integer` | PK / NN | primary key, `index=True` | MySQL auto-increment inferred; verify |
| `user_id` | `Integer` | NN | FK → `users.user_id` | — |
| `emergency_id` | `Integer` | NULL | FK → `emergencies.emergency_id` | — |
| `provider_id` | `Integer` | NULL | FK → `service_providers.provider_id` | — |
| `title` | `String(255)` | NN | — | — |
| `message` | `String(500)` | NN | — | — |
| `status` | `String(30)` | NN | — | Python `"sent"`; server `"sent"` |
| `created_at` | `DateTime` | NN | — | server `CURRENT_TIMESTAMP` |

### `payments` — `backend/models/payment.py`

| Column | Type | Nullability | Keys / rules | Default |
|---|---|---|---|---|
| `payment_id` | `Integer` | PK / NN | primary key, `index=True` | MySQL auto-increment inferred; verify |
| `request_id` | `Integer` | NN | FK → `service_requests.request_id` | — |
| `user_id` | `Integer` | NN | FK → `users.user_id` | — |
| `amount` | `DECIMAL(10, 2)` | NN | — | — |
| `payment_method` | `Enum('upi', 'card', 'cash', 'wallet')` | NULL* | — | Python `"upi"` |
| `payment_status` | `Enum('pending', 'success', 'failed', 'refunded')` | NULL* | — | Python `"pending"` |
| `transaction_id` | `String(100)` | NULL | — | — |
| `invoice_number` | `String(100)` | NULL | no FK or uniqueness declared | — |
| `paid_at` | `TIMESTAMP` | NULL | — | — |
| `created_at` | `TIMESTAMP` | NULL* | — | server `func.now()` |

### `provider_locations` — `backend/models/provider_location.py`

| Column | Type | Nullability | Keys / rules | Default |
|---|---|---|---|---|
| `location_id` | `Integer` | PK / NN | primary key, `index=True` | MySQL auto-increment inferred; verify |
| `provider_id` | `Integer` | NN | FK → `service_providers.provider_id` | — |
| `latitude` | `DECIMAL(10, 7)` | NN | — | — |
| `longitude` | `DECIMAL(10, 7)` | NN | — | — |
| `updated_at` | `TIMESTAMP` | NULL* | — | server `func.now()` |

The model also declares ORM-side `onupdate=func.now()` behavior for this column. The baseline intentionally does not add a database-level `ON UPDATE` clause; updates rely on SQLAlchemy-issued update behavior.

### `providers` — `backend/models/provider.py`

| Column | Type | Nullability | Keys / rules | Default |
|---|---|---|---|---|
| `provider_id` | `Integer` | PK / NN | primary key, `index=True` | MySQL auto-increment inferred; verify |
| `provider_name` | `String(100)` | NN | — | — |
| `service_type` | `String(50)` | NN | — | — |
| `phone` | `String(15)` | NN | — | — |
| `email` | `String(100)` | NULL* | no uniqueness declared | — |
| `latitude` | `DECIMAL(10, 7)` | NN | — | — |
| `longitude` | `DECIMAL(10, 7)` | NN | — | — |
| `city` | `String(100)` | NULL* | — | — |
| `rating` | `DECIMAL(2, 1)` | NULL* | — | Python `5.0` |
| `availability` | `Boolean` | NULL* | — | Python `True` |
| `created_at` | `TIMESTAMP` | NULL* | — | server `func.now()` |

This is a separate `providers` table. No ORM foreign key connects it to `service_providers`; whether it is legacy or still used requires verification in application services and the target database.

### `ratings` — `backend/models/rating.py`

| Column | Type | Nullability | Keys / rules | Default |
|---|---|---|---|---|
| `rating_id` | `Integer` | PK / NN | primary key, `index=True` | MySQL auto-increment inferred; verify |
| `request_id` | `Integer` | NULL* | FK → `service_requests.request_id` | — |
| `user_id` | `Integer` | NULL* | FK → `users.user_id` | — |
| `provider_id` | `Integer` | NULL* | FK → `service_providers.provider_id` | — |
| `rating_value` | `Integer` | NULL* | — | — |
| `review_text` | `Text` | NULL* | — | — |
| `created_at` | `TIMESTAMP` | NULL* | — | server `func.now()` |

### `service_providers` — `backend/models/service_provider.py`

| Column | Type | Nullability | Keys / rules | Default |
|---|---|---|---|---|
| `provider_id` | `Integer` | PK / NN | primary key, `index=True` | MySQL auto-increment inferred; verify |
| `name` | `String(100)` | NN | — | — |
| `service_type` | `String(50)` | NN | — | — |
| `phone` | `String(20)` | NN | — | — |
| `location_lat` | `Numeric(10, 7)` | NULL | — | — |
| `location_lng` | `Numeric(10, 7)` | NULL | — | — |
| `rating_avg` | `Numeric(3, 2)` | NN | — | Python `0.0` |
| `is_available` | `Boolean` | NN | — | Python `True` |
| `provider_image` | `String(255)` | NULL | — | — |
| `experience_years` | `Integer` | NULL | — | — |
| `verified` | `Boolean` | NN | — | Python `False` |
| `created_at` | `DateTime` | NULL | — | — |
| `is_tracking` | `Boolean` | NN | — | Python `False` |
| `user_id` | `Integer` | NULL | named FK `fk_provider_user` → `users.user_id` | — |

The `User.service_provider` relationship declares `uselist=False`, but `service_providers.user_id` has no `unique=True` or unique constraint in this model. The one-to-one relationship is therefore not enforced by the model's database constraints; decide whether existing data and product rules require a unique constraint before proposing one.

### `service_requests` — `backend/models/service_request.py`

| Column | Type | Nullability | Keys / rules | Default |
|---|---|---|---|---|
| `request_id` | `Integer` | PK / NN | primary key, `index=True` | MySQL auto-increment inferred; verify |
| `emergency_id` | `Integer` | NN | FK → `emergencies.emergency_id` | — |
| `provider_id` | `Integer` | NULL | FK → `service_providers.provider_id` | — |
| `excluded_provider_ids` | `MutableList` over `JSON` | NULL | — | Python `list` factory |
| `user_id` | `Integer` | NN | FK → `users.user_id` | — |
| `request_status` | `String(50)` | NN | — | Python `"pending"` |
| `estimated_arrival` | `Integer` | NULL | — | — |
| `notes` | `String(500)` | NULL | — | — |
| `requested_at` | `DateTime` | NULL* | — | server `func.now()` |
| `accepted_at` | `DateTime` | NULL | — | — |
| `started_at` | `DateTime` | NULL | — | — |
| `arrived_at` | `DateTime` | NULL | — | — |
| `completed_at` | `DateTime` | NULL | — | — |
| `cancelled_at` | `DateTime` | NULL | — | — |

### `sos_alerts` — `backend/models/sos_alert.py`

| Column | Type | Nullability | Keys / rules | Default |
|---|---|---|---|---|
| `alert_id` | `Integer` | PK / NN | primary key, `index=True` | MySQL auto-increment inferred; verify |
| `user_id` | `Integer` | NN | FK → `users.user_id` | — |
| `latitude` | `DECIMAL(10, 7)` | NN | — | — |
| `longitude` | `DECIMAL(10, 7)` | NN | — | — |
| `status` | `Enum('sent', 'received', 'acknowledged')` | NULL* | — | Python `"sent"` |

### `users` — `backend/models/user.py`

| Column | Type | Nullability | Keys / rules | Default |
|---|---|---|---|---|
| `user_id` | `Integer` | PK / NN | primary key, `index=True` | MySQL auto-increment inferred; verify |
| `full_name` | `String(100)` | NN | — | — |
| `email` | `String(255)` | NN | unique and `index=True` | — |
| `phone` | `String(20)` | NULL | — | — |
| `password_hash` | `String(255)` | NN | — | — |
| `created_at` | `DateTime` | NULL* | — | Python `datetime.utcnow` |

The Python-side `created_at` default is not a database server default. The relationship to `ServiceProvider` sets `uselist=False`, but no uniqueness rule is declared on `service_providers.user_id` (see above).

### `vehicles` — `backend/models/vehicle.py`

| Column | Type | Nullability | Keys / rules | Default |
|---|---|---|---|---|
| `vehicle_id` | `Integer` | PK / NN | primary key, `index=True` | MySQL auto-increment inferred; verify |
| `user_id` | `Integer` | NN | FK → `users.user_id` | — |
| `plate_number` | `String(50)` | NN | — | — |
| `make` | `String(100)` | NN | — | — |
| `model` | `String(100)` | NN | — | — |
| `year` | `Integer` | NN | — | — |
| `vehicle_type` | `String(50)` | NULL | — | — |
| `fuel_type` | `String(50)` | NULL | — | — |
| `vehicle_color` | `String(50)` | NULL | — | — |

## Indexes, uniqueness, and relationships

- Column-level unique rules: `admins.email`; `coupons.coupon_code`; both `fcm_tokens.user_id` and `fcm_tokens.token`; `invoices.invoice_number`; `users.email`.
- Explicit non-primary indexes: `index=True` on the model's ID columns (all listed tables except `agent_events.event_id`) and `users.email`; the two named composite indexes on `agent_events` are listed above. Confirm actual emitted index names and whether redundant indexes exist.
- Foreign keys: all are listed with their owning columns above. Only the four `agent_events` FKs specify `ON DELETE SET NULL`; other FK delete behavior is unspecified in model source.
- ORM relationships describe object navigation, not extra columns or constraints. In particular, `uselist=False` does not by itself create a uniqueness constraint.
- No additional `CheckConstraint`, table-level `UniqueConstraint`, or composite `ForeignKeyConstraint` was found in the inspected model classes. This does not establish that the existing database lacks such constraints.

## Existing migration comparison

The pre-existing `database/sql/migrations/001_agent_events.sql` creates `agent_events` using `CREATE TABLE IF NOT EXISTS`, an explicit `INT NOT NULL AUTO_INCREMENT` primary key, nullable event references, `VARCHAR(80)` / `VARCHAR(30)` event fields, JSON details, `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`, the two composite indexes, four named foreign keys with `ON DELETE SET NULL`, and `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4`. The new `000_core_schema_baseline.sql` is a proposed file only; it is not evidence that any database has applied it.

These columns, nullability, indexes, and delete actions align with `AgentEvent` as inspected. Integer auto-increment in the model is implicit rather than explicit. The ORM does not specify the migration's engine or charset. The SQL file is not a migration ledger and `IF NOT EXISTS` does not reconcile a pre-existing table with different columns, indexes, constraints, engine, or charset. It can silently leave drift in place.

Before this proposal, the other 15 ORM tables had no migration coverage. The proposed baseline now contains source-derived DDL for those tables, but their deployed definitions, data, and migration history remain unknown and require verification. Do not infer that any environment matches the proposal or `create_all` output.

## Foreign-key creation order

For a new empty database, a topological order consistent with the model FKs is:

1. Independent tables: `admins`, `coupons`, `providers`, `users`.
2. Tables depending only on `users`: `fcm_tokens`, `sos_alerts`, `vehicles`, `service_providers`.
3. `emergencies` (depends on `users` and `vehicles`); `provider_locations` (depends on `service_providers`).
4. `service_requests` (depends on `emergencies`, `service_providers`, and `users`); `notifications` (depends on `users`, `emergencies`, and `service_providers`); `ratings` (depends on `service_requests`, `users`, and `service_providers`); `payments` (depends on `service_requests` and `users`).
5. `invoices` (depends on `payments`).
6. `agent_events` (depends on `emergencies`, `service_requests`, `users`, and `service_providers`).

Tables at the same step can be reordered if all their referenced tables already exist. This order reflects only the ORM foreign keys; any additional deployed constraints require verification.

## Proposed numbered migration sequence

The proposed `000_core_schema_baseline.sql` has been created in this candidate using SQLAlchemy 2.0.51's MySQL dialect compiler; it has not been executed or verified against a server. No other migration script has been created, and the existing `001_agent_events.sql` remains unchanged. Preserve its number and contents.

**Migration execution is currently blocked.** Before running the proposed baseline or any upgrade migration, verify the deployed schema and migration history, confirm the target MySQL version/settings, and resolve the open table/constraint questions in a disposable staging environment. For a fresh database, verify its target MySQL settings and the proposed DDL in disposable staging first. This document and SQL file are proposals, not approval to execute DDL.

### Fresh database

This sequence applies only to a genuinely new, empty database after its MySQL version/settings and generated schema have been reviewed in disposable staging. It does not claim that any step has been executed or verified.

1. **`000_core_schema_baseline.sql` (proposed file, not executed or verified):** create the 15 ORM tables other than `agent_events` in the dependency order above. The DDL is generated from the models with SQLAlchemy 2.0.51's MySQL dialect; Python-side defaults are not turned into server defaults. The ORM does not specify table engine or charset, so the file omits them. **REQUIRES VERIFICATION:** target MySQL version and SQL mode, JSON support, generated `NOW()` defaults, and the engine/charset policy. The existing migration specifies InnoDB/utf8mb4 for `agent_events`; that alone does not establish the policy for every table. The baseline must not seed production or synthetic customer data.
2. **`001_agent_events.sql` (existing):** after its parent tables exist, apply this existing migration in the fresh-database sequence. Its behavior has not been tested here; review and test it in disposable staging first. `CREATE TABLE IF NOT EXISTS` does not reconcile schema drift.
3. **`002_schema_reconciliation.sql` (conditional, proposed):** create only if staging comparison establishes an approved difference that is not already handled by the baseline. Do not author it until each alteration is supported by verified schema evidence.
4. **A later data-backfill migration (conditional):** create only if source behavior and staging data demonstrate a necessary transformation. Document a data-preserving mapping and row-level pre/post checks first; otherwise do not create one.

The proposed `000` baseline keeps the existing `001` file unchanged and creates its foreign-key parents first. Confirm migration naming and tracking conventions before authoring any additional scripts.

### Existing database upgrade (separate from the fresh-database sequence)

1. Inspect the actual database schema and confirm migration history from a reliable ledger or deployment records, then reconcile that history with the actual schema. Treat the database as populated unless inspection proves otherwise. The repository contains no migration ledger. A filename or existing table alone does not prove whether a migration was applied.
2. If migration history is absent or unreliable, do not run a migration yet. First produce a documented schema-to-ORM comparison, identify which legacy migrations are already reflected in the database, and obtain explicit approval for a baseline/adoption procedure that records that starting state.
3. Never retroactively apply or record `000_core_schema_baseline.sql` after `001_agent_events.sql` has already been applied. Use `000` only for a genuinely fresh database. For an existing database, select a new forward-only migration number strictly after the latest migration whose application is confirmed; if the latest state cannot be established, stop until the adoption procedure is approved.
4. Before any approved DDL, take and restore-test a full backup in an isolated environment. Compare every table with the ORM and proposed target; identify orphaned FK values, duplicate values that conflict with unique rules, nulls in columns that may become `NOT NULL`, and incompatible types. Resolve each with an approved data-preserving plan.
5. Apply only a reviewed forward migration containing changes supported by that comparison. Do not run the fresh-database baseline against an existing schema. If `001_agent_events.sql` is confirmed unapplied, review its exact table and parent definitions in staging before selecting it; if already applied, do not rerun it as a repair operation.
6. Record the adopted starting state and every applied migration using the explicitly approved tracking process. Verify post-migration schema, constraints, and row counts in disposable staging before considering any other environment.

## Backup, dry-run, verification, and rollback

### Before authoring or applying migrations

1. Confirm target environment identity and access boundaries; use a separate disposable MySQL staging database and a dedicated least-privilege account. Never use production credentials for staging.
2. Take a consistent full backup using the database provider's snapshot/backup facility or a reviewed MySQL backup procedure appropriate to the actual table engines. Restore the backup into a separate isolated database and verify the restore before testing DDL.
3. Capture baseline schema metadata and table row counts for all 16 model tables, plus critical request/emergency/payment counts and constraints. Do not include personal records in audit output.
4. Review generated SQL and expected lock, duration, and storage impact against the actual MySQL version and data volume. MySQL DDL may implicitly commit; do not assume a transaction can roll back schema changes.

### Dry run and staging verification

There is no generic safe MySQL DDL dry run. Treat a restore of the staging backup as the dry run: apply the exact reviewed SQL only to that disposable database, capture output, inspect warnings, and test both a clean fresh database and a copy of the existing schema. No such database test was performed for this document.

After staging migration, compare `SHOW CREATE TABLE` and `information_schema` columns, indexes, foreign keys, nullability, defaults, engine, charset, and collation against the approved baseline. Verify each FK has no orphan rows; each proposed unique key has no duplicates; each tightened non-null column has no nulls; and before/after row counts match except for a separately approved backfill. Specifically verify `admins.password` is wide enough for the stored hash format (the ORM declares `VARCHAR(255)`) and that all service-request, emergency, payment, and identity rows remain present. Verify the unique `users.email` index on `VARCHAR(255)` against the target MySQL version, storage engine, charset, and row format; confirm its full index length is supported by that configuration. Run application smoke tests against staging with automatic table creation disabled.

### Rollback and recovery

Prefer additive changes and forward-fix scripts. For any step that drops, truncates, overwrites, or irreversibly converts data, require a separately reviewed restore plan before applying it. If a migration fails, stop dependent rollout, preserve logs without secrets, inspect actual DDL state, and restore the verified backup to a separate recovery target or apply a reviewed compensating migration. Do not run an automatic inverse migration that may discard data. Validate the recovered schema and data before redirecting application traffic.

## Startup and configuration notes

`backend/database.py` loads local configuration and creates the SQLAlchemy engine/session; it defines the `get_db` session dependency. It reads `DATABASE_URL` or the component variables `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME`. This document records names only; configure separate staging values through the deployment secret store or the local backend environment file, and never copy production credentials into staging.

`backend/deployment_config.py` sets `AUTO_CREATE_TABLES` to disabled by default and rejects enabling it when production mode is detected. `backend/main.py` calls `Base.metadata.create_all(bind=engine)` only when that guard returns true. When disabled, startup does not create or update ORM tables; an externally provisioned schema must already exist. Keep this setting disabled in production and use reviewed migrations instead.

## Unresolved questions requiring verification

- **Requires verification:** actual staging/deployed MySQL version, engine, charset, collation, SQL mode, and timestamp/time-zone behavior.
- **Requires verification:** actual definitions, indexes, constraints, row counts, and migration history for all tables; production compatibility is not established by model inspection.
- **Requires verification:** whether `001_agent_events.sql` has been applied in any existing environment and whether its table has drifted.
- **Requires verification:** actual `admins.password` column width and all existing stored formats; model source only declares `String(255)`.
- **Requires verification:** whether the separate `providers` table is still used and whether it contains data that must be retained or migrated.
- **Requires verification:** whether `service_providers.user_id` must be unique to enforce the ORM's one-to-one relationship; do not add uniqueness until current data and business rules are checked.
- **Requires verification:** whether the current implicit nullable columns and Python-only defaults match application expectations and historical data.
- **Requires verification:** whether additional tables or constraints are created outside the inspected ORM models and migration directory.
- **Requires verification:** which migration ledger/process deployment will use, who approves migration execution, and the tested restore/rollback procedure.

The proposed `000_core_schema_baseline.sql` was created for review only; no migration was executed, no database was contacted, and automatic table creation was not enabled.
