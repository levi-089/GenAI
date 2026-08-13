
# Travel AI Planner

## Caso Práctico – Generative AI

Travel AI Planner es un prototipo de planificación inteligente de viajes desarrollado
como parte del módulo de **Generative AI**.

El proyecto explora y compara diferentes estrategias de personalización de modelos
de lenguaje:

- Prompt Engineering
- Retrieval-Augmented Generation (RAG)
- Fine-tuning mediante LoRA / PEFT
- Arquitectura híbrida RAG + LoRA
- Salida estructurada en JSON
- Validación determinista
- Control de presupuesto
- Interfaz web

---

# 1. Objetivo

Desarrollar un sistema capaz de generar itinerarios de viaje personalizados a partir
de preferencias introducidas por el usuario.

El usuario puede indicar:

- destino;
- duración del viaje;
- presupuesto;
- moneda;
- número de adultos;
- número de niños;
- intereses;
- ritmo de viaje;
- restricciones o preferencias.

El sistema devuelve un itinerario organizado por:

- mañana;
- tarde;
- noche.

Además, proporciona:

- lugar recomendado;
- actividad;
- rango de gasto estimado;
- descripción del sitio;
- acceso a Google Maps;
- resumen global de presupuesto.

---

# 2. Modelo utilizado

Modelo base:

`Qwen/Qwen2.5-1.5B-Instruct`

El modelo fue cargado mediante Hugging Face Transformers.

---

# 3. Fine-tuning

Se realizó una prueba de fine-tuning utilizando:

- PEFT;
- LoRA;
- Hugging Face Trainer.

Configuración principal:

- LoRA rank: 8
- LoRA alpha: 16
- LoRA dropout: 0.05
- Learning rate: 2e-4
- Epochs: 5
- Batch size: 1
- Gradient accumulation: 2

Parámetros entrenables:

`2,179,072`

Parámetros totales:

`1,545,893,376`

Porcentaje entrenado:

`0.141 %`

El entrenamiento finalizó con:

`train_loss ≈ 1.62`

El dataset utilizado contenía únicamente tres ejemplos, por lo que el fine-tuning
se considera una **prueba de concepto académica**, no un entrenamiento suficiente
para producción.

---

# 4. Estrategias evaluadas

Durante el desarrollo se compararon los siguientes enfoques:

| Enfoque | JSON válido | Esquema correcto | Grounding | Alucinaciones |
|---|---:|---:|---:|---:|
| Modelo base | Sí | No | No | Sí |
| Prompting | Parcial | Parcial | No | Sí |
| RAG inicial | Parcial | Parcial | Parcial | Sí |
| RAG ampliado | Parcial | Parcial | Parcial | Sí |
| RAG estructurado | Sí | Sí | Sí | No |
| Fine-tuning LoRA | Sí | No | No | Sí |
| Híbrido RAG + LoRA | Sí | Sí | Sí | No |

La arquitectura híbrida presentó el mejor comportamiento dentro del experimento.

---

# 5. Arquitectura final

    Usuario
       |
       v
    Frontend HTML / CSS / JavaScript
       |
       v
    FastAPI
       |
       v
    Prompt Engineering
       |
       v
    Base de conocimiento estructurada
       |
       v
    Qwen2.5 + LoRA
       |
       v
    Validación determinista
       |
       v
    Reparación de inconsistencias
       |
       v
    Cálculo de costos en Python
       |
       v
    Control de presupuesto
       |
       v
    JSON validado
       |
       v
    Frontend

---

# 6. RAG y grounding

Inicialmente se utilizó una base de conocimiento pequeña y recuperación mediante:

- Sentence Transformers;
- embeddings multilingües;
- FAISS.

Modelo de embeddings:

`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

Los primeros experimentos mostraron que RAG reducía las alucinaciones, pero no
garantizaba que el modelo utilizara exclusivamente la información recuperada.

Por este motivo se evolucionó hacia un **RAG estructurado**, donde cada lugar contiene
un conjunto explícito de actividades autorizadas.

Ejemplo conceptual:

    {
      "Museo Botero": {
        "category": [
          "arte",
          "cultura"
        ],
        "allowed_activities": {
          "observar obras de Fernando Botero": {
            "min_cost_usd": 5,
            "max_cost_usd": 15
          }
        }
      }
    }

---

# 7. Control de alucinaciones

La salida del modelo no se acepta directamente.

Después de la generación, Python valida:

1. JSON válido.
2. Número correcto de días.
3. Existencia de mañana, tarde y noche.
4. Lugares existentes en la base autorizada.
5. Actividades autorizadas para cada lugar.
6. Máximo de repeticiones por lugar.
7. Estructura requerida.

Si una respuesta falla, el sistema puede intentar una corrección y posteriormente
aplicar una reparación determinista.

Solo los itinerarios que pasan la validación son enviados al frontend.

---

# 8. Presupuesto y costos

Los costos NO son generados libremente por el LLM.

Los rangos de gasto se almacenan dentro de la base estructurada y Python calcula:

- costo estimado por persona;
- costo estimado para el grupo;
- costo diario;
- costo mínimo del viaje;
- costo máximo del viaje;
- comparación con el presupuesto.

Los valores utilizados en este prototipo son **estimaciones académicas de planificación**
y no deben interpretarse como precios oficiales o en tiempo real.

Ejemplo:

    Presupuesto: USD 1,700
    Gasto estimado: USD 270 - 740
    Viajeros: 2
    Estado: Dentro del presupuesto

---

# 9. Información adicional de los lugares

Cada recomendación puede contener:

- descripción;
- rango estimado de gasto;
- enlace a Google Maps.

Los enlaces de Google Maps utilizan búsquedas por nombre del sitio para evitar depender
de coordenadas o direcciones almacenadas que puedan quedar desactualizadas.

---

# 10. Interfaz

La aplicación utiliza:

- HTML5;
- CSS3;
- JavaScript.

El frontend permite:

- configurar el viaje;
- seleccionar intereses;
- definir presupuesto;
- indicar viajeros;
- generar el itinerario;
- visualizar gasto estimado;
- consultar información adicional;
- abrir los lugares en Google Maps.

Las tarjetas cuentan con interacción mediante hover y selección, facilitando la
exploración visual del itinerario.

Los días se presentan mediante bloques diferenciados con mañana, tarde y noche,
mejorando la jerarquía visual y la experiencia del usuario.

---

# 11. Backend

El backend fue construido utilizando:

`FastAPI`

Endpoints principales:

    GET /
    POST /generate

El endpoint `/generate` recibe las preferencias y devuelve únicamente itinerarios
que superan la validación.

La API integra:

- generación con Qwen;
- adaptador LoRA;
- base estructurada;
- validación determinista;
- reparación de repeticiones;
- cálculo de costos;
- evaluación de presupuesto.

---

# 12. Estructura del proyecto

    travel_ai_project/
    │
    ├── app.py
    ├── app_config.json
    ├── authorized_places.json
    ├── requirements.txt
    ├── README.md
    │
    ├── qwen_travel_lora/
    │   ├── adapter_config.json
    │   ├── adapter_model.safetensors
    │   ├── tokenizer.json
    │   ├── tokenizer_config.json
    │   ├── chat_template.jinja
    │   └── README.md
    │
    └── frontend/
        ├── index.html
        ├── styles.css
        └── script.js

---



> **Nota de reproducibilidad sobre LoRA:** el notebook `Deivy_G_GenAI_U1.ipynb`
> contiene el entrenamiento y la evidencia de ejecución del adaptador LoRA. El
> binario `adapter_model.safetensors` no se versiona en este repositorio. Si la
> carpeta `qwen_travel_lora/` no está disponible, `app.py` puede ejecutarse con
> el modelo base y mantiene el RAG estructurado, las validaciones y el control
> de presupuesto. Para reproducir exactamente la variante híbrida, regenere el
> adaptador ejecutando las celdas de fine-tuning del notebook.

---

# 13. Instalación

Instalar dependencias:

    pip install -r requirements.txt

Ejecutar FastAPI:

    uvicorn app:app --host 0.0.0.0 --port 8000

Abrir la interfaz:

    http://localhost:8000/ui/

---

# 14. Tecnologías utilizadas

- Python
- PyTorch
- Hugging Face Transformers
- Qwen2.5
- PEFT
- LoRA
- Sentence Transformers
- FAISS
- FastAPI
- Pydantic
- HTML
- CSS
- JavaScript
- Google Colab
- Google Maps

---

# 15. Resultados

El experimento mostró que el modelo base puede generar itinerarios coherentes,
pero presenta problemas de factualidad y control de formato.

Prompt Engineering mejoró considerablemente el seguimiento de instrucciones, pero
no eliminó las alucinaciones.

RAG permitió introducir conocimiento externo, aunque el contexto por sí solo no
garantizó que el modelo respetara completamente las restricciones.

El RAG estructurado y la validación determinista permitieron controlar de forma
mucho más efectiva los lugares y actividades generados.

El fine-tuning mediante LoRA demostró que es posible adaptar eficientemente un LLM,
entrenando únicamente una pequeña fracción de sus parámetros. No obstante, el dataset
de tres ejemplos fue insuficiente para conseguir una mejora funcional robusta de forma
independiente.

La combinación de:

- Prompt Engineering;
- RAG estructurado;
- LoRA;
- validación determinista;
- reparación programática;

produjo el resultado más consistente del experimento.

---

# 16. Conclusiones

RAG y fine-tuning resuelven problemas diferentes.

**RAG** es adecuado cuando la aplicación necesita incorporar conocimiento externo,
controlado o actualizable.

**Fine-tuning** resulta útil para adaptar patrones de comportamiento, formato,
estilo o especialización del modelo.

Para aplicaciones donde la exactitud y el control de las respuestas son importantes,
no es recomendable confiar únicamente en el LLM.

Una arquitectura que combine:

`LLM + RAG + structured output + validación determinista`

puede ofrecer un mayor nivel de control y reducir significativamente las alucinaciones.

El desarrollo también evidenció que la generación de lenguaje y la lógica de negocio
deben mantenerse separadas cuando existen restricciones objetivas. Por esta razón,
los costos y la validación de presupuesto fueron implementados mediante lógica
determinista en Python en lugar de solicitar al LLM que estimara libremente los valores.

---

# 17. Limitaciones

Este proyecto es una prueba de concepto académica.

Principales limitaciones:

- base de conocimiento limitada principalmente a Bogotá;
- costos estimados y no conectados a precios en tiempo real;
- dataset de fine-tuning de solo tres ejemplos;
- no existe todavía una fuente externa de información turística dinámica;
- la versión de prueba ejecuta el modelo en infraestructura temporal de Google Colab;
- los valores de moneda distintos a USD requieren conversión externa;
- no se incluyen costos completos de vuelos, alojamiento u otros componentes del viaje;
- la base de lugares y actividades es controlada y relativamente pequeña;
- los costos son rangos académicos orientativos.

---

# 18. Posibles mejoras

Como evolución del prototipo se podrían implementar:

- integración con APIs turísticas;
- precios reales de hoteles y actividades;
- información meteorológica;
- conversión automática de moneda;
- rutas geográficas optimizadas;
- recomendaciones de restaurantes;
- base RAG para múltiples ciudades;
- evaluación automática de relevancia;
- dataset de fine-tuning de mayor tamaño;
- autenticación de usuarios;
- almacenamiento de viajes;
- exportación del itinerario;
- generación de itinerarios en PDF;
- backend desplegado permanentemente en infraestructura cloud;
- integración con vuelos y alojamiento;
- uso de información turística actualizada;
- incorporación de coordenadas geográficas;
- optimización de trayectos entre lugares.

---

# 19. Flujo de funcionamiento

El flujo final de la aplicación es:

1. El usuario introduce sus preferencias.
2. El frontend envía los datos a FastAPI.
3. El backend crea el prompt estructurado.
4. Qwen + LoRA genera una propuesta.
5. Python valida el esquema.
6. Se comprueban lugares y actividades.
7. Se controlan las repeticiones.
8. Si es necesario, se aplica reparación.
9. Python añade los costos autorizados.
10. Se calcula el gasto mínimo y máximo del grupo.
11. Se compara el gasto con el presupuesto.
12. La API devuelve el JSON validado.
13. El frontend renderiza el itinerario.
14. El usuario puede consultar detalles y abrir Google Maps.

---

# 20. Aprendizajes del experimento

El desarrollo permitió comprobar en la práctica varias diferencias importantes
entre Prompting, RAG y Fine-tuning.

### Prompting

Es una técnica rápida y económica para modificar el comportamiento del modelo,
pero no garantiza factualidad.

### RAG

Permite incorporar información externa sin modificar los pesos del modelo.

Su calidad depende significativamente de:

- calidad de la base documental;
- diversidad del contexto;
- estrategia de recuperación;
- estructura de la información recuperada.

### Fine-tuning

Permite modificar patrones aprendidos por el modelo, pero necesita:

- suficientes ejemplos;
- datos de buena calidad;
- evaluación posterior;
- recursos de entrenamiento.

### Arquitectura híbrida

El mejor comportamiento se obtuvo al asignar responsabilidades diferentes a
cada componente:

- LLM: generación y selección;
- RAG: conocimiento;
- LoRA: adaptación;
- Python: reglas y validación;
- frontend: experiencia del usuario.

---

# 21. Contexto académico

Proyecto desarrollado como Caso Práctico de la Unidad 1 del módulo de
**Generative AI**, enfocado en personalización de modelos de lenguaje mediante:

- Prompting;
- Retrieval-Augmented Generation;
- Fine-tuning;
- arquitecturas híbridas.

El proyecto se desarrolló de forma experimental, comparando diferentes estrategias
y documentando tanto los resultados exitosos como las limitaciones encontradas.
