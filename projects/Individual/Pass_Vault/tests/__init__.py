"""
©AngelaMos | 2026
__init__.py

Why this file exists even though it is empty

────────────────────────────────────────────────────────────────────
The one-sentence version
────────────────────────────────────────────────────────────────────
The mere PRESENCE of a file named `__init__.py` in a folder tells
Python "this folder is a package — you may import from it". The
file does not need to contain anything

────────────────────────────────────────────────────────────────────
Why THIS one is empty (and the src one is not)
────────────────────────────────────────────────────────────────────
Two folders in this project both have `__init__.py`, but they use
it for different jobs

  src/password_manager/__init__.py
      Has CODE inside. It re-exports the most useful classes so
      callers can write `from password_manager import UnlockedVault`
      instead of digging into submodules. This is the package's
      front door

  tests/__init__.py   <-- you are here, and it is EMPTY
      Has no code. It exists only as a MARKER so Python and pytest
      treat `tests/` as a package. That matters because some test
      files do this

          from tests.conftest import TEST_KDF_PARAMETERS

      For `tests.conftest` to be a valid dotted import path,
      `tests` has to be a package, which means this file has to
      exist. The header docstring is the only content; everything
      else is silence

────────────────────────────────────────────────────────────────────
Takeaway
────────────────────────────────────────────────────────────────────
`__init__.py` is dual-purpose

  EXISTENCE  → "this folder is a package"   (always, even when empty)
  CONTENTS   → optional code that runs on first import (re-exports,
               version constants, etc.)

A folder full of `.py` files with no `__init__.py` is just files;
add the `__init__.py` and it becomes something you can import as a
single unit
"""
