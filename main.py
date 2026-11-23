from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime, timezone
from pymongo import MongoClient
import uvicorn
import numpy as np
from PIL import Image
import requests
import random
import io

# Uncomment once TensorFlow is installed and you have your .h5 model file
# import tensorflow as tf

app = FastAPI(title="AgriTech API")

# --- CORS SETUP ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION ---
MONGO_URI = "mongodb+srv://harshithr391_db_user:qMGsCUzjZ4sn7I63@cluster0.drf4pro.mongodb.net/?retryWrites=true&w=majority"
DATA_GOV_API_KEY = "579b464db66ec23bdd000001cc291d62f61d40dc53fb4f79cf103d79"
MANDI_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"

# --- DATABASE CONNECTION ---
db = None
crops_collection = None
scans_collection = None
market_collection = None

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client["agritech_db"]
    crops_collection = db["crops"]
    scans_collection = db["leaf_scans"]
    market_collection = db["market_prices"]
    print("✅ Database connected successfully.")
except Exception as e:
    print(f"⚠️ Database Connection Warning: {e}")

# --- 40 MAJOR INDIAN CROPS DATASET ---
DEFAULT_CROPS = [
    # Cereals & Millets
    {"name": "Rice (Paddy)", "keywords": "rice paddy dhan", "category": "cereal", "season": "KHARIF • CEREAL", "emoji": "🌾", "climate": "Hot & Humid (20°C–37°C)", "soil": "Clayey loams retaining standing water.", "color": "emerald"},
    {"name": "Wheat (Gehun)", "keywords": "wheat gehun", "category": "cereal", "season": "RABI • CEREAL", "emoji": "🌾", "climate": "Cool Winter (10°C–15°C)", "soil": "Well-drained fertile loams.", "color": "amber"},
    {"name": "Maize (Makka)", "keywords": "maize makka corn", "category": "cereal", "season": "KHARIF • CEREAL", "emoji": "🌽", "climate": "Warm Climate (21°C–27°C)", "soil": "Old alluvial soil with good drainage.", "color": "emerald"},
    {"name": "Jowar (Sorghum)", "keywords": "jowar sorghum millet", "category": "cereal", "season": "KHARIF / RABI • MILLET", "emoji": "🌾", "climate": "Warm & Dry (26°C–33°C)", "soil": "Black clayey loams and red soils.", "color": "amber"},
    {"name": "Bajra (Pearl Millet)", "keywords": "bajra pearl millet", "category": "cereal", "season": "KHARIF • MILLET", "emoji": "🌾", "climate": "Hot & Dry (25°C–35°C)", "soil": "Sandy loams and shallow black soils.", "color": "amber"},
    {"name": "Ragi (Finger Millet)", "keywords": "ragi finger millet nachni", "category": "cereal", "season": "KHARIF • MILLET", "emoji": "🌾", "climate": "Moderate (20°C–30°C)", "soil": "Red, black, sandy, and loamy soils.", "color": "emerald"},
    {"name": "Barley (Jau)", "keywords": "barley jau", "category": "cereal", "season": "RABI • CEREAL", "emoji": "🌾", "climate": "Cool & Dry (12°C–18°C)", "soil": "Sandy loam to medium loam soils.", "color": "amber"},
    # Pulses
    {"name": "Gram (Chana)", "keywords": "gram chana chickpea pulses", "category": "pulse", "season": "RABI • PULSE", "emoji": "🌱", "climate": "Cool Climate (20°C–25°C)", "soil": "Light loamy or heavy clay soils.", "color": "amber"},
    {"name": "Pigeon Pea (Tur / Arhar)", "keywords": "pigeon pea tur arhar toor pulses", "category": "pulse", "season": "KHARIF • PULSE", "emoji": "🫘", "climate": "Warm & Moist (26°C–30°C)", "soil": "Well-drained loamy soils.", "color": "emerald"},
    {"name": "Moong (Green Gram)", "keywords": "moong mung green gram pulses", "category": "pulse", "season": "KHARIF / ZAID • PULSE", "emoji": "🫘", "climate": "Warm (25°C–35°C)", "soil": "Well-drained sandy loams.", "color": "emerald"},
    {"name": "Urad (Black Gram)", "keywords": "urad black gram pulses", "category": "pulse", "season": "KHARIF • PULSE", "emoji": "🫘", "climate": "Hot & Humid (25°C–35°C)", "soil": "Heavy clay or loamy soils.", "color": "emerald"},
    {"name": "Masoor (Red Lentil)", "keywords": "masoor lentil dal pulses", "category": "pulse", "season": "RABI • PULSE", "emoji": "🫘", "climate": "Cool Winter (18°C–25°C)", "soil": "Alluvial and well-drained loams.", "color": "amber"},
    # Oilseeds
    {"name": "Groundnut (Mungfali)", "keywords": "groundnut peanut mungfali oilseed", "category": "oilseed", "season": "KHARIF • OILSEED", "emoji": "🥜", "climate": "Warm Climate (20°C–30°C)", "soil": "Sandy loams and well-drained soils.", "color": "amber"},
    {"name": "Soybean", "keywords": "soybean soya oilseed", "category": "oilseed", "season": "KHARIF • OILSEED", "emoji": "🌿", "climate": "Warm & Humid (20°C–30°C)", "soil": "Fertile alluvial or clay-loam soils.", "color": "emerald"},
    {"name": "Mustard (Sarson)", "keywords": "mustard sarson rai oilseed", "category": "oilseed", "season": "RABI • OILSEED", "emoji": "🌼", "climate": "Cool & Dry (15°C–25°C)", "soil": "Light to heavy loamy soils.", "color": "amber"},
    {"name": "Sunflower (Surajmukhi)", "keywords": "sunflower surajmukhi oilseed", "category": "oilseed", "season": "ALL SEASON • OILSEED", "emoji": "🌻", "climate": "Moderate (20°C–25°C)", "soil": "Deep loamy and black cotton soils.", "color": "amber"},
    {"name": "Sesame (Til)", "keywords": "sesame til gingelly oilseed", "category": "oilseed", "season": "KHARIF • OILSEED", "emoji": "🌱", "climate": "Warm (25°C–30°C)", "soil": "Well-drained light sandy loams.", "color": "emerald"},
    {"name": "Castor (Arandi)", "keywords": "castor arandi oilseed", "category": "oilseed", "season": "KHARIF • OILSEED", "emoji": "🌿", "climate": "Warm & Dry (20°C–30°C)", "soil": "Deep sandy loam and red soils.", "color": "emerald"},
    # Commercial & Cash Crops
    {"name": "Cotton (Kapas)", "keywords": "cotton kapas commercial", "category": "commercial", "season": "KHARIF • COMMERCIAL", "emoji": "☁️", "climate": "High Temp (21°C–30°C)", "soil": "Black cotton soil (Regur) of Deccan.", "color": "purple"},
    {"name": "Sugarcane (Ganna)", "keywords": "sugarcane ganna commercial", "category": "commercial", "season": "ANNUAL • COMMERCIAL", "emoji": "🎋", "climate": "Hot & Humid (20°C–35°C)", "soil": "Deep rich loamy soils with high moisture.", "color": "purple"},
    {"name": "Jute (Pat)", "keywords": "jute pat golden fibre commercial", "category": "commercial", "season": "KHARIF • COMMERCIAL", "emoji": "🌾", "climate": "Hot & Wet (24°C–37°C)", "soil": "New alluvial soil of river deltas.", "color": "purple"},
    {"name": "Natural Rubber", "keywords": "rubber plantation commercial", "category": "commercial", "season": "PERENNIAL • COMMERCIAL", "emoji": "🌳", "climate": "Equatorial Humid (25°C–35°C)", "soil": "Deep well-drained laterite soils.", "color": "purple"},
    # Spices & Plantation
    {"name": "Tea (Chai)", "keywords": "tea chai plantation spice", "category": "spice", "season": "PERENNIAL • PLANTATION", "emoji": "🍵", "climate": "Cool & Humid (15°C–30°C)", "soil": "Deep acidic hill-slope loams.", "color": "rose"},
    {"name": "Coffee", "keywords": "coffee arabica robusta plantation", "category": "spice", "season": "PERENNIAL • PLANTATION", "emoji": "☕", "climate": "Cool Tropical (15°C–28°C)", "soil": "Rich, well-drained forest loams.", "color": "rose"},
    {"name": "Turmeric (Haldi)", "keywords": "turmeric haldi spice", "category": "spice", "season": "KHARIF • SPICE", "emoji": "🫚", "climate": "Warm & Humid (20°C–30°C)", "soil": "Friable, well-drained loamy soils.", "color": "rose"},
    {"name": "Ginger (Adrak)", "keywords": "ginger adrak spice", "category": "spice", "season": "KHARIF • SPICE", "emoji": "🫚", "climate": "Warm & Humid (20°C–30°C)", "soil": "Sandy or clay loam rich in humus.", "color": "rose"},
    {"name": "Black Pepper (Kali Mirch)", "keywords": "black pepper kali mirch spice", "category": "spice", "season": "PERENNIAL • SPICE", "emoji": "🫑", "climate": "Hot & Humid (20°C–30°C)", "soil": "Red laterite and forest loams.", "color": "rose"},
    {"name": "Cardamom (Elaichi)", "keywords": "cardamom elaichi spice", "category": "spice", "season": "PERENNIAL • SPICE", "emoji": "🌿", "climate": "Cool & Wet (10°C–35°C)", "soil": "Acidic, humus-rich forest loams.", "color": "rose"},
    {"name": "Red Chilli (Mirchi)", "keywords": "chilli mirchi pepper spice", "category": "spice", "season": "KHARIF / RABI • SPICE", "emoji": "🌶️", "climate": "Warm & Humid (20°C–30°C)", "soil": "Well-drained black or loamy soils.", "color": "rose"},
    {"name": "Cumin (Jeera)", "keywords": "cumin jeera spice", "category": "spice", "season": "RABI • SPICE", "emoji": "🌱", "climate": "Cool & Dry (15°C–25°C)", "soil": "Well-drained sandy loam soils.", "color": "rose"},
    # Horticulture
    {"name": "Potato (Aloo)", "keywords": "potato aloo vegetable horticulture", "category": "horticulture", "season": "RABI • HORTICULTURE", "emoji": "🥔", "climate": "Cool Weather (15°C–20°C)", "soil": "Loose, friable sandy loams rich in humus.", "color": "blue"},
    {"name": "Tomato (Tamatar)", "keywords": "tomato tamatar vegetable horticulture", "category": "horticulture", "season": "ALL SEASON • HORTICULTURE", "emoji": "🍅", "climate": "Moderate (18°C–25°C)", "soil": "Well-drained sandy loam with organic matter.", "color": "blue"},
    {"name": "Onion (Pyaaz)", "keywords": "onion pyaaz kanda vegetable horticulture", "category": "horticulture", "season": "KHARIF / RABI • HORTICULTURE", "emoji": "🧅", "climate": "Mild Climate (13°C–25°C)", "soil": "Deep friable alluvial and loamy soils.", "color": "blue"},
    {"name": "Brinjal (Baingan)", "keywords": "brinjal eggplant baingan vegetable horticulture", "category": "horticulture", "season": "ALL SEASON • HORTICULTURE", "emoji": "🍆", "climate": "Warm (20°C–30°C)", "soil": "Fertile silt loam or clay loam.", "color": "blue"},
    {"name": "Cauliflower (Gobhi)", "keywords": "cauliflower gobhi vegetable horticulture", "category": "horticulture", "season": "RABI • HORTICULTURE", "emoji": "🥦", "climate": "Cool (15°C–20°C)", "soil": "Deep loamy soil rich in organic matter.", "color": "blue"},
    {"name": "Banana (Kela)", "keywords": "banana kela fruit horticulture", "category": "horticulture", "season": "PERENNIAL • HORTICULTURE", "emoji": "🍌", "climate": "Tropical Warm (20°C–35°C)", "soil": "Rich, deep, well-drained fertile soils.", "color": "blue"},
    {"name": "Mango (Aam)", "keywords": "mango aam fruit horticulture", "category": "horticulture", "season": "SUMMER • HORTICULTURE", "emoji": "🥭", "climate": "Tropical Warm (24°C–30°C)", "soil": "Deep, well-drained alluvial or laterite soils.", "color": "blue"},
    {"name": "Apple (Seb)", "keywords": "apple seb fruit horticulture", "category": "horticulture", "season": "TEMPERATE • HORTICULTURE", "emoji": "🍎", "climate": "Cold Winters (0°C–24°C)", "soil": "Well-drained loamy hill soils.", "color": "blue"},
    {"name": "Grapes (Angoor)", "keywords": "grapes angoor fruit horticulture", "category": "horticulture", "season": "PERENNIAL • HORTICULTURE", "emoji": "🍇", "climate": "Dry & Warm (15°C–35°C)", "soil": "Well-drained sandy loam to black soils.", "color": "blue"},
    {"name": "Coconut (Nariyal)", "keywords": "coconut nariyal plantation horticulture", "category": "horticulture", "season": "PERENNIAL • HORTICULTURE", "emoji": "🥥", "climate": "Coastal Humid (25°C–32°C)", "soil": "Coastal sandy, alluvial, and red loamy soils.", "color": "blue"}
]

# Auto-seed crops collection if empty
if crops_collection is not None and crops_collection.count_documents({}) == 0:
    crops_collection.insert_many(DEFAULT_CROPS)
    print(f"🌱 Seeded {len(DEFAULT_CROPS)} Indian crops.")

# --- AI MODEL SETUP ---
MODEL_PATH = "leaf_disease_model.h5"
model = None
CLASS_NAMES = [
    "Healthy Leaf",
    "Tomato - Early Blight",
    "Tomato - Late Blight",
    "Potato - Early Blight",
    "Rice - Brown Spot"
]

def preprocess_image(image_bytes: bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode != "RGB":
            image = image.convert("RGB")
        image = image.resize((224, 224))
        img_array = np.array(image) / 255.0
        return np.expand_dims(img_array, axis=0)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file format.")

# ==========================================
# ENDPOINTS
# ==========================================

@app.get("/")
def root():
    return {"status": "AgriTech API Running"}

# 1. LEAF DISEASE DETECTION
@app.post("/analyze-leaf")
async def analyze_leaf(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    image_bytes = await file.read()
    processed_image = preprocess_image(image_bytes)

    if model is not None:
        # predictions = model.predict(processed_image)
        # idx = int(np.argmax(predictions[0]))
        # score = float(np.max(predictions[0]))
        pass
    else:
        idx = random.randint(0, len(CLASS_NAMES) - 1)
        score = random.uniform(0.85, 0.99)

    diagnosis = CLASS_NAMES[idx]
    confidence = f"{score * 100:.1f}%"

    if scans_collection is not None:
        scans_collection.insert_one({
            "filename": file.filename,
            "diagnosis": diagnosis,
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    return {"diagnosis": diagnosis, "confidence": confidence}

# 2. RECENT LEAF SCANS
@app.get("/scan-history")
def get_scan_history(limit: int = 20):
    if scans_collection is None:
        return {"count": 0, "data": []}
    scans = list(scans_collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))
    return {"count": len(scans), "data": scans}

# 3. INDIAN CROPS DIRECTORY
@app.get("/crops")
def get_crops(category: Optional[str] = None, search: Optional[str] = None):
    if crops_collection is None:
        return {"count": len(DEFAULT_CROPS), "data": DEFAULT_CROPS}

    query = {}
    if category and category != "all":
        query["category"] = category
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"keywords": {"$regex": search, "$options": "i"}}
        ]

    crops = list(crops_collection.find(query, {"_id": 0}))
    return {"count": len(crops), "data": crops}

# 4. LIVE DAILY MARKET PRICES (CACHED DAILY)
@app.get("/market-prices")
def get_live_market_prices(limit: int = 40, state: Optional[str] = None):
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if market_collection is not None and not state:
        cached = market_collection.find_one({"date": today_str}, {"_id": 0})
        if cached and cached.get("records"):
            return {"status": "cached", "count": len(cached["records"]), "data": cached["records"]}

    url = f"https://api.data.gov.in/resource/{MANDI_RESOURCE_ID}"
    params = {
        "api-key": DATA_GOV_API_KEY,
        "format": "json",
        "limit": limit
    }
    if state:
        params["filters[state]"] = state

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        records = response.json().get("records", [])

        formatted_prices = [
            {
                "commodity": item.get("commodity", "N/A"),
                "variety": item.get("variety", ""),
                "market": f"{item.get('market', '')}, {item.get('state', '')}",
                "min_price": item.get("min_price", "--"),
                "max_price": item.get("max_price", "--"),
                "modal_price": item.get("modal_price", "--"),
                "arrival_date": item.get("arrival_date", today_str)
            }
            for item in records
        ]

        if market_collection is not None and formatted_prices and not state:
            market_collection.update_one(
                {"date": today_str},
                {"$set": {"date": today_str, "records": formatted_prices}},
                upsert=True
            )

        return {"status": "live", "count": len(formatted_prices), "data": formatted_prices}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch live prices: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)