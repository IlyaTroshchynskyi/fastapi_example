# Import Style

## Rule: All Imports at the Top of the File (CRITICAL)

NEVER place imports inside functions or class bodies. ALL imports MUST appear at the top of the file, after the module docstring and before any other code.

```python
# WRONG — import inside a function
def get_user():
    from app.apps.users.models import UserModel  # ❌
    return UserModel()

# WRONG — import inside a class method
class MyService:
    def process(self, data):
        import json  # ❌
        return json.dumps(data)

# CORRECT — all imports at the top
import json  # ✅
from app.apps.users.models import UserModel  # ✅

def get_user():
    return User()

class MyService:
    def process(self, data):
        return json.dumps(data)
```

## Import Order (follow isort / ruff `I` rules)

1. Standard library imports (`import json`, `from datetime import datetime`)
2. Third-party imports (`from fastapi import APIRouter`, `from sqlalchemy import select`)
3. Local/project imports (`from app.apps.users.models import User`)

Separate each group with a blank line. Ruff enforces this automatically — run `ruff check --fix` to auto-sort.

## Rationale

- Top-level imports are the file's **dependency manifest** — visible at a glance without reading the full file.
- Inline imports **hide dependencies**, making refactoring and code review harder.
- Inline imports re-execute the `sys.modules` lookup on every call, adding unnecessary overhead.
- If you hit a **circular import**, fix the architecture — move shared code to `shared/` or `core/`. A circular import is a design signal, not a reason for an inline import.

## Exceptions

None. There are no acceptable exceptions in this codebase.

## Checklist Addition

Add to code quality checklist before marking work complete:
- [ ] No imports inside functions or class bodies — all at top of file