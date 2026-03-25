# Multi-Tenancy Implementation Notes

This document captures the architecture, data model, and implementation plan for adding multi-tenancy to number-adder. It serves as context for any AI agent (Claude, Codex, etc.) continuing this work.

## Goal

Transform number-adder from a single-user app to a multi-tenant SaaS with:
- Organizations (tenants)
- Role-based access control at org level
- Sub-resources (calculators) with their own access control
- UI that respects permissions (show/hide buttons based on role)

## Current State

### Existing Tables

```sql
users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_premium BOOLEAN DEFAULT FALSE,
    stripe_customer_id TEXT,
    api_key_hash TEXT,
    created_at TIMESTAMP
)

calculations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    operation TEXT DEFAULT 'add',
    num_a DOUBLE PRECISION,
    num_b DOUBLE PRECISION,
    result DOUBLE PRECISION,
    created_at TIMESTAMP
)
```

### Existing Auth
- JWT tokens via `/login` and `/register`
- API key auth via `X-API-Key` header
- Google OAuth
- `get_current_user_id_flexible()` dependency extracts user from either auth method

---

## Target Architecture

### Data Model

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           MULTI-TENANCY DATA MODEL                            │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐       ┌─────────────────────┐       ┌──────────────┐
│    users     │       │  organization_users │       │ organizations│
├──────────────┤       ├─────────────────────┤       ├──────────────┤
│ id           │◄──────│ user_id             │       │ id           │
│ email        │       │ organization_id     │──────►│ name         │
│ password_hash│       │ role                │       │ created_at   │
│ ...          │       │ created_at          │       └──────────────┘
└──────────────┘       └─────────────────────┘
       │                                                    │
       │               ORG ROLES:                           │
       │               • 'admin'  → pay, add users, use     │
       │               • 'manager'→ add users, use          │
       │               • 'member' → use only                │
       │                                                    │
       ▼                                                    ▼
┌──────────────┐       ┌─────────────────────┐       ┌──────────────┐
│              │       │  calculator_users   │       │  calculators │
│              │       ├─────────────────────┤       ├──────────────┤
│              │◄──────│ user_id             │       │ id           │
│              │       │ calculator_id       │──────►│ org_id       │──┐
│              │       │ role                │       │ name         │  │
│              │       │ created_at          │       │ created_by   │  │
│              │       └─────────────────────┘       │ created_at   │  │
│              │                                     └──────────────┘  │
│              │       CALCULATOR ROLES:                    │          │
│              │       • 'admin'   → manage + add users     │          │
│              │       • 'operator'→ use calculator         │          │
│              │       • 'viewer'  → view history only      │          │
│              │                                            ▼          │
│              │                                     ┌──────────────┐  │
│              │                                     │ calculations │  │
│              │                                     ├──────────────┤  │
│              │─────────────────────────────────────│ user_id      │  │
│              │                                     │ calculator_id│◄─┘
│              │                                     │ operation    │
└──────────────┘                                     │ num_a, num_b │
                                                     │ result       │
                                                     │ created_at   │
                                                     └──────────────┘
```

### New Tables to Add

```sql
-- Organizations (tenants)
CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Maps users to organizations with roles
CREATE TABLE organization_users (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('admin', 'manager', 'member')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organization_id, user_id)
);

-- Calculators (sub-resources within orgs)
CREATE TABLE calculators (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_by_user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organization_id, name)
);

-- Maps users to calculators with roles
CREATE TABLE calculator_users (
    id SERIAL PRIMARY KEY,
    calculator_id INTEGER NOT NULL REFERENCES calculators(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('admin', 'operator', 'viewer')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(calculator_id, user_id)
);

-- MODIFY existing calculations table: add calculator_id
ALTER TABLE calculations ADD COLUMN calculator_id INTEGER REFERENCES calculators(id) ON DELETE CASCADE;
```

---

## Permission Matrix

### Organization-Level Permissions

| Action | admin | manager | member |
|--------|-------|---------|--------|
| View org settings | Yes | Yes | No |
| Upgrade/billing | Yes | No | No |
| Invite users | Yes | Yes | No |
| Remove users | Yes | No | No |
| Change user roles | Yes | No | No |
| Create calculators | Yes | Yes | No |
| Delete org | Yes | No | No |

### Calculator-Level Permissions

| Action | admin | operator | viewer |
|--------|-------|----------|--------|
| Use calculator (add numbers) | Yes | Yes | No |
| View calculation history | Yes | Yes | Yes |
| Manage calculator settings | Yes | No | No |
| Add users to calculator | Yes | No | No |
| Remove users from calculator | Yes | No | No |
| Delete calculator | Yes | No | No |

---

## Implementation Plan

### Step 1: Schema - Organizations
**Files to modify:** `database.py`

Add:
- `organizations` table
- `organization_users` table
- CRUD functions: `create_organization()`, `add_user_to_organization()`, `get_user_organizations()`, `get_org_users()`
- Permission check functions: `is_org_admin()`, `is_org_manager()`, `is_org_member()`

**Checkpoint:** Can create org, add users with roles via direct DB calls.

### Step 2: Org-Level Route Protection
**Files to modify:** `server.py`

Add:
- Decorator: `@requires_org_admin`, `@requires_org_manager`, `@requires_org_member`
- Endpoints: `POST /organizations`, `GET /organizations`, `POST /organizations/{id}/users`, `GET /organizations/{id}/users`
- All org endpoints enforce role checks

**Checkpoint:** API enforces org-level permissions. Unauthorized requests return 403.

### Step 3: Frontend - Org Permissions
**Files to modify:** `static/` HTML/JS files, `mobile/` React Native files

Add:
- Org context in JWT or separate endpoint
- Show/hide upgrade button (admin only)
- Show/hide organization menu item (admin + manager)
- Organization management page (admin + manager)

**Checkpoint:** UI respects org permissions. Members don't see admin buttons.

### Step 4: Schema - Calculators
**Files to modify:** `database.py`

Add:
- `calculators` table
- `calculator_users` table
- Modify `calculations` to include `calculator_id`
- CRUD functions: `create_calculator()`, `add_user_to_calculator()`, `get_calculator_users()`
- Permission check functions: `is_calculator_admin()`, `is_calculator_operator()`, `can_access_calculator()`

**Checkpoint:** Can create calculators within orgs, assign users.

### Step 5: Calculator-Level Route Protection
**Files to modify:** `server.py`

Add:
- Decorator: `@requires_calculator_admin`, `@requires_calculator_access`
- Modify `/add` endpoint to require calculator context
- Endpoints: `POST /calculators`, `GET /calculators`, `POST /calculators/{id}/users`
- `/history` scoped to calculator

**Checkpoint:** API enforces calculator-level permissions. Users only see their calculators' data.

### Step 6: Frontend - Calculator Permissions
**Files to modify:** `static/`, `mobile/`

Add:
- Calculator selector dropdown
- Calculator list filtered by user access
- Calculator management page (calculator admins only)
- Calculation history scoped to selected calculator

**Checkpoint:** Full multi-tenant demo working end-to-end.

---

## Key Code Patterns (from Vanna reference)

### Permission Check Functions (database.py)

```python
def is_org_admin(org_id: int, user_id: int) -> bool:
    """Check if user is an organization admin."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM organization_users
            WHERE organization_id = %s AND user_id = %s AND role = 'admin'
        """, (org_id, user_id))
        return cursor.fetchone() is not None

def is_org_member(org_id: int, user_id: int) -> bool:
    """Check if user belongs to organization (any role)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM organization_users
            WHERE organization_id = %s AND user_id = %s
        """, (org_id, user_id))
        return cursor.fetchone() is not None
```

### Route Protection Decorator (server.py)

```python
def requires_org_admin(org_id_param: str = "org_id"):
    """Decorator that requires user to be org admin."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get("user_id")
            org_id = kwargs.get(org_id_param)

            if not org_id:
                raise HTTPException(status_code=400, detail="org_id required")

            if not db.is_org_admin(org_id, user_id):
                raise HTTPException(status_code=403, detail="Org admin required")

            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### Frontend Permission Flags

Backend returns permission booleans with user/org data:

```python
@app.get("/organizations/{org_id}")
def get_organization(org_id: int, user_id: int = Depends(get_current_user_id)):
    org = db.get_organization(org_id)
    return {
        "id": org["id"],
        "name": org["name"],
        # Permission flags for frontend
        "is_admin": db.is_org_admin(org_id, user_id),
        "is_manager": db.is_org_manager(org_id, user_id),
        "can_invite": db.is_org_admin(org_id, user_id) or db.is_org_manager(org_id, user_id),
    }
```

Frontend uses these to conditionally render:

```javascript
{org.is_admin && <button>Upgrade</button>}
{org.can_invite && <button>Invite User</button>}
```

---

## API Endpoints (Target State)

### Organization Endpoints
```
POST   /organizations                    # Create org (any authenticated user)
GET    /organizations                    # List user's orgs
GET    /organizations/{id}               # Get org details + permissions
DELETE /organizations/{id}               # Delete org (admin only)

POST   /organizations/{id}/users         # Add user to org (admin/manager)
GET    /organizations/{id}/users         # List org users (admin/manager)
DELETE /organizations/{id}/users/{uid}   # Remove user (admin only)
PATCH  /organizations/{id}/users/{uid}   # Change role (admin only)
```

### Calculator Endpoints
```
POST   /organizations/{org_id}/calculators           # Create calculator (admin/manager)
GET    /organizations/{org_id}/calculators           # List calculators user can access
GET    /calculators/{id}                             # Get calculator details
DELETE /calculators/{id}                             # Delete (calculator admin only)

POST   /calculators/{id}/users                       # Add user (calculator admin)
GET    /calculators/{id}/users                       # List users (calculator admin)
DELETE /calculators/{id}/users/{uid}                 # Remove user (calculator admin)

POST   /calculators/{id}/add                         # Add numbers (operator+)
GET    /calculators/{id}/history                     # Get history (viewer+)
```

---

## Testing Strategy

For each step, verify:

1. **Happy path:** Authorized user can perform action
2. **Unauthorized:** User without permission gets 403
3. **Cross-tenant:** User from Org A cannot access Org B's resources
4. **Cascade delete:** Deleting org removes all child resources

Example test cases:
```python
def test_org_admin_can_invite():
    # Admin creates org, invites member
    # Assert: member appears in org users list

def test_member_cannot_invite():
    # Member tries to invite
    # Assert: 403 Forbidden

def test_cross_org_isolation():
    # User in Org A tries to access Org B calculator
    # Assert: 403 or 404
```

---

## Reference Implementation

This design is based on [vanna-ai/vanna-hosted](https://github.com/vanna-ai/vanna-hosted), specifically:
- `backend/db.py` - Schema and permission check functions
- `backend/vanna_flask/__init__.py` - Route decorators
- `backend/vanna_flask/auth.py` - Auth interface
- `frontend/src/lib/types.ts` - Permission flag types
- `frontend/src/lib/AgentList.svelte` - Conditional UI rendering

---

## Current Progress

- [x] Created feature branch: `feature/multi-tenancy`
- [x] Created this notes.md
- [ ] Step 1: Schema - Organizations
- [ ] Step 2: Org-level route protection
- [ ] Step 3: Frontend - org permissions
- [ ] Step 4: Schema - Calculators
- [ ] Step 5: Calculator-level route protection
- [ ] Step 6: Frontend - calculator permissions

---

## Open Questions / Decisions Made

1. **Calculator purpose:** Access control demo only. All calculators do the same thing (add). Named for teams (Sales Calculator, Marketing Calculator) to demonstrate isolation.

2. **Premium/billing:** Stays at org level. Org admin pays to upgrade the whole org.

3. **User can belong to multiple orgs:** Yes, like Slack workspaces. Each org membership has independent role.

4. **Default on signup:** New users don't belong to any org. They must create one or be invited.
