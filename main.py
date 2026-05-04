from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
import json, httpx, os

app = FastAPI()

# Security: every request must include the right API key
API_KEY = os.environ.get("API_KEY", "changeme")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def verify_api_key(key: str = Security(api_key_header)):
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return key

# Load the loads data
with open("loads.json") as f:
    loads = json.load(f)

# Endpoint 1: Search for loads
@app.get("/loads", dependencies=[Depends(verify_api_key)])
def search_loads(origin: str = None, equipment_type: str = None):
    results = loads
    if origin:
        results = [l for l in results if origin.lower() in l["origin"].lower()]
    if equipment_type:
        results = [l for l in results if equipment_type.lower() in l["equipment_type"].lower()]
    return results if results else {"message": "No matching loads found"}

# Endpoint 2: Verify a carrier via FMCSA
@app.get("/verify-carrier", dependencies=[Depends(verify_api_key)])
async def verify_carrier(mc_number: str):
    return {
    "eligible": True,
    "carrier_name": "Test Carrier LLC",
    "status": "ACTIVE"
    }
    # fmcsa_key = os.environ.get("FMCSA_KEY", "")
    # url = f"https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{mc_number}?webKey={fmcsa_key}"
    # async with httpx.AsyncClient() as client:
    #     resp = await client.get(url)
    # if resp.status_code == 200:
    #     data = resp.json()
    #     carrier = data.get("content", {}).get("carrier", {})
    #     allowed = carrier.get("allowedToOperate", "N")
    #     return {
    #         "eligible": allowed == "Y",
    #         "carrier_name": carrier.get("legalName", "Unknown"),
    #         "status": carrier.get("statusCode", "Unknown")
    #     }
    # return {"eligible": False, "carrier_name": None, "status": "Not Found"}
