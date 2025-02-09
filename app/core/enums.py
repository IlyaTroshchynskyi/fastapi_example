from enum import StrEnum


class Environment(StrEnum):
    PRODUCTION = 'production'
    DEV = 'dev'
    LOCAL = 'local'
    TEST = 'test'
