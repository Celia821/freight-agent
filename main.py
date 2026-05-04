from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import json, httpx, os, sqlite3
from datetime import datetime

app = FastAPI()

# --- Security ---
API_KEY = os.environ.get("API_KEY", "changeme")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def verify_api_key(key: str = Security(api_key_header)):
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return key

# --- Database Setup ---
def get_db():
    db = sqlite3.connect("calls.db")
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            mc_number TEXT,
            carrier_name TEXT,
            carrier_eligible TEXT,
            load_id TEXT,
            loadboard_rate REAL,
            agreed_rate REAL,
            rounds_of_negotiation INTEGER,
            call_outcome TEXT,
            carrier_sentiment TEXT
        )
    """)
    db.commit()
    db.close()

init_db()

# --- Load the loads data ---
with open("loads.json") as f:
    loads = json.load(f)

# --- Model for incoming call data ---
class CallData(BaseModel):
    mc_number: Optional[str] = None
    carrier_name: Optional[str] = None
    carrier_eligible: Optional[str] = None
    load_id: Optional[str] = None
    loadboard_rate: Optional[str] = None
    agreed_rate: Optional[str] = None
    rounds_of_negotiation: Optional[str] = None
    call_outcome: Optional[str] = None
    carrier_sentiment: Optional[str] = None

# ================================================
# ENDPOINT 1: Verify carrier (called by HappyRobot)
# ================================================
@app.get("/verify-carrier", dependencies=[Depends(verify_api_key)])
async def verify_carrier(mc_number: str):
    try:
        fmcsa_key = os.environ.get("FMCSA_KEY", "")
        url = f"https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{mc_number}?webKey={fmcsa_key}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("content", {})
            if not content:
                return {"eligible": False, "carrier_name": None, "status": "Not Found"}
            carrier = content.get("carrier", {})
            if not carrier:
                return {"eligible": False, "carrier_name": None, "status": "Not Found"}
            allowed = carrier.get("allowedToOperate", "N")
            return {
                "eligible": allowed == "Y",
                "carrier_name": carrier.get("legalName", "Unknown"),
                "status": carrier.get("statusCode", "Unknown")
            }
        return {"eligible": False, "carrier_name": None, "status": f"FMCSA returned {resp.status_code}"}
    except Exception as e:
        return {"eligible": False, "carrier_name": None, "status": f"Error: {str(e)}"}

# ================================================
# ENDPOINT 2: Search loads (called by HappyRobot)
# ================================================
@app.get("/loads", dependencies=[Depends(verify_api_key)])
def search_loads(origin: str = None, equipment_type: str = None):
    results = loads
    if origin:
        results = [l for l in results if origin.lower() in l["origin"].lower()]
    if equipment_type:
        results = [l for l in results if equipment_type.lower() in l["equipment_type"].lower()]
    return results if results else {"message": "No matching loads found"}

# ================================================
# ENDPOINT 3: Receive call data from HappyRobot
# ================================================
@app.post("/calls", dependencies=[Depends(verify_api_key)])
def save_call(data: CallData):
    def to_float(val):
        try: return float(val)
        except: return None
    def to_int(val):
        try: return int(val)
        except: return None

    db = get_db()
    db.execute("""
        INSERT INTO calls (
            created_at, mc_number, carrier_name, carrier_eligible,
            load_id, loadboard_rate, agreed_rate, rounds_of_negotiation,
            call_outcome, carrier_sentiment
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        data.mc_number,
        data.carrier_name,
        data.carrier_eligible,
        data.load_id,
        to_float(data.loadboard_rate),
        to_float(data.agreed_rate),
        to_int(data.rounds_of_negotiation),
        data.call_outcome,
        data.carrier_sentiment
    ))
    db.commit()
    db.close()
    return {"status": "saved"}

# ================================================
# ENDPOINT 4: Get all calls as JSON (for dashboard)
# ================================================
@app.get("/calls-data", dependencies=[Depends(verify_api_key)])
def get_calls():
    db = get_db()
    rows = db.execute("SELECT * FROM calls ORDER BY created_at DESC").fetchall()
    db.close()
    return [dict(row) for row in rows]

# ================================================
# ENDPOINT 5: The dashboard page (public)
# ================================================
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    with open("dashboard.html") as f:
        return f.read()

# from fastapi import FastAPI, HTTPException, Security, Depends
# from fastapi.security.api_key import APIKeyHeader
# import json, httpx, os

# app = FastAPI()

# # Security: every request must include the right API key
# API_KEY = os.environ.get("API_KEY", "changeme")
# api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

# async def verify_api_key(key: str = Security(api_key_header)):
#     if key != API_KEY:
#         raise HTTPException(status_code=403, detail="Invalid API Key")
#     return key

# # Load the loads data
# with open("loads.json") as f:
#     loads = json.load(f)

# # Endpoint 1: Search for loads
# @app.get("/loads", dependencies=[Depends(verify_api_key)])
# def search_loads(origin: str = None, equipment_type: str = None):
#     results = loads
#     if origin:
#         results = [l for l in results if origin.lower() in l["origin"].lower()]
#     if equipment_type:
#         results = [l for l in results if equipment_type.lower() in l["equipment_type"].lower()]
#     return results if results else {"message": "No matching loads found"}

# # Endpoint 2: Verify a carrier via FMCSA
# @app.get("/verify-carrier", dependencies=[Depends(verify_api_key)])
# async def verify_carrier(mc_number: str):
#     return {
#     "eligible": True,
#     "carrier_name": "Test Carrier LLC",
#     "status": "ACTIVE"
#     }
#     # fmcsa_key = os.environ.get("FMCSA_KEY", "")
#     # url = f"https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{mc_number}?webKey={fmcsa_key}"
#     # async with httpx.AsyncClient() as client:
#     #     resp = await client.get(url)
#     # if resp.status_code == 200:
#     #     data = resp.json()
#     #     carrier = data.get("content", {}).get("carrier", {})
#     #     allowed = carrier.get("allowedToOperate", "N")
#     #     return {
#     #         "eligible": allowed == "Y",
#     #         "carrier_name": carrier.get("legalName", "Unknown"),
#     #         "status": carrier.get("statusCode", "Unknown")
#     #     }
#     # return {"eligible": False, "carrier_name": None, "status": "Not Found"}
