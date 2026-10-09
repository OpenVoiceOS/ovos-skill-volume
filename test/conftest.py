"""Pytest collection config for the test suite.

The ``test/end2end/`` suite boots ovoscope MiniCrofts on the adapt, padacioso
and m2v pipelines. The ``test`` and ``end2end`` extras both install ovoscope.
When ovoscope is not installed, pytest skips that directory, so a run with
only the core dependencies still collects the unit tests.
"""
from importlib.util import find_spec

collect_ignore_glob = []

if find_spec("ovoscope") is None:
    collect_ignore_glob.append("end2end/*")
