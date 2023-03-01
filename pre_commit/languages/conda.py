from __future__ import annotations

import contextlib
import os
import pathlib
from typing import Generator
from typing import Sequence

from pre_commit import lang_base
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import SubstitutionT
from pre_commit.envcontext import UNSET
from pre_commit.envcontext import Var
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output_b

ENVIRONMENT_DIR = 'conda'
get_default_version = lang_base.basic_get_default_version
health_check = lang_base.basic_health_check
run_hook = lang_base.basic_run_hook


def get_env_patch(env: str) -> PatchesT:
    # On non-windows systems executable live in $CONDA_PREFIX/bin, on Windows
    # they can be in $CONDA_PREFIX/bin, $CONDA_PREFIX/Library/bin,
    # $CONDA_PREFIX/Scripts and $CONDA_PREFIX. Whereas the latter only
    # seems to be used for python.exe.
    path: SubstitutionT = (os.path.join(env, 'bin'), os.pathsep, Var('PATH'))
    if os.name == 'nt':  # pragma: no cover (platform specific)
        path = (env, os.pathsep, *path)
        path = (os.path.join(env, 'Scripts'), os.pathsep, *path)
        path = (os.path.join(env, 'Library', 'bin'), os.pathsep, *path)

    return (
        ('PYTHONHOME', UNSET),
        ('VIRTUAL_ENV', UNSET),
        ('CONDA_PREFIX', env),
        ('PATH', path),
    )


@contextlib.contextmanager
def in_env(prefix: Prefix, version: str) -> Generator[None, None, None]:
    envdir = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)
    with envcontext(get_env_patch(envdir)):
        yield


def _conda_exe() -> str:
    if os.environ.get('PRE_COMMIT_USE_MICROMAMBA'):
        return 'micromamba'
    elif os.environ.get('PRE_COMMIT_USE_MAMBA'):
        return 'mamba'
    else:
        return 'conda'


def install_environment(
        prefix: Prefix,
        version: str,
        additional_dependencies: Sequence[str],
) -> None:
    lang_base.assert_version_default('conda', version)

    conda_exe = _conda_exe()
    envfile_dir = pathlib.Path(prefix.prefix_dir)
    default_environment_yml = '''\
channels: [conda-forge, defaults]
dependencies: [openssl]
'''
    if not (envfile_dir / 'environment.yml').exists():
        (envfile_dir / 'environment.yml').write_text(default_environment_yml)

    env_dir = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)
    cmd_output_b(
        conda_exe, 'env', 'create', '-p', env_dir, '--file',
        'environment.yml', cwd=prefix.prefix_dir,
    )
    if additional_dependencies:
        cmd_output_b(
            conda_exe, 'install', '-p', env_dir, *additional_dependencies,
            cwd=prefix.prefix_dir,
        )
