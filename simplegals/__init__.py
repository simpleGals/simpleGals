from importlib.metadata import PackageNotFoundError, version as _version

try:
    __version__ = _version("simplegals")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0+unknown"
