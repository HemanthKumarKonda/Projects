# mcp_server/server.py
# This MCP server exposes TOOLS that call your Flask API at http://localhost:8000

import requests
from typing import Optional, List
from fastmcp import FastMCP

FLASK_BASE = "http://localhost:8000"  # your existing Flask server

mcp = FastMCP("hospital-mcp")  # MCP server name

# ---------- Helpers ----------
def get_json(url: str, params: dict | None = None):
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

# ---------- TOOLS (for LLM to call) ----------

@mcp.tool()
def health() -> dict:
    """Check Flask server health and loaded datasets."""
    return get_json(f"{FLASK_BASE}/health")

@mcp.tool()
def list_datasets() -> list:
    """List all datasets with columns and row counts."""
    return get_json(f"{FLASK_BASE}/datasets")

@mcp.tool()
def get_patient_by_id(patient_id: str) -> dict:
    """Return a single patient by patient_id."""
    return get_json(f"{FLASK_BASE}/patients/{patient_id}")

@mcp.tool()
def search_patients(service: Optional[str] = None,
                    name_like: Optional[str] = None,
                    age_min: Optional[float] = None,
                    age_max: Optional[float] = None,
                    satisfaction_ge: Optional[float] = None,
                    arrival_from: Optional[str] = None,
                    limit: int = 50) -> dict:
    """Search patients with simple filters."""
    params = {k: v for k, v in {
        "service": service,
        "name_like": name_like,
        "age_min": age_min,
        "age_max": age_max,
        "satisfaction_ge": satisfaction_ge,
        "arrival_from": arrival_from,
        "limit": limit,
    }.items() if v is not None}
    return get_json(f"{FLASK_BASE}/patients", params)

@mcp.tool()
def get_staff_by_id(staff_id: str) -> dict:
    """Return one staff member by staff_id."""
    return get_json(f"{FLASK_BASE}/staff/{staff_id}")

@mcp.tool()
def search_staff(role: Optional[str] = None,
                 service: Optional[str] = None,
                 name_like: Optional[str] = None,
                 limit: int = 50) -> dict:
    """Search staff with filters."""
    params = {k: v for k, v in {
        "role": role,
        "service": service,
        "name_like": name_like,
        "limit": limit
    }.items() if v is not None}
    return get_json(f"{FLASK_BASE}/staff", params)

@mcp.tool()
def staff_present(week: Optional[str] = None,
                  service: Optional[str] = None,
                  present: bool = True,
                  limit: int = 50) -> dict:
    """List staff presence for a given week/service."""
    params = {k: v for k, v in {
        "week": week,
        "service": service,
        "present": str(present).lower(),
        "limit": limit
    }.items() if v is not None}
    return get_json(f"{FLASK_BASE}/staff_schedule", params)

@mcp.tool()
def weekly_service_stats(service: Optional[str] = None,
                         week: Optional[str] = None,
                         week_like: Optional[str] = None,
                         limit: int = 50) -> dict:
    """Hospital weekly KPIs for a service and/or week."""
    params = {k: v for k, v in {
        "service": service,
        "week": week,
        "week_like": week_like,
        "limit": limit
    }.items() if v is not None}
    return get_json(f"{FLASK_BASE}/services_weekly", params)

@mcp.tool()
def service_week_overview(service: Optional[str] = None,
                          week: Optional[str] = None,
                          week_like: Optional[str] = None,
                          limit: int = 50) -> dict:
    """Join view: weekly outcomes + headcount_present."""
    params = {k: v for k, v in {
        "service": service,
        "week": week,
        "week_like": week_like,
        "limit": limit
    }.items() if v is not None}
    return get_json(f"{FLASK_BASE}/service_week_overview", params)

if __name__ == "__main__":
    # Run MCP server over stdio (good for local LLMs)
    # You can also serve HTTP/SSE transports with FastMCP if needed.
    mcp.run()
