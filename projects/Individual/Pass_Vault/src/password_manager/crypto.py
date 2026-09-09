"""
©AngelaMos | 2026
crypto.py

All the cryptography for the password manager lives in this one file

"Cryptography" is just the math we use to scramble data so nobody can
read it without the right key. Two big ideas live in this file, and
together they protect the user's vault

────────────────────────────────────────────────────────────────────
Idea 1: Key Derivation — turning a password into a key
────────────────────────────────────────────────────────────────────
When the user types their master password, we cannot use it directly
as an encryption key. Two reasons

  1. Passwords are short and predictable. A real key needs to be 256
     bits of randomness, but "hunter2" is maybe 50 bits at best
  2. If we used the password directly, an attacker who got their
     hands on the encrypted vault could try millions of passwords
     per second on a GPU until one worked

The fix is a Key Derivation Function (KDF). It takes the password
plus a random "salt" and runs them through a deliberately slow,
memory-hungry algorithm to produce a key. We use Argon2id — the
algorithm that won the 2015 Password Hashing Competition and is the
modern standard recommended by OWASP

Why slow on purpose? Because the legitimate user only does this ONCE
per session. An attacker has to do it for every password they guess.
Even a half-second delay multiplied by billions of guesses makes
brute-force impractical

────────────────────────────────────────────────────────────────────
Idea 2: Authenticated Encryption — locking and tamper-proofing
────────────────────────────────────────────────────────────────────
Once we have a key, we use it to encrypt the vault contents. We use
AES-256-GCM. AES is the encryption algorithm itself. GCM is a "mode"
that does two jobs at once

  1. Confidentiality — scrambles the data so nobody can read it
     without the key
  2. Authenticity — stamps the result with a tamper-proof seal. If
     anyone changes one byte of the ciphertext (or even the nonce),
     decryption refuses and raises an error

Without GCM (or another authenticated mode), an attacker could flip
bits in the encrypted file in ways that flip bits in the decrypted
plaintext, even without knowing the key. GCM defeats that

────────────────────────────────────────────────────────────────────
What this file exposes
────────────────────────────────────────────────────────────────────
  derive_key(...)        — Argon2id: master password + salt → 32-byte key
  generate_salt()        — fresh random salt for a new vault
  generate_nonce()       — fresh random nonce for every encryption
  encrypt(plaintext, key) — AES-256-GCM scramble
  decrypt(ciphertext, ...)— AES-256-GCM unscramble (raises on tampering)
  WrongPasswordError     — exception raised when decryption fails

Connects to
  vault.py — calls these functions to encrypt and decrypt vault data
  constants.py — pulls KDF and cipher parameters from here
"""

# Standard library: cryptographically-secure random bytes — used
# here to generate fresh salts and nonces. NEVER use `random` for
# anything security-related.
import secrets
# Standard library: a decorator that turns a class into a small,
# immutable data record without writing `__init__` boilerplate.
from dataclasses import dataclass

# Third-party (argon2-cffi): the password-hashing function we use
# as our KDF (key-derivation function). `Type` selects the Argon2id
# variant; `hash_secret_raw` returns raw key bytes (no PHC string).
from argon2.low_level import Type, hash_secret_raw
# Third-party (cryptography): the specific exception raised when
# AES-GCM decryption fails its authentication check — we catch it
# and turn it into our own WrongPasswordError.
from cryptography.exceptions import InvalidTag
# Third-party (cryptography): authenticated symmetric encryption.
# AES-GCM gives us both confidentiality AND tamper detection in one.
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Local: pull every magic number from the constants module — sizes
# and Argon2 cost parameters all live there, never in this file.
from password_manager.constants import (
    ARGON2_MEMORY_KIB,
    ARGON2_PARALLELISM,
    ARGON2_TIME_COST,
    KEY_LENGTH_BYTES,
    NONCE_LENGTH_BYTES,
    SALT_LENGTH_BYTES,
)


# =============================================================================
# Custom exceptions — give meaningful names to the errors we raise
# =============================================================================
# Defining our own exception classes (instead of just raising plain
# `Exception`) lets callers handle them precisely. The CLI layer can
# say "if WrongPasswordError, print a friendly message" without
# accidentally catching unrelated errors


class CryptoError(Exception):
    """
    Base class for every cryptography error we raise

    Catching this catches every error from this module
    """


class WrongPasswordError(CryptoError):
    """
    Raised when decryption fails

    GCM authentication failure means one of three things, and we
    cannot tell which without more context

      1. The user typed the wrong master password
      2. The vault file was tampered with
      3. The vault file is corrupted

    From the user's perspective, all three look the same: "I cannot
    open this vault." So we raise a single error and let the CLI
    show a single, honest message
    """


# =============================================================================
# KDF parameters — bundled so we can pass them around as one value
# =============================================================================


@dataclass(frozen = True, slots = True)
class KdfParameters:
    """
    The Argon2id tuning knobs used to derive a key

    `frozen=True` makes instances immutable — once created, they
    cannot be modified. `slots=True` makes them lightweight in
    memory. These two flags together give us a "value object" — a
    bundle of fields that behaves like a single value

    Why bundle them? Because the vault file stores these parameters
    alongside the ciphertext. If we change the defaults later, old
    vaults still decrypt correctly because they remember their own
    parameters

    Fields
    ------
    time_cost
        Number of passes Argon2 makes. Higher = slower = harder to crack
    memory_cost
        Memory in KiB. Higher = harder to attack with GPUs
    parallelism
        Threads Argon2 may use. Should match available cores
    """
    time_cost: int
    memory_cost: int
    parallelism: int

    @classmethod
    def defaults(cls) -> "KdfParameters":
        """
        Return the current recommended Argon2id parameters

        The values live in constants.py and are informed by the OWASP
        Password Storage Cheat Sheet. They are tuned for a single-user
        local password manager (parallelism=4 instead of the
        server-oriented parallelism=1) — see constants.py for the
        full reasoning
        """
        return cls(
            time_cost = ARGON2_TIME_COST,
            memory_cost = ARGON2_MEMORY_KIB,
            parallelism = ARGON2_PARALLELISM,
        )


# =============================================================================
# Random byte generation — salts and nonces
# =============================================================================
# Both salts and nonces need to be unpredictable. We use the `secrets`
# module from the Python standard library. It pulls bytes from the
# operating system's cryptographically secure random source
# (/dev/urandom on Linux, BCryptGenRandom on Windows)
#
# DO NOT use `random.randbytes()` for this. The `random` module is
# fast but predictable — given enough output, an attacker can predict
# future values. The `secrets` module is built for exactly this case


def generate_salt() -> bytes:
    """
    Return SALT_LENGTH_BYTES of fresh, unpredictable random bytes

    The salt is mixed in with the password before key derivation, so
    that two users picking the same password get DIFFERENT keys. It
    also defeats "rainbow table" attacks where an attacker
    pre-computes a giant lookup table of common-password → key

    The salt is NOT secret — we store it in plain text inside the
    vault file. Its job is to be unique, not hidden

    Returns
    -------
    bytes
        A new random byte string of length SALT_LENGTH_BYTES (16 bytes)
    """
    # secrets.token_bytes(n) returns n random bytes from the OS-level
    # cryptographic random pool. Same call we would use to generate
    # session tokens or API keys
    return secrets.token_bytes(SALT_LENGTH_BYTES)


def generate_nonce() -> bytes:
    """
    Return NONCE_LENGTH_BYTES of fresh, unpredictable random bytes

    A nonce ("number used once") is generated FRESH for every single
    encryption. Reusing a nonce with the same key in GCM mode is
    catastrophic — it leaks plaintext to anyone watching. So we
    generate a new one every time we save the vault

    GCM allows nonces up to 2^32 messages safely with random 12-byte
    nonces, which is far more vault saves than any human will ever
    perform. So random generation is fine here

    Returns
    -------
    bytes
        A new random byte string of length NONCE_LENGTH_BYTES (12 bytes)
    """
    return secrets.token_bytes(NONCE_LENGTH_BYTES)


# =============================================================================
# Key derivation — the slow part
# =============================================================================


def derive_key(
    master_password: str,
    salt: bytes,
    parameters: KdfParameters | None = None,
) -> bytes:
    """
    Turn a master password and a salt into a 32-byte encryption key

    This is the SLOW step. On a modern laptop with the default
    parameters, expect about 0.3–1 second per call. That is on
    purpose — it is the cost an attacker must pay for every guess

    The output is suitable as input to AES-256-GCM (which wants
    exactly 32 bytes of key material)

    Parameters
    ----------
    master_password
        What the user typed at the prompt, as a normal Python string
    salt
        The vault's salt (16 random bytes). Passing the SAME password
        and SAME salt always produces the SAME key, which is how we
        re-derive the key when the user comes back later
    parameters
        Argon2id tuning. Defaults to the project's recommended values
        (see KdfParameters.defaults). The vault file stores whatever
        was used so old vaults keep working when defaults change

    Returns
    -------
    bytes
        A 32-byte (256-bit) key, ready to hand to AES-256-GCM

    Notes
    -----
    Argon2 needs BYTES, not strings. Cryptographic libraries always
    work in raw bytes because that is the natural form for hashing
    and arithmetic. We encode the password to UTF-8 bytes here
    """
    # Refuse an empty password outright. Argon2 itself would happily
    # derive a key from b"" + the salt, but the resulting "lock" has
    # effectively no secret in it — anyone who steals the vault file
    # can re-derive the same key from the public salt. We treat this
    # as a programming error and raise loudly
    if not master_password:
        raise ValueError("master_password must not be empty")

    # Default to recommended parameters if the caller did not specify.
    # We do this lazily (`is None` check) instead of using
    # `parameters = KdfParameters.defaults()` as a default argument,
    # because Python evaluates default arguments ONCE at function
    # definition time, which would make the default a singleton.
    # That is fine for an immutable dataclass, but the lazy pattern
    # is the safer general habit
    if parameters is None:
        parameters = KdfParameters.defaults()

    # Strings live in memory as Unicode code points. Argon2 needs raw
    # bytes. .encode("utf-8") is the standard way to convert
    password_bytes = master_password.encode("utf-8")

    # hash_secret_raw is the low-level Argon2 function. The argon2-cffi
    # library also offers a high-level PasswordHasher that produces a
    # formatted string — we do NOT want that here. We want the raw
    # 32 bytes of key material to feed into AES
    return hash_secret_raw(
        secret = password_bytes,
        salt = salt,
        time_cost = parameters.time_cost,
        memory_cost = parameters.memory_cost,
        parallelism = parameters.parallelism,
        hash_len = KEY_LENGTH_BYTES,
        # Type.ID = Argon2id, the recommended variant
        # Argon2id resists both side-channel attacks (Argon2i strength)
        # and GPU-cracking attacks (Argon2d strength) — best of both
        type = Type.ID,
    )


# =============================================================================
# Symmetric encryption — AES-256-GCM
# =============================================================================
# "Symmetric" means the same key is used to encrypt AND decrypt
# (as opposed to public-key crypto where the keys differ)
#
# We use the high-level AESGCM class from the cryptography library.
# It bundles the cipher, the authentication tag, and constant-time
# tag verification into a single API. Using AES-GCM "by hand" with
# raw primitives is one of the easier ways to get cryptography wrong


def encrypt(plaintext: bytes, key: bytes) -> tuple[bytes, bytes]:
    """
    Encrypt plaintext bytes with AES-256-GCM and return (nonce, ciphertext)

    A new random nonce is generated for every call. The caller MUST
    store the nonce alongside the ciphertext — without it, decryption
    is impossible

    The "ciphertext" returned actually contains both the encrypted
    data AND a 16-byte authentication tag appended to the end. The
    AESGCM library handles this concatenation automatically. The
    tag is what makes the encryption tamper-evident

    Parameters
    ----------
    plaintext
        Raw bytes to encrypt. Anything — JSON-encoded vault entries,
        plain text, an image. The cipher does not care
    key
        The 32-byte key from derive_key. Wrong size raises ValueError

    Returns
    -------
    tuple[bytes, bytes]
        (nonce, ciphertext_with_tag). Both must be stored to allow
        later decryption
    """
    # Construct a cipher object bound to our key. AESGCM validates
    # the key size: must be 16, 24, or 32 bytes (AES-128, 192, or 256)
    cipher = AESGCM(key)

    # Fresh nonce for every encryption — never reuse with the same key
    nonce = generate_nonce()

    # encrypt() returns ciphertext concatenated with the auth tag.
    # `associated_data` is for data we want authenticated but NOT
    # encrypted (like a packet header). We do not have any, so None
    ciphertext = cipher.encrypt(
        nonce = nonce,
        data = plaintext,
        associated_data = None,
    )

    return nonce, ciphertext


def decrypt(ciphertext: bytes, nonce: bytes, key: bytes) -> bytes:
    """
    Decrypt ciphertext produced by encrypt() and verify it was not tampered with

    If the key is wrong, the nonce is wrong, or anyone modified even
    one byte of the ciphertext, the GCM authentication tag will not
    validate and we raise WrongPasswordError. We do NOT distinguish
    between "wrong password" and "tampered file" — they look the same
    cryptographically and exposing the difference helps attackers

    Parameters
    ----------
    ciphertext
        The output from encrypt() — encrypted data + 16-byte auth tag
    nonce
        The same nonce used during encryption
    key
        The 32-byte key derived from the master password

    Returns
    -------
    bytes
        The original plaintext bytes

    Raises
    ------
    WrongPasswordError
        If decryption fails for any reason (wrong key, wrong nonce,
        modified ciphertext, corruption)
    """
    cipher = AESGCM(key)

    # InvalidTag is the cryptography library's signal that the auth
    # tag did not match. We catch it and re-raise as our own error
    # so callers do not need to know about cryptography internals
    try:
        return cipher.decrypt(
            nonce = nonce,
            data = ciphertext,
            associated_data = None,
        )
    except InvalidTag as exc:
        # `from exc` preserves the original traceback for debugging
        # while still raising our cleaner exception type
        raise WrongPasswordError(
            "Decryption failed: wrong master password or corrupted vault"
        ) from exc
