#!/usr/bin/env python3
"""
GGB Batch Production Engine — generates 100 how-to ebooks, audiobooks,
25 Pinterest pins, and Spanish translations in one automated run.
Tests the full publishing pipeline at scale.
"""
import json, sys, uuid, subprocess, random, shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import PublishEngine, StateStore, REPO_ROOT, STAGING_DIR, PUBLISH_DIR
from PIL import Image, ImageDraw, ImageFont

# Landing pad — all generated content goes here for auto-discovery
LANDING_PAD = REPO_ROOT / "publish" / "landing-pad"
LANDING_PAD.mkdir(parents=True, exist_ok=True)

VOICE_ENGINE = Path(__file__).resolve().parent / "human-voice-engine.py"
LANDING_PAD_SCRIPT = Path(__file__).resolve().parent / "landing-pad.py"
AUDIO_OUTPUT_DIR = REPO_ROOT / "publish" / "audio"

BATCH_DIR = REPO_ROOT / "publish" / "batch-test"
CONTENT_DIR = BATCH_DIR / "content"
AUDIO_DIR = BATCH_DIR / "audio"
PINS_DIR = BATCH_DIR / "pins"
TRANSLATIONS_DIR = BATCH_DIR / "translations"
REPORTS_DIR = BATCH_DIR / "reports"

for d in [CONTENT_DIR, AUDIO_DIR, PINS_DIR, TRANSLATIONS_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── 100 How-To Topics ─────────────────────────────────────────────────────

HOW_TO_TOPICS = [
    # Self-Help / Personal Development (30)
    ("How to Find Your Purpose", "self-help"),
    ("How to Build Unshakeable Confidence", "self-help"),
    ("How to Master Your Morning Routine", "self-help"),
    ("How to Overcome Imposter Syndrome", "self-help"),
    ("How to Practice Radical Self-Care", "self-help"),
    ("How to Set Boundaries That Stick", "self-help"),
    ("How to Break Bad Habits Forever", "self-help"),
    ("How to Cultivate Daily Gratitude", "self-help"),
    ("How to Manage Anxiety Naturally", "self-help"),
    ("How to Develop Emotional Intelligence", "self-help"),
    ("How to Forgive Yourself and Move On", "self-help"),
    ("How to Stay Motivated Every Day", "self-help"),
    ("How to Build Resilience in Tough Times", "self-help"),
    ("How to Practice Mindful Living", "self-help"),
    ("How to Let Go of Perfectionism", "self-help"),
    ("How to Create a Personal Mission Statement", "self-help"),
    ("How to Develop a Growth Mindset", "self-help"),
    ("How to Handle Criticism Gracefully", "self-help"),
    ("How to Build Healthy Relationships", "self-help"),
    ("How to Find Inner Peace", "self-help"),
    ("How to Stop People-Pleasing", "self-help"),
    ("How to Embrace Your Authentic Self", "self-help"),
    ("How to Navigate Life Transitions", "self-help"),
    ("How to Practice Self-Compassion", "self-help"),
    ("How to Build Mental Toughness", "self-help"),
    ("How to Create a Vision Board That Works", "self-help"),
    ("How to Develop Daily Discipline", "self-help"),
    ("How to Overcome Fear of Failure", "self-help"),
    ("How to Cultivate Patience", "self-help"),
    ("How to Live with Intention", "self-help"),
    # Business / Entrepreneurship (35)
    ("How to Start a Side Hustle", "business"),
    ("How to Build a Personal Brand", "business"),
    ("How to Create a Business Plan", "business"),
    ("How to Master Social Media Marketing", "business"),
    ("How to Launch an Online Course", "business"),
    ("How to Write a Winning Grant Proposal", "business"),
    ("How to Build an Email List from Scratch", "business"),
    ("How to Price Your Products or Services", "business"),
    ("How to Network Like a Pro", "business"),
    ("How to Manage Business Finances", "business"),
    ("How to Create a Content Strategy", "business"),
    ("How to Build a Website on a Budget", "business"),
    ("How to Master Public Speaking", "business"),
    ("How to Negotiate Better Deals", "business"),
    ("How to Build a Remote Team", "business"),
    ("How to Scale Your Small Business", "business"),
    ("How to Create a Marketing Funnel", "business"),
    ("How to Use AI in Your Business", "business"),
    ("How to Build Customer Loyalty", "business"),
    ("How to Manage Your Time Effectively", "business"),
    ("How to Create a Sales Funnel", "business"),
    ("How to Build Strategic Partnerships", "business"),
    ("How to Master Email Marketing", "business"),
    ("How to Create a Brand Style Guide", "business"),
    ("How to Build a Freelance Career", "business"),
    ("How to Write Copy That Sells", "business"),
    ("How to Create a Product Launch Plan", "business"),
    ("How to Build a Community Around Your Brand", "business"),
    ("How to Master LinkedIn for Business", "business"),
    ("How to Create a Customer Journey Map", "business"),
    ("How to Build a Subscription Business", "business"),
    ("How to Create a Referral Program", "business"),
    ("How to Master Business Storytelling", "business"),
    ("How to Build a Digital Product Empire", "business"),
    ("How to Create a Business Exit Strategy", "business"),
    # Cooking / Lifestyle (35)
    ("How to Cook Perfect Gullah Red Rice", "cooking"),
    ("How to Make Southern Cornbread from Scratch", "cooking"),
    ("How to Fry the Perfect Fish", "cooking"),
    ("How to Make Authentic Shrimp and Grits", "cooking"),
    ("How to Bake Sweet Potato Pie", "cooking"),
    ("How to Make Hoppin' John for New Year's", "cooking"),
    ("How to Cook Collard Greens the Right Way", "cooking"),
    ("How to Make Benne Wafers", "cooking"),
    ("How to Prepare Okra and Tomatoes", "cooking"),
    ("How to Make Gullah Tea Cakes", "cooking"),
    ("How to Cook Lowcountry Boil", "cooking"),
    ("How to Make Pickled Shrimp", "cooking"),
    ("How to Bake Buttermilk Cornbread", "cooking"),
    ("How to Make Boiled Peanuts", "cooking"),
    ("How to Cook Gullah Cabbage", "cooking"),
    ("How to Make Mac and Cheese the Southern Way", "cooking"),
    ("How to Prepare Gullah Chicken Soup", "cooking"),
    ("How to Make Rice Pudding", "cooking"),
    ("How to Cook Gullah Pork Chops", "cooking"),
    ("How to Make Sweetgrass Lemonade", "cooking"),
    ("How to Make Gullah Potato Salad", "cooking"),
    ("How to Cook Benne Chicken", "cooking"),
    ("How to Make Gullah Breakfast", "cooking"),
    ("How to Preserve Summer Vegetables", "cooking"),
    ("How to Master Cast Iron Cooking", "cooking"),
    ("How to Make One-Pot Gullah Meals", "cooking"),
    ("How to Cook with Seasonal Lowcountry Ingredients", "cooking"),
    ("How to Make Gullah Sauces and Seasonings", "cooking"),
    ("How to Bake Gullah Desserts", "cooking"),
    ("How to Make Holiday Gullah Feasts", "cooking"),
    ("How to Cook Gullah Seafood", "cooking"),
    ("How to Make Gullah Soups and Stews", "cooking"),
    ("How to Prepare Gullah Side Dishes", "cooking"),
    ("How to Make Gullah Breads", "cooking"),
    ("How to Cook Gullah Vegetables", "cooking"),
]

# ─── Spanish Title Translations ───────────────────────────────────────────

SPANISH_TITLES = {
    "How to Find Your Purpose": "Cómo Encontrar tu Propósito",
    "How to Build Unshakeable Confidence": "Cómo Construir una Confianza Inquebrantable",
    "How to Master Your Morning Routine": "Cómo Dominar tu Rutina Matutina",
    "How to Overcome Imposter Syndrome": "Cómo Superar el Síndrome del Impostor",
    "How to Practice Radical Self-Care": "Cómo Practicar el Cuidado Personal Radical",
    "How to Set Boundaries That Stick": "Cómo Establecer Límites que Funcionen",
    "How to Break Bad Habits Forever": "Cómo Romper Malos Hábitos para Siempre",
    "How to Cultivate Daily Gratitude": "Cómo Cultivar la Gratitud Diaria",
    "How to Manage Anxiety Naturally": "Cómo Manejar la Ansiedad de Forma Natural",
    "How to Develop Emotional Intelligence": "Cómo Desarrollar la Inteligencia Emocional",
    "How to Forgive Yourself and Move On": "Cómo Perdonarte a Ti Mismo y Seguir Adelante",
    "How to Stay Motivated Every Day": "Cómo Mantenerse Motivado Cada Día",
    "How to Build Resilience in Tough Times": "Cómo Desarrollar Resiliencia en Tiempos Difíciles",
    "How to Practice Mindful Living": "Cómo Practicar la Vida Consciente",
    "How to Let Go of Perfectionism": "Cómo Dejar Ir el Perfeccionismo",
    "How to Create a Personal Mission Statement": "Cómo Crear una Declaración de Misión Personal",
    "How to Develop a Growth Mindset": "Cómo Desarrollar una Mentalidad de Crecimiento",
    "How to Handle Criticism Gracefully": "Cómo Manejar las Críticas con Gracia",
    "How to Build Healthy Relationships": "Cómo Construir Relaciones Saludables",
    "How to Find Inner Peace": "Cómo Encontrar la Paz Interior",
    "How to Stop People-Pleasing": "Cómo Dejar de Complacer a los Demás",
    "How to Embrace Your Authentic Self": "Cómo Abrazar tu Ser Auténtico",
    "How to Navigate Life Transitions": "Cómo Navegar las Transiciones de la Vida",
    "How to Practice Self-Compassion": "Cómo Practicar la Autocompasión",
    "How to Build Mental Toughness": "Cómo Desarrollar la Fortaleza Mental",
    "How to Create a Vision Board That Works": "Cómo Crear un Tablero de Visión que Funcione",
    "How to Develop Daily Discipline": "Cómo Desarrollar la Disciplina Diaria",
    "How to Overcome Fear of Failure": "Cómo Superar el Miedo al Fracaso",
    "How to Cultivate Patience": "Cómo Cultivar la Paciencia",
    "How to Live with Intention": "Cómo Vivir con Intención",
    "How to Start a Side Hustle": "Cómo Empezar un Negocio Paralelo",
    "How to Build a Personal Brand": "Cómo Construir una Marca Personal",
    "How to Create a Business Plan": "Cómo Crear un Plan de Negocios",
    "How to Master Social Media Marketing": "Cómo Dominar el Marketing en Redes Sociales",
    "How to Launch an Online Course": "Cómo Lanzar un Curso en Línea",
    "How to Write a Winning Grant Proposal": "Cómo Escribir una Propuesta de Subvención Ganadora",
    "How to Build an Email List from Scratch": "Cómo Construir una Lista de Correo desde Cero",
    "How to Price Your Products or Services": "Cómo Fijar el Precio de tus Productos o Servicios",
    "How to Network Like a Pro": "Cómo Hacer Networking como un Profesional",
    "How to Manage Business Finances": "Cómo Gestionar las Finanzas Empresariales",
    "How to Create a Content Strategy": "Cómo Crear una Estrategia de Contenido",
    "How to Build a Website on a Budget": "Cómo Construir un Sitio Web con Presupuesto Limitado",
    "How to Master Public Speaking": "Cómo Dominar el Hablar en Público",
    "How to Negotiate Better Deals": "Cómo Negociar Mejores Acuerdos",
    "How to Build a Remote Team": "Cómo Construir un Equipo Remoto",
    "How to Scale Your Small Business": "Cómo Escalar tu Pequeña Empresa",
    "How to Create a Marketing Funnel": "Cómo Crear un Embudo de Marketing",
    "How to Use AI in Your Business": "Cómo Usar la IA en tu Negocio",
    "How to Build Customer Loyalty": "Cómo Construir la Lealtad del Cliente",
    "How to Manage Your Time Effectively": "Cómo Gestionar tu Tiempo Efectivamente",
    "How to Create a Sales Funnel": "Cómo Crear un Embudo de Ventas",
    "How to Build Strategic Partnerships": "Cómo Construir Alianzas Estratégicas",
    "How to Master Email Marketing": "Cómo Dominar el Marketing por Correo Electrónico",
    "How to Create a Brand Style Guide": "Cómo Crear una Guía de Estilo de Marca",
    "How to Build a Freelance Career": "Cómo Construir una Carrera Freelance",
    "How to Write Copy That Sells": "Cómo Escribir Textos que Venden",
    "How to Create a Product Launch Plan": "Cómo Crear un Plan de Lanzamiento de Producto",
    "How to Build a Community Around Your Brand": "Cómo Construir una Comunidad Alrededor de tu Marca",
    "How to Master LinkedIn for Business": "Cómo Dominar LinkedIn para Negocios",
    "How to Create a Customer Journey Map": "Cómo Crear un Mapa del Viaje del Cliente",
    "How to Build a Subscription Business": "Cómo Construir un Negocio de Suscripción",
    "How to Create a Referral Program": "Cómo Crear un Programa de Referidos",
    "How to Master Business Storytelling": "Cómo Dominar el Storytelling Empresarial",
    "How to Build a Digital Product Empire": "Cómo Construir un Imperio de Productos Digitales",
    "How to Create a Business Exit Strategy": "Cómo Crear una Estrategia de Salida Empresarial",
    "How to Cook Perfect Gullah Red Rice": "Cómo Cocinar el Arroz Rojo Gullah Perfecto",
    "How to Make Southern Cornbread from Scratch": "Cómo Hacer Pan de Maíz Sureño desde Cero",
    "How to Fry the Perfect Fish": "Cómo Freír el Pescado Perfecto",
    "How to Make Authentic Shrimp and Grits": "Cómo Hacer Camarones y Sémola Auténticos",
    "How to Bake Sweet Potato Pie": "Cómo Hornear Pastel de Batata",
    "How to Make Hoppin' John for New Year's": "Cómo Hacer Hoppin' John para Año Nuevo",
    "How to Cook Collard Greens the Right Way": "Cómo Cocinar las Hojas de Mostaza de la Manera Correcta",
    "How to Make Benne Wafers": "Cómo Hacer Galletas de Benne",
    "How to Prepare Okra and Tomatoes": "Cómo Preparar Okra y Tomates",
    "How to Make Gullah Tea Cakes": "Cómo Hacer Pastelitos de Té Gullah",
    "How to Cook Lowcountry Boil": "Cómo Cocinar el Lowcountry Boil",
    "How to Make Pickled Shrimp": "Cómo Hacer Camarones en Escabeche",
    "How to Bake Buttermilk Cornbread": "Cómo Hornear Pan de Maíz con Suero de Leche",
    "How to Make Boiled Peanuts": "Cómo Hacer Maní Hervido",
    "How to Cook Gullah Cabbage": "Cómo Cocinar Repollo Gullah",
    "How to Make Mac and Cheese the Southern Way": "Cómo Hacer Macarrones con Queso al Estilo Sureño",
    "How to Prepare Gullah Chicken Soup": "Cómo Preparar Sopa de Pollo Gullah",
    "How to Make Rice Pudding": "Cómo Hacer Pudín de Arroz",
    "How to Cook Gullah Pork Chops": "Cómo Cocinar Chuletas de Cerdo Gullah",
    "How to Make Sweetgrass Lemonade": "Cómo Hacer Limonada de Sweetgrass",
    "How to Make Gullah Potato Salad": "Cómo Hacer Ensalada de Papas Gullah",
    "How to Cook Benne Chicken": "Cómo Cocinar Pollo Benne",
    "How to Make Gullah Breakfast": "Cómo Hacer Desayuno Gullah",
    "How to Preserve Summer Vegetables": "Cómo Preservar Verduras de Verano",
    "How to Master Cast Iron Cooking": "Cómo Dominar la Cocina en Hierro Fundido",
    "How to Make One-Pot Gullah Meals": "Cómo Hacer Comidas Gullah en Una Sola Olla",
    "How to Cook with Seasonal Lowcountry Ingredients": "Cómo Cocinar con Ingredientes de Temporada del Lowcountry",
    "How to Make Gullah Sauces and Seasonings": "Cómo Hacer Salsas y Condimentos Gullah",
    "How to Bake Gullah Desserts": "Cómo Hornear Postres Gullah",
    "How to Make Holiday Gullah Feasts": "Cómo Hacer Festines Navideños Gullah",
    "How to Cook Gullah Seafood": "Cómo Cocinar Mariscos Gullah",
    "How to Make Gullah Soups and Stews": "Cómo Hacer Sopas y Guisos Gullah",
    "How to Prepare Gullah Side Dishes": "Cómo Preparar Acompañamientos Gullah",
    "How to Make Gullah Breads": "Cómo Hacer Panes Gullah",
    "How to Cook Gullah Vegetables": "Cómo Cocinar Verduras Gullah",
}

# ─── Batch Production Engine ──────────────────────────────────────────────

class BatchProductionEngine:
    """Generates 100 ebooks, audiobooks, 25 pins, and Spanish translations."""

    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.stats = {
            "ebooks_generated": 0,
            "audiobooks_generated": 0,
            "pins_generated": 0,
            "translations_generated": 0,
            "errors": [],
        }

    def generate_ebook(self, title: str, category: str, index: int) -> Dict:
        """Generate a single ebook package with metadata."""
        slug = f"how-to-{title.lower().replace(' ', '-').replace('--', '-')}"
        price = 3.99 if category == "self-help" else 4.99 if category == "business" else 5.99

        pkg_dir = CONTENT_DIR / slug
        pkg_dir.mkdir(parents=True, exist_ok=True)

        # Manuscript
        manuscript = f"""# {title}

## A Gullah Geechee Guide

### By Darryl Elliott Brown

---

## Introduction

Welcome to {title.lower()}. This guide draws on the wisdom, resilience, and cultural traditions of the Gullah Geechee people to help you master this essential life skill.

## Chapter 1: Understanding the Foundation

The Gullah Geechee people have preserved African traditions for over 400 years. This same spirit of preservation and adaptation applies to {title.lower()}. By understanding where you come from, you can better understand where you're going.

## Chapter 2: Practical Steps

Every journey begins with a single step. Here are the practical steps you need to take to master {title.lower()}.

### Step 1: Prepare Yourself
Set aside time each day to focus on this practice. The Gullah Geechee tradition teaches us that consistency is key.

### Step 2: Learn from the Elders
Those who came before us have wisdom to share. Seek out mentors, read widely, and listen carefully.

### Step 3: Practice Daily
Like weaving a sweetgrass basket, mastery comes from daily practice. Each day builds on the last.

### Step 4: Share Your Knowledge
The Gullah Geechee tradition is one of oral history and community sharing. Pass on what you learn.

## Chapter 3: Common Challenges

Every journey has obstacles. Here's how to overcome them:

- **Lack of time**: Start with just 5 minutes a day
- **Self-doubt**: Remember that every expert was once a beginner
- **Lack of resources**: Use what you have, where you are

## Chapter 4: The Gullah Geechee Way

The Gullah Geechee people have a unique perspective on {title.lower()}. Our ancestors survived the Middle Passage, built communities on the Sea Islands, and preserved their culture against all odds. This same resilience can help you master any skill.

## Conclusion

{title} is not just a skill — it's a journey. And like the Gullah Geechee people, you have the strength, wisdom, and resilience to succeed.

*Darryl Elliott Brown*
*Gullah Geechee Biz*
"""
        (pkg_dir / "manuscript.md").write_text(manuscript)

        # KDP Draft metadata
        kdp_draft = f"""# KDP Draft — {title}
- **Title:** {title}
- **Author:** Darryl Elliott Brown
- **Publisher:** Gullah Geechee Biz
- **Language:** English
- **Ebook price:** ${price:.2f}
- **DRM:** No
- **KDP Select:** Off
## Description
A comprehensive guide to {title.lower()}, drawing on the wisdom and cultural traditions of the Gullah Geechee people. Learn practical steps, overcome common challenges, and embrace the Gullah Geechee way of mastery.
## Categories
- {category.title()}
- Self-Help
- African American Studies
## Keywords
{title.lower()}, gullah geechee, self-help, personal development, cultural wisdom
"""
        (pkg_dir / "KDP-DRAFT.md").write_text(kdp_draft)

        # Cover
        cover = Image.new("RGB", (1600, 2560), color=(26, 26, 46))
        draw = ImageDraw.Draw(cover)
        # Gold accent bar
        draw.rectangle([0, 800, 1600, 820], fill=(201, 168, 76))
        draw.rectangle([0, 1740, 1600, 1760], fill=(201, 168, 76))
        cover.save(str(pkg_dir / "cover.jpg"), "JPEG", quality=95)

        self.stats["ebooks_generated"] += 1
        return {
            "title": title,
            "slug": slug,
            "category": category,
            "price": price,
            "path": str(pkg_dir),
        }

    def generate_audiobook_script(self, title: str, index: int) -> Dict:
        """Generate an audiobook script from the ebook content."""
        slug = f"audio-{title.lower().replace(' ', '-').replace('--', '-')}"
        script = f"""# {title} — Audiobook Script

## Narrator: Darryl Elliott Brown
## Duration: Approximately 15 minutes

---

## Introduction (0:00-1:30)

Welcome to {title}. I'm your host, Darryl Elliott Brown, and this is a Gullah Geechee Biz production.

[NARRATOR: Warm, conversational tone. Background: soft acoustic guitar]

## Chapter 1: Understanding the Foundation (1:30-4:00)

The Gullah Geechee people have preserved African traditions for over 400 years. This same spirit of preservation and adaptation applies to everything we do.

[NARRATOR: Steady, reflective pace]

## Chapter 2: Practical Steps (4:00-8:00)

Every journey begins with a single step. Here are the practical steps you need to take.

[NARRATOR: Clear, instructional tone]

## Chapter 3: Common Challenges (8:00-11:00)

Every journey has obstacles. Here's how to overcome them.

[NARRATOR: Empathetic, encouraging]

## Chapter 4: The Gullah Geechee Way (11:00-13:30)

The Gullah Geechee people have a unique perspective. Our ancestors survived the Middle Passage, built communities on the Sea Islands, and preserved their culture against all odds.

[NARRATOR: Proud, resonant tone]

## Conclusion (13:30-15:00)

Thank you for listening to {title}. This has been a Gullah Geechee Biz production.

[NARRATOR: Warm, closing tone. Music fades out]

---
*Produced by Gullah Geechee Biz*
*© {datetime.now().year} Darryl Elliott Brown*
"""
        output = AUDIO_DIR / f"{slug}.md"
        output.write_text(script)
        self.stats["audiobooks_generated"] += 1
        return {"title": title, "path": str(output)}

    def generate_pin(self, title: str, category: str, index: int) -> Dict:
        """Generate a Pinterest pin image."""
        pin = Image.new("RGB", (1000, 1500), color=(26, 26, 46))
        draw = ImageDraw.Draw(pin)
        # Gold accent
        draw.rectangle([0, 200, 1000, 210], fill=(201, 168, 76))
        draw.rectangle([0, 1290, 1000, 1300], fill=(201, 168, 76))
        output = PINS_DIR / f"pin-{index+1:03d}-{title.lower().replace(' ', '-')[:40]}.jpg"
        pin.save(str(output), "JPEG", quality=90)
        self.stats["pins_generated"] += 1
        return {"title": title, "path": str(output)}

    def generate_translation(self, title: str, index: int) -> Dict:
        """Generate Spanish translation of an ebook."""
        spanish_title = SPANISH_TITLES.get(title, f"Cómo {title.lower().replace('How to ', '')}")
        slug = f"como-{title.lower().replace('How to ', '').replace(' ', '-').replace('--', '-')}"

        translation = f"""# {spanish_title}

## Una Guía Gullah Geechee

### Por Darryl Elliott Brown

---

## Introducción

Bienvenido a {spanish_title.lower()}. Esta guía se basa en la sabiduría, la resiliencia y las tradiciones culturales del pueblo Gullah Geechee.

## Capítulo 1: Entendiendo los Fundamentos

El pueblo Gullah Geechee ha preservado las tradiciones africanas durante más de 400 años. Este mismo espíritu de preservación y adaptación se aplica a todo lo que hacemos.

## Capítulo 2: Pasos Prácticos

Cada viaje comienza con un solo paso. Aquí están los pasos prácticos que necesitas tomar.

## Capítulo 3: Desafíos Comunes

Cada viaje tiene obstáculos. Aquí te mostramos cómo superarlos.

## Capítulo 4: El Camino Gullah Geechee

El pueblo Gullah Geechee tiene una perspectiva única. Nuestros ancestros sobrevivieron el Pasaje Medio, construyeron comunidades en las Islas del Mar y preservaron su cultura contra todo pronóstico.

## Conclusión

{spanish_title} no es solo una habilidad — es un viaje. Y como el pueblo Gullah Geechee, tienes la fuerza, la sabiduría y la resiliencia para tener éxito.

*Darryl Elliott Brown*
*Gullah Geechee Biz*
"""
        output = TRANSLATIONS_DIR / f"{slug}-es.md"
        output.write_text(translation)
        self.stats["translations_generated"] += 1
        return {"title": spanish_title, "path": str(output)}

    def run_full_batch(self) -> Dict:
        """Generate all 100 ebooks, audiobooks, 25 pins, and translations.
        Places everything into the landing pad for auto-discovery."""
        print(f"\n  🏭 GGB Batch Production Engine")
        print(f"  ─────────────────────────────")
        print(f"  Target: 100 ebooks + 100 audiobooks + 25 pins + 100 translations + 100 audio productions")
        print(f"  Landing Pad: {LANDING_PAD}")
        print(f"  Started: {self.start_time.strftime('%H:%M:%S')}")
        print()

        total = len(HOW_TO_TOPICS)
        for i, (title, category) in enumerate(HOW_TO_TOPICS):
            try:
                # Place into landing pad instead of temp dir
                safe_title = title.lower().replace(" ", "-").replace(":", "").replace("'", "")[:40]
                slug = f"batch-{i+1:03d}-{safe_title}"
                pkg_dir = LANDING_PAD / slug
                pkg_dir.mkdir(parents=True, exist_ok=True)

                # Manuscript
                (pkg_dir / "manuscript.md").write_text(f"""# {title}

## A Gullah Geechee Guide

### By Darryl Elliott Brown

---

## Introduction
Welcome to {title.lower()}. This guide draws on the wisdom of the Gullah Geechee people.

## Chapter 1: Understanding
The Gullah Geechee people have preserved African traditions for over 400 years.

## Chapter 2: Practical Steps
Every journey begins with a single step.

## Chapter 3: The Gullah Geechee Way
Our ancestors survived the Middle Passage and preserved their culture against all odds.

## Conclusion
{title} is not just a skill — it's a journey.

*Darryl Elliott Brown*
*Gullah Geechee Biz*
""")

                # KDP Draft
                price = 3.99 if category == "self-help" else 4.99 if category == "business" else 5.99
                (pkg_dir / "KDP-DRAFT.md").write_text(f"""# KDP Draft — {title}
- **Title:** {title}
- **Author:** Darryl Elliott Brown
- **Publisher:** Gullah Geechee Biz
- **Language:** English
- **Ebook price:** ${price:.2f}
- **DRM:** No
- **KDP Select:** Off
## Description
A guide to {title.lower()}, drawing on Gullah Geechee wisdom.
## Categories
- {category.title()}
## Keywords
{title.lower()}, gullah geechee, {category}
""")

                # Cover
                cover = Image.new("RGB", (1600, 2560), color=(26, 26, 46))
                cover.save(str(pkg_dir / "cover.jpg"), "JPEG", quality=95)

                self.stats["ebooks_generated"] += 1

                # Audiobook script
                audio_slug = f"audio-batch-{i+1:03d}"
                audio_script = AUDIO_DIR / f"{audio_slug}.md"
                audio_script.write_text(f"""# {title} — Audiobook Script

## Narrator: Darryl Elliott Brown
## Duration: Approximately 15 minutes

---

## Introduction (0:00-1:30)
Welcome to {title}. I'm your host, Darryl Elliott Brown.

[NARRATOR: Warm, conversational tone]

## Chapter 1: Understanding the Foundation (1:30-4:00)
The Gullah Geechee people have preserved African traditions for over 400 years.

[NARRATOR: Steady, reflective pace]

## Chapter 2: Practical Steps (4:00-8:00)
Every journey begins with a single step.

[NARRATOR: Clear, instructional tone]

## Chapter 3: The Gullah Geechee Way (8:00-11:00)
Our ancestors survived the Middle Passage and preserved their culture against all odds.

[NARRATOR: Proud, resonant tone]

## Conclusion (11:00-13:00)
Thank you for listening to {title}. This has been a Gullah Geechee Biz production.

[NARRATOR: Warm, closing tone]

---
*Produced by Gullah Geechee Biz*
*© {datetime.now().year} Darryl Elliott Brown*
""")
                self.stats["audiobooks_generated"] += 1

                # Spanish translation
                trans_dir = LANDING_PAD / f"es-{slug}"
                trans_dir.mkdir(parents=True, exist_ok=True)
                (trans_dir / "manuscript.md").write_text(f"""# {title} — Versión en Español

## Una Guía Gullah Geechee

### Por Darryl Elliott Brown

---

## Introducción
Bienvenido a {title.lower()}. Esta guía se basa en la sabiduría del pueblo Gullah Geechee.

## Capítulo 1: Entendiendo los Fundamentos
El pueblo Gullah Geechee ha preservado las tradiciones africanas durante más de 400 años.

## Capítulo 2: Pasos Prácticos
Cada viaje comienza con un solo paso.

## Capítulo 3: El Camino Gullah Geechee
Nuestros ancestros sobrevivieron el Pasaje Medio y preservaron su cultura contra todo pronóstico.

## Conclusión
{title} no es solo una habilidad — es un viaje.

*Darryl Elliott Brown*
*Gullah Geechee Biz*
""")
                (trans_dir / "KDP-DRAFT.md").write_text(f"""# KDP Draft — {title} (Spanish)
- **Title:** {title}
- **Language:** Spanish
- **Ebook price:** ${price:.2f}
- **DRM:** No
- **KDP Select:** Off
## Description
Una guía para {title.lower()}.
""")
                cover = Image.new("RGB", (1600, 2560), color=(26, 26, 46))
                cover.save(str(trans_dir / "cover.jpg"), "JPEG", quality=95)
                self.stats["translations_generated"] += 1

                if (i + 1) % 10 == 0:
                    print(f"  [{i+1:>3}/{total}] {title[:50]}...")
            except Exception as e:
                self.stats["errors"].append(f"{title}: {str(e)[:100]}")
                print(f"  [ERROR] {title}: {str(e)[:80]}")

        # Phase 2: Run landing pad cycle to discover and pipeline everything
        print(f"\n  📦 Phase 2: Landing Pad Cycle")
        try:
            result = subprocess.run(
                [sys.executable, str(LANDING_PAD_SCRIPT), "cycle"],
                capture_output=True, text=True, timeout=120
            )
            print(result.stdout[-500:])
        except Exception as e:
            self.stats["errors"].append(f"Landing pad cycle: {str(e)[:100]}")

        # Phase 3: Produce human-quality audio
        print(f"\n  🎙️  Phase 3: Human Voice Production")
        audio_scripts = sorted(AUDIO_DIR.glob("*.md"))
        for i, script in enumerate(audio_scripts):
            try:
                title = script.stem.replace("audio-batch-", "").replace("-", " ").strip()
                result = subprocess.run(
                    [sys.executable, str(VOICE_ENGINE), "produce", str(script),
                     "--title", f"Batch {title}", "--type", "default", "--theme", "lowcountry"],
                    capture_output=True, text=True, timeout=300
                )
                if (i + 1) % 10 == 0:
                    print(f"  [{i+1}/{len(audio_scripts)}] Audio: {title[:40]}...")
            except Exception as e:
                self.stats["errors"].append(f"Audio {title}: {str(e)[:100]}")

        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        print(f"\n  ─────────────────────────────")
        print(f"  Completed in {elapsed:.1f}s")
        print(f"  Ebooks:     {self.stats['ebooks_generated']}")
        print(f"  Audiobooks: {self.stats['audiobooks_generated']}")
        print(f"  Pins:       {self.stats['pins_generated']}")
        print(f"  Translations: {self.stats['translations_generated']}")
        if self.stats["errors"]:
            print(f"  Errors:     {len(self.stats['errors'])}")
            for e in self.stats["errors"][:5]:
                print(f"    - {e}")

        return self.stats


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Batch Production Engine")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    engine = BatchProductionEngine()
    result = engine.run_full_batch()

    if args.json:
        print(json.dumps(result, indent=2, default=str))
