from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    if os.name != "nt":
        return

    import _pytest.tmpdir as pytest_tmpdir

    factory_cls = pytest_tmpdir.TempPathFactory
    if getattr(factory_cls, "_content_research_windows_basetemp_patch", False):
        return

    original_getbasetemp = factory_cls.getbasetemp

    def getbasetemp(self: pytest_tmpdir.TempPathFactory) -> Path:
        if self._basetemp is not None:
            return self._basetemp

        if self._given_basetemp is None:
            return original_getbasetemp(self)

        basetemp = self._given_basetemp
        try:
            if basetemp.exists():
                pytest_tmpdir.rm_rf(basetemp)
        except OSError:
            basetemp = _unused_sibling(basetemp)

        basetemp.mkdir(parents=True, exist_ok=True)
        basetemp = basetemp.resolve()
        self._basetemp = basetemp
        self._trace("new basetemp", basetemp)
        return basetemp

    def mktemp(
        self: pytest_tmpdir.TempPathFactory, basename: str, numbered: bool = True
    ) -> Path:
        basename = self._ensure_relative_to_basetemp(basename)
        if not numbered:
            path = self.getbasetemp().joinpath(basename)
            path.mkdir()
        else:
            path = pytest_tmpdir.make_numbered_dir(
                root=self.getbasetemp(), prefix=basename, mode=0o777
            )
            self._trace("mktemp", path)
        return path

    factory_cls.getbasetemp = getbasetemp
    factory_cls.mktemp = mktemp
    factory_cls._content_research_windows_basetemp_patch = True


def _unused_sibling(path: Path) -> Path:
    for index in range(100):
        candidate = path.with_name(f"{path.name}_{os.getpid()}_{index}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find an unused pytest temp directory near {path}")
