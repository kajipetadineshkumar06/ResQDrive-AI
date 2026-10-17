# Initial admin bootstrap

The public admin-creation route is protected by an active admin token. The first
admin is created separately with the one-time command below; the API does not
create an admin during startup.

1. Provision the database schema through the normal reviewed deployment process.
2. In a private management shell, explicitly set `ADMIN_BOOTSTRAP_ENABLED=true`.
   The setting defaults to `false` (including when `APP_ENV=production`).
3. From the `backend` directory, run
   `venv\Scripts\python.exe -m admin_bootstrap`.
4. Enter the initial admin name and email. The command prompts for the password
   without echoing it and asks for confirmation. Choose a password of at least
   12 characters.
5. The command refuses to proceed if any admin row already exists. After it
   succeeds, unset the setting or set it to `false` before running the API.

There is no bootstrap secret: authorization is explicit operator execution of
the management command plus the temporary enable switch. The enable switch does
not create an API endpoint. Keep it unset or false in the API service.

The model maps `admins.password` as `VARCHAR(255)`, which accommodates the
project's PBKDF2 hash. Before production bootstrap, verify the deployed schema
using an authorized database console (do not query or export admin records):

```sql
SELECT CHARACTER_MAXIMUM_LENGTH
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'admins'
  AND COLUMN_NAME = 'password';
```

The returned length must be at least 255 to match the model. If it is shorter,
stop and prepare a reviewed migration before creating or upgrading admin
passwords. This command does not inspect or modify the production database.
