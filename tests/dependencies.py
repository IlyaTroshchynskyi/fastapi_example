from dataclasses import dataclass
from typing import Callable

from fastapi import FastAPI
from starlette.routing import Mount

from app.core.database import get_session


@dataclass(frozen=True, kw_only=True, slots=True)
class _DependencyOverride:
    dependency: Callable
    override: Callable


def override_app_test_dependencies(app: FastAPI) -> None:
    dependency_overrides: list[_DependencyOverride] = [
        _DependencyOverride(dependency=get_session, override=lambda: 'Fast Test drop if session is not set explicitly'),
    ]
    for dependency_override in dependency_overrides:
        override_dependency(app, dependency_override.dependency, dependency_override.override)


def override_dependency(app: FastAPI, dependency: Callable, override: Callable) -> None:
    app.dependency_overrides[dependency] = override
    for route in app.router.routes:
        if isinstance(route, Mount) and isinstance(route.app, FastAPI):
            route.app.dependency_overrides[dependency] = override
