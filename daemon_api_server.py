# -*- coding: utf-8 -*-
"""
daemon_api_server.py
====================
Ultra-Fast REST & Webhook Gateway for RealJarvis 24/7 Always-On Daemon.

Features:
- Pure multi-threaded HTTP server (zero external web framework dependencies needed).
- Token-authenticated endpoints (Authorization: Bearer <token> or ?token=).
- Mobile & Webhook integration:
  • GET  /                    -> Service info & health check
  • GET  /api/status          -> Telemetry, uptime, mission counts
  • POST /api/message         -> Send prompt from phone, returns AI reply
  • POST /api/task/schedule   -> Schedule autonomous background mission
  • GET  /api/tasks           -> List pending/recent missions
  • POST /api/webhook/whatsapp-> Twilio / Meta WhatsApp incoming webhook
  • POST /api/laptop/wake     -> Trigger Wake-on-LAN remotely
  • POST /api/control/power   -> Remote lock / sleep / shutdown
"""

import os
import sys
import json
import time
import hmac
import hashlib
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Dict, Any, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    import config
except ImportError:
    config = None
from jarvis_daemon import daemon
import remote_boot_wol

def _load_auth_token() -> str:
    """Gateway token load karo (.env ya environment se).

    SECURITY: Pehle yahan ek hardcoded fallback token tha
    ("realjarvis-daemon-secure-token") - usse poora internet-facing daemon
    publicly open ho jaata tha. Ab fallback HATA diya gaya hai: token nahi
    mila toh server start hi nahi hoga.
    """
    token = (os.environ.get("DAEMON_AUTH_TOKEN") or "").strip()
    if token:
        return token
    if config is not None:
        token = (getattr(config, "DAEMON_AUTH_TOKEN", "") or "").strip()
    return token


def _load_twilio_auth_token() -> str:
    """Twilio Auth Token for WhatsApp webhook signature verification."""
    token = (os.environ.get("TWILIO_AUTH_TOKEN") or "").strip()
    if token:
        return token
    if config is not None:
        token = (getattr(config, "TWILIO_AUTH_TOKEN", "") or "").strip()
    return token


AUTH_TOKEN = _load_auth_token()
TWILIO_AUTH_TOKEN = _load_twilio_auth_token()
DEFAULT_PORT = int(os.environ.get("PORT", os.environ.get("DAEMON_PORT", 8765)))
# Localhost by default - sirf is machine se reachable. Public exposure ke liye
# explicitly DAEMON_HOST=0.0.0.0 set karo.
DEFAULT_HOST = os.environ.get("DAEMON_HOST", "127.0.0.1")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handles each request in a separate thread for concurrent mobile access."""
    daemon_threads = True


class DaemonAPIHandler(BaseHTTPRequestHandler):
    server_version = "RealJarvisDaemon/1.0"

    def log_message(self, format, *args):
        # Clean logging format
        sys.stderr.write(f"[API Server] {self.address_string()} - {format % args}\n")

    def _send_json(self, status_code: int, data: Dict[str, Any]):
        """Helper to send JSON response."""
        response_bytes = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(response_bytes)

    def _send_xml(self, status_code: int, xml_str: str):
        """Helper to send XML response for Twilio WhatsApp Webhooks."""
        response_bytes = xml_str.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def _bearer_token_valid(self) -> bool:
        """Header ya query string me diya gaya token constant-time compare karo."""
        if not AUTH_TOKEN:
            return False

        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            if hmac.compare_digest(auth_header[7:].strip(), AUTH_TOKEN):
                return True

        parsed = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed.query)
        if "token" in query_params and query_params["token"]:
            if hmac.compare_digest(query_params["token"][0], AUTH_TOKEN):
                return True

        return False

    def _twilio_signature_valid(self) -> bool:
        """Twilio webhook signature (X-Twilio-Signature) verify karo.

        SECURITY: Pehle saare /api/webhook/* paths bina kisi check ke allow ho
        rahe the - matlab koi bhi anonymous request daemon.execute_command()
        chala sakta tha (remote command execution). Ab Twilio ki documented
        HMAC-SHA1 signature verification lagti hai.
        """
        if not TWILIO_AUTH_TOKEN:
            # Twilio configure nahi hai - webhook ko bearer token chahiye.
            return False

        signature = self.headers.get("X-Twilio-Signature", "")
        if not signature:
            return False

        # Twilio signature URL + sorted POST params ka HMAC-SHA1 hota hai.
        content_length = int(self.headers.get("Content-Length", 0) or 0)
        raw_body = self.read_cached_body(content_length)
        params = urllib.parse.parse_qs(raw_body.decode("utf-8", errors="ignore"))

        request_url = self._reconstruct_url()
        payload = request_url
        for key in sorted(params.keys()):
            for value in params[key]:
                payload += key + value

        expected = hmac.new(
            TWILIO_AUTH_TOKEN.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha1,
        ).digest()

        try:
            provided = bytes.fromhex(signature.strip())
        except ValueError:
            return False

        return hmac.compare_digest(expected, provided)

    def read_cached_body(self, content_length: int) -> bytes:
        """Raw POST body ko sirf ek baar padho aur cache karo."""
        cached = getattr(self, "_raw_body_cache", None)
        if cached is None:
            cached = self.rfile.read(content_length) if content_length else b""
            self._raw_body_cache = cached
        return cached

    def _reconstruct_url(self) -> str:
        """Webhook verify karne ke liye original public URL banao."""
        forwarded_proto = self.headers.get("X-Forwarded-Proto", "")
        scheme = forwarded_proto.split(",")[0].strip() if forwarded_proto else "http"

        host = self.headers.get("X-Forwarded-Host") or self.headers.get("Host", "")

        return f"{scheme}://{host}{self.path}"

    def _is_authenticated(self) -> bool:
        """Bearer token ya (webhook ke case me) valid Twilio signature chahiye."""
        path = urllib.parse.urlparse(self.path).path
        if self._bearer_token_valid():
            return True
        if path.startswith("/api/webhook/") and self._twilio_signature_valid():
            return True
        return False

    def _reject_unauthorized(self, is_webhook: bool = False):
        if is_webhook:
            self._send_json(403, {
                "error": "Webhook signature verification failed. Set TWILIO_AUTH_TOKEN "
                         "or authenticate with a Bearer token."
            })
        else:
            self._send_json(401, {"error": "Unauthorized. Provide valid Bearer token."})

    def do_OPTIONS(self):
        """CORS pre-flight support."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)

        # Authentication Check for all API endpoints (root bhi ab protected hai)
        if not self._is_authenticated():
            self._reject_unauthorized(is_webhook=path.startswith("/api/webhook/"))
            return

        # 1. Root Health Check / Service Info
        if path == "/":
            self._send_json(200, {
                "service": "RealJarvis 24/7 Always-On Daemon",
                "status": "online",
                "version": "1.0",
                "uptime": daemon.get_telemetry()["uptime_str"],
                "endpoints": [
                    "GET  /",
                    "GET  /api/status",
                    "POST /api/message",
                    "POST /api/task/schedule",
                    "GET  /api/tasks",
                    "POST /api/webhook/whatsapp",
                    "POST /api/laptop/wake",
                    "POST /api/control/power"
                ]
            })
            return

        # 2. Telemetry Status
        if path == "/api/status":
            self._send_json(200, daemon.get_telemetry())
            return

        # 3. List Missions
        if path == "/api/tasks":
            limit = int(query_params.get("limit", [20])[0])
            missions = daemon.list_missions(limit=limit)
            self._send_json(200, {"count": len(missions), "tasks": missions})
            return

        self._send_json(404, {"error": "Endpoint not found"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0) or 0)
        raw_body = self.read_cached_body(content_length)

        # 1. WhatsApp / Twilio Webhook (Supports form-urlencoded and JSON)
        if path == "/api/webhook/whatsapp":
            # SECURITY: Twilio signature (ya bearer token) ke bina koi bhi
            # anonymous request daemon command chala sakta tha. Ab blocked.
            if not self._is_authenticated():
                self._reject_unauthorized(is_webhook=True)
                return

            incoming_text = ""
            sender = ""

            content_type = self.headers.get("Content-Type", "")
            if "application/x-www-form-urlencoded" in content_type:
                form_data = urllib.parse.parse_qs(raw_body.decode("utf-8", errors="ignore"))
                incoming_text = form_data.get("Body", [""])[0]
                sender = form_data.get("From", [""])[0]
            else:
                try:
                    json_data = json.loads(raw_body.decode("utf-8"))
                    incoming_text = json_data.get("message", "") or json_data.get("Body", "")
                    sender = json_data.get("sender", "") or json_data.get("From", "")
                except Exception:
                    pass

            if not incoming_text:
                self._send_json(400, {"error": "No incoming message text found."})
                return

            print(f"[API Server] Incoming WhatsApp Webhook from {sender}: {incoming_text}")
            result = daemon.execute_command(incoming_text, sender=sender)
            reply_text = result["reply"]

            # Return TwiML XML if Twilio requested, else JSON
            if "application/x-www-form-urlencoded" in content_type:
                twiml = (
                    f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
                    f"<Response>\n"
                    f"  <Message>{reply_text}</Message>\n"
                    f"</Response>"
                )
                self._send_xml(200, twiml)
            else:
                self._send_json(200, {"reply": reply_text, "type": result.get("type", "unknown")})
            return

        # Authentication Check for all other POST endpoints
        if not self._is_authenticated():
            self._reject_unauthorized()
            return

        # Parse JSON payload
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            self._send_json(400, {"error": "Invalid JSON payload."})
            return

        # 2. General Message Query (/api/message)
        if path == "/api/message":
            msg = payload.get("message", "").strip()
            if not msg:
                self._send_json(400, {"error": "Field 'message' is required."})
                return
            result = daemon.execute_command(msg, sender="api")
            self._send_json(200, result)
            return

        # 3. Schedule Mission (/api/task/schedule)
        if path == "/api/task/schedule":
            task_name = payload.get("task_name", "Remote Scheduled Task")
            prompt = payload.get("prompt", "").strip()
            delay = float(payload.get("delay_seconds", 0))
            repeat = int(payload.get("repeat_interval_sec", 0))
            if not prompt:
                self._send_json(400, {"error": "Field 'prompt' is required."})
                return

            mid = daemon.schedule_mission(task_name=task_name, prompt=prompt, delay_seconds=delay, repeat_interval_sec=repeat)
            self._send_json(200, {
                "success": True,
                "mission_id": mid,
                "task_name": task_name,
                "scheduled_delay_seconds": delay
            })
            return

        # 4. Wake-on-LAN Trigger (/api/laptop/wake)
        if path == "/api/laptop/wake":
            mac = payload.get("mac_address", "")
            ip = payload.get("ip_address", "255.255.255.255")
            if mac:
                ok = remote_boot_wol.send_wake_on_lan_packet(mac, broadcast_ip=ip)
                self._send_json(200, {"success": ok, "message": f"WoL packet sent to {mac}"})
            else:
                info = remote_boot_wol.get_wol_configuration_info()
                self._send_json(200, {"success": True, "info": info})
            return

        # 5. Remote Power Control (/api/control/power)
        if path == "/api/control/power":
            action = payload.get("action", "").lower().strip()
            if action not in ("lock", "sleep", "restart", "shutdown"):
                self._send_json(400, {"error": "Invalid action. Supported: lock, sleep, restart, shutdown."})
                return
            msg = remote_boot_wol.execute_power_action(action)
            self._send_json(200, {"success": True, "action": action, "detail": msg})
            return

        self._send_json(404, {"error": "Endpoint not found"})


def run_api_server(host: str = None, port: int = DEFAULT_PORT):
    """Runs the API Gateway server."""
    if host is None:
        host = DEFAULT_HOST

    # SECURITY: Bina token ke server start karne ka matlab hai poora laptop
    # internet par khula. Isliye fail-fast.
    if not AUTH_TOKEN:
        print("=" * 60)
        print("  [FATAL] DAEMON_AUTH_TOKEN set nahi hai - server start nahi ho sakta.")
        print("  .env me daalo: DAEMON_AUTH_TOKEN=<long-random-secret>")
        print("  Generate: python -c \"import secrets; print(secrets.token_urlsafe(48))\"")
        print("=" * 60)
        raise SystemExit(1)

    # Ensure daemon background worker is running
    daemon.start()

    server_address = (host, port)
    httpd = ThreadedHTTPServer(server_address, DaemonAPIHandler)
    print("=" * 60)
    print(f"  RealJarvis 24/7 Remote Gateway listening on http://{host}:{port}")
    print(f"  Auth Token: {AUTH_TOKEN[:4]}...{AUTH_TOKEN[-4:]} (masked)")
    print(f"  Twilio signature verification: {'ON' if TWILIO_AUTH_TOKEN else 'OFF (bearer token only)'}")
    if host in ("0.0.0.0", "::"):
        print("  [WARN] 0.0.0.0 par bind hai - har incoming connection ko token chahiye.")
    print("=" * 60)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[API Server] Shutting down gateway...")
        httpd.shutdown()
        daemon.stop()


if __name__ == "__main__":
    run_api_server()
