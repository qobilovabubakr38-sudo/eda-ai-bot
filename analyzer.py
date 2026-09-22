import os
import json
import base64
from typing import Optional, List
from pydantic import BaseModel, Field
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Data models for structured nutrition output
class IngredientItem(BaseModel):
    name: str = Field(description="Masalliq nomi (o'zbek tilida)")
    amount_g: float = Field(description="Taxminiy og'irligi (grammda)")

class FoodItemDetail(BaseModel):
    name: str = Field(description="Taom yoki mahsulot nomi (o'zbek tilida)")
    weight_g: float = Field(description="Taxminiy vazni (grammda)")
    calories: float = Field(description="Kaloriyasi (kkal)")
    protein: float = Field(description="Oqsil (grammda)")
    fats: float = Field(description="Yog' (grammda)")
    carbs: float = Field(description="Uglevod (grammda)")

class FoodAnalysisResult(BaseModel):
    food_name: str = Field(description="Umumiy taom nomi (o'zbek tilida)")
    cuisine_type: str = Field(description="Oshxona turi (masalan: O'zbek milliy oshxonasi, Fast food, Yevropa, va h.k.)")
    total_weight_g: float = Field(description="Umumiy porsiya og'irligi grammda")
    calories: float = Field(description="Umumiy kaloriya (kkal)")
    protein: float = Field(description="Umumiy oqsil (grammda)")
    fats: float = Field(description="Umumiy yog' (grammda)")
    carbs: float = Field(description="Umumiy uglevod (grammda)")
    ingredients: List[IngredientItem] = Field(description="Aniqlangan asosiy masalliqlar")
    items_breakdown: List[FoodItemDetail] = Field(description="Likopchadagi har bir alohida taom/mahsulot bo'yicha taqsimot")
    health_verdict: str = Field(description="Taomning qisqa sog'lomlik darajasi (A'lo, O'rtacha, Og'ir/Yog'li)")
    dietary_advice: str = Field(description="Foydalanuvchi uchun amaliy maslahat va tavsiya (o'zbek tilida)")
    confidence: str = Field(description="AI ishonch darajasi: Yuqori, O'rtacha, Taxminiy")

MOCK_FOOD_DB = {
    "osh": FoodAnalysisResult(
        food_name="Osh (Toshkentcha To'y oshi)",
        cuisine_type="O'zbek milliy oshxonasi",
        total_weight_g=400,
        calories=860,
        protein=28.5,
        fats=42.0,
        carbs=92.0,
        ingredients=[
            IngredientItem(name="Devzira/Lazer guruch", amount_g=180),
            IngredientItem(name="Mol go'shti (laxta)", amount_g=90),
            IngredientItem(name="Sariq va qizil sabzi", amount_g=80),
            IngredientItem(name="Paxta/Dumba yog'i", amount_g=35),
            IngredientItem(name="No'xat va mayiz", amount_g=15),
        ],
        items_breakdown=[
            FoodItemDetail(name="Osh asosiy porsiyasi", weight_g=350, calories=780, protein=25, fats=38, carbs=85),
            FoodItemDetail(name="Qo'shimcha go'sht va no'xat", weight_g=50, calories=80, protein=3.5, fats=4, carbs=7),
        ],
        health_verdict="Energetik va to'yimli (Yuqori kaloriyali)",
        dietary_advice="Tushlik uchun ajoyib quvvat manbai. Yog' miqdori yuqori bo'lgani sababli yoniga achchiq-chuchuk salati va ko'k choy ichish hazmni osonlashtiradi.",
        confidence="Yuqori"
    ),
    "somsa": FoodAnalysisResult(
        food_name="Tandir Somsa (Go'shtli)",
        cuisine_type="O'zbek milliy oshxonasi",
        total_weight_g=180,
        calories=460,
        protein=16.0,
        fats=26.0,
        carbs=40.5,
        ingredients=[
            IngredientItem(name="Qatlama xamir", amount_g=90),
            IngredientItem(name="Mol go'shti qiymasi", amount_g=60),
            IngredientItem(name="Piyoz va ziravorlar", amount_g=20),
            IngredientItem(name="Dumba yog'i", amount_g=10),
        ],
        items_breakdown=[
            FoodItemDetail(name="Go'shtli somsa (1 dona)", weight_g=180, calories=460, protein=16, fats=26, carbs=40.5),
        ],
        health_verdict="O'rtacha kaloriyali, to'yimli",
        dietary_advice="Tez to'yintiradi, lekin xamiri qatlama va yog'li bo'lgani sababli kunning birinchi yarmida iste'mol qilish tavsiya etiladi.",
        confidence="Yuqori"
    )
}

SYSTEM_INSTRUCTION = """
Siz dunyodagi eng tajribali parhezshunos, taom mutaxassisi va ovqat kaloriyasini vizual aniqlovchi sun'iy intellekt (EDA.AI modeli) hisoblanasiz.

Vazifangiz:
1. Suratdagi taomni diqqat bilan o'rganish. Ayniqsa O'zbek milliy taomlari (osh/palov, somsa, manti, shashlik, lag'mon, sho'rva, dimlama, norin, mastava, salatlar, nonlar) va jahon taomlarini aniq farqlash.
2. Likopcha yoki idish hajmidan kelib chiqib, taomning taxminiy vaznini (grammda) va uning tarkibidagi masalliqlarni aniqlash.
3. Umumiy kaloriyani (kkal), hamda Makronutrientlarni (Oqsil/Protein, Yog'/Fat, Uglevod/Carbs) grammlarda aniq hisoblab berish.
4. Qisqa, tushunarli va do'stona o'zbek tilida sog'lomlik xulosasi va ovqatlanish tavsiyasini berish.
5. Hech qanday ortiqcha matnsiz, faqat ko'rsatilgan JSON sxemasi bo'yicha toza ma'lumot qaytarish.
"""

_ENC_KEY = "QVEuQWI4Uk42SVp4RmRxNUF0WVlGaUZFYktYUlhRZXZ4RkowbS1iUTh1SGtrdDNZUDVqaFE="
DEFAULT_GEMINI_KEY = base64.b64decode(_ENC_KEY).decode("utf-8")

def analyze_food_image(image_bytes: bytes, mime_type: str = "image/jpeg", custom_api_key: Optional[str] = None) -> FoodAnalysisResult:
    """
    Rasm baytlarini olib, o'rnatilgan Gemini Vision AI orqali tahlil qiladi.
    Tashqaridan hech qanday API kalit so'ramaydi - barchasi ichiga o'rnatilgan.
    """
    from google.genai import types

    api_key = custom_api_key or os.environ.get("GEMINI_API_KEY") or DEFAULT_GEMINI_KEY
    client = genai.Client(api_key=api_key)

    prompt_text = (
        "Ushbu rasmda qanday taom tasvirlangan? Idishdagi porsiyani va masalliqlarni baholang. "
        "Umumiy og'irlik (gramm), kaloriya (kkal), oqsillar, yog'lar va uglevodlarni to'liq hisoblab, "
        "o'zbek tilida berilgan sxema bo'yicha aniq JSON formatida natija qaytaring."
    )

    models_to_try = ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.8-flash"]
    last_err = None

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt_text
                ],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=FoodAnalysisResult
                )
            )
            if response.text:
                data = json.loads(response.text)
                return FoodAnalysisResult(**data)
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"AI tahlilida xatolik: {str(last_err)}")
