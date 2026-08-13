
const API_URL = "/generate";

const form = document.getElementById("travelForm");
const statusSection = document.getElementById("statusSection");
const statusMessage = document.getElementById("statusMessage");
const resultSection = document.getElementById("resultSection");
const itineraryContainer = document.getElementById("itineraryContainer");
const generateButton = document.getElementById("generateButton");
const newSearchButton = document.getElementById("newSearchButton");


function getSelectedInterests() {

    return Array.from(
        document.querySelectorAll(
            'input[name="interests"]:checked'
        )
    ).map(
        input => input.value
    );
}


function getRestrictions() {

    const value = document
        .getElementById("restrictions")
        .value
        .trim();

    if (!value) {
        return [];
    }

    return value
        .split(",")
        .map(item => item.trim())
        .filter(Boolean);
}


function showStatus(message) {

    statusMessage.textContent = message;

    statusSection.classList.remove("hidden");
    resultSection.classList.add("hidden");
}


function hideStatus() {

    statusSection.classList.add("hidden");
}


function showError(message) {

    hideStatus();

    itineraryContainer.innerHTML = `
        <div class="error-box">
            <strong>No fue posible generar el itinerario.</strong>
            <p>${message}</p>
        </div>
    `;

    resultSection.classList.remove("hidden");
}


function createPeriodCard(title, data) {

    const cost = data.costo_estimado || {};
    const groupCost = cost.grupo || {};

    const minCost =
        groupCost.min !== undefined
        ? groupCost.min
        : "-";

    const maxCost =
        groupCost.max !== undefined
        ? groupCost.max
        : "-";

    return `
        <div class="period-card">

            <div class="period-title">
                ${title}
            </div>

            <p class="place">
                ${data.lugar}
            </p>

            <p class="activity">
                ${data.actividad}
            </p>

            <p class="activity">
                <strong>Costo estimado grupo:</strong>
                USD ${minCost} - ${maxCost}
            </p>

            <details class="place-details">

                <summary>
                    Ver detalles
                </summary>

                <p>
                    ${data.descripcion || "Información no disponible."}
                </p>

                ${
                    data.google_maps_url
                    ? `
                        <a
                            href="${data.google_maps_url}"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="maps-link"
                        >
                            Abrir en Google Maps
                        </a>
                    `
                    : ""
                }

            </details>

        </div>
    `;
}




function activatePeriodCards() {

    const cards = document.querySelectorAll(
        ".period-card"
    );

    cards.forEach(card => {

        card.setAttribute(
            "tabindex",
            "0"
        );

        card.addEventListener(
            "click",
            event => {

                // Permitir que los enlaces de Google Maps
                // funcionen normalmente
                if (
                    event.target.closest(
                        ".maps-link"
                    )
                ) {
                    return;
                }

                // Quitar selección anterior
                cards.forEach(
                    otherCard => {
                        if (otherCard !== card) {
                            otherCard.classList.remove(
                                "selected"
                            );
                        }
                    }
                );

                // Activar tarjeta actual
                card.classList.toggle(
                    "selected"
                );

                // Abrir detalles automáticamente
                const details =
                    card.querySelector(
                        ".place-details"
                    );

                if (
                    details &&
                    card.classList.contains(
                        "selected"
                    )
                ) {
                    details.open = true;
                }
            }
        );


        // Accesibilidad con teclado
        card.addEventListener(
            "keydown",
            event => {

                if (
                    event.key === "Enter" ||
                    event.key === " "
                ) {

                    event.preventDefault();
                    card.click();
                }
            }
        );
    });
}




function createBudgetSummary(summary) {

    if (!summary) {
        return "";
    }

    const budget =
        summary.presupuesto_ingresado ?? "-";

    const minCost =
        summary.costo_estimado_min ?? "-";

    const maxCost =
        summary.costo_estimado_max ?? "-";

    const currency =
        summary.moneda_presupuesto || "USD";

    const status =
        summary.estado || "";

    let statusText = "";
    let statusClass = "";

    if (status === "dentro_del_presupuesto") {
        statusText = "Dentro del presupuesto";
        statusClass = "budget-ok";
    }

    else if (
        status === "riesgo_de_superar_presupuesto"
    ) {
        statusText = "Riesgo de superar el presupuesto";
        statusClass = "budget-warning";
    }

    else if (
        status === "fuera_del_presupuesto"
    ) {
        statusText = "Fuera del presupuesto";
        statusClass = "budget-danger";
    }

    else {
        statusText = "Revisión de presupuesto requerida";
        statusClass = "budget-neutral";
    }


    return `
        <section class="budget-summary">

            <div class="budget-item">
                <span class="budget-label">
                    Presupuesto
                </span>

                <strong>
                    ${currency} ${budget}
                </strong>
            </div>


            <div class="budget-item">
                <span class="budget-label">
                    Gasto estimado
                </span>

                <strong>
                    USD ${minCost} - ${maxCost}
                </strong>
            </div>


            <div class="budget-item">
                <span class="budget-label">
                    Viajeros
                </span>

                <strong>
                    ${summary.viajeros?.total ?? "-"}
                </strong>
            </div>


            <div class="budget-status ${statusClass}">
                ${statusText}
            </div>

        </section>
    `;
}


function renderItinerary(data) {

    if (!data || !Array.isArray(data.dias)) {
        throw new Error(
            "La respuesta recibida no tiene el formato esperado."
        );
    }

    itineraryContainer.innerHTML = "";

    itineraryContainer.insertAdjacentHTML(
        "beforeend",
        createBudgetSummary(
            data.resumen_presupuesto
        )
    );

    data.dias.forEach(day => {

        const dayCard = document.createElement("article");

        dayCard.className = "day-card";

        const dayCost = day.costo_dia || {};

        const dayMin =
            dayCost.min !== undefined
            ? dayCost.min
            : "-";

        const dayMax =
            dayCost.max !== undefined
            ? dayCost.max
            : "-";


        dayCard.innerHTML = `
            <div class="day-header">

                <h3>
                    Día ${day.dia}
                </h3>

                <span class="day-cost">
                    USD ${dayMin} - ${dayMax}
                </span>

            </div>

            <div class="period-grid">

                ${createPeriodCard(
                    "Mañana",
                    day.manana
                )}

                ${createPeriodCard(
                    "Tarde",
                    day.tarde
                )}

                ${createPeriodCard(
                    "Noche",
                    day.noche
                )}

            </div>
        `;

        itineraryContainer.appendChild(dayCard);
    });

    activatePeriodCards();

    hideStatus();
    resultSection.classList.remove("hidden");

    resultSection.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


function cleanModelResponse(response) {

    if (typeof response !== "string") {
        return response;
    }

    let cleaned = response.trim();

    cleaned = cleaned.replace(
        /^```json\s*/i,
        ""
    );

    cleaned = cleaned.replace(
        /\s*```$/,
        ""
    );

    return JSON.parse(cleaned);
}


form.addEventListener(
    "submit",
    async event => {

        event.preventDefault();

        const interests = getSelectedInterests();

        if (interests.length === 0) {

            showError(
                "Selecciona al menos un interés."
            );

            return;
        }

        const payload = {
            destination:
                document.getElementById(
                    "destination"
                ).value.trim(),

            days:
                Number(
                    document.getElementById(
                        "days"
                    ).value
                ),

            budget:
                Number(
                    document.getElementById(
                        "budget"
                    ).value
                ),

            currency:
                document.getElementById(
                    "currency"
                ).value,

            adults:
                Number(
                    document.getElementById(
                        "adults"
                    ).value
                ),

            children:
                Number(
                    document.getElementById(
                        "children"
                    ).value
                ),

            interests:
                interests,

            travel_style:
                document.getElementById(
                    "travelStyle"
                ).value,

            restrictions:
                getRestrictions()
        };


        generateButton.disabled = true;
        generateButton.textContent =
            "Generando...";

        showStatus(
            "La IA está construyendo tu itinerario..."
        );


        try {

            const response = await fetch(
                API_URL,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            payload
                        )
                }
            );


            if (!response.ok) {

                const errorText =
                    await response.text();

                throw new Error(
                    `Error ${response.status}: ${errorText}`
                );
            }


            const apiData =
                await response.json();


            if (
                apiData.status !== "validated" ||
                !apiData.itinerary
            ) {
                throw new Error(
                    "La API no devolvió un itinerario validado."
                );
            }


            renderItinerary(
                apiData.itinerary
            );

        }

        catch (error) {

            console.error(error);

            showError(
                error.message
            );

        }

        finally {

            generateButton.disabled = false;

            generateButton.textContent =
                "Generar itinerario";
        }
    }
);


newSearchButton.addEventListener(
    "click",
    () => {

        resultSection.classList.add(
            "hidden"
        );

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    }
);