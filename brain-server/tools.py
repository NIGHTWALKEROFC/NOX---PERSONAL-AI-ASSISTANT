import re
import socket
import subprocess
import logging
import requests
from bs4 import BeautifulSoup
import psutil
import settings

logger = logging.getLogger("nox.tools")

_HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9.\-]{1,253}$")
CODE_TIMEOUT_SECONDS = 20
MAX_OUTPUT_CHARS = 4000

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the live internet for current information — news, recent releases, "
                "today's date-sensitive facts, anything that might have changed since training. "
                "Use this whenever the user asks about something recent, current, or time-sensitive."
            ),
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_processes",
            "description": "List running processes on this local machine (read-only, top by memory usage).",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "description": "Max processes to return, default 15"}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_open_ports",
            "description": "List TCP ports currently open/listening on this local machine (read-only).",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "network_info",
            "description": "Get basic local network info: hostname, local IP, active interfaces (read-only).",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "dns_lookup",
            "description": "Resolve a hostname to its IP address(es) (read-only DNS lookup).",
            "parameters": {
                "type": "object",
                "properties": {"hostname": {"type": "string", "description": "Hostname to resolve"}},
                "required": ["hostname"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ping_host",
            "description": "Ping a host a few times to check reachability and latency (read-only).",
            "parameters": {
                "type": "object",
                "properties": {"host": {"type": "string", "description": "Hostname or IP to ping"}},
                "required": ["host"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "wifi_scan",
            "description": "List nearby Wi-Fi networks visible to this machine (read-only, Windows only).",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_recon",
            "description": (
                "Run a full read-only recon checklist: processes, open ports, network info, "
                "and nearby Wi-Fi networks, combined into one summary."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": (
                "Execute a short Python snippet on this local machine and return its output. "
                "Runs with the same permissions as NOX itself, on Nightwalker's own computer only. "
                "Use for calculations, quick scripts, or automating a task he explicitly asked for. "
                "Requires code execution to be enabled in NOX Settings — if disabled, this will refuse."
            ),
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string", "description": "Python code to run"}},
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": (
                "Execute a shell/command-line command on this local Windows machine and return its output. "
                "Runs with the same permissions as NOX itself, on Nightwalker's own computer only — never "
                "targets other machines. Use for local system tasks he explicitly asks for. "
                "Requires code execution to be enabled in NOX Settings — if disabled, this will refuse."
            ),
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "Command to run"}},
                "required": ["command"]
            }
        }
    },
]


def web_search(query: str) -> str:
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for a in soup.select(".result__a")[:5]:
            title = a.get_text(strip=True)
            link = a.get("href", "")
            if title:
                results.append(f"{title} — {link}")
        return "\n".join(results) if results else "No results found."
    except Exception as e:
        logger.exception("web_search failed")
        return f"Search failed: {e}"


def list_processes(limit: int = 15) -> str:
    procs = []
    for p in psutil.process_iter(["pid", "name", "memory_percent"]):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda x: x.get("memory_percent") or 0, reverse=True)
    top = procs[:limit]
    lines = [f"PID {p['pid']}: {p['name']} ({p.get('memory_percent', 0):.1f}% mem)" for p in top]
    return "\n".join(lines) if lines else "No process data available."


def check_open_ports() -> str:
    seen = set()
    lines = []
    for conn in psutil.net_connections(kind="tcp"):
        if conn.status == psutil.CONN_LISTEN and conn.laddr:
            port = conn.laddr.port
            if port not in seen:
                seen.add(port)
                lines.append(f"Port {port} (PID {conn.pid or 'unknown'})")
    lines.sort()
    return "\n".join(lines) if lines else "No listening TCP ports found."


def network_info() -> str:
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "unknown"
    lines = [f"Hostname: {hostname}", f"Local IP: {local_ip}"]
    addrs = psutil.net_if_addrs()
    for iface, addr_list in addrs.items():
        for addr in addr_list:
            if addr.family == socket.AF_INET:
                lines.append(f"Interface {iface}: {addr.address}")
    return "\n".join(lines)


def dns_lookup(hostname: str) -> str:
    if not hostname or not _HOSTNAME_RE.match(hostname):
        return "Invalid hostname."
    try:
        infos = socket.getaddrinfo(hostname, None)
        ips = sorted({info[4][0] for info in infos})
        return f"{hostname} resolves to: {', '.join(ips)}"
    except socket.gaierror as e:
        return f"Could not resolve {hostname}: {e}"


def ping_host(host: str) -> str:
    if not host or not _HOSTNAME_RE.match(host):
        return "Invalid host."
    try:
        result = subprocess.run(["ping", "-n", "4", host], capture_output=True, text=True, timeout=15)
        return result.stdout.strip() or result.stderr.strip() or "No output from ping."
    except subprocess.TimeoutExpired:
        return f"Ping to {host} timed out."
    except Exception as e:
        logger.exception("ping_host failed")
        return f"Could not run ping: {e}"


def wifi_scan() -> str:
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "networks", "mode=bssid"],
            capture_output=True, text=True, timeout=15
        )
        output = result.stdout.strip()
        return output if output else "No Wi-Fi networks found, or Wi-Fi adapter unavailable."
    except FileNotFoundError:
        return "wifi_scan is only available on Windows."
    except Exception as e:
        logger.exception("wifi_scan failed")
        return f"Could not scan Wi-Fi: {e}"


def run_recon() -> str:
    parts = [
        "=== Processes (top 5 by memory) ===", list_processes(5),
        "\n=== Open TCP Ports ===", check_open_ports(),
        "\n=== Network Info ===", network_info(),
        "\n=== Nearby Wi-Fi Networks ===", wifi_scan(),
    ]
    return "\n".join(parts)


def _truncate(text: str) -> str:
    return text if len(text) <= MAX_OUTPUT_CHARS else text[:MAX_OUTPUT_CHARS] + "\n...(truncated)"


def run_python(code: str) -> str:
    if not settings.is_code_execution_enabled():
        return "Code execution is currently disabled. Enable it in NOX Settings first."
    logger.info("run_python executing (%d chars)", len(code))
    try:
        result = subprocess.run(
            ["python", "-c", code], capture_output=True, text=True, timeout=CODE_TIMEOUT_SECONDS
        )
        output = result.stdout + (("\n" + result.stderr) if result.stderr else "")
        return _truncate(output.strip() or "(no output)")
    except subprocess.TimeoutExpired:
        logger.warning("run_python timed out")
        return "Execution timed out."
    except Exception as e:
        logger.exception("run_python failed")
        return f"Execution error: {e}"


def run_shell(command: str) -> str:
    if not settings.is_code_execution_enabled():
        return "Code execution is currently disabled. Enable it in NOX Settings first."
    logger.info("run_shell executing: %s", command)
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=CODE_TIMEOUT_SECONDS
        )
        output = result.stdout + (("\n" + result.stderr) if result.stderr else "")
        return _truncate(output.strip() or "(no output)")
    except subprocess.TimeoutExpired:
        logger.warning("run_shell timed out")
        return "Execution timed out."
    except Exception as e:
        logger.exception("run_shell failed")
        return f"Execution error: {e}"


TOOL_FUNCTIONS = {
    "web_search": web_search,
    "list_processes": list_processes,
    "check_open_ports": check_open_ports,
    "network_info": network_info,
    "dns_lookup": dns_lookup,
    "ping_host": ping_host,
    "wifi_scan": wifi_scan,
    "run_recon": run_recon,
    "run_python": run_python,
    "run_shell": run_shell,
}
