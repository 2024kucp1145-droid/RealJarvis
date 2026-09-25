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
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Dict, Any, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import config
from jarvis_daemon import daemon
import remote_boot_wol

# Load Authentication Token from environment or generate a stable default
AUTH_TOKEN = os.environ.get("DAEMON_AUTH_TOKEN", "realjarvis-daemon-secure-token")
DEFAULT_PORT = int(os.environ.get("DAEMON_PORT", 8765))


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

    def _is_authenticated(self, query_params: Dict[str, list]) -> bool:
        """Validates Bearer token in header or query string."""
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if token == AUTH_TOKEN:
                return True

        if "token" in query_params and query_params["token"]:
            if query_params["token"][0] == AUTH_TOKEN:
                return True

        # If incoming from Twilio webhook, allow validation or check configured signature
        if self.path.startswith("/api/webhook/"):
            return True

        return False

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

        # 1. Root Health Check (Public)
        if path == "/":
            self._send_json(200, {
                "service": "RealJarvis 24/7 Always-On Daemon",
                "status": "online",
                "version": "1.0",
                "uptime": daemon.get_telemetry()["uptime_str"],
                "endpoints": [
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

        # Authentication Check for all API endpoints
        if not self._is_authenticated(query_params):
            self._send_json(401, {"error": "Unauthorized. Provide valid Bearer token."})
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
        query_params = urllib.parse.parse_qs(parsed.query)

        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        # 1. WhatsApp / Twilio Webhook (Supports form-urlencoded and JSON)
        if path == "/api/webhook/whatsapp":
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
        if not self._is_authenticated(query_params):
            self._send_json(401, {"error": "Unauthorized. Provide valid Bearer token."})
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


def run_api_server(host: str = "0.0.0.0", port: int = DEFAULT_PORT):
    """Runs the API Gateway server."""
    # Ensure daemon background worker is running
    daemon.start()

    server_address = (host, port)
    httpd = ThreadedHTTPServer(server_address, DaemonAPIHandler)
    print("=" * 60)
    print(f"  RealJarvis 24/7 Remote Gateway listening on http://{host}:{port}")
    print(f"  Auth Token: {AUTH_TOKEN}")
    print("=" * 60)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[API Server] Shutting down gateway...")
        httpd.shutdown()
        daemon.stop()


if __name__ == "__main__":
    run_api_server()
