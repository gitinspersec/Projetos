"""
©AngelaMos | 2026
__init__.py

What an __init__.py file even IS

────────────────────────────────────────────────────────────────────
The one-sentence version
────────────────────────────────────────────────────────────────────
A folder that contains a file named `__init__.py` becomes a Python
"package" — which is just a fancy word for "a folder you can import
from like it were a single module"

────────────────────────────────────────────────────────────────────
The slightly longer version
────────────────────────────────────────────────────────────────────
Imagine you have this layout

    password_manager/
        __init__.py
        vault.py
        crypto.py
        generator.py

WITHOUT the `__init__.py`, the folder is just a folder. Python does
not know it is allowed to look inside. Writing `import
password_manager` would fail

WITH the `__init__.py`, Python looks at the folder and goes "ah, a
package". Now `import password_manager` works, and so does
`from password_manager.vault import UnlockedVault`

The file does NOT have to contain anything. An EMPTY `__init__.py`
is perfectly valid — its mere PRESENCE is the signal. The contents,
if any, are bonus

────────────────────────────────────────────────────────────────────
When the file DOES contain stuff (like this one)
────────────────────────────────────────────────────────────────────
Whatever code is inside `__init__.py` runs the FIRST time anybody
imports the package. It is the package's "front door" or setup
script. Two common things people put inside

  1. Re-exports — pulling names up from submodules so callers can
     write the short form instead of the long form

        # without re-exports
        from password_manager.vault import UnlockedVault

        # with re-exports (what we do below)
        from password_manager import UnlockedVault

     This lets us reorganize the internals (split vault.py into
     three files later, say) without breaking anyone's imports

  2. Package metadata — things like `__version__` so other tools
     can ask `password_manager.__version__` and get an answer

────────────────────────────────────────────────────────────────────
What THIS specific __init__.py does
────────────────────────────────────────────────────────────────────
  - Re-exports the public classes and errors from vault.py and
    crypto.py so callers do not need to know which file holds what
  - Sets `__version__` so `pip` and tooling can read it
  - Defines `__all__` — the explicit list of "what `from
    password_manager import *` is allowed to bring in"

Connects to
  vault.py — re-exports UnlockedVault, Entry, and every vault error
  crypto.py — re-exports CryptoError, KdfParameters, WrongPasswordError
"""

# Local: re-export the crypto-layer pieces callers actually need —
# the KDF parameter record plus the two error types they may catch.
from password_manager.crypto import (
    CryptoError,
    KdfParameters,
    WrongPasswordError,
)
# Local: re-export the vault-layer pieces — the Entry record, the
# main UnlockedVault class, and every domain-specific error.
from password_manager.vault import (
    Entry,
    EntryAlreadyExistsError,
    EntryNotFoundError,
    UnlockedVault,
    VaultAlreadyExistsError,
    VaultError,
    VaultFormatError,
    VaultNotFoundError,
)


__version__ = "1.0.0"

__all__ = [
    "CryptoError",
    "Entry",
    "EntryAlreadyExistsError",
    "EntryNotFoundError",
    "KdfParameters",
    "UnlockedVault",
    "VaultAlreadyExistsError",
    "VaultError",
    "VaultFormatError",
    "VaultNotFoundError",
    "WrongPasswordError",
]
