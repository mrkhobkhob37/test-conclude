# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/nedbat/coveragepy/blob/master/NOTICE.txt

"""Code coverage measurement for Python"""

# Distutils setup for test_conclude (fork of coverage.py)
# This file is used unchanged under all versions of Python.

import os
import sys

# Setuptools has to be imported before distutils, or things break.
from setuptools import setup
from distutils.core import Extension  # pylint: disable=wrong-import-order
from setuptools.command.build_ext import build_ext  # pylint: disable=wrong-import-order
from distutils import errors  # pylint: disable=wrong-import-order

# Get or massage our metadata.  We exec coverage/version.py so we can avoid
# importing the product code into setup.py.

# PYVERSIONS
classifiers = """\
Environment :: Console
Intended Audience :: Developers
Operating System :: OS Independent
Programming Language :: Python
Programming Language :: Python :: 3
Programming Language :: Python :: 3.8
Programming Language :: Python :: 3.9
Programming Language :: Python :: 3.10
Programming Language :: Python :: 3.11
Programming Language :: Python :: 3.12
Programming Language :: Python :: 3.13
Programming Language :: Python :: Implementation :: CPython
Programming Language :: Python :: Implementation :: PyPy
Topic :: Software Development :: Quality Assurance
Topic :: Software Development :: Testing
"""

cov_ver_py = os.path.join(os.path.split(__file__)[0], "test_conclude/version.py")
with open(cov_ver_py) as version_file:
    # __doc__ will be overwritten by version.py.
    doc = __doc__
    # Keep pylint happy.
    __version__ = __url__ = version_info = ""
    # Execute the code in version.py.
    exec(compile(version_file.read(), cov_ver_py, "exec", dont_inherit=True))

# Fork note: the upstream version is frozen explicitly below so tags,
# checkouts, and sdist builds can never silently disagree about the fork
# version.  See test_conclude/version.py FORK_VERSION.
FORK_VERSION = "7.5.0+epic.1"

with open("README.rst") as readme:
    readme_text = readme.read()

temp_url = __url__.replace("readthedocs", "@@")
assert "@@" not in readme_text
long_description = (
    readme_text.replace("https://coverage.readthedocs.io/en/latest", temp_url)
    .replace("https://coverage.readthedocs.io", temp_url)
    .replace("@@", "readthedocs")
)

with open("CONTRIBUTORS.txt", "rb") as contributors:
    paras = contributors.read().split(b"\n\n")
    num_others = len(paras[-1].splitlines())
    num_others += 1  # Count Gareth Rees, who is mentioned in the top paragraph.

classifier_list = classifiers.splitlines()

if version_info[3] == "alpha":
    devstat = "3 - Alpha"
elif version_info[3] in ["beta", "candidate"]:
    devstat = "4 - Beta"
else:
    assert version_info[3] == "final"
    devstat = "5 - Production/Stable"
classifier_list.append(f"Development Status :: {devstat}")

# Create the keyword arguments for setup()

setup_args = dict(
    name="test-conclude",
    version=FORK_VERSION,
    packages=[
        "test_conclude",
    ],
    package_data={
        "test_conclude": [
            "htmlfiles/*.*",
            "py.typed",
        ],
    },
    entry_points={
        # Install a script as "test-conclude".
        "console_scripts": [
            "test-conclude = test_conclude.cmdline:main",
        ],
    },
    extras_require={
        # Enable pyproject.toml support.
        "toml": ['tomli; python_full_version<="3.11.0a6"'],
    },
    # We need to get HTML assets from our htmlfiles directory.
    zip_safe=False,
    author=f"Ned Batchelder and {num_others} others",
    author_email="ned@nedbatchelder.com",
    description=doc,
    long_description=long_description,
    long_description_content_type="text/x-rst",
    keywords="code coverage testing",
    license="Apache-2.0",
    license_files=["LICENSE.txt"],
    classifiers=classifier_list,
    url="https://github.com/nedbat/coveragepy",
    project_urls={
        "Documentation": __url__,
        "Funding": (
            "https://tidelift.com/subscription/pkg/pypi-coverage"
            + "?utm_source=pypi-coverage&utm_medium=referral&utm_campaign=pypi"
        ),
        "Issues": "https://github.com/nedbat/coveragepy/issues",
        "Mastodon": "https://hachyderm.io/@coveragepy",
        "Mastodon (nedbat)": "https://hachyderm.io/@nedbat",
    },
    python_requires=">=3.8",  # minimum of PYVERSIONS
)

# A replacement for the build_ext command which raises a single exception
# if the build fails, so we can fallback nicely.

ext_errors = (
    errors.CCompilerError,
    errors.DistutilsExecError,
    errors.DistutilsPlatformError,
)
if sys.platform == "win32":
    # distutils.msvc9compiler can raise an IOError when failing to
    # find the compiler
    ext_errors += (IOError,)


class BuildFailed(Exception):
    """Raise this to indicate the C extension wouldn't build."""

    def __init__(self):
        Exception.__init__(self)
        self.cause = sys.exc_info()[1]  # work around py 2/3 different syntax


class ve_build_ext(build_ext):
    """Build C extensions, but fail with a straightforward exception."""

    def run(self):
        """Wrap `run` with `BuildFailed`."""
        try:
            build_ext.run(self)
        except errors.DistutilsPlatformError as exc:
            raise BuildFailed() from exc

    def build_extension(self, ext):
        """Wrap `build_extension` with `BuildFailed`."""
        try:
            # Uncomment to test compile failure handling:
            #   raise errors.CCompilerError("OOPS")
            build_ext.build_extension(self, ext)
        except ext_errors as exc:
            raise BuildFailed() from exc
        except ValueError as err:
            # this can happen on Windows 64 bit, see Python issue 7511
            if "'path'" in str(err):  # works with both py 2/3
                raise BuildFailed() from err
            raise


# There are a few reasons we might not be able to compile the C extension.
# Figure out if we should attempt the C extension or not.

compile_extension = True

if "__pypy__" in sys.builtin_module_names:
    # Pypy can't compile C extensions
    compile_extension = False

if compile_extension:
    setup_args.update(
        dict(
            ext_modules=[
                Extension(
                    "test_conclude.tracer",
                    sources=[
                        "test_conclude/ctracer/datastack.c",
                        "test_conclude/ctracer/filedisp.c",
                        "test_conclude/ctracer/module.c",
                        "test_conclude/ctracer/tracer.c",
                    ],
                ),
            ],
            cmdclass={
                "build_ext": ve_build_ext,
            },
        ),
    )


def main():
    """Actually invoke setup() with the arguments we built above."""
    # For a variety of reasons, it might not be possible to install the C
    # extension.  Try it with, and if it fails, try it without.
    try:
        setup(**setup_args)
    except BuildFailed as exc:
        msg = "Couldn't install with extension module, trying without it..."
        exc_msg = f"{exc.__class__.__name__}: {exc.cause}"
        print(f"**\n** {msg}\n** {exc_msg}\n**")

        del setup_args["ext_modules"]
        setup(**setup_args)


if __name__ == "__main__":
    main()
