"""
ADK finance analyzer agent.

Run this script after scrape.py has populated the pdf/ directory:

    uv run agent.py
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pdfplumber
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

load_dotenv()

# ADK/Gemini expects GOOGLE_API_KEY for the Developer API (non-Vertex path).
os.environ.setdefault("GOOGLE_API_KEY", os.environ["G_STUDIO_API_KEY"])

MODEL = "gemini-3.1-flash-lite-preview"
APP_NAME = "lukaton"
USER_ID = "owner"

# ---------------------------------------------------------------------------
# System instruction
# ---------------------------------------------------------------------------

SYSTEM_INSTRUCTION = """\
Eres un analista financiero personal experto en finanzas domésticas chilenas.
Recibes el texto extraído de estados de cuenta bancarios y de tarjetas de crédito
(Banco de Chile, CMR Falabella y otros) y generas reportes financieros mensuales
claros, detallados y accionables.

## Tus tareas

### 1. Extracción de transacciones
- Identifica cada cargo: fecha, comercio/descripción, monto en CLP (o USD/EUR si aplica).
- Ignora pagos/abonos al estado de cuenta (entradas de crédito, no gastos),
  reversas y transferencias entre cuentas propias del usuario.

### 2. Categorización
Asigna cada gasto exactamente a una categoría:

| Categoría | Ejemplos |
|-----------|----------|
| 🛒 Supermercado & Almacén | Líder, Jumbo, Unimarc, Santa Isabel |
| 🍽️ Restaurantes & Delivery | PedidosYa, Uber Eats, restaurantes |
| ⛽ Combustible & Transporte | Copec, Shell, Uber, Cabify, Bip! |
| 🏥 Salud & Farmacia | Cruz Verde, Salcobrand, consultas médicas |
| 🎓 Educación & Suscripciones | colegiaturas, cursos, libros, software |
| 🛍️ Ropa & Moda | Falabella, Ripley, Zara, tiendas de ropa |
| 🏠 Hogar & Servicios | agua, luz, gas, arriendo, ferretería |
| 🎮 Entretenimiento & Ocio | cine, streaming (Netflix, Spotify), juegos |
| 💻 Tecnología & Gadgets | electrónica, accesorios tech, Apple, Samsung |
| 🐾 Mascotas | veterinaria, alimento, accesorios |
| 💼 Trabajo & Profesional | herramientas de trabajo, coworking, viáticos |
| ✈️ Viajes & Turismo | vuelos, hoteles, LATAM, Booking |
| 🏦 Cargos bancarios | comisiones, mantención, intereses |
| ❓ Sin categoría | todo lo demás |

### 3. Resumen mensual
- Total gastado por categoría: monto absoluto y porcentaje del total.
- Total general del período.
- Si hay estados que cubren varios meses, muestra desglose mes a mes.

### 4. Métricas clave
- Top 5 comercios por gasto total.
- Transacción individual de mayor monto.
- Promedio de gasto diario.
- Comparación gasto fin de semana vs días hábiles (si hay fechas disponibles).

### 5. Insights y recomendaciones
Proporciona entre 4 y 6 observaciones concretas y personalizadas:
- Categorías que concentran un porcentaje desproporcionado del total.
- Suscripciones o cargos recurrentes que vale la pena revisar o cancelar.
- Comparación con benchmarks típicos de un hogar chileno de clase media.
- Sugerencias específicas y prácticas para reducir el gasto en las 2–3 categorías más altas.
- Patrones de comportamiento (ej. gasto excesivo los fines de semana, acumulación a fin de mes).
- Oportunidades de ahorro concretas (planes, alternativas más baratas, etc.).

## Formato de salida
- Responde en **español** usando Markdown con encabezados, tablas y listas.
- Todos los montos en CLP con separador de miles (ejemplo: $1.234.567).
- Sé conciso pero completo — el reporte debe ser accionable de inmediato.
- Termina siempre con una sección **"Próximos pasos"** con 3 acciones prioritarias ordenadas
  por impacto esperado en el ahorro mensual.
"""

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

PDF_DIR = Path(__file__).parent / "pdf"


def read_bank_statements() -> str:
    """
    Lee todos los PDFs de estados de cuenta bancarios descargados en el
    directorio pdf/ del proyecto y retorna su contenido de texto completo,
    etiquetado por nombre de archivo.

    Retorna un mensaje descriptivo si el directorio está vacío o no existen PDFs.
    """
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))

    if not pdf_files:
        return (
            "No se encontraron archivos PDF en el directorio pdf/. "
            "Ejecuta primero scrape.py para descargar los estados de cuenta."
        )

    sections: list[str] = []
    for path in pdf_files:
        with pdfplumber.open(path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        body = "\n".join(pages).strip()
        sections.append(f"=== Estado de cuenta: {path.name} ===\n{body}")

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

finance_agent = Agent(
    name="lukaton_finance_analyzer",
    model=MODEL,
    description=(
        "Analiza estados de cuenta chilenos para resumir gastos mensuales, "
        "categorizar el gasto y generar insights financieros accionables."
    ),
    instruction=SYSTEM_INSTRUCTION,
    tools=[read_bank_statements],
)

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


async def run_analysis() -> None:
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )

    runner = Runner(
        agent=finance_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    message = types.Content(
        role="user",
        parts=[
            types.Part(
                text=(
                    "Usa la herramienta read_bank_statements para leer mis estados "
                    "de cuenta y genera el reporte financiero mensual completo."
                )
            )
        ],
    )

    print("Analizando estados de cuenta...\n")
    print("=" * 60)

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=message,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(part.text)


if __name__ == "__main__":
    asyncio.run(run_analysis())
