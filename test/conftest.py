from ctypeslib.codegen.cindex import Config
from pathlib import Path
import os
import pytest


def pytest_addoption(parser):
    parser.addoption('--libclang-library', default=None)
    parser.addoption('--libclang-include-dir', default=None)


@pytest.fixture(scope="session", autouse=True)
def libclang_config(pytestconfig, request):
    libclang_library = pytestconfig.getoption("libclang_library")
    libclang_include_dir = pytestconfig.getoption("libclang_include_dir")
    if libclang_library:
        Config.set_library_file(libclang_library)
    if libclang_include_dir:
        Config.set_include_dir(libclang_include_dir)


@pytest.fixture(scope="class", autouse=True)
def change_test_dir(request):
    os.chdir(str(Path(request.fspath).parent.parent))
    yield
    os.chdir(request.config.invocation_dir)
