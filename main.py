from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import numpy as np
from io import BytesIO
import tensorflow as tf # Assuming TensorFlow/Keras

app = FastAPI(title="AgriTech Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. LOAD THE AI MODEL ONCE WHEN THE SERVER STARTS
# Uncomment the lines below once you upload your model file
# model = tf.keras.models.load_model('your_model_name.h5')
# CLASS_NAMES = ["Healthy", "Early Blight", "Late Blight", "Rust"] # Update with your crop classes
@app.get("/")
def read_root():
     return {"message": "AgriTech API is running!"}
@app.post("/analyze-leaf")
async def analyze_leaf(file: UploadFile = File(...)):
    try:
        # 2. READ THE UPLOADED IMAGE (FROM THE CAMERA)
        image_data = await file.read()
        image = Image.open(BytesIO(image_data)).convert("RGB")
        
        # 3. PREPROCESS THE IMAGE FOR YOUR MODEL
        # (Resize to what your model expects, typically 224x224 or 256x256)
        image = image.resize((256, 256))
        img_array = np.array(image) / 255.0  # Normalize pixel values
        img_array = np.expand_dims(img_array, axis=0) # Add batch dimension

        # 4. MAKE THE PREDICTION
        # Uncomment the lines below when the model is loaded
        # predictions = model.predict(img_array)
        # predicted_index = np.argmax(predictions[0])
        # diagnosis = CLASS_NAMES[predicted_index]
        # confidence = round(100 * np.max(predictions[0]), 2)
        
        # For now, keeping a placeholder until you uncomment the model code above
        diagnosis = "Early Blight (Testing)"
        confidence = 88.5

        return {
            "status": "success",
            "diagnosis": diagnosis,
            "confidence": f"{confidence}%"
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}