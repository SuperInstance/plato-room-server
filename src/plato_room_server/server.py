"""HTTP room management server with routing."""
import time
import json
from dataclasses import dataclass, field
from typing import Callable, Optional
from collections import defaultdict
from enum import Enum

class HttpMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"

@dataclass
class Request:
    method: str
    path: str
    body: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    query: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

@dataclass
class Response:
    status: int = 200
    body: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    latency_ms: float = 0.0

@dataclass
class Route:
    method: str
    path: str
    handler: str
    middleware: list[str] = field(default_factory=list)

class RoomServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self._rooms: dict[str, dict] = {}
        self._routes: list[Route] = []
        self._middleware: dict[str, Callable] = {}
        self._request_log: list[dict] = []
        self._started_at: float = 0.0

    def add_route(self, method: str, path: str, handler: str, middleware: list[str] = None):
        self._routes.append(Route(method=method.upper(), path=path, handler=handler,
                                  middleware=middleware or []))

    def add_middleware(self, name: str, fn: Callable):
        self._middleware[name] = fn

    def handle(self, request: Request) -> Response:
        start = time.time()
        response = Response()
        # Route matching
        for route in self._routes:
            if route.method != request.method:
                continue
            if not self._match_path(route.path, request.path):
                continue
            # Run middleware
            for mw_name in route.middleware:
                mw = self._middleware.get(mw_name)
                if mw:
                    mw(request)
            response.status = 200
            response.body = {"handler": route.handler, "matched": True}
            break
        else:
            response.status = 404
            response.body = {"error": "Not found"}
        response.latency_ms = (time.time() - start) * 1000
        self._log_request(request, response)
        return response

    def _match_path(self, pattern: str, path: str) -> bool:
        if pattern == path:
            return True
        pattern_parts = pattern.split("/")
        path_parts = path.split("/")
        if len(pattern_parts) != len(path_parts):
            return False
        for pp, rp in zip(pattern_parts, path_parts):
            if pp.startswith("{") and pp.endswith("}"):
                continue
            if pp != rp:
                return False
        return True

    def _log_request(self, request: Request, response: Response):
        entry = {"method": request.method, "path": request.path, "status": response.status,
                 "latency_ms": round(response.latency_ms, 2), "timestamp": time.time()}
        self._request_log.append(entry)
        if len(self._request_log) > 1000:
            self._request_log = self._request_log[-1000:]

    # Room management API
    def create_room(self, room_id: str, name: str = "", domain: str = "general",
                    metadata: dict = None) -> dict:
        room = {"id": room_id, "name": name or room_id, "domain": domain,
                "created_at": time.time(), "tiles": 0, "agents": [],
                "metadata": metadata or {}}
        self._rooms[room_id] = room
        return room

    def get_room(self, room_id: str) -> Optional[dict]:
        return self._rooms.get(room_id)

    def list_rooms(self, domain: str = "") -> list[dict]:
        rooms = list(self._rooms.values())
        if domain:
            rooms = [r for r in rooms if r.get("domain") == domain]
        return rooms

    def delete_room(self, room_id: str) -> bool:
        return self._rooms.pop(room_id, None) is not None

    def recent_requests(self, n: int = 20) -> list[dict]:
        return self._request_log[-n:]

    @property
    def stats(self) -> dict:
        domains = defaultdict(int)
        for r in self._rooms.values():
            domains[r.get("domain", "unknown")] += 1
        return {"rooms": len(self._rooms), "routes": len(self._routes),
                "middleware": list(self._middleware.keys()),
                "total_requests": len(self._request_log),
                "domains": dict(domains)}
