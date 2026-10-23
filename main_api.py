# main_api.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import uvicorn

app = FastAPI(
    title="Shiraz Medical API",
    description="پلتفرم جامع گردشگری سلامت شیراز",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_json(filename: str):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "data", filename)
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/")
def read_root():
    return {"message": "به API شیراز مدیکال خوش آمدید", "status": "active"}

@app.get("/api/hospitals")
def get_hospitals():
    return {"hospitals": load_json("hospitals2.json")}

@app.get("/api/insurances")
def get_insurances():
    return {"insurances": load_json("insurances.json")}

@app.get("/api/tourism")
def get_tourism():
    return {"tourism": load_json("leisure_city.json")}

@app.get("/api/paramedical")
def get_paramedical():
    return {"paramedical": load_json("paramedical.json")}

@app.get("/api/elderly")
def get_elderly():
    return {"elderly": load_json("elderly_homes.json")}

@app.get("/api/emergency")
def get_emergency():
    data = load_json("support.json")
    emergency = [item for item in data if item.get("emergency_contact")]
    return {"emergency": emergency}

@app.get("/api/transport")
def get_transport():
    return {"transport": load_json("transport_hubs.json")}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)