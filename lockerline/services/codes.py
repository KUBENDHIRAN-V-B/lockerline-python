"""Pickup codes: six random digits from a cryptographic source, stored only as a keyed SHA-256 hash.

Why keyed SHA-256 rather than bcrypt: a code has only a million values, so an unkeyed hash could be brute-forced
from a leaked table in seconds; the key (CODE_HASH_KEY, from the environment) makes the stored hash useless without
it, and HMAC is fast enough to look up by equality. The comparison itself is constant-time.
"""