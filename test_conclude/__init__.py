# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/nedbat/coveragepy/blob/master/NOTICE.txt

"""
Code coverage measurement for Python.

Ned Batchelder
https://coverage.readthedocs.io

"""

from __future__ import annotations

# mypy's convention is that "import as" names are public from the module.
# We import names as themselves to indicate that. Pylint sees it as pointless,
# so disable its warning.
# pylint: disable=useless-import-alias

from test_conclude.version import (
    FORK_VERSION as FORK_VERSION,
    __version__ as __version__,
    version_info as version_info,
)

from test_conclude.control import (
    Coverage as Coverage,
    process_startup as process_startup,
)
from test_conclude.data import CoverageData as CoverageData
from test_conclude.exceptions import CoverageException as CoverageException
from test_conclude.plugin import (
    CodeRegion as CodeRegion,
    CoveragePlugin as CoveragePlugin,
    FileReporter as FileReporter,
    FileTracer as FileTracer,
)

# Backward compatibility.
coverage = Coverage
