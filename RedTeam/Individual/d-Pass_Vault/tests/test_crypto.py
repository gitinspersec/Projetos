"""
©AngelaMos | 2026
test_crypto.py

Tests for the crypto module — KDF (Argon2id) and authenticated
encryption (AES-256-GCM)

These tests verify the cryptographic primitives in isolation. They
do not touch disk and they do not depend on the vault module. Each
test exercises ONE property of ONE function, so a failure points
directly at the broken piece

────────────────────────────────────────────────────────────────────
What is "the crypto" doing that we need to verify?
────────────────────────────────────────────────────────────────────
Two cryptographic ideas live in crypto.py

  1. Key derivation — turning a master password into a 32-byte AES
     key. The KDF must be
        deterministic    so the user can come back tomorrow and
                         re-derive the SAME key from their password
        salt-sensitive   so two users with the same password get
                         DIFFERENT keys (defeats rainbow tables)
        slow             so brute-force is expensive
     We test all three properties below

  2. Authenticated encryption — encrypting bytes with AES-256-GCM in
     a way that ANY tampering (wrong key, modified ciphertext, or
     modified nonce) causes decryption to refuse. GCM gives us this
     for free; we verify each failure mode in turn

────────────────────────────────────────────────────────────────────
Why TEST_KDF_PARAMETERS exists
────────────────────────────────────────────────────────────────────
Production Argon2 parameters are expensive on purpose (~300 ms per
derivation). Running 20 tests at that cost would mean a 6-second
test suite, which discourages running tests during development.
TEST_KDF_PARAMETERS (in conftest.py) uses the absolute minimum
Argon2-acceptable values — derivation finishes in milliseconds while
still exercising the same code path. Crypto correctness does not
depend on parameter strength

────────────────────────────────────────────────────────────────────
A short pytest primer for this file
────────────────────────────────────────────────────────────────────
`assert <expr>`
    pytest fails the test if <expr> is falsy

`pytest.raises(SomeError)`
    Context manager that requires the block to raise SomeError. This
    is how we verify "refuses bad input" cases — wrong password,
    tampered ciphertext, modified nonce

`bytearray(...)` vs `bytes(...)`
    Python's bytes is IMMUTABLE; you cannot do `b[0] = 0x42`. To
    flip a bit for a tampering test, copy into a bytearray (mutable),
    mutate, then cast back to bytes when handing it to a function
    that expects bytes
"""

# Third-party: the test runner. Used for `pytest.raises` and the
# `@pytest.mark.parametrize` decorator below.
import pytest

# Local: every crypto helper under test — the dataclass, the error
# type, the encrypt/decrypt pair, and the random-bytes helpers.
from password_manager.crypto import (
    KdfParameters,
    WrongPasswordError,
    decrypt,
    derive_key,
    encrypt,
    generate_nonce,
    generate_salt,
)
# Local: byte-length constants — we assert outputs match these
# without ever hard-coding 32 or 16 inside this file.
from password_manager.constants import (
    KEY_LENGTH_BYTES,
    NONCE_LENGTH_BYTES,
    SALT_LENGTH_BYTES,
)
# Local: the fast KDF parameters defined in conftest. Importing
# directly (rather than via a fixture) keeps test bodies short.
from tests.conftest import TEST_KDF_PARAMETERS


# =============================================================================
# Random byte generation — salts and nonces must be the right size + unpredictable
# =============================================================================


def test_generate_salt_returns_correct_length() -> None:
    """
    Verify generate_salt() produces exactly SALT_LENGTH_BYTES of output

    The salt length is part of our on-disk format contract — change
    it without updating SALT_LENGTH_BYTES and every existing vault
    would fail to decrypt. The most basic invariant to pin down
    """
    salt = generate_salt()
    assert len(salt) == SALT_LENGTH_BYTES


def test_generate_salt_returns_different_values_on_each_call() -> None:
    """
    Verify generate_salt() yields a fresh random value every time

    The whole point of a salt is that two users with the same
    password get different keys. If generate_salt() returned the same
    bytes every call, that property collapses

    We collect 50 salts into a set; if the source is random, all 50
    will be unique with overwhelming probability (16 random bytes =
    128 bits of entropy, collisions are astronomically unlikely).
    A failure here means `secrets.token_bytes` is broken or has been
    replaced with a non-secure source
    """
    salts = {generate_salt() for _ in range(50)}
    # 50 unique 16-byte values is overwhelmingly likely if the source
    # is truly random. A failure here means token_bytes is broken
    assert len(salts) == 50


def test_generate_nonce_returns_correct_length() -> None:
    """
    Verify generate_nonce() produces exactly NONCE_LENGTH_BYTES of output

    AES-GCM's recommended nonce length is 12 bytes. Other lengths are
    technically valid but degrade security guarantees. We pin to
    NONCE_LENGTH_BYTES (12) and verify here so an accidental refactor
    to 16 or 8 would fail this test immediately
    """
    nonce = generate_nonce()
    assert len(nonce) == NONCE_LENGTH_BYTES


def test_generate_nonce_returns_different_values_on_each_call() -> None:
    """
    Verify nonces are fresh on every call — the most security-critical property in the file

    Nonce reuse in GCM is CATASTROPHIC. Two messages encrypted with
    the same (key, nonce) pair leak the XOR of the plaintexts to
    anyone watching, and let an attacker forge messages. So
    `generate_nonce` is the most security-critical function here,
    and "no two values are ever the same" is the property that matters

    Same 50-into-a-set check as for salts. Different values = working
    """
    nonces = {generate_nonce() for _ in range(50)}
    assert len(nonces) == 50


# =============================================================================
# Key derivation — Argon2id properties
# =============================================================================


def test_derive_key_returns_correct_length() -> None:
    """
    Verify derive_key produces exactly KEY_LENGTH_BYTES of output

    KEY_LENGTH_BYTES is 32 — what AES-256-GCM expects. The Argon2
    library lets us request any output length; if we accidentally
    asked for 16 we would get an AES-128 vault, and if we asked for
    64 the cipher would refuse to construct at all
    """
    key = derive_key(
        "password",
        generate_salt(),
        TEST_KDF_PARAMETERS,
    )
    assert len(key) == KEY_LENGTH_BYTES


def test_derive_key_is_deterministic() -> None:
    """
    Verify derive_key is deterministic — same inputs always produce the same key

    This is THE property that makes the password manager work. When
    the user types their master password tomorrow, we must derive
    the EXACT same key we used to encrypt the vault yesterday. If
    Argon2 were non-deterministic (say, mixed in a timestamp
    internally), the user could never unlock their vault again

    Notice we generate the salt ONCE and reuse it for both
    derivations — that is what isolates the "same inputs" condition
    """
    salt = generate_salt()
    key_a = derive_key("hunter2", salt, TEST_KDF_PARAMETERS)
    key_b = derive_key("hunter2", salt, TEST_KDF_PARAMETERS)
    assert key_a == key_b


def test_derive_key_different_passwords_yield_different_keys() -> None:
    """
    Verify changing the password (with the salt held constant) yields a different key

    This is the basic "the password matters" property. If derive_key
    produced the same key for "password-a" and "password-b" with the
    same salt, the function would be ignoring its first argument —
    which would mean every vault could be unlocked with any password.
    Catastrophic
    """
    salt = generate_salt()
    key_a = derive_key("password-a", salt, TEST_KDF_PARAMETERS)
    key_b = derive_key("password-b", salt, TEST_KDF_PARAMETERS)
    assert key_a != key_b


def test_derive_key_different_salts_yield_different_keys() -> None:
    """
    Verify changing the salt (with the password held constant) yields a different key

    The salt is what defeats rainbow tables — two users with the same
    password must end up with different keys because their salts
    differ. Without this property, an attacker who steals 10 million
    encrypted vaults could pre-compute keys for the top 1000 common
    passwords and instantly unlock every vault belonging to anyone
    who picked one
    """
    key_a = derive_key("hunter2", generate_salt(), TEST_KDF_PARAMETERS)
    key_b = derive_key("hunter2", generate_salt(), TEST_KDF_PARAMETERS)
    assert key_a != key_b


def test_kdf_parameters_defaults_are_immutable() -> None:
    """
    Verify KdfParameters instances reject attribute assignment after construction

    `frozen=True` on the dataclass is what makes this work. Trying
    to assign to a frozen instance raises AttributeError at runtime.
    We confirm here so a future refactor that drops `frozen=True`
    would fail this test immediately

    The `# type: ignore[misc]` comment tells mypy "yes, we KNOW this
    line is illegal — that is the whole point of the test." Without
    the comment, type-checking would refuse before pytest could even
    run the test
    """
    params = KdfParameters.defaults()
    with pytest.raises(AttributeError):
        params.time_cost = 999  # type: ignore[misc]


def test_derive_key_rejects_empty_password() -> None:
    """
    Verify derive_key refuses an empty master password

    Argon2 itself would happily derive a key from b"" + the salt,
    but the resulting "lock" has effectively no secret in it —
    anyone who steals the vault file can re-derive the same key
    from the public salt. derive_key refuses outright as a
    programming-error floor, and we verify here that the refusal
    takes the form of a ValueError
    """
    with pytest.raises(ValueError):
        derive_key("", generate_salt(), TEST_KDF_PARAMETERS)


# =============================================================================
# Encrypt / decrypt round-trip — the basic AES-GCM contract
# =============================================================================


def test_encrypt_decrypt_round_trip() -> None:
    """
    Verify decrypt(encrypt(x)) returns the original x

    The most basic encryption test imaginable: encrypt some bytes,
    decrypt them, get the same bytes back. If this ever fails, the
    encryption module is fundamentally broken and nothing else in
    the test suite will be meaningful

    Notice the structure: we derive a key from a password (same flow
    as production), encrypt, decrypt, compare. We use a real
    password+salt rather than hard-coded key bytes so the full
    derive-then-encrypt path is exercised
    """
    salt = generate_salt()
    key = derive_key("master", salt, TEST_KDF_PARAMETERS)
    plaintext = b"the quick brown fox jumps over the lazy dog"

    nonce, ciphertext = encrypt(plaintext, key)
    recovered = decrypt(ciphertext, nonce, key)

    assert recovered == plaintext


def test_encrypt_produces_fresh_nonce_each_call() -> None:
    """
    Verify two calls to encrypt() with the same plaintext+key still produce different output

    Each encrypt() call internally calls generate_nonce(). Because
    the nonce is fresh, the ciphertext for the same plaintext+key
    WILL differ across calls — both the nonce bytes and the
    ciphertext bytes

    If a future refactor accidentally cached the nonce (or used a
    counter that reset), this test would catch it. Nonce reuse with
    the same key in GCM is one of the all-time worst cryptographic
    mistakes — see "Nonce Disrespecting Adversaries" if you want a
    deep dive
    """
    salt = generate_salt()
    key = derive_key("master", salt, TEST_KDF_PARAMETERS)
    plaintext = b"hello"

    nonce1, ct1 = encrypt(plaintext, key)
    nonce2, ct2 = encrypt(plaintext, key)

    # Same plaintext + same key but different nonce → different ciphertext
    assert nonce1 != nonce2
    assert ct1 != ct2


def test_encrypt_handles_empty_plaintext() -> None:
    """
    Verify encrypt() handles an empty bytes object cleanly

    The empty plaintext is a real edge case: a freshly-initialized
    vault encrypts an empty entries dict, which JSON-serializes to
    b"{}" — but if a user deletes every entry, we end up in the
    same place. Pinning down b"" specifically here guards against
    off-by-one bugs in length-prefix code or similar
    """
    salt = generate_salt()
    key = derive_key("master", salt, TEST_KDF_PARAMETERS)
    nonce, ciphertext = encrypt(b"", key)
    assert decrypt(ciphertext, nonce, key) == b""


# =============================================================================
# Decryption refuses tampered or wrong-key input — GCM authentication
# =============================================================================


def test_decrypt_with_wrong_key_raises_wrong_password_error() -> None:
    """
    Verify decrypt() refuses when the key does not match the encryption key

    This is the "wrong master password" path. Encrypt with one
    derived key, attempt to decrypt with a DIFFERENT derived key,
    GCM refuses because the authentication tag will not validate.
    We re-raise that low-level failure as WrongPasswordError (in
    crypto.py) so the CLI can show the user a clean message instead
    of leaking cryptography-library internals

    This is the primary security property of the entire password
    manager: only the correct master password can unlock the vault
    """
    salt = generate_salt()
    correct_key = derive_key("correct", salt, TEST_KDF_PARAMETERS)
    wrong_key = derive_key("wrong", salt, TEST_KDF_PARAMETERS)
    nonce, ciphertext = encrypt(b"secret", correct_key)

    with pytest.raises(WrongPasswordError):
        decrypt(ciphertext, nonce, wrong_key)


def test_decrypt_with_modified_ciphertext_raises() -> None:
    """
    Verify flipping any byte of the ciphertext causes decryption to fail

    This is GCM's "tamper-evidence" property. The authentication tag
    appended to the ciphertext covers every byte of it — flip one
    bit and the tag no longer matches, GCM refuses. We do NOT get a
    quietly-mangled plaintext back; we get an exception

    The bit-flip we perform — `tampered[middle] ^= 0x01` — uses XOR
    against 0x01 to flip the lowest bit of the byte at the middle of
    the ciphertext. The exact bit does not matter; ANY change to ANY
    byte of the ciphertext must trip the auth tag
    """
    salt = generate_salt()
    key = derive_key("master", salt, TEST_KDF_PARAMETERS)
    nonce, ciphertext = encrypt(b"important data", key)

    # Flip one bit somewhere in the middle. We need a mutable copy
    # because Python's `bytes` is immutable — `b[0] = 0x42` would
    # raise. `bytearray` is the mutable cousin. After flipping we
    # cast back to bytes for the decrypt call (which expects bytes,
    # not bytearray, as a matter of type-strict API discipline)
    middle = len(ciphertext) // 2
    tampered = bytearray(ciphertext)
    tampered[middle] ^= 0x01
    tampered_bytes = bytes(tampered)

    with pytest.raises(WrongPasswordError):
        decrypt(tampered_bytes, nonce, key)


def test_decrypt_with_modified_nonce_raises() -> None:
    """
    Verify modifying the nonce also causes decryption to fail

    Many beginners assume only the ciphertext is authenticated. In
    fact GCM authenticates the (nonce, ciphertext) pair together —
    if an attacker swaps the nonce for some other valid-looking
    value, the tag still will not match and decryption refuses

    Flipping every bit of the first nonce byte with `^= 0xFF` is a
    high-confidence way to produce a definitively-different nonce
    (a tampered byte may collide with the original; flipping every
    bit guarantees it does not)
    """
    salt = generate_salt()
    key = derive_key("master", salt, TEST_KDF_PARAMETERS)
    nonce, ciphertext = encrypt(b"important data", key)

    bad_nonce = bytearray(nonce)
    bad_nonce[0] ^= 0xFF  # flip every bit of the first byte

    with pytest.raises(WrongPasswordError):
        decrypt(ciphertext, bytes(bad_nonce), key)
