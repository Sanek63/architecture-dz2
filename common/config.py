import os


def get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise RuntimeError(f"Missing env var: {name}")
    return value


def get_int_env(name: str, default: int | None = None) -> int:
    fallback = str(default) if default is not None else None
    return int(get_env(name, fallback))
