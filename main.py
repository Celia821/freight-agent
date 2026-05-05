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
os.makedirs("data", exist_ok=True)

def get_db():
    db = sqlite3.connect("data/calls.db")
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
# ENDPOINT 1: Verify carrier
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
            if isinstance(content, list):
                content = content[0] if content else {}
            carrier = content.get("carrier", {})
            if isinstance(carrier, list):
                carrier = carrier[0] if carrier else {}
            if not carrier:
                return {"eligible": False, "carrier_name": None, "status": "Not Found"}
            allowed = carrier.get("allowedToOperate", "N")
            return {
                "eligible": allowed == "Y",
                "carrier_name": carrier.get("legalName", "Unknown"),
                "status": carrier.get("statusCode", "Unknown")
            }
        return {"eligible": False, "carrier_name": None, "status": f"FMCSA error {resp.status_code}"}
    except Exception as e:
        return {"eligible": False, "carrier_name": None, "status": f"Error: {str(e)}"}

# ================================================
# ENDPOINT 2: Search loads
# ================================================
@app.get("/loads", dependencies=[Depends(verify_api_key)])
def search_loads(
    origin: str = None,
    equipment_type: str = None,
    destination: str = None,
    pickup_date: str = None
):
    results = loads
    if origin:
        origin_city = origin.split(",")[0].strip().lower()
        results = [l for l in results if origin_city in l["origin"].lower()]
    if equipment_type:
        types = [t.strip().lower() for t in equipment_type.split(",")]
        results = [l for l in results if any(
            t in l["equipment_type"].lower() for t in types
        )]
    if destination:
        dest_city = destination.split(",")[0].strip().lower()
        results = [l for l in results if dest_city in l["destination"].lower()]
    if pickup_date:
        results = [l for l in results if pickup_date.lower()
                   in l["pickup_datetime"].lower()]
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
# ENDPOINT 4: Get all calls as JSON
# ================================================
@app.get("/calls-data", dependencies=[Depends(verify_api_key)])
def get_calls():
    db = get_db()
    rows = db.execute("SELECT * FROM calls ORDER BY created_at DESC").fetchall()
    db.close()
    return [dict(row) for row in rows]

# ================================================
# ENDPOINT 5: Dashboard page
# ================================================
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    with open("dashboard.html") as f:
        return f.read()



# SEED DATA FOR LAST 7 DAYS
@app.post("/seed-demo-data")
def seed_demo_data():
    from datetime import timedelta
    import random
    seed_calls = [
        {"days_ago":6,"mc":"133655","carrier":"Schneider National","eligible":"true","load":"LD-001","listed":2400,"agreed":2400,"rounds":0,"outcome":"booked","sentiment":"positive"},
        {"days_ago":6,"mc":"254958","carrier":"Werner Enterprises","eligible":"true","load":"LD-004","listed":850,"agreed":900,"rounds":2,"outcome":"booked","sentiment":"neutral"},
        {"days_ago":6,"mc":"999111","carrier":None,"eligible":"false","load":None,"listed":None,"agreed":None,"rounds":None,"outcome":"ineligible","sentiment":"negative"},
        {"days_ago":5,"mc":"107919","carrier":"Swift Transportation","eligible":"true","load":"LD-006","listed":950,"agreed":950,"rounds":0,"outcome":"booked","sentiment":"positive"},
        {"days_ago":5,"mc":"153470","carrier":"JB Hunt Transport","eligible":"true","load":"LD-002","listed":1800,"agreed":None,"rounds":3,"outcome":"no_deal","sentiment":"neutral"},
        {"days_ago":5,"mc":"888222","carrier":None,"eligible":"false","load":None,"listed":None,"agreed":None,"rounds":None,"outcome":"ineligible","sentiment":"negative"},
        {"days_ago":4,"mc":"133655","carrier":"Schneider National","eligible":"true","load":"LD-003","listed":1200,"agreed":1200,"rounds":0,"outcome":"booked","sentiment":"positive"},
        {"days_ago":4,"mc":"254958","carrier":"Werner Enterprises","eligible":"true","load":None,"listed":None,"agreed":None,"rounds":None,"outcome":"no_load_match","sentiment":"neutral"},
        {"days_ago":4,"mc":"107919","carrier":"Swift Transportation","eligible":"true","load":"LD-005","listed":1100,"agreed":1150,"rounds":1,"outcome":"booked","sentiment":"positive"},
        {"days_ago":3,"mc":"153470","carrier":"JB Hunt Transport","eligible":"true","load":"LD-001","listed":2400,"agreed":2450,"rounds":1,"outcome":"booked","sentiment":"positive"},
        {"days_ago":3,"mc":"777333","carrier":None,"eligible":"false","load":None,"listed":None,"agreed":None,"rounds":None,"outcome":"ineligible","sentiment":"negative"},
        {"days_ago":3,"mc":"133655","carrier":"Schneider National","eligible":"true","load":"LD-004","listed":850,"agreed":None,"rounds":3,"outcome":"no_deal","sentiment":"neutral"},
        {"days_ago":2,"mc":"254958","carrier":"Werner Enterprises","eligible":"true","load":"LD-002","listed":1800,"agreed":1800,"rounds":0,"outcome":"booked","sentiment":"positive"},
        {"days_ago":2,"mc":"107919","carrier":"Swift Transportation","eligible":"true","load":"LD-006","listed":950,"agreed":1000,"rounds":2,"outcome":"booked","sentiment":"positive"},
        {"days_ago":2,"mc":"153470","carrier":"JB Hunt Transport","eligible":"true","load":None,"listed":None,"agreed":None,"rounds":None,"outcome":"no_load_match","sentiment":"neutral"},
        {"days_ago":1,"mc":"133655","carrier":"Schneider National","eligible":"true","load":"LD-003","listed":1200,"agreed":1250,"rounds":1,"outcome":"booked","sentiment":"positive"},
        {"days_ago":1,"mc":"999444","carrier":None,"eligible":"false","load":None,"listed":None,"agreed":None,"rounds":None,"outcome":"ineligible","sentiment":"negative"},
        {"days_ago":1,"mc":"254958","carrier":"Werner Enterprises","eligible":"true","load":"LD-005","listed":1100,"agreed":1100,"rounds":0,"outcome":"booked","sentiment":"positive"},
    ]
    now = datetime.utcnow()
    db = get_db()
    for call in seed_calls:
        created = now - timedelta(days=call["days_ago"], hours=random.randint(0,8), minutes=random.randint(0,59))
        db.execute("""
            INSERT INTO calls (created_at, mc_number, carrier_name, carrier_eligible,
                load_id, loadboard_rate, agreed_rate, rounds_of_negotiation,
                call_outcome, carrier_sentiment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (created.isoformat(), call["mc"], call["carrier"], call["eligible"],
              call["load"], call["listed"], call["agreed"], call["rounds"],
              call["outcome"], call["sentiment"]))
    db.commit()
    db.close()
    return {"status": "seeded", "calls_inserted": len(seed_calls)}

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
