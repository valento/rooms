# Adding a New App to Nobrain

## Architecture Overview

```sh
apps_registry (one row per app — created once by admin)
    ^
content_blocks.app_id  (one row per instance — created per poll, game, etc.)
    ^
app-specific schema (polls.polls, toto2.draws, etc. — stores instance data)
```

- **App** — a React component in the Nx monorepo (e.g. `PollsApp`, `LototechApp`)
- **Instance** — a `content_block` that represents one use of that app (e.g. "BG Elections" poll)
- **App data** — lives in the app's own schema (e.g. `polls.polls`, linked via `content_blocks.id`)

---

## Step 1 — Build the React App

In the Nx monorepo, create a new package:

```sh
# tree -d -L 3
packages/
└── my-new-app/
    └── src/
        └── MyNewApp.tsx   ← the component
```

The component must support two modes:
- **widget** — small teaser, rendered on the landing page
- **full** — full featured page, rendered at `/play/:slug`

---

## Step 2 — Create the DB Schema (if needed)

If the app needs its own data tables, create a dedicated schema:

```sql
CREATE SCHEMA my_app;
ALTER SCHEMA my_app OWNER TO admin;

-- Grant access to the API role
GRANT USAGE ON SCHEMA my_app TO web_api;
```

Create tables inside that schema. See `polls/` or `toto2/` as reference patterns.

---

## Step 3 — Register the App in `apps_registry`

This is a **one-time manual insert** by the admin. It tells Nobrain where to find the React component.

```sql
INSERT INTO company.apps_registry (package_name, component_name, route_path)
VALUES (
    '@nx-mono/my-new-app',   -- Nx package name
    'MyNewApp',              -- exported React component name
    '/play/my-new-app'       -- base route prefix
);
```

Verify:
```sql
SELECT * FROM company.apps_registry;
```

> Note: `apps_registry` no longer has a `content_id` column. It is a standalone registry.
> `content_blocks.app_id` points to it — not the other way around.

---

## Step 4 — Create App Instances via DynamicForm

Each instance is a `content_block` with `app_id` pointing to the registered app.

The admin uses the DynamicForm UI (`POST /content/`) to create instances:

| Field | Value |
|-------|-------|
| `title` | Instance name e.g. "BG Elections" |
| `slug` | URL-friendly e.g. `bg-elections` |
| `deck` | Short description for the widget teaser |
| `metadata.content_type` | `"app"` |
| `metadata.status` | `"published"` |
| `app_id` | Selected from `GET /apps-registry` dropdown |
| `widget_size` | `small` / `medium` / `large` / `xlarge` |
| `category_id` | Selected from `GET /categories` dropdown |

The DynamicForm fetches available apps from:
```
GET /apps-registry  →  dropdown list of registered apps
```

---

## Step 5 — Create the Instance Data (app-specific)

After the `content_block` is created, create the corresponding data record in the app schema.

For polls:
```
POST /polls/  →  { content_id: <new content_block id>, question: "...", poll_type: "binary" }
```

For future apps, equivalent endpoints follow the same pattern.

---

## Step 6 — Verify the Full Chain

```bash
# Check content_block exists with correct app_id
curl http://localhost:8000/content/<slug>
# Should return: package_name, component_name, route_path, app_id

# Check instance data
curl http://localhost:8000/polls/<poll_id>
```

---

## Current Registered Apps

| id | package_name | component_name | route_path |
|----|-------------|----------------|------------|
| 1 | @nx-mono/lototech | LototechApp | /play/lototech |
| 6 | @nx-mono/polls | PollsApp | /play/polls |

---

## Current App Instances

| content_block | slug | app_id | app |
|--------------|------|--------|-----|
| Lototech | lototech | 1 | LototechApp |
| Programming Languages Poll | programming-languages-poll | 6 | PollsApp |
| BG Elections | bg-elections | 6 | PollsApp |

---

## Key Rules

- `apps_registry` is the **source of truth** for component identity — never store `component_name` in `content_blocks.metadata`
- One app → many instances. `PollsApp` can have unlimited poll instances, all sharing `app_id=6`
- Each app owns its schema (`polls`, `toto2`) — app data never goes into `company` tables
- The `auto_register_app` trigger has been removed — registration is always manual and intentional