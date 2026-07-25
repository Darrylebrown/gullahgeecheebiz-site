#!/usr/bin/env python3
"""
Gullah Geechee Biz — Viral Page Engine (Bilingual: EN + ES)
Generates SEO-optimized pages in English and Spanish for trending topics.
Spanish content is written directly (no slow translation needed).
"""

import os, json, datetime
from pathlib import Path

HOME = Path.home()
SITE_DIR = HOME / "gullahgeecheebiz-site"
PAGES_DIR = SITE_DIR / "viral"
os.makedirs(PAGES_DIR, exist_ok=True)

# ── Trending Topics (English) ──
TRENDING_EN = [
    {
        "slug": "heirs-property-explained",
        "title": "What Is Heirs' Property? A Gullah Geechee Explainer",
        "meta_desc": "Heirs' property explained — how Gullah Geechee families have held land for generations and the fight to protect it.",
        "keywords": "heirs property, land ownership, Gullah Geechee land rights, family land",
        "content": [
            "Heirs' property is land passed down through generations without a formal will. In the Gullah Geechee community, this has been the primary way families have held onto their land since Reconstruction.",
            "But without clear legal title, this land is vulnerable. Developers, corporations, and even government agencies have used partition sales to force families off land they've owned for over a century.",
            "The Gullah Geechee Cultural Heritage Corridor has lost over 70% of its original land base. Heirs' property is at the center of this crisis.",
            "Our documentary series Season 1 covers this in depth. Our books trace the history county by county. And our Substack keeps you updated on the fight to protect Gullah Geechee land."
        ],
        "cta": "Watch the Heirs' Property documentary →",
    },
    {
        "slug": "sweetgrass-baskets-history",
        "title": "Sweetgrass Baskets: The 300-Year-Old Art Form Going Viral",
        "meta_desc": "Sweetgrass baskets are one of the oldest African art forms in North America. Discover the Gullah Geechee tradition going viral.",
        "keywords": "sweetgrass baskets, Gullah Geechee art, African American crafts, Lowcountry culture",
        "content": [
            "Sweetgrass baskets are one of the oldest African art forms in North America. Brought to the Lowcountry by enslaved West Africans, this coiled basket tradition has been passed down through generations of Gullah Geechee women.",
            "Today, these baskets sell for hundreds to thousands of dollars. They've been featured in museums, celebrity homes, and design magazines worldwide. But the tradition is at risk — sweetgrass itself is becoming scarce due to coastal development.",
            "The Gullah Geechee Biz Travel Magazine covers the communities where this art form thrives. Our books document the history. And our podcast interviews the artisans keeping the tradition alive."
        ],
        "cta": "Explore Gullah Geechee art →",
    },
    {
        "slug": "gullah-language-survival",
        "title": "The Gullah Language Is Still Spoken — Here's Why It Matters",
        "meta_desc": "The Gullah language is an English-based creole with West African roots. Learn why its survival matters for American history.",
        "keywords": "Gullah language, Geechee language, African American dialect, Sea Islands culture",
        "content": [
            "The Gullah language is an English-based creole with direct roots in West African languages like Mende, Twi, and Yoruba. It developed on the Sea Islands of South Carolina and Georgia during the transatlantic slave trade.",
            "Today, only a few thousand fluent speakers remain. But there's a resurgence. Linguists, educators, and Gullah Geechee communities are working to preserve and teach the language to new generations.",
            "Our Roots & Rivers encyclopedia documents Gullah language history county by county. Our podcast features native speakers. And our Substack shares language lessons and cultural context."
        ],
        "cta": "Learn Gullah language history →",
    },
    {
        "slug": "penn-center-history",
        "title": "Penn Center: The School That Changed Gullah Geechee History",
        "meta_desc": "Penn Center on St. Helena Island was one of the first schools for freed African Americans. A Gullah Geechee landmark.",
        "keywords": "Penn Center, St. Helena Island, Gullah Geechee education, civil rights history",
        "content": [
            "Penn Center on St. Helena Island was one of the first schools in the United States established to educate formerly enslaved African Americans. Founded in 1862, it became a cornerstone of Gullah Geechee education and community life.",
            "During the Civil Rights Movement, Penn Center was one of the only places in the South where interracial groups could meet safely. Dr. Martin Luther King Jr. and the Southern Christian Leadership Conference held retreats there.",
            "Today, Penn Center is a National Historic Landmark and a living testament to Gullah Geechee resilience. Our Travel Magazine covers St. Helena Island in depth. Our books trace the full history."
        ],
        "cta": "Read about St. Helena Island →",
    },
    {
        "slug": "gullah-geechee-food-history",
        "title": "How Gullah Geechee Cuisine Shaped Southern Food",
        "meta_desc": "Red rice, okra soup, shrimp and grits — Gullah Geechee cuisine shaped Southern food. Discover the West African roots.",
        "keywords": "Gullah Geechee food, Lowcountry cuisine, soul food history, African American cooking",
        "content": [
            "Red rice, okra soup, shrimp and grits, benne wafers — these aren't just Southern dishes. They're Gullah Geechee dishes with direct roots in West African cooking traditions.",
            "Enslaved Gullah Geechee people brought rice cultivation expertise that made South Carolina the rice capital of America. They brought okra, black-eyed peas, and watermelon from Africa. They created one-pot meals that became the foundation of Southern cuisine.",
            "Today, Gullah Geechee chefs are reclaiming this culinary heritage. Our Travel Magazine covers the best Gullah Geechee restaurants. Our books document food history."
        ],
        "cta": "Explore Gullah Geechee food →",
    },
    {
        "slug": "robert-smalls-hero",
        "title": "Robert Smalls: The Gullah Geechee Hero Who Stole a Confederate Ship",
        "meta_desc": "Robert Smalls commandeered a Confederate ship and sailed to freedom. The incredible true story of a Gullah Geechee hero.",
        "keywords": "Robert Smalls, Gullah Geechee hero, Civil War history, African American naval history",
        "content": [
            "In 1862, an enslaved Gullah Geechee man named Robert Smalls commandeered a Confederate transport ship, the CSS Planter, sailed it past Confederate checkpoints, and delivered it to the Union Navy — along with its cannons and munitions.",
            "He freed himself, his crew, and their families. He went on to serve in the Union Navy, became a successful businessman, and was elected to the U.S. House of Representatives.",
            "Robert Smalls is one of the greatest American heroes you've never heard of. Our Season 1 documentary covers his story in depth. Our books trace his life and legacy."
        ],
        "cta": "Watch the Robert Smalls documentary →",
    },
    {
        "slug": "sea-islands-climate-change",
        "title": "The Sea Islands Are Sinking — A Gullah Geechee Crisis",
        "meta_desc": "Rising sea levels threaten the Sea Islands and the Gullah Geechee communities that have lived there for centuries.",
        "keywords": "Sea Islands, climate change, Gullah Geechee displacement, coastal erosion",
        "content": [
            "The Sea Islands of South Carolina and Georgia are on the front lines of climate change. Rising sea levels, stronger hurricanes, and coastal erosion threaten the very land the Gullah Geechee community has called home for centuries.",
            "Hilton Head, St. Helena, Edisto, Daufuskie — these islands are losing ground. And with the land goes the culture. Cemeteries are flooding. Historic sites are eroding. Communities are being forced to relocate.",
            "This is the most urgent story in Gullah Geechee history today. Our documentary series covers it. Our books document what's being lost."
        ],
        "cta": "Learn about the Sea Islands →",
    },
    {
        "slug": "gullah-geechee-music-origins",
        "title": "From Ring Shouts to Hip-Hop: Gullah Geechee Music's Hidden Influence",
        "meta_desc": "The ring shout is the oldest surviving African American musical practice. Discover how Gullah Geechee music shaped American culture.",
        "keywords": "Gullah Geechee music, ring shout, African American music history, spirituals",
        "content": [
            "The ring shout — an African-derived dance and worship tradition — is the oldest surviving African American musical practice in North America. And it was preserved by the Gullah Geechee.",
            "From ring shouts came spirituals. From spirituals came gospel, blues, jazz, and eventually R&B and hip-hop. The Gullah Geechee people didn't just preserve African music — they shaped the entire trajectory of American music.",
            "Our documentary series features Gullah Geechee music traditions. Our books document the cultural history. And our podcast plays the music and tells the stories behind it."
        ],
        "cta": "Explore Gullah Geechee music →",
    },
    {
        "slug": "combahee-river-raid",
        "title": "The Combahee River Raid: Harriet Tubman's Greatest Mission",
        "meta_desc": "Harriet Tubman led the Combahee River Raid, freeing over 700 enslaved Gullah Geechee people. The story of her greatest mission.",
        "keywords": "Combahee River Raid, Harriet Tubman, Gullah Geechee history, Civil War",
        "content": [
            "In June 1863, Harriet Tubman became the first woman to lead a major military operation in American history. The Combahee River Raid freed over 700 enslaved people in the South Carolina Lowcountry — most of them Gullah Geechee.",
            "The raid was a turning point in the Civil War. It proved that Black soldiers could fight and win. It also showed the Union that the Gullah Geechee people were ready to fight for their own freedom.",
            "Our Season 1 documentary covers the Combahee River Raid in detail. Our books trace the history of the river and the communities along it."
        ],
        "cta": "Watch the Combahee River Raid documentary →",
    },
    {
        "slug": "gullah-geechee-tourism",
        "title": "Beyond the Resorts: Authentic Gullah Geechee Tourism Guide",
        "meta_desc": "Experience the real Gullah Geechee Lowcountry — sweetgrass baskets, Gullah cuisine, historic sites, and cultural tours.",
        "keywords": "Gullah Geechee tourism, Lowcountry travel, cultural tourism, Sea Islands travel",
        "content": [
            "Hilton Head, Charleston, Savannah — millions of tourists visit the Lowcountry every year. Most never experience the real Gullah Geechee culture.",
            "But there's a growing movement toward authentic cultural tourism. Travelers want more than golf courses and beach resorts. They want to meet the people, taste the food, and learn the history that makes the Lowcountry unique.",
            "Our Travel Magazine covers the best Gullah Geechee experiences — from sweetgrass basket demonstrations on St. Helena to Gullah cuisine tours in Charleston. Our books are the definitive guides."
        ],
        "cta": "Plan your Gullah Geechee trip →",
    },
]

# ── Spanish Versions (written directly) ──
TRENDING_ES = [
    {
        "slug": "heirs-property-explained",
        "title": "¿Qué es la Propiedad Hereditaria? Una Explicación Gullah Geechee",
        "meta_desc": "La propiedad hereditaria explicada — cómo las familias Gullah Geechee han conservado sus tierras por generaciones y la lucha por protegerlas.",
        "keywords": "propiedad hereditaria, derechos de tierra, Gullah Geechee, tierras familiares",
        "content": [
            "La propiedad hereditaria es tierra transmitida de generación en generación sin un testamento formal. En la comunidad Gullah Geechee, esta ha sido la forma principal en que las familias han conservado sus tierras desde la Reconstrucción.",
            "Pero sin un título legal claro, esta tierra es vulnerable. Desarrolladores, corporaciones e incluso agencias gubernamentales han utilizado ventas por partición para forzar a las familias a abandonar tierras que han poseído por más de un siglo.",
            "El Corredor del Patrimonio Cultural Gullah Geechee ha perdido más del 70% de su base territorial original. La propiedad hereditaria está en el centro de esta crisis.",
            "Nuestra serie documental Temporada 1 cubre esto en profundidad. Nuestros libros rastrean la historia condado por condado. Y nuestro Substack te mantiene actualizado sobre la lucha por proteger la tierra Gullah Geechee."
        ],
        "cta": "Ver el documental sobre Propiedad Hereditaria →",
    },
    {
        "slug": "sweetgrass-baskets-history",
        "title": "Cestas de Sweetgrass: El Arte de 300 Años que se Vuelve Viral",
        "meta_desc": "Las cestas de sweetgrass son una de las formas de arte africano más antiguas de América del Norte. Descubre la tradición Gullah Geechee.",
        "keywords": "cestas de sweetgrass, arte Gullah Geechee, artesanía afroamericana, cultura Lowcountry",
        "content": [
            "Las cestas de sweetgrass son una de las formas de arte africano más antiguas de América del Norte. Traídas al Lowcountry por africanos occidentales esclavizados, esta tradición de cestas enrolladas se ha transmitido por generaciones de mujeres Gullah Geechee.",
            "Hoy, estas cestas se venden por cientos a miles de dólares. Han aparecido en museos, casas de celebridades y revistas de diseño en todo el mundo. Pero la tradición está en riesgo — el sweetgrass mismo se está volviendo escaso debido al desarrollo costero.",
            "Nuestra Revista de Viajes Gullah Geechee Biz cubre las comunidades donde prospera esta forma de arte. Nuestros libros documentan la historia. Y nuestro podcast entrevista a los artesanos que mantienen viva la tradición."
        ],
        "cta": "Explora el arte Gullah Geechee →",
    },
    {
        "slug": "gullah-language-survival",
        "title": "El Idioma Gullah Todavía se Habla — Por Qué es Importante",
        "meta_desc": "El idioma Gullah es un criollo basado en el inglés con raíces africanas occidentales. Aprende por qué su supervivencia es importante.",
        "keywords": "idioma Gullah, lengua Geechee, dialecto afroamericano, cultura Sea Islands",
        "content": [
            "El idioma Gullah es un criollo basado en el inglés con raíces directas en lenguas africanas occidentales como el Mende, Twi y Yoruba. Se desarrolló en las Sea Islands de Carolina del Sur y Georgia durante la trata transatlántica de esclavos.",
            "Hoy, solo quedan unos pocos miles de hablantes fluidos. Pero hay un resurgimiento. Lingüistas, educadores y comunidades Gullah Geechee están trabajando para preservar y enseñar el idioma a nuevas generaciones.",
            "Nuestra enciclopedia Roots & Rivers documenta la historia del idioma Gullah condado por condado. Nuestro podcast presenta hablantes nativos. Y nuestro Substack comparte lecciones de idioma y contexto cultural."
        ],
        "cta": "Aprende sobre la historia del idioma Gullah →",
    },
    {
        "slug": "penn-center-history",
        "title": "Penn Center: La Escuela que Cambió la Historia Gullah Geechee",
        "meta_desc": "Penn Center en la Isla St. Helena fue una de las primeras escuelas para afroamericanos liberados. Un hito Gullah Geechee.",
        "keywords": "Penn Center, Isla St. Helena, educación Gullah Geechee, historia de derechos civiles",
        "content": [
            "Penn Center en la Isla St. Helena fue una de las primeras escuelas en los Estados Unidos establecida para educar a afroamericanos anteriormente esclavizados. Fundado en 1862, se convirtió en una piedra angular de la educación y la vida comunitaria Gullah Geechee.",
            "Durante el Movimiento de Derechos Civiles, Penn Center fue uno de los únicos lugares en el Sur donde los grupos interraciales podían reunirse de manera segura. El Dr. Martin Luther King Jr. y la Conferencia de Liderazgo Cristiano del Sur realizaron retiros allí.",
            "Hoy, Penn Center es un Monumento Histórico Nacional y un testimonio vivo de la resiliencia Gullah Geechee. Nuestra Revista de Viajes cubre la Isla St. Helena en profundidad."
        ],
        "cta": "Lee sobre la Isla St. Helena →",
    },
    {
        "slug": "gullah-geechee-food-history",
        "title": "Cómo la Cocina Gullah Geechee Transformó la Comida del Sur",
        "meta_desc": "Arroz rojo, sopa de okra, camarones y sémola — la cocina Gullah Geechee transformó la comida sureña. Descubre las raíces africanas.",
        "keywords": "comida Gullah Geechee, cocina Lowcountry, historia de la soul food, cocina afroamericana",
        "content": [
            "Arroz rojo, sopa de okra, camarones y sémola, galletas de benne — estos no son solo platos sureños. Son platos Gullah Geechee con raíces directas en las tradiciones culinarias de África Occidental.",
            "Los Gullah Geechee esclavizados trajeron experiencia en el cultivo de arroz que hizo de Carolina del Sur la capital del arroz de América. Trajeron okra, frijoles caritas y sandía de África. Crearon comidas de una sola olla que se convirtieron en la base de la cocina sureña.",
            "Hoy, los chefs Gullah Geechee están reclamando esta herencia culinaria. Nuestra Revista de Viajes cubre los mejores restaurantes Gullah Geechee. Nuestros libros documentan la historia de la comida."
        ],
        "cta": "Explora la comida Gullah Geechee →",
    },
    {
        "slug": "robert-smalls-hero",
        "title": "Robert Smalls: El Héroe Gullah Geechee que Robó un Barco Confederado",
        "meta_desc": "Robert Smalls tomó el mando de un barco confederado y navegó hacia la libertad. La increíble historia real de un héroe Gullah Geechee.",
        "keywords": "Robert Smalls, héroe Gullah Geechee, historia de la Guerra Civil, historia naval afroamericana",
        "content": [
            "En 1862, un hombre Gullah Geechee esclavizado llamado Robert Smalls tomó el mando de un barco de transporte confederado, el CSS Planter, navegó más allá de los puestos de control confederados y lo entregó a la Armada de la Unión — junto con sus cañones y municiones.",
            "Liberó a sí mismo, a su tripulación y a sus familias. Luego sirvió en la Armada de la Unión, se convirtió en un exitoso hombre de negocios y fue elegido para la Cámara de Representantes de los Estados Unidos.",
            "Robert Smalls es uno de los grandes héroes estadounidenses de los que nunca has oído hablar. Nuestro documental de la Temporada 1 cubre su historia en profundidad."
        ],
        "cta": "Ver el documental de Robert Smalls →",
    },
    {
        "slug": "sea-islands-climate-change",
        "title": "Las Sea Islands se Están Hundiendo — Una Crisis Gullah Geechee",
        "meta_desc": "El aumento del nivel del mar amenaza las Sea Islands y las comunidades Gullah Geechee que han vivido allí durante siglos.",
        "keywords": "Sea Islands, cambio climático, desplazamiento Gullah Geechee, erosión costera",
        "content": [
            "Las Sea Islands de Carolina del Sur y Georgia están en la primera línea del cambio climático. El aumento del nivel del mar, huracanes más fuertes y la erosión costera amenazan la tierra que la comunidad Gullah Geechee ha llamado hogar durante siglos.",
            "Hilton Head, St. Helena, Edisto, Daufuskie — estas islas están perdiendo terreno. Y con la tierra se va la cultura. Los cementerios se inundan. Los sitios históricos se erosionan. Las comunidades se ven obligadas a reubicarse.",
            "Esta es la historia más urgente en la historia Gullah Geechee hoy. Nuestra serie documental la cubre. Nuestros libros documentan lo que se está perdiendo."
        ],
        "cta": "Aprende sobre las Sea Islands →",
    },
    {
        "slug": "gullah-geechee-music-origins",
        "title": "De los Ring Shouts al Hip-Hop: La Influencia Oculta de la Música Gullah Geechee",
        "meta_desc": "El ring shout es la práctica musical afroamericana más antigua que sobrevive. Descubre cómo la música Gullah Geechee transformó la cultura estadounidense.",
        "keywords": "música Gullah Geechee, ring shout, historia de la música afroamericana, espirituales",
        "content": [
            "El ring shout — una tradición de danza y adoración de origen africano — es la práctica musical afroamericana más antigua que sobrevive en América del Norte. Y fue preservada por los Gullah Geechee.",
            "De los ring shouts vinieron los espirituales. De los espirituales vinieron el gospel, el blues, el jazz, y eventualmente el R&B y el hip-hop. Los Gullah Geechee no solo preservaron la música africana — transformaron toda la trayectoria de la música estadounidense.",
            "Nuestra serie documental presenta las tradiciones musicales Gullah Geechee. Nuestros libros documentan la historia cultural. Y nuestro podcast reproduce la música y cuenta las historias detrás de ella."
        ],
        "cta": "Explora la música Gullah Geechee →",
    },
    {
        "slug": "combahee-river-raid",
        "title": "La Incursión del Río Combahee: La Mayor Misión de Harriet Tubman",
        "meta_desc": "Harriet Tubman lideró la Incursión del Río Combahee, liberando a más de 700 personas Gullah Geechee esclavizadas. La historia de su mayor misión.",
        "keywords": "Incursión del Río Combahee, Harriet Tubman, historia Gullah Geechee, Guerra Civil",
        "content": [
            "En junio de 1863, Harriet Tubman se convirtió en la primera mujer en liderar una operación militar importante en la historia de Estados Unidos. La Incursión del Río Combahee liberó a más de 700 personas esclavizadas en el Lowcountry de Carolina del Sur — la mayoría de ellos Gullah Geechee.",
            "La incursión fue un punto de inflexión en la Guerra Civil. Demostró que los soldados negros podían luchar y ganar. También mostró a la Unión que los Gullah Geechee estaban listos para luchar por su propia libertad.",
            "Nuestro documental de la Temporada 1 cubre la Incursión del Río Combahee en detalle. Nuestros libros rastrean la historia del río y las comunidades a lo largo de él."
        ],
        "cta": "Ver el documental de la Incursión del Río Combahee →",
    },
    {
        "slug": "gullah-geechee-tourism",
        "title": "Más Allá de los Resorts: Guía de Turismo Gullah Geechee Auténtico",
        "meta_desc": "Experimenta el verdadero Lowcountry Gullah Geechee — cestas de sweetgrass, cocina Gullah, sitios históricos y tours culturales.",
        "keywords": "turismo Gullah Geechee, viajes Lowcountry, turismo cultural, viajes Sea Islands",
        "content": [
            "Hilton Head, Charleston, Savannah — millones de turistas visitan el Lowcountry cada año. La mayoría nunca experimenta la verdadera cultura Gullah Geechee.",
            "Pero hay un movimiento creciente hacia el turismo cultural auténtico. Los viajeros quieren más que campos de golf y resorts de playa. Quieren conocer a la gente, probar la comida y aprender la historia que hace único al Lowcountry.",
            "Nuestra Revista de Viajes cubre las mejores experiencias Gullah Geechee — desde demostraciones de cestas de sweetgrass en St. Helena hasta tours de cocina Gullah en Charleston. Nuestros libros son las guías definitivas."
        ],
        "cta": "Planifica tu viaje Gullah Geechee →",
    },
]

# ── HTML Template ──
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | Gullah Geechee Biz</title>
  <meta name="description" content="{meta_desc}">
  <meta name="keywords" content="{keywords}">
  <meta property="og:title" content="{title} | Gullah Geechee Biz">
  <meta property="og:description" content="{meta_desc}">
  <meta property="og:image" content="https://gullahgeecheebiz.com/logo.png">
  <meta property="og:url" content="https://gullahgeecheebiz.com/viral/{slug}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="canonical" href="https://gullahgeecheebiz.com/viral/{slug}">
  <link rel="alternate" hreflang="en" href="https://gullahgeecheebiz.com/viral/{slug_en}">
  <link rel="alternate" hreflang="es" href="https://gullahgeecheebiz.com/viral/{slug_es}">
  <link rel="alternate" hreflang="x-default" href="https://gullahgeecheebiz.com/viral/{slug_en}">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a14; color: #f0ede5; line-height: 1.8; }}
    .container {{ max-width: 800px; margin: 0 auto; padding: 40px 20px; }}
    h1 {{ font-family: Georgia, 'Times New Roman', serif; font-size: 2.2em; color: #d4af37; margin-bottom: 20px; line-height: 1.3; }}
    p {{ margin-bottom: 20px; font-size: 1.1em; }}
    .cta {{ display: inline-block; background: #d4af37; color: #0a0a14; padding: 16px 32px; border-radius: 30px; text-decoration: none; font-weight: bold; font-size: 1.1em; margin: 20px 0; }}
    .cta:hover {{ background: #e8c84a; }}
    .lang-switch {{ text-align: right; margin-bottom: 20px; }}
    .lang-switch a {{ color: #d4af37; text-decoration: none; font-size: 0.9em; margin-left: 10px; }}
    .lang-switch a:hover {{ text-decoration: underline; }}
    .links {{ margin-top: 40px; padding-top: 30px; border-top: 1px solid #333; }}
    .links a {{ display: block; color: #d4af37; text-decoration: none; margin-bottom: 10px; font-size: 1em; }}
    .links a:hover {{ text-decoration: underline; }}
    .brand {{ text-align: center; margin-top: 60px; padding-top: 30px; border-top: 1px solid #333; }}
    .brand img {{ width: 60px; height: 60px; border-radius: 50%; border: 2px solid #d4af37; }}
    .brand p {{ color: #d4af37; font-size: 0.9em; margin-top: 10px; letter-spacing: 2px; }}
    .date {{ color: #666; font-size: 0.85em; margin-bottom: 30px; }}
    @media (max-width: 600px) {{ h1 {{ font-size: 1.6em; }} .container {{ padding: 20px 15px; }} }}
  </style>
</head>
<body>
  <div class="container">
    <div class="lang-switch">
      <a href="{slug_en}.html">English</a> | <a href="{slug_es}.html">Español</a>
    </div>
    <h1>{title}</h1>
    <div class="date">Published {date} · Gullah Geechee Biz</div>
    {content_html}
    <a href="{cta_link}" class="cta">{cta}</a>
    <div class="links">
      <strong style="color: #d4af37;">{explore_label}:</strong>
      <a href="https://gullahgeecheebiz.com/books">{books_label} →</a>
      <a href="https://kofigullahgeecheebiz.substack.com">{newsletter_label} →</a>
      <a href="https://gullahgeecheebiz.com">{home_label} →</a>
    </div>
    <div class="brand">
      <img src="https://gullahgeecheebiz.com/logo.png" alt="Gullah Geechee Biz">
      <p>GULLAH GEECHEE BIZ</p>
    </div>
  </div>
</body>
</html>"""

LABELS = {
    "en": {"explore": "Explore more:", "books": "📚 Browse our books", "newsletter": "📧 Subscribe to our newsletter", "home": "🏠 Visit Gullah Geechee Biz"},
    "es": {"explore": "Explora más:", "books": "📚 Explora nuestros libros", "newsletter": "📧 Suscríbete a nuestro boletín", "home": "🏠 Visita Gullah Geechee Biz"},
}

def generate_page(topic, lang="en"):
    slug = topic["slug"]
    slug_lang = f"{slug}-{lang}" if lang == "es" else slug
    content_html = "\n".join(f"    <p>{p}</p>" for p in topic["content"] if p)
    date = datetime.date.today().strftime("%B %d, %Y")
    labels = LABELS[lang]
    
    html = HTML_TEMPLATE.format(
        lang=lang, title=topic["title"], meta_desc=topic["meta_desc"],
        keywords=topic["keywords"], slug=slug_lang,
        slug_en=f"{slug}.html", slug_es=f"{slug}-es.html",
        date=date, content_html=content_html, cta=topic["cta"],
        cta_link="https://gullahgeecheebiz.com/books",
        explore_label=labels["explore"], books_label=labels["books"],
        newsletter_label=labels["newsletter"], home_label=labels["home"],
    )
    
    path = PAGES_DIR / f"{slug_lang}.html"
    with open(path, "w") as f:
        f.write(html)
    return path

def update_sitemap():
    sitemap_path = SITE_DIR / "sitemap.xml"
    urls = ["https://gullahgeecheebiz.com/", "https://gullahgeecheebiz.com/shop.html", "https://gullahgeecheebiz.com/shop-binyah.html"]
    for f in sorted(PAGES_DIR.glob("*.html")):
        urls.append(f"https://gullahgeecheebiz.com/viral/{f.stem}")
    
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        sitemap += f"  <url><loc>{url}</loc></url>\n"
    sitemap += "</urlset>"
    with open(sitemap_path, "w") as f:
        f.write(sitemap)
    return sitemap_path

def main():
    print("=" * 60)
    print("  GULLAH GEECHEE BIZ — VIRAL PAGE ENGINE (BILINGUAL)")
    print("=" * 60)
    print()
    
    print("Generating English pages...")
    for t in TRENDING_EN:
        p = generate_page(t, "en")
        print(f"  ✓ EN: {p.name}")
    
    print("\nGenerating Spanish pages...")
    for t in TRENDING_ES:
        p = generate_page(t, "es")
        print(f"  ✓ ES: {p.name}")
    
    update_sitemap()
    print("\n  ✓ Sitemap updated")
    
    # Index page
    index = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Gullah Geechee Culture | Gullah Geechee Biz</title>
  <meta name="description" content="Trending topics in Gullah Geechee culture, history, and heritage — in English and Spanish.">
  <link rel="canonical" href="https://gullahgeecheebiz.com/viral/">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a14; color: #f0ede5; line-height: 1.6; }
    .container { max-width: 800px; margin: 0 auto; padding: 40px 20px; }
    h1 { font-family: Georgia, 'Times New Roman', serif; font-size: 2em; color: #d4af37; margin-bottom: 10px; }
    .subtitle { margin-bottom: 30px; color: #999; }
    .card { background: #12121e; border-radius: 12px; padding: 24px; margin-bottom: 16px; border: 1px solid #222; }
    .card h2 { font-size: 1.2em; margin-bottom: 8px; }
    .card h2 a { color: #d4af37; text-decoration: none; }
    .card h2 a:hover { text-decoration: underline; }
    .card .lang { color: #666; font-size: 0.8em; margin-top: 8px; }
    .card .lang a { color: #d4af37; text-decoration: none; }
    .brand { text-align: center; margin-top: 60px; padding-top: 30px; border-top: 1px solid #333; }
    .brand p { color: #d4af37; font-size: 0.9em; letter-spacing: 2px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Gullah Geechee Culture</h1>
    <p class="subtitle">Trending topics in Gullah Geechee history, culture, and heritage — English & Español</p>
"""
    for t in TRENDING_EN:
        index += f"""    <div class="card">
      <h2><a href="{t['slug']}.html">{t['title']}</a></h2>
      <p>{t['meta_desc'][:120]}...</p>
      <div class="lang"><a href="{t['slug']}.html">English</a> | <a href="{t['slug']}-es.html">Español</a></div>
    </div>
"""
    index += """    <div class="brand"><p>GULLAH GEECHEE BIZ</p></div>
  </div>
</body>
</html>"""
    
    with open(PAGES_DIR / "index.html", "w") as f:
        f.write(index)
    print("  ✓ Index page created")
    
    print(f"\n{'=' * 60}")
    print(f"  ✓ {len(TRENDING_EN)} topics × 2 languages = {len(TRENDING_EN) * 2} pages")
    print(f"  📍 {PAGES_DIR}")
    print(f"  🌐 https://gullahgeecheebiz.com/viral/")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
