"""Entry-point package for bundled sc2reader CLI scripts.

This module intentionally avoids importing script submodules eagerly so that
`python -m unittest discover` does not fail when optional script dependencies
or removed modules are unavailable.
"""
