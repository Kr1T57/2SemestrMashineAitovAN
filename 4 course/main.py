import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Real Estate Price Prediction API", version="1.0.0")

MODEL_PATH = "real_estate_model.pkl"

try:
    artifacts = joblib.load(MODEL_PATH)
    pipeline = artifacts['pipeline']
    mape_value = 29.18
    cities_list = artifacts.get('cities', [])
    districts_list = artifacts.get('districts', [])
    subtypes_list = artifacts.get('subtypes', [])
    heatings_list = artifacts.get('heatings', [])
except Exception as e:
    raise RuntimeError(f"Ошибка загрузки артефактов из {MODEL_PATH}: {e}")


class PropertyFeatures(BaseModel):
    size: float = Field(..., ge=15.0, le=800.0, description="Площадь в кв. метрах")
    room_count: int = Field(..., ge=1, le=20, description="Количество комнат")
    building_age: int = Field(..., ge=0, le=100, description="Возраст здания (лет)")
    floor_no: int = Field(..., ge=0, le=60, description="Этаж объекта")
    total_floor_count: int = Field(..., ge=1, le=60, description="Всего этажей в здании")
    tom: int = Field(30, ge=0, le=365, description="Дней на рынке")
    city: str = Field(..., description="Город")
    district: str = Field(..., description="Район")
    sub_type: str = Field(..., description="Тип недвижимости")
    heating_type: str = Field(..., description="Тип отопления")


@app.get("/metadata")
def get_metadata():
    return {
        "cities": cities_list,
        "districts": districts_list,
        "subtypes": subtypes_list,
        "heatings": heatings_list,
        "mape": mape_value
    }


@app.post("/predict")
async def predict_price(data: PropertyFeatures):
    try:
        if data.floor_no > data.total_floor_count:
            raise HTTPException(
                status_code=400,
                detail="Номер этажа не может превышать общее количество этажей здания."
            )

        city_grouped = data.city if data.city in cities_list else "Другой"
        district_grouped = data.district if data.district in districts_list else "Другой"
        sub_type_grouped = data.sub_type if data.sub_type in subtypes_list else "Другой"

        input_df = pd.DataFrame([{
            'size': float(data.size),
            'room_count': float(data.room_count),
            'building_age': float(data.building_age),
            'floor_no': float(data.floor_no),
            'total_floor_count': float(data.total_floor_count),
            'tom': float(data.tom),
            'size_per_room': float(data.size) / max(float(data.room_count), 1.0),
            'floor_ratio': float(data.floor_no) / max(float(data.total_floor_count), 1.0),
            'is_first_floor': int(data.floor_no <= 1),
            'is_top_floor': int(data.floor_no == data.total_floor_count),
            'city_grouped': city_grouped,
            'district_grouped': district_grouped,
            'sub_type_grouped': sub_type_grouped,
            'heating_type': data.heating_type
        }])

        log_prediction = pipeline.predict(input_df)[0]
        predicted_price = float(np.expm1(log_prediction))

        # Расчет динамической погрешности через MAPE модели (+- 29.18%)
        margin = predicted_price * (mape_value / 100.0)
        lower_bound = max(0.0, predicted_price - margin)
        upper_bound = predicted_price + margin

        return {
            "status": "success",
            "predicted_price": round(predicted_price, 2),
            "confidence_interval": {
                "lower": round(lower_bound, 2),
                "upper": round(upper_bound, 2),
                "margin": round(margin, 2),
                "mape": mape_value
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сервера при прогнозе: {str(e)}")