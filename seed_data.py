import sqlite3
import os
from datetime import datetime, timedelta
import random

os.makedirs("data", exist_ok=True)
db = sqlite3.connect("data/calls.db")

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

# Seed data — 7 days of realistic calls
seed_calls = [
    # Day 1
    {"days_ago":6,"mc":"133655","carrier":"Schneider National Carriers","eligible":"true","load":"LD-001","listed":2400,"agreed":2400,"rounds":0,"outcome":"booked","sentiment":"positive"},
    {"days_ago":6,"mc":"254958","carrier":"Werner Enterprises","eligible":"true","load":"LD-004","listed":850,"agreed":900,"rounds":2,"outcome":"booked","sentiment":"neutral"},
    {"days_ago":6,"mc":"999111","carrier":None,"eligible":"false","load":None,"listed":None,"agreed":None,"rounds":None,"outcome":"ineligible","sentiment":"negative"},
    # Day 2
    {"days_ago":5,"mc":"107919","carrier":"Swift Transportation","eligible":"true","load":"LD-006","listed":950,"agreed":950,"rounds":0,"outcome":"booked","sentiment":"positive"},
    {"days_ago":5,"mc":"153470","carrier":"JB Hunt Transport","eligible":"true","load":"LD-002","listed":1800,"agreed":None,"rounds":3,"outcome":"no_deal","sentiment":"neutral"},
    {"days_ago":5,"mc":"888222","carrier":None,"eligible":"false","load":None,"listed":None,"agreed":None,"rounds":None,"outcome":"ineligible","sentiment":"negative"},
    # Day 3
    {"days_ago":4,"mc":"133655","carrier":"Schneider National Carriers","eligible":"true","load":"LD-003","listed":1200,"agreed":1200,"rounds":0,"outcome":"booked","sentiment":"positive"},
    {"days_ago":4,"mc":"254958","carrier":"Werner Enterprises","eligible":"true","load":None,"listed":None,"agreed":None,"rounds":None,"outcome":"no_load_match","sentiment":"neutral"},
    {"days_ago":4,"mc":"107919","carrier":"Swift Transportation","eligible":"true","load":"LD-005","listed":1100,"agreed":1150,"rounds":1,"outcome":"booked","sentiment":"positive"},
    # Day 4
    {"days_ago":3,"mc":"153470","carrier":"JB Hunt Transport","eligible":"true","load":"LD-001","listed":2400,"agreed":2450,"rounds":1,"outcome":"booked","sentiment":"positive"},
    {"days_ago":3,"mc":"777333","carrier":None,"eligible":"false","load":None,"listed":None,"agreed":None,"rounds":None,"outcome":"ineligible","sentiment":"negative"},
    {"days_ago":3,"mc":"133655","carrier":"Schneider National Carriers","eligible":"true","load":"LD-004","listed":850,"agreed":None,"rounds":3,"outcome":"no_deal","sentiment":"neutral"},
    # Day 5
    {"days_ago":2,"mc":"254958","carrier":"Werner Enterprises","eligible":"true","load":"LD-002","listed":1800,"agreed":1800,"rounds":0,"outcome":"booked","sentiment":"positive"},
    {"days_ago":2,"mc":"107919","carrier":"Swift Transportation","eligible":"true","load":"LD-006","listed":950,"agreed":1000,"rounds":2,"outcome":"booked","sentiment":"positive"},
    {"days_ago":2,"mc":"153470","carrier":"JB Hunt Transport","eligible":"true","load":None,"listed":None,"agreed":None,"rounds":None,"outcome":"no_load_match","sentiment":"neutral"},
    # Day 6
    {"days_ago":1,"mc":"133655","carrier":"Schneider National Carriers","eligible":"true","load":"LD-003","listed":1200,"agreed":1250,"rounds":1,"outcome":"booked","sentiment":"positive"},
    {"days_ago":1,"mc":"999444","carrier":None,"eligible":"false","load":None,"listed":None,"agreed":None,"rounds":None,"outcome":"ineligible","sentiment":"negative"},
    {"days_ago":1,"mc":"254958","carrier":"Werner Enterprises","eligible":"true","load":"LD-005","listed":1100,"agreed":1100,"rounds":0,"outcome":"booked","sentiment":"positive"},
    # Day 7 (today)
    {"days_ago":0,"mc":"107919","carrier":"Swift Transportation","eligible":"true","load":"LD-001","listed":2400,"agreed":2400,"rounds":0,"outcome":"booked","sentiment":"positive"},
    {"days_ago":0,"mc":"153470","carrier":"JB Hunt Transport","eligible":"true","load":"LD-004","listed":850,"agreed":900,"rounds":2,"outcome":"booked","sentiment":"positive"},
    {"days_ago":0,"mc":"555666","carrier":None,"eligible":"false","load":None,"listed":None,"agreed":None,"rounds":None,"outcome":"ineligible","sentiment":"negative"},
    {"days_ago":0,"mc":"133655","carrier":"Schneider National Carriers","eligible":"true","load":None,"listed":None,"agreed":None,"rounds":None,"outcome":"no_load_match","sentiment":"neutral"},
]

now = datetime.utcnow()
for i, call in enumerate(seed_calls):
    created = now - timedelta(days=call["days_ago"], hours=random.randint(0,8), minutes=random.randint(0,59))
    db.execute("""
        INSERT INTO calls (
            created_at, mc_number, carrier_name, carrier_eligible,
            load_id, loadboard_rate, agreed_rate, rounds_of_negotiation,
            call_outcome, carrier_sentiment
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        created.isoformat(),
        call["mc"],
        call["carrier"],
        call["eligible"],
        call["load"],
        call["listed"],
        call["agreed"],
        call["rounds"],
        call["outcome"],
        call["sentiment"],
    ))

db.commit()
db.close()
print(f"✅ Seeded {len(seed_calls)} calls successfully")
