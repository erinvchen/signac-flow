# Copyright (c) 2021 The Regents of the University of Michigan
# All rights reserved.
# This software is licensed under the BSD 3-Clause License.
"""Handle migrations of signac-flow schema versions."""

import os
import sys
from contextlib import contextmanager

from filelock import FileLock
from packaging import version
from signac.common.config import get_config

from flow.util.config import get_config_value

from ..version import SCHEMA_VERSION, __version__
from .v0_to_v1 import migrate_v0_to_v1

FN_MIGRATION_LOCKFILE = ".FLOW_PROJECT_MIGRATION_LOCK"


MIGRATIONS = {
    ("0", "1"): migrate_v0_to_v1,
}


def _reload_project_config(project):
    project_reloaded = project.get_project(
        root=project.root_directory(), search=False, _ignore_flow_schema_version=True
    )
    project._config = project_reloaded._config


def _update_project_config(project, **kwargs):
    """Update the project configuration."""
    for fn in ("signac.rc", ".signacrc"):
        config = get_config(project.fn(fn))
        if "project" in config:
            break
    else:
        raise RuntimeError("Unable to determine project configuration file.")
    config.setdefault("flow", {}).update(kwargs)
    config.write()
    _reload_project_config(project)


@contextmanager
def _lock_for_migration(project):
    lock = FileLock(project.fn(FN_MIGRATION_LOCKFILE))
    try:
        with lock:
            yield
    finally:
        try:
            os.unlink(lock.lock_file)
        except FileNotFoundError:
            pass


def _collect_migrations(project):
    schema_version = version.parse(SCHEMA_VERSION)

    def get_config_schema_version():
        # TODO: The means of getting schema versions will have to change for
        # flow versions in schema versions > 1 that no longer rely on signac's
        # configuration file and schema.
        return version.parse(get_config_value("schema_version", config=project.config))

    if get_config_schema_version() > schema_version:
        # Project config schema version is newer and therefore not supported.
        raise RuntimeError(
            "The signac-flow configuration schema version used by this project is {}, "
            "but signac-flow {} only supports up to schema version {}. Try updating "
            "signac-flow.".format(
                get_config_schema_version(), __version__, SCHEMA_VERSION
            )
        )

    while get_config_schema_version() < schema_version:
        for (origin, destination), migration in MIGRATIONS.items():
            if version.parse(origin) == get_config_schema_version():
                yield (origin, destination), migration
                break
        else:
            raise RuntimeError(
                "The signac-flow configuration schema version used by this project is "
                "{}, but signac-flow {} uses schema version {} and does not know how "
                "to migrate.".format(
                    get_config_schema_version(), __version__, schema_version
                )
            )


def apply_migrations(project):
    """Apply migrations to a project."""
    with _lock_for_migration(project):
        for (origin, destination), migrate in _collect_migrations(project):
            try:
                print(
                    f"Applying migration for version {origin} to {destination}... ",
                    end="",
                    file=sys.stderr,
                )
                migrate(project)
            except Exception as e:
                raise RuntimeError(f"Failed to apply migration {destination}.") from e
            else:
                _update_project_config(project, schema_version=destination)
                print("OK", file=sys.stderr)
                yield origin, destination


__all__ = [
    "apply_migrations",
]
