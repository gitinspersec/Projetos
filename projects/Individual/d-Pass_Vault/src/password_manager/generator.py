"""
©AngelaMos | 2026
generator.py

Cryptographically secure random password generation

A password generator is just a function that picks N random
characters from a pool. The interesting part is HOW you pick them

────────────────────────────────────────────────────────────────────
Why `secrets`, not `random`
────────────────────────────────────────────────────────────────────
Python has TWO modules that produce random numbers

  random  — fast, predictable, fine for games and simulations
  secrets — slow-ish, unpredictable, made for cryptography

If we used `random.choice` to pick characters, an attacker who saw
ONE password could deduce the internal state of the random generator
and predict every other password it produced. The `secrets` module
pulls bytes from the operating system's cryptographic source, which
is unpredictable by design

Rule of thumb: any time the output is meant to be hard to guess by
humans OR computers, use `secrets`

────────────────────────────────────────────────────────────────────
What this module exposes
────────────────────────────────────────────────────────────────────
  generate_password(length, ...) — return a random password string
  PasswordTooShortError          — raised when length is below the floor

Connects to
  main.py — the `pv gen` command and the `pv add` command call this
  constants.py — pulls character pools and length defaults from here
"""

# Standard library: cryptographically-secure random — we pick each
# character from the alphabet with `secrets.choice`. Plain `random`
# would be predictable to an attacker and unsafe for passwords.
import secrets

# Local: pull every character pool and length default from constants —
# no magic strings or numbers ever live in this file.
from password_manager.constants import (
    DEFAULT_GENERATED_PASSWORD_LENGTH,
    DIGITS,
    LOWERCASE_LETTERS,
    MINIMUM_GENERATED_PASSWORD_LENGTH,
    SAFE_SYMBOLS,
    UPPERCASE_LETTERS,
)


class PasswordTooShortError(ValueError):
    """
    Raised when the requested password length is below the safe minimum
    """


def generate_password(
    length: int = DEFAULT_GENERATED_PASSWORD_LENGTH,
    *,
    use_lowercase: bool = True,
    use_uppercase: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
) -> str:
    """
    Return a random password of the given length

    All character-pool flags after `length` are keyword-only (the *
    in the signature). That keeps call sites readable

        generate_password(20, use_symbols=False)

    is much clearer than

        generate_password(20, True, True, True, False)

    The function GUARANTEES at least one character from each enabled
    pool — without this, a 12-character password might randomly end
    up as all lowercase, which fails most "must contain a digit"
    rules even though it is technically random

    Parameters
    ----------
    length
        How many characters in the result. Must be at least
        MINIMUM_GENERATED_PASSWORD_LENGTH. Must also be at least
        as large as the number of enabled pools (we have to fit
        one character from each)
    use_lowercase, use_uppercase, use_digits, use_symbols
        Which character pools to draw from. At least one must be True

    Returns
    -------
    str
        A random password of exactly `length` characters

    Raises
    ------
    PasswordTooShortError
        If `length` is below the floor or below the number of pools
    ValueError
        If every pool flag is False
    """
    if length < MINIMUM_GENERATED_PASSWORD_LENGTH:
        raise PasswordTooShortError(
            f"Password length must be >= "
            f"{MINIMUM_GENERATED_PASSWORD_LENGTH}, got {length}"
        )

    # Build the lookup of enabled pools so we can pick one char from
    # each. This dict comprehension only includes pools whose flag is
    # True — any False flag is left out entirely
    enabled_pools = {
        "lower": LOWERCASE_LETTERS if use_lowercase else "",
        "upper": UPPERCASE_LETTERS if use_uppercase else "",
        "digit": DIGITS if use_digits else "",
        "symbol": SAFE_SYMBOLS if use_symbols else "",
    }
    enabled_pools = {k: v for k, v in enabled_pools.items() if v}

    if not enabled_pools:
        raise ValueError("At least one character pool must be enabled")

    if length < len(enabled_pools):
        raise PasswordTooShortError(
            f"length={length} is too small to include one character "
            f"from each of {len(enabled_pools)} enabled pools"
        )

    alphabet = "".join(enabled_pools.values())

    # Step 1: take ONE character from each enabled pool, guaranteeing
    # the password contains at least one of each kind
    required = [secrets.choice(pool) for pool in enabled_pools.values()]

    # Step 2: fill the rest from the combined alphabet
    fill_count = length - len(required)
    fill = [secrets.choice(alphabet) for _ in range(fill_count)]

    # Step 3: combine and shuffle. Shuffling matters — without it, the
    # required characters would always be at positions 0..N-1
    chars = required + fill
    _secure_shuffle(chars)

    return "".join(chars)


def _secure_shuffle(items: list[str]) -> None:
    """
    Shuffle a list in place using a cryptographically secure source

    The standard library's random.shuffle uses the predictable Mersenne
    Twister. We implement Fisher-Yates (also called Knuth shuffle) on
    top of secrets.randbelow so the order is unpredictable

    Mutates `items` in place — returns None
    """
    # Fisher-Yates: walk the list from the end to the beginning, and
    # at each position swap the current item with a randomly chosen
    # earlier item (or itself). This produces a uniform random
    # permutation if the random source is uniform — and secrets is
    for i in range(len(items) - 1, 0, -1):
        # randbelow(n) returns 0..n-1 uniformly. We need 0..i inclusive,
        # so we ask for i+1
        j = secrets.randbelow(i + 1)
        items[i], items[j] = items[j], items[i]
