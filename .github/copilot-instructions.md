Should apply available patterns and describe where and why it was used
Should use modern Python syntax matching the project (requires-python is 3.12+; use 3.12-compatible features unless the target version is raised)
Should use StrEnum for enums
Should use list instead of List for typehints
Should use class ConfigDict in pydantic models and use syntaxis of pydantic version 2.0. Should be placed after all fields
Should use None type instead of Optional
Don't use ... for mandatory fields in pydantic models
For default values in pydantic models use Field(default=None) in pydantic models
All enums should be in the file enums.py
Must use dependency injection from fastapi
We shouldn't create any global values
All protected functions should be in the end of class
Follow mypy styles or ty styles
Don't read .env file
Follow the existing code style and conventions used in the project to maintain
Don't create migrations manually
The field length must be a multiple of 2
Should follow the same structure as existing files in the project
Should use f-strings for string formatting
Should use SQLAlchemy the same way as existing code: async sessions, models, and repository-style access; use `text()` or Core only where the codebase already does for a specific case
