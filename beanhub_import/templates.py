import pathlib

from jinja2.sandbox import SandboxedEnvironment


def as_posix_path(path: pathlib.Path) -> str:
    return pathlib.Path(path).as_posix()


def make_environment():
    env = SandboxedEnvironment()
    env.filters["as_posix_path"] = as_posix_path
    return env
