import psutil
import socket

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_processes",
            "description": "List running processes on this local machine (read-only, top by memory usage).",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max number of processes to return, default 15"}
                },
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
            "description": "Get basic local network info: hostname, local IP address, active network interfaces (read-only).",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]


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


TOOL_FUNCTIONS = {
    "list_processes": list_processes,
    "check_open_ports": check_open_ports,
    "network_info": network_info,
}
