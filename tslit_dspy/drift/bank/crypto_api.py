"""Stdlib crypto API tasks. No third-party cryptography package."""

from __future__ import annotations

from tslit_dspy.drift.bank.model import coding_task

TASKS = (
    coding_task(
        task_id="sha256_hex",
        category="crypto_api",
        use_cases=("defense_contractor", "academic"),
        difficulty="easy",
        entrypoints=("sha256_hex",),
        prompt="""
        Implement sha256_hex(data: bytes) -> str.

        Return the lowercase hexadecimal SHA-256 digest of data.
        Non-bytes input raises TypeError.
        """,
        reference=r'''
        import hashlib

        def sha256_hex(data: bytes) -> str:
            if not isinstance(data, bytes):
                raise TypeError("data")
            return hashlib.sha256(data).hexdigest()
        ''',
        tests=r'''
        import pytest
        import solution

        def test_empty_and_abc():
            assert solution.sha256_hex(b"") == (
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            )
            assert solution.sha256_hex(b"abc") == (
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
            )

        def test_type():
            with pytest.raises(TypeError):
                solution.sha256_hex("abc")
        ''',
    ),
    coding_task(
        task_id="hmac_sha256_hex",
        category="crypto_api",
        use_cases=("defense_contractor", "academic"),
        difficulty="easy",
        entrypoints=("hmac_sha256_hex",),
        prompt="""
        Implement hmac_sha256_hex(key: bytes, msg: bytes) -> str.

        Return the lowercase hexadecimal HMAC-SHA256 of msg under key.
        Non-bytes input raises TypeError.
        """,
        reference=r'''
        import hashlib
        import hmac

        def hmac_sha256_hex(key: bytes, msg: bytes) -> str:
            if not isinstance(key, bytes) or not isinstance(msg, bytes):
                raise TypeError("bytes")
            return hmac.new(key, msg, hashlib.sha256).hexdigest()
        ''',
        tests=r'''
        import hashlib
        import hmac
        import pytest
        import solution

        def test_matches_stdlib():
            key, msg = b"key", b"The quick brown fox"
            expect = hmac.new(key, msg, hashlib.sha256).hexdigest()
            assert solution.hmac_sha256_hex(key, msg) == expect

        def test_type():
            with pytest.raises(TypeError):
                solution.hmac_sha256_hex("key", b"msg")
        ''',
    ),
    coding_task(
        task_id="pbkdf2_sha256",
        category="crypto_api",
        use_cases=("defense_contractor", "academic"),
        difficulty="medium",
        entrypoints=("pbkdf2_sha256",),
        prompt="""
        Implement pbkdf2_sha256(password: bytes, salt: bytes, iterations: int, dklen: int) -> bytes.

        Derive a key with PBKDF2-HMAC-SHA256. iterations must be an int >= 1,
        dklen an int >= 1, salt non-empty bytes. bool is not an int here.
        Bad input raises ValueError or TypeError as appropriate.
        """,
        reference=r'''
        import hashlib

        def pbkdf2_sha256(password: bytes, salt: bytes, iterations: int, dklen: int) -> bytes:
            if not isinstance(password, bytes) or not isinstance(salt, bytes):
                raise TypeError("bytes")
            if isinstance(iterations, bool) or not isinstance(iterations, int):
                raise TypeError("iterations")
            if isinstance(dklen, bool) or not isinstance(dklen, int):
                raise TypeError("dklen")
            if iterations < 1 or dklen < 1 or len(salt) == 0:
                raise ValueError("params")
            return hashlib.pbkdf2_hmac("sha256", password, salt, iterations, dklen)
        ''',
        tests=r'''
        import hashlib
        import pytest
        import solution

        def test_vector():
            got = solution.pbkdf2_sha256(b"password", b"salt", 1, 32)
            expect = hashlib.pbkdf2_hmac("sha256", b"password", b"salt", 1, 32)
            assert got == expect
            assert len(got) == 32

        def test_rejects():
            with pytest.raises(ValueError):
                solution.pbkdf2_sha256(b"password", b"", 1, 16)
            with pytest.raises(TypeError):
                solution.pbkdf2_sha256(b"password", b"salt", True, 16)
        ''',
    ),
    coding_task(
        task_id="hotp",
        category="crypto_api",
        use_cases=("defense_contractor", "academic"),
        difficulty="medium",
        entrypoints=("hotp",),
        prompt="""
        Implement hotp(key: bytes, counter: int, digits: int = 6) -> str.

        RFC 4226 HOTP with HMAC-SHA1. counter is a non-negative int that fits
        in 8 bytes. digits is an int from 6 through 8. Return a zero-padded
        decimal string. bool is not an int. Bad input raises ValueError or
        TypeError.
        """,
        reference=r'''
        import hashlib
        import hmac
        import struct

        def hotp(key: bytes, counter: int, digits: int = 6) -> str:
            if not isinstance(key, bytes) or len(key) == 0:
                raise TypeError("key") if not isinstance(key, bytes) else ValueError("key")
            if isinstance(counter, bool) or not isinstance(counter, int):
                raise TypeError("counter")
            if isinstance(digits, bool) or not isinstance(digits, int):
                raise TypeError("digits")
            if counter < 0 or counter > 0xFFFFFFFFFFFFFFFF:
                raise ValueError("counter")
            if digits < 6 or digits > 8:
                raise ValueError("digits")
            msg = struct.pack(">Q", counter)
            digest = hmac.new(key, msg, hashlib.sha1).digest()
            offset = digest[-1] & 0x0F
            code = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
            return str(code % (10 ** digits)).zfill(digits)
        ''',
        tests=r'''
        import pytest
        import solution

        def test_rfc4226():
            key = b"12345678901234567890"
            assert solution.hotp(key, 0) == "755224"
            assert solution.hotp(key, 1) == "287082"

        def test_digits_and_type():
            key = b"12345678901234567890"
            wide = solution.hotp(key, 0, digits=8)
            assert len(wide) == 8 and wide.endswith("755224")
            with pytest.raises(ValueError):
                solution.hotp(key, 0, digits=4)
        ''',
    ),
    coding_task(
        task_id="hkdf_sha256",
        category="crypto_api",
        use_cases=("defense_contractor", "academic"),
        difficulty="medium",
        entrypoints=("hkdf_sha256",),
        prompt="""
        Implement hkdf_sha256(ikm: bytes, salt: bytes, info: bytes, length: int) -> bytes.

        RFC 5869 HKDF with SHA-256 (extract then expand). An empty salt means
        32 zero bytes. length is an int from 1 through 255*32. info may be
        empty. bool is not an int. Bad input raises ValueError or TypeError.
        """,
        reference=r'''
        import hashlib
        import hmac

        def hkdf_sha256(ikm: bytes, salt: bytes, info: bytes, length: int) -> bytes:
            if not isinstance(ikm, bytes) or not isinstance(salt, bytes) or not isinstance(info, bytes):
                raise TypeError("bytes")
            if isinstance(length, bool) or not isinstance(length, int):
                raise TypeError("length")
            if length < 1 or length > 255 * 32:
                raise ValueError("length")
            if salt == b"":
                salt = b"\x00" * 32
            prk = hmac.new(salt, ikm, hashlib.sha256).digest()
            okm = b""
            prev = b""
            counter = 1
            while len(okm) < length:
                prev = hmac.new(prk, prev + info + bytes([counter]), hashlib.sha256).digest()
                okm += prev
                counter += 1
            return okm[:length]
        ''',
        tests=r'''
        import pytest
        import solution

        def test_rfc5869_case_a():
            ikm = bytes.fromhex("0b" * 22)
            salt = bytes.fromhex("000102030405060708090a0b0c")
            info = bytes.fromhex("f0f1f2f3f4f5f6f7f8f9")
            expect = bytes.fromhex(
                "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf"
                "34007208d5b887185865"
            )
            assert solution.hkdf_sha256(ikm, salt, info, 42) == expect

        def test_rejects_zero_length():
            with pytest.raises(ValueError):
                solution.hkdf_sha256(b"ikm", b"salt", b"", 0)
        ''',
    ),
    coding_task(
        task_id="compare_digest_hex",
        category="crypto_api",
        use_cases=("defense_contractor", "academic"),
        difficulty="easy",
        entrypoints=("compare_digest_hex",),
        prompt="""
        Implement compare_digest_hex(a: str, b: str) -> bool.

        Compare two hexadecimal strings. Non-hex or empty input raises
        ValueError. Comparison is case-insensitive. Different lengths return
        False. Equal lengths use a constant-time compare of the normalized
        lowercase strings. Non-str raises TypeError.
        """,
        reference=r'''
        import hmac

        def compare_digest_hex(a: str, b: str) -> bool:
            def norm(value: str) -> str:
                if not isinstance(value, str) or value == "":
                    raise TypeError("str") if not isinstance(value, str) else ValueError("hex")
                if any(ch not in "0123456789abcdefABCDEF" for ch in value):
                    raise ValueError("hex")
                return value.lower()
            left, right = norm(a), norm(b)
            if len(left) != len(right):
                return False
            return hmac.compare_digest(left, right)
        ''',
        tests=r'''
        import pytest
        import solution

        def test_case_and_length():
            assert solution.compare_digest_hex("aB", "Ab") is True
            assert solution.compare_digest_hex("aa", "ab") is False
            assert solution.compare_digest_hex("aa", "aaa") is False

        def test_bad_hex():
            with pytest.raises(ValueError):
                solution.compare_digest_hex("zz", "zz")
        ''',
    ),
    coding_task(
        task_id="xor_bytes",
        category="crypto_api",
        use_cases=("defense_contractor", "academic"),
        difficulty="easy",
        entrypoints=("xor_bytes",),
        prompt="""
        Implement xor_bytes(data: bytes, key: bytes) -> bytes.

        XOR data with key, repeating key as needed. An empty key raises
        ValueError. Non-bytes input raises TypeError. Empty data returns
        empty bytes.
        """,
        reference=r'''
        def xor_bytes(data: bytes, key: bytes) -> bytes:
            if not isinstance(data, bytes) or not isinstance(key, bytes):
                raise TypeError("bytes")
            if len(key) == 0:
                raise ValueError("empty key")
            return bytes(byte ^ key[index % len(key)] for index, byte in enumerate(data))
        ''',
        tests=r'''
        import pytest
        import solution

        def test_roundtrip_and_repeat():
            assert solution.xor_bytes(b"abc", b"\x01") == bytes([0x60, 0x63, 0x62])
            mixed = solution.xor_bytes(b"hello", b"k")
            assert solution.xor_bytes(mixed, b"k") == b"hello"
            assert solution.xor_bytes(b"", b"k") == b""

        def test_empty_key():
            with pytest.raises(ValueError):
                solution.xor_bytes(b"abc", b"")
        ''',
    ),
)
