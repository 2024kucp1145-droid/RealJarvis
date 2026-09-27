# -*- coding: utf-8 -*-
"""
tests/test_critical_fixes.py
============================
Regression tests for the critical security/correctness fixes:

  1. daemon_api_server.py - hardcoded auth token fallback removed, webhook
     signature bypass closed.
  2. ast_safety_scanner.py - blocklist -> allowlist (bypass attempts blocked).
  3. memory.py - deterministic offline embeddings + pinned embedding dimension.
  4. config.py - PBKDF2 password hashing (legacy SHA-256 still verifies).

Run:  venv\\Scripts\\python.exe -m pytest tests -v
"""

import hashlib
import hmac
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ===========================================================================
# 1. AST SAFETY SCANNER  (allowlist enforcement)
# ===========================================================================

SAFE_SKILL = '''
import os.path
import json
from datetime import datetime


def execute(context=None):
    data = {"time": datetime.now().isoformat()}
    joined = os.path.join("logs", "today.txt")
    return {"status": "success", "path": joined, "data": data}
'''

SAFE_READ_ONLY = '''
def execute(context=None):
    with open("C:/RealJarvis_v2/notes.json", "r") as f:
        return f.read()
'''


@pytest.fixture(scope="module")
def scanner():
    import ast_safety_scanner
    return ast_safety_scanner.scanner


def test_allowlist_scanner_accepts_safe_skill(scanner):
    result = scanner.scan_code(SAFE_SKILL)
    assert result.syntax_valid is True
    assert result.has_entrypoint is True
    assert result.is_safe is True, f"Safe skill should pass, got: {result.issues}"


def test_scanner_allows_read_only_open(scanner):
    result = scanner.scan_code(SAFE_READ_ONLY)
    assert result.is_safe is True, f"Read-only open should pass: {result.issues}"


def test_scanner_requires_execute_entrypoint(scanner):
    result = scanner.scan_code("import json\n\n\ndef helper():\n    return 1\n")
    assert result.is_safe is False
    assert any("execute" in issue for issue in result.issues)


def test_scanner_reports_imported_modules_for_dependency_check(scanner):
    result = scanner.scan_code(SAFE_SKILL)
    assert "os.path" in result.imported_modules
    assert "json" in result.imported_modules

BLOCKED_SKILL_CASES = [
    # subprocess shell-out (blocklist me pehle ye pakda hi nahi jaata tha)
    (
        'import subprocess\n\n\ndef execute(context=None):\n'
        '    return subprocess.run(["format", "C:"], shell=True)\n',
        "subprocess",
    ),
    # os.system - module root blocked
    (
        'import os\n\n\ndef execute(context=None):\n'
        '    return os.system("shutdown /s /t 0")\n',
        "os",
    ),
    # aliased import bypass attempt
    (
        'import os as o\n\n\ndef execute(context=None):\n'
        '    return o.remove("important.txt")\n',
        "os",
    ),
    # from subprocess import run
    (
        'from subprocess import run\n\n\ndef execute(context=None):\n'
        '    return run(["cmd", "/c", "dir"])\n',
        "subprocess",
    ),
    # shutil.move
    (
        'import shutil\n\n\ndef execute(context=None):\n'
        '    return shutil.move("a", "b")\n',
        "shutil",
    ),
    # dynamic eval
    (
        'def execute(context=None):\n    return eval("2+2")\n',
        "eval",
    ),
    # __import__ escape
    (
        'def execute(context=None):\n'
        '    mod = __import__("os")\n    return mod.listdir(".")\n',
        "__import__",
    ),
    # ctypes / native
    (
        'import ctypes\n\n\ndef execute(context=None):\n'
        '    return ctypes.windll.kernel32\n',
        "ctypes",
    ),
    # wildcard import
    (
        'from os import *\n\n\ndef execute(context=None):\n    return 1\n',
        "Wildcard",
    ),
    # file write via open()
    (
        'def execute(context=None):\n'
        '    return open("payload.py", "w").write("x")\n',
        "open",
    ),
    # sandbox escape via dunder attribute
    (
        'def execute(context=None):\n'
        '    return ().__class__.__bases__\n',
        "__class__",
    ),
    # getattr string-based escape
    (
        'def execute(context=None):\n'
        '    target = 1\n'
        '    return getattr(target, "__globals__")\n',
        "__globals__",
    ),
    # protected Windows path literal
    (
        'def execute(context=None):\n'
        '    return "c:\\\\windows\\\\system32"\n',
        "protected Windows system path",
    ),
    # relative import
    (
        'from . import evil\n\n\ndef execute(context=None):\n    return 1\n',
        "Relative import",
    ),
]


@pytest.mark.parametrize("code, expected_fragment", BLOCKED_SKILL_CASES)
def test_allowlist_scanner_blocks_bypass_attempts(scanner, code, expected_fragment):
    result = scanner.scan_code(code)
    assert result.is_safe is False, f"Should have been blocked: {code}"
    assert any(
        expected_fragment.lower() in issue.lower() for issue in result.issues
    ), f"Expected issue mentioning '{expected_fragment}', got {result.issues}"


# ===========================================================================
# 2. MEMORY - deterministic embeddings + dimension contract
# ===========================================================================


def test_stable_hash_is_deterministic_across_processes():
    """Built-in hash() randomized tha - blake2b across processes same hona chahiye."""
    probe = "import memory;print(memory._stable_hash('jarvis_memory_probe', 512))"
    env = dict(os.environ)
    outputs = set()
    for seed in ("0", "1", "12345"):
        env["PYTHONHASHSEED"] = seed
        out = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        assert out.returncode == 0, out.stderr
        outputs.add(out.stdout.strip())
    assert len(outputs) == 1, f"Hash changed across processes: {outputs}"


def test_local_fallback_embedding_dimension_and_similarity():
    import memory

    vec = memory._generate_local_fallback_embedding("jarvis remembers my project")
    assert len(vec) == memory.LOCAL_FALLBACK_DIM

    same_a = memory._generate_local_fallback_embedding("mera project RealJarvis hai")
    same_b = memory._generate_local_fallback_embedding("mera project RealJarvis hai")
    assert same_a == same_b

    related = memory._generate_local_fallback_embedding("RealJarvis project memory")
    unrelated = memory._generate_local_fallback_embedding("banana apple orange fruit")
    assert memory.cosine_similarity(same_a, related) > memory.cosine_similarity(
        same_a, unrelated
    )


def test_gemini_embedding_dim_is_pinned():
    import memory

    assert memory.GEMINI_EMBEDDING_DIM == 768
    assert memory.GEMINI_EMBEDDING_MODEL == "gemini-embedding-001"
    source = (PROJECT_ROOT / "memory.py").read_text(encoding="utf-8")
    assert "output_dimensionality" in source, (
        "Gemini embedding dim pinned nahi hai - 3072 vs 512 mismatch wapas aa jayega."
    )


def test_local_query_matches_locally_stored_doc(tmp_path, monkeypatch):
    """Offline mode me store ki hui memory offline query se match honi chahiye."""
    import memory

    monkeypatch.setattr(memory, "DB_PATH", str(tmp_path / "memory_offline.db"))
    monkeypatch.setattr(memory, "_EMBEDDING_CACHE", {})
    memory.init_db()

    monkeypatch.setattr(
        memory,
        "generate_embedding",
        lambda text: (memory._generate_local_fallback_embedding(text), "local"),
    )
    memory.store_vector(
        "note", "offline-1", "mera favourite database sqlite hai", sync=True
    )

    results = memory.search_vector_memory("favourite database sqlite", threshold=0.05)
    assert results, "Offline vector memory ne apni hi stored entry match nahi ki."
    assert any("sqlite" in row["text"] for row in results)


def test_retrieval_handles_incompatible_dimension_space(tmp_path, monkeypatch):
    """Legacy incompatible-space doc par crash ya jhoota match nahi hona chahiye."""
    import memory

    monkeypatch.setattr(memory, "DB_PATH", str(tmp_path / "memory_legacy.db"))
    monkeypatch.setattr(memory, "_EMBEDDING_CACHE", {})
    memory.init_db()

    def fake_embedding(text):
        if text == "legacy doc":
            return ([0.1] * 1024, "legacy-3072-doc")
        return (memory._generate_local_fallback_embedding(text), "local")

    monkeypatch.setattr(memory, "generate_embedding", fake_embedding)
    memory.store_vector("note", "legacy-1", "legacy doc", sync=True)

    results = memory.search_vector_memory("legacy doc", threshold=0.0)
    for row in results:
        assert row["score"] >= 0.0


# ===========================================================================
# 3. CONFIG - password hashing upgrade
# ===========================================================================


def test_pbkdf2_hash_format_and_verification(monkeypatch):
    import config

    hashed = config.hash_password("S3cret-Pass!")
    assert hashed.startswith("pbkdf2_sha256$"), hashed
    assert len(hashed.split("$")) == 4

    monkeypatch.setattr(config, "PASSWORD_HASH", hashed)
    assert config.verify_password("S3cret-Pass!") is True
    assert config.verify_password("wrong-pass") is False
    assert config.verify_password("") is False


def test_salt_is_unique_per_hash():
    import config

    first = config.hash_password("same-password")
    second = config.hash_password("same-password")
    assert first != second, "Salt reuse ho raha hai."


def test_legacy_sha256_hash_still_verifies(monkeypatch):
    import config

    legacy_hash = hashlib.sha256("purana-password".encode("utf-8")).hexdigest()
    monkeypatch.setattr(config, "PASSWORD_HASH", legacy_hash)
    assert config.verify_password("purana-password") is True
    assert config.verify_password("galat") is False


def test_verify_password_handles_missing_hash(monkeypatch):
    import config

    monkeypatch.setattr(config, "PASSWORD_HASH", "")
    assert config.verify_password("anything") is False


# ===========================================================================
# 4. DAEMON GATEWAY - bearer token + Twilio signature enforcement
# ===========================================================================


@pytest.fixture(scope="module")
def gateway():
    """Real HTTP server on an ephemeral port with stubbed command execution."""
    daemon_api_server = pytest.importorskip("daemon_api_server")

    original_token = daemon_api_server.AUTH_TOKEN
    original_twilio = daemon_api_server.TWILIO_AUTH_TOKEN
    original_execute = daemon_api_server.daemon.execute_command

    daemon_api_server.AUTH_TOKEN = "unit-test-bearer-token"
    daemon_api_server.TWILIO_AUTH_TOKEN = "unit-test-twilio-secret"
    daemon_api_server.daemon.execute_command = (
        lambda text, sender="": {"reply": f"stub:{text}", "type": "stub"}
    )

    server = daemon_api_server.ThreadedHTTPServer(
        ("127.0.0.1", 0), daemon_api_server.DaemonAPIHandler
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address[0], server.server_address[1]
    yield {
        "base": f"http://{host}:{port}",
        "token": "unit-test-bearer-token",
        "twilio": "unit-test-twilio-secret",
    }

    server.shutdown()
    server.server_close()
    daemon_api_server.AUTH_TOKEN = original_token
    daemon_api_server.TWILIO_AUTH_TOKEN = original_twilio
    daemon_api_server.daemon.execute_command = original_execute


def _request(url, method="GET", data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


@pytest.mark.parametrize("path", ["/", "/api/status", "/api/tasks"])
def test_gateway_rejects_unauthenticated_requests(gateway, path):
    status, _ = _request(gateway["base"] + path)
    assert status == 401, f"{path} bina token khul gaya"


def test_gateway_rejects_wrong_token(gateway):
    status, _ = _request(gateway["base"] + "/?token=definitely-not-the-token")
    assert status == 401


def test_gateway_accepts_valid_bearer_token(gateway):
    status, body = _request(
        gateway["base"] + "/",
        headers={"Authorization": f"Bearer {gateway['token']}"},
    )
    assert status == 200
    assert "RealJarvis" in body


def test_gateway_accepts_token_query_param(gateway):
    status, _ = _request(gateway["base"] + f"/api/tasks?token={gateway['token']}")
    assert status == 200


def test_webhook_requires_twilio_signature(gateway):
    """Ye exact bypass fix hai: pehle /api/webhook/* bina check allow tha."""
    body = urllib.parse.urlencode(
        {"From": "whatsapp:+910000000000", "Body": "hi"}
    ).encode()
    status, _ = _request(
        gateway["base"] + "/api/webhook/whatsapp",
        method="POST",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert status == 403, "Webhook bina signature khul gaya - RCE risk!"


def test_webhook_rejects_invalid_signature(gateway):
    body = urllib.parse.urlencode(
        {"From": "whatsapp:+910000000000", "Body": "hi"}
    ).encode()
    status, _ = _request(
        gateway["base"] + "/api/webhook/whatsapp",
        method="POST",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Twilio-Signature": "deadbeef",
        },
    )
    assert status == 403


def test_webhook_accepts_valid_signature(gateway):
    params = {"From": "whatsapp:+910000000000", "Body": "system stats"}
    body = urllib.parse.urlencode(params).encode()
    url = gateway["base"] + "/api/webhook/whatsapp"

    payload = url + "".join(key + params[key] for key in sorted(params))
    signature = hmac.new(
        gateway["twilio"].encode("utf-8"), payload.encode("utf-8"), hashlib.sha1
    ).hexdigest()

    status, response = _request(
        url,
        method="POST",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Twilio-Signature": signature,
        },
    )
    assert status == 200, response
    assert "stub:system stats" in response


def test_no_hardcoded_token_fallback_in_source():
    """Regression guard: purana public default token code me wapas na aaye."""
    import ast as _ast

    source = (PROJECT_ROOT / "daemon_api_server.py").read_text(encoding="utf-8")
    tree = _ast.parse(source)

    hardcoded = [
        node.value
        for node in _ast.walk(tree)
        if isinstance(node, _ast.Constant)
        and isinstance(node.value, str)
        and node.value == "realjarvis-daemon-secure-token"
    ]
    assert not hardcoded, "Hardcoded fallback token code me wapas aa gaya!"

    # AUTH_TOKEN ka default kisi non-empty string se set nahi hona chahiye
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Assign):
            for target in node.targets:
                if isinstance(target, _ast.Name) and target.id == "AUTH_TOKEN":
                    assert isinstance(node.value, _ast.Call), (
                        "AUTH_TOKEN ko direct string se assign nahi karna."
                    )


def test_daemon_refuses_to_start_without_token(monkeypatch):
    daemon_api_server = pytest.importorskip("daemon_api_server")

    monkeypatch.setattr(daemon_api_server, "AUTH_TOKEN", "")
    with pytest.raises(SystemExit):
        daemon_api_server.run_api_server(host="127.0.0.1", port=0)

