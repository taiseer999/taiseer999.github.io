# -*- coding: utf-8 -*-
import base64
from typing import List, Union

KEY = 0x42

def deobfuscate(data: Union[List[int], str]) -> str:
    if not data or not isinstance(data, list):
        return ""
    return "".join(chr(b ^ KEY) for b in data)

def obfuscate(data: str) -> List[int]:
    if not data:
        return []
    return [ord(c) ^ KEY for c in data]

def _b(s):
    return base64.b64decode(s).decode("utf-8")

startup_snippet = _b("IyAtLS0tLSBBTSBMaXRlIFRyYWt0IHN0YXJ0dXAgc3luYyBwYXRjaCBCRUdJTiAtLS0tLQpkZWYgd2FpdF9mb3JfYW1fdHJha3QodGltZW91dD01LCBtYXhfYWdlPTMwMCk6CiAgICBpbXBvcnQgdGltZQogICAgaW1wb3J0IHhibWMKICAgIGltcG9ydCB4Ym1jYWRkb24KCiAgICB3YWl0ZWQgPSAwCgogICAgd2hpbGUgd2FpdGVkIDwgdGltZW91dDoKICAgICAgICB0cnk6CiAgICAgICAgICAgIGFtID0geGJtY2FkZG9uLkFkZG9uKCdzY3JpcHQubW9kdWxlLmFjY3RtZ3InKQogICAgICAgICAgICByZWFkeSA9IGFtLmdldFNldHRpbmcoJ2FtX3RyYWt0X3JlYWR5JykKICAgICAgICAgICAgbGFzdF9wcmVwYXJlID0gYW0uZ2V0U2V0dGluZygnYW1fbGFzdF9wcmVwYXJlJykKCiAgICAgICAgICAgIGlmIHJlYWR5ID09ICd0cnVlJyBhbmQgbGFzdF9wcmVwYXJlOgogICAgICAgICAgICAgICAgYWdlID0gaW50KHRpbWUudGltZSgpKSAtIGludChsYXN0X3ByZXBhcmUpCiAgICAgICAgICAgICAgICBpZiAwIDw9IGFnZSA8PSBtYXhfYWdlOgogICAgICAgICAgICAgICAgICAgIHJldHVybiBUcnVlCiAgICAgICAgZXhjZXB0IEV4Y2VwdGlvbjoKICAgICAgICAgICAgcGFzcwoKICAgICAgICB4Ym1jLnNsZWVwKDEwMDApCiAgICAgICAgd2FpdGVkICs9IDEKCiAgICByZXR1cm4gRmFsc2UKCndhaXRfZm9yX2FtX3RyYWt0KCkKIyAtLS0tLSBBTSBMaXRlIFRyYWt0IHN0YXJ0dXAgc3luYyBwYXRjaCBFTkQgLS0tLS0KCg==")
startup_marker = "# ----- AM Lite Trakt startup sync patch BEGIN -----"
