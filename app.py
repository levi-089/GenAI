
import json
import os
import re
import torch

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel


BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
ADAPTER_PATH = "./qwen_travel_lora"
AUTHORIZED_PLACES_PATH = "./authorized_places.json"


app = FastAPI(
    title="Travel AI API",
    description=(
        "API para generar itinerarios personalizados "
        "con Qwen + LoRA + RAG estructurado + "
        "validación determinista + control de presupuesto."
    ),
    version="1.2"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TravelRequest(BaseModel):
    destination: str
    days: int
    budget: float
    currency: str

    adults: int
    children: int

    interests: list[str]
    travel_style: str
    restrictions: list[str]


# ============================================================
# CARGAR BASE AUTORIZADA
# ============================================================

with open(
    AUTHORIZED_PLACES_PATH,
    "r",
    encoding="utf-8"
) as f:
    authorized_places = json.load(f)


# ============================================================
# CARGAR MODELO
# ============================================================

adapter_available = os.path.isdir(ADAPTER_PATH)

tokenizer_source = (
    ADAPTER_PATH
    if adapter_available
    else BASE_MODEL
)

tokenizer = AutoTokenizer.from_pretrained(
    tokenizer_source
)

base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.float16,
    device_map="auto"
)

if adapter_available:
    model = PeftModel.from_pretrained(
        base_model,
        ADAPTER_PATH
    )
else:
    # El adaptador LoRA se genera en el notebook de experimentación.
    # Si no está disponible, la aplicación sigue siendo ejecutable
    # con el modelo base + RAG estructurado + validación determinista.
    model = base_model

model.eval()


# ============================================================
# LIMPIEZA JSON
# ============================================================

def clean_json_response(response: str):

    cleaned = response.strip()

    cleaned = re.sub(
        r"^```json\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned
    )

    return cleaned.strip()


# ============================================================
# VALIDACIÓN DETERMINISTA
# ============================================================

def validate_itinerary(
    itinerary: dict,
    expected_days: int
):

    errors = []

    if "dias" not in itinerary:
        return [
            "Falta la clave principal 'dias'."
        ]

    days = itinerary["dias"]

    if len(days) != expected_days:
        errors.append(
            f"Se esperaban {expected_days} días "
            f"y se encontraron {len(days)}."
        )

    periods = [
        "manana",
        "tarde",
        "noche"
    ]

    place_counter = {}

    for expected_day, day in enumerate(
        days,
        start=1
    ):

        if day.get("dia") != expected_day:
            errors.append(
                f"Número de día incorrecto. "
                f"Se esperaba {expected_day}."
            )

        for period in periods:

            if period not in day:
                errors.append(
                    f"Día {expected_day}: "
                    f"falta '{period}'."
                )
                continue

            block = day[period]

            place = block.get("lugar")
            activity = block.get("actividad")

            # -------------------------------
            # Lugar autorizado
            # -------------------------------

            if place not in authorized_places:

                errors.append(
                    f"Día {expected_day} - {period}: "
                    f"lugar no autorizado '{place}'."
                )

                continue


            place_counter[place] = (
                place_counter.get(place, 0) + 1
            )


            # -------------------------------
            # Actividad autorizada
            # -------------------------------

            allowed_activities = authorized_places[
                place
            ]["allowed_activities"]

            if activity not in allowed_activities:

                errors.append(
                    f"Día {expected_day} - {period}: "
                    f"actividad no autorizada para "
                    f"'{place}': '{activity}'."
                )


    # -------------------------------
    # Control de repetición
    # -------------------------------

    for place, count in place_counter.items():

        if count > 2:

            errors.append(
                f"El lugar '{place}' aparece "
                f"{count} veces; máximo permitido: 2."
            )

    return errors



# ============================================================
# REPARACIÓN DETERMINISTA DE REPETICIONES
# ============================================================

def repair_repeated_places(
    itinerary: dict,
    max_repetitions: int = 2
):

    periods = [
        "manana",
        "tarde",
        "noche"
    ]

    place_counter = {}

    # Contar uso actual
    for day in itinerary["dias"]:

        for period in periods:

            place = day[period]["lugar"]

            place_counter[place] = (
                place_counter.get(place, 0) + 1
            )


    # Uso progresivo durante reparación
    seen = {}

    for day in itinerary["dias"]:

        for period in periods:

            block = day[period]

            place = block["lugar"]

            seen[place] = (
                seen.get(place, 0) + 1
            )

            # Mantener las primeras apariciones
            if seen[place] <= max_repetitions:
                continue


            # Buscar alternativas con menor uso
            candidates = []

            for candidate_place, info in authorized_places.items():

                candidate_count = place_counter.get(
                    candidate_place,
                    0
                )

                if candidate_count < max_repetitions:

                    candidates.append(
                        (
                            candidate_count,
                            candidate_place
                        )
                    )


            if not candidates:
                continue


            # Priorizar el lugar menos utilizado
            candidates.sort(
                key=lambda x: (
                    x[0],
                    x[1]
                )
            )

            new_place = candidates[0][1]


            # Seleccionar una actividad válida
            available_activities = list(
                authorized_places[
                    new_place
                ]["allowed_activities"].keys()
            )

            new_activity = available_activities[0]


            # Actualizar contadores
            place_counter[place] -= 1

            place_counter[new_place] = (
                place_counter.get(new_place, 0) + 1
            )


            # Reemplazar bloque
            block["lugar"] = new_place
            block["actividad"] = new_activity


    return itinerary



# ============================================================
# AÑADIR COSTOS AL ITINERARIO
# ============================================================

def add_costs_to_itinerary(
    itinerary: dict,
    adults: int,
    children: int,
    budget: float,
    currency: str
):

    total_travelers = adults + children

    total_min = 0
    total_max = 0

    periods = [
        "manana",
        "tarde",
        "noche"
    ]


    for day in itinerary["dias"]:

        day_min = 0
        day_max = 0

        for period in periods:

            block = day[period]

            place = block["lugar"]
            activity = block["actividad"]

            cost_data = authorized_places[
                place
            ]["allowed_activities"][activity]

            min_per_person = cost_data[
                "min_cost_usd"
            ]

            max_per_person = cost_data[
                "max_cost_usd"
            ]

            min_total = (
                min_per_person * total_travelers
            )

            max_total = (
                max_per_person * total_travelers
            )


            # Información adicional del lugar
            block["descripcion"] = authorized_places[
                place
            ].get(
                "descripcion",
                ""
            )

            block["google_maps_url"] = authorized_places[
                place
            ].get(
                "google_maps_url",
                ""
            )


            # Costos añadidos a la tarjeta
            block["costo_estimado"] = {
                "moneda": "USD",

                "por_persona": {
                    "min": min_per_person,
                    "max": max_per_person
                },

                "grupo": {
                    "min": min_total,
                    "max": max_total
                }
            }


            day_min += min_total
            day_max += max_total


        # Resumen diario
        day["costo_dia"] = {
            "moneda": "USD",
            "min": day_min,
            "max": day_max
        }


        total_min += day_min
        total_max += day_max


    # ========================================================
    # PRESUPUESTO
    # ========================================================

    budget_evaluation = {
        "moneda_costos": "USD",
        "presupuesto_ingresado": budget,
        "moneda_presupuesto": currency,
        "costo_estimado_min": total_min,
        "costo_estimado_max": total_max,
        "viajeros": {
            "adultos": adults,
            "ninos": children,
            "total": total_travelers
        }
    }


    # Comparación directa solo si el presupuesto está en USD.
    # No hacemos conversión automática para evitar inventar
    # tasas de cambio.
    if currency.upper() == "USD":

        if total_max <= budget:

            status = "dentro_del_presupuesto"

        elif total_min > budget:

            status = "fuera_del_presupuesto"

        else:

            status = "riesgo_de_superar_presupuesto"


        budget_evaluation[
            "estado"
        ] = status


        budget_evaluation[
            "saldo_estimado_usando_maximo"
        ] = budget - total_max


    else:

        budget_evaluation[
            "estado"
        ] = "requiere_conversion_moneda"

        budget_evaluation[
            "advertencia"
        ] = (
            "Los costos del prototipo están almacenados "
            "en USD. No se realizó conversión automática "
            "para evitar utilizar una tasa de cambio no "
            "verificada."
        )


    itinerary[
        "resumen_presupuesto"
    ] = budget_evaluation


    return itinerary


# ============================================================
# PROMPT
# ============================================================

def get_prompt_places():

    prompt_places = {}

    for place, info in authorized_places.items():

        prompt_places[place] = {
            "category": info["category"],
            "allowed_activities": list(
                info["allowed_activities"].keys()
            )
        }

    return prompt_places


def build_prompt(data: TravelRequest):

    # El modelo necesita conocer nombres y actividades,
    # pero NO debe calcular los precios.
    prompt_places = get_prompt_places()

    authorized_places_json = json.dumps(
        prompt_places,
        ensure_ascii=False,
        indent=2
    )


    return f"""
Genera un itinerario personalizado para {data.destination}.

BASE AUTORIZADA:
{authorized_places_json}

PREFERENCIAS:
- Duración: {data.days} días
- Presupuesto: {data.budget} {data.currency}
- Adultos: {data.adults}
- Niños: {data.children}
- Intereses: {", ".join(data.interests)}
- Ritmo: {data.travel_style}
- Restricciones: {", ".join(data.restrictions)}

REGLAS OBLIGATORIAS:

1. Genera exactamente {data.days} días.

2. Cada día debe tener exactamente:
   - manana
   - tarde
   - noche

3. Cada bloque debe contener únicamente:
   - lugar
   - actividad

4. "lugar" debe coincidir EXACTAMENTE
   con una clave de BASE AUTORIZADA.

5. "actividad" debe coincidir EXACTAMENTE
   con una actividad autorizada para ese lugar.

6. No combines actividades.

7. No parafrasees actividades.

8. No inventes lugares.

9. No inventes actividades.

10. NO calcules costos.

11. NO agregues precios.

12. NO agregues horarios.

13. NO agregues transporte.

14. No repitas un lugar más de dos veces.

15. Prioriza los intereses del usuario.

16. Devuelve únicamente JSON válido.

FORMATO EXACTO:

{{
  "dias": [
    {{
      "dia": 1,
      "manana": {{
        "lugar": "nombre exacto",
        "actividad": "actividad exacta"
      }},
      "tarde": {{
        "lugar": "nombre exacto",
        "actividad": "actividad exacta"
      }},
      "noche": {{
        "lugar": "nombre exacto",
        "actividad": "actividad exacta"
      }}
    }}
  ]
}}
"""


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/")
def root():

    return {
        "status": "ok",
        "service": "Travel AI API",
        "version": "1.2"
    }


@app.post("/generate")
def generate_itinerary(
    data: TravelRequest
):

    # Validaciones básicas de entrada
    if data.adults < 1:

        raise HTTPException(
            status_code=400,
            detail="Debe existir al menos un adulto."
        )


    if data.children < 0:

        raise HTTPException(
            status_code=400,
            detail="El número de niños no puede ser negativo."
        )


    if data.budget <= 0:

        raise HTTPException(
            status_code=400,
            detail="El presupuesto debe ser mayor que cero."
        )


    prompt_places = get_prompt_places()

    prompt = build_prompt(data)


    messages = [
        {
            "role": "system",
            "content": (
                "Eres un planificador profesional "
                "de viajes. Debes seleccionar "
                "exclusivamente valores exactos "
                "de la base autorizada y devolver "
                "únicamente JSON válido."
            )
        },
        {
            "role": "user",
            "content": prompt
        }
    ]


    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )


    inputs = tokenizer(
        text,
        return_tensors="pt"
    ).to(model.device)


    with torch.no_grad():

        outputs = model.generate(
            **inputs,
            max_new_tokens=1400,
            do_sample=False
        )


    raw_response = tokenizer.decode(
        outputs[0][
            inputs["input_ids"].shape[1]:
        ],
        skip_special_tokens=True
    )


    cleaned_response = clean_json_response(
        raw_response
    )


    # ========================================================
    # JSON
    # ========================================================

    try:

        itinerary = json.loads(
            cleaned_response
        )

    except json.JSONDecodeError as e:

        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "El modelo no generó JSON válido."
                ),
                "error": str(e),
                "raw_response": raw_response
            }
        )


    # ========================================================
    # VALIDACIÓN
    # ========================================================

    validation_errors = validate_itinerary(
        itinerary,
        data.days
    )


    # ========================================================
    # REINTENTO AUTOMÁTICO
    # ========================================================

    if validation_errors:

        correction_prompt = f"""
La respuesta anterior no superó la validación.

ERRORES DETECTADOS:
{json.dumps(validation_errors, ensure_ascii=False, indent=2)}

RESPUESTA ANTERIOR:
{json.dumps(itinerary, ensure_ascii=False, indent=2)}

Corrige exclusivamente los errores detectados.

REGLAS:

1. Mantén exactamente {data.days} días.
2. Cada día debe contener manana, tarde y noche.
3. Usa solo lugares de la BASE AUTORIZADA.
4. Usa solo actividades exactas autorizadas para cada lugar.
5. No repitas ningún lugar más de dos veces.
6. No inventes lugares ni actividades.
7. No añadas precios, horarios ni transporte.
8. Devuelve únicamente JSON válido.

BASE AUTORIZADA:
{json.dumps(prompt_places, ensure_ascii=False, indent=2)}
"""

        correction_messages = [
            {
                "role": "system",
                "content": (
                    "Corrige itinerarios usando exclusivamente "
                    "los valores de la base autorizada. "
                    "Devuelve únicamente JSON válido."
                )
            },
            {
                "role": "user",
                "content": correction_prompt
            }
        ]

        correction_text = tokenizer.apply_chat_template(
            correction_messages,
            tokenize=False,
            add_generation_prompt=True
        )

        correction_inputs = tokenizer(
            correction_text,
            return_tensors="pt"
        ).to(model.device)

        with torch.no_grad():

            correction_outputs = model.generate(
                **correction_inputs,
                max_new_tokens=1400,
                do_sample=False
            )

        corrected_raw_response = tokenizer.decode(
            correction_outputs[0][
                correction_inputs["input_ids"].shape[1]:
            ],
            skip_special_tokens=True
        )

        corrected_cleaned = clean_json_response(
            corrected_raw_response
        )

        try:

            corrected_itinerary = json.loads(
                corrected_cleaned
            )

        except json.JSONDecodeError as e:

            raise HTTPException(
                status_code=422,
                detail={
                    "message": (
                        "El reintento no generó JSON válido."
                    ),
                    "error": str(e),
                    "first_validation_errors": validation_errors,
                    "raw_response": corrected_raw_response
                }
            )


        corrected_errors = validate_itinerary(
            corrected_itinerary,
            data.days
        )


        if corrected_errors:

            # Reparación determinista final
            repaired_itinerary = repair_repeated_places(
                corrected_itinerary
            )

            repaired_errors = validate_itinerary(
                repaired_itinerary,
                data.days
            )

            if repaired_errors:

                raise HTTPException(
                    status_code=422,
                    detail={
                        "message": (
                            "El itinerario no superó la validación "
                            "después del reintento ni de la "
                            "reparación determinista."
                        ),
                        "first_validation_errors":
                            validation_errors,
                        "second_validation_errors":
                            corrected_errors,
                        "repair_validation_errors":
                            repaired_errors,
                        "raw_response":
                            corrected_raw_response
                    }
                )

            itinerary = repaired_itinerary

        else:

            itinerary = corrected_itinerary


    # ========================================================
    # COSTOS
    # ========================================================

    itinerary = add_costs_to_itinerary(
        itinerary=itinerary,
        adults=data.adults,
        children=data.children,
        budget=data.budget,
        currency=data.currency
    )


    return {
        "status": "validated",
        "itinerary": itinerary
    }


# ============================================================
# FRONTEND
# ============================================================

app.mount(
    "/ui",
    StaticFiles(
        directory="./frontend",
        html=True
    ),
    name="frontend"
)
