#!/usr/bin/env python3
"""
Gullah Geechee Biz — Daily Recipe Pipeline
Generates new SEO-optimized recipe pages every day.
Tracks what's been created, never repeats, keeps growing.
"""

import json, os, re, random
from datetime import date

HOME = os.path.expanduser("~")
SITE_DIR = os.path.join(HOME, "gullahgeecheebiz-site")
RECIPE_DIR = os.path.join(SITE_DIR, "recipes")
STATE_FILE = os.path.join(RECIPE_DIR, ".recipe-state.json")
os.makedirs(RECIPE_DIR, exist_ok=True)

# ─── Master Recipe Database (keeps growing) ──────────────────────────────────

RECIPES = [
    # ── Batch 1: Core Classics (10) ──
    {
        "slug": "gullah-red-rice",
        "title": "Authentic Gullah Red Rice Recipe",
        "title_es": "Receta Auténtica de Arroz Rojo Gullah",
        "description": "The signature dish of the Lowcountry. Tomato, rice, bacon, and love in every bite. This authentic Gullah red rice recipe has been passed down for generations.",
        "description_es": "El plato emblemático de las Lowcountry. Tomate, arroz, tocino y amor en cada bocado.",
        "keywords": "Gullah red rice, Lowcountry red rice, Charleston red rice recipe, authentic Southern rice, Gullah Geechee food",
        "keywords_es": "arroz rojo Gullah, arroz rojo Lowcountry, receta de arroz rojo Charleston",
        "prep_time": "PT15M", "cook_time": "PT45M", "total_time": "PT1H",
        "servings": 6, "calories": 380,
        "ingredients": ["2 cups long-grain white rice","4 slices thick-cut bacon, chopped","1 large onion, diced","1 green bell pepper, diced","2 cloves garlic, minced","1 can (14.5 oz) diced tomatoes","2 cups chicken broth","2 tbsp tomato paste","1 tsp smoked paprika","1 tsp salt","1/2 tsp black pepper","1/4 tsp cayenne pepper (optional)","2 green onions, sliced for garnish"],
        "ingredients_es": ["2 tazas de arroz blanco de grano largo","4 rebanadas de tocino grueso, picado","1 cebolla grande, picada","1 pimiento verde, picado","2 dientes de ajo, picados","1 lata (410g) de tomates picados","2 tazas de caldo de pollo","2 cucharadas de pasta de tomate","1 cucharadita de pimentón ahumado","1 cucharadita de sal","1/2 cucharadita de pimienta negra","1/4 cucharadita de cayena (opcional)","2 cebollas verdes, en rodajas para decorar"],
        "instructions": ["Cook bacon in a large Dutch oven over medium heat until crispy, about 5 minutes. Remove bacon and set aside, leaving drippings in the pot.","Add onion and bell pepper to the bacon drippings. Cook until softened, about 5 minutes. Add garlic and cook 1 minute more.","Stir in diced tomatoes, chicken broth, tomato paste, smoked paprika, salt, black pepper, and cayenne. Bring to a simmer.","Add rice and stir to combine. Return bacon to the pot. Cover and reduce heat to low.","Cook for 35-40 minutes until rice is tender and liquid is absorbed. Do not lift the lid while cooking.","Remove from heat and let rest, covered, for 5 minutes. Fluff with a fork. Garnish with green onions and serve."],
        "instructions_es": ["Cocine el tocino en una olla grande a fuego medio hasta que esté crujiente, unos 5 minutos. Retire el tocino y reserve.","Agregue la cebolla y el pimiento a la grasa del tocino. Cocine hasta que estén suaves, unos 5 minutos. Agregue el ajo y cocine 1 minuto más.","Incorpore los tomates picados, el caldo de pollo, la pasta de tomate, el pimentón, la sal, la pimienta y la cayena. Lleve a fuego lento.","Agregue el arroz y mezcle. Vuelva a poner el tocino en la olla. Tape y reduzca el fuego a bajo.","Cocine durante 35-40 minutos hasta que el arroz esté tierno. No levante la tapa mientras se cocina.","Retire del fuego y deje reposar tapado durante 5 minutos. Esponje con un tenedor. Decore con cebollas verdes y sirva."],
        "notes": "For extra flavor, use smoked turkey instead of bacon. This dish freezes beautifully for up to 3 months.",
        "notes_es": "Para más sabor, use pavo ahumado en lugar de tocino. Este plato se congela perfectamente hasta por 3 meses.",
        "category": "Main Dish", "cuisine": "Gullah Geechee",
        "pinterest_title": "Authentic Gullah Red Rice Recipe — Lowcountry Soul Food",
        "pinterest_desc": "This Gullah red rice recipe is the real deal. Tomato, bacon, and rice cooked low and slow."
    },
    {
        "slug": "shrimp-and-grits",
        "title": "Lowcountry Shrimp and Grits Recipe",
        "title_es": "Receta de Camarones con Sémola de las Lowcountry",
        "description": "Fresh shrimp over creamy stone-ground grits with smoky bacon and rich gravy. This Gullah Geechee shrimp and grits recipe is pure Lowcountry soul food.",
        "description_es": "Camarones frescos sobre sémola de molino de piedra cremosa con tocino ahumado y salsa rica.",
        "keywords": "shrimp and grits recipe, Lowcountry shrimp and grits, Gullah Geechee shrimp and grits, Charleston shrimp and grits",
        "keywords_es": "receta de camarones con sémola, camarones con sémola Lowcountry, camarones con sémola Gullah Geechee",
        "prep_time": "PT15M", "cook_time": "PT30M", "total_time": "PT45M",
        "servings": 4, "calories": 520,
        "ingredients": ["1 cup stone-ground grits (not instant)","4 cups water","1 tsp salt","2 tbsp butter","1/2 cup sharp cheddar cheese, grated","1 lb large shrimp, peeled and deveined","4 slices bacon, chopped","1/2 cup diced onion","2 cloves garlic, minced","1 tbsp all-purpose flour","1 cup chicken broth","1/2 cup heavy cream","1 tbsp lemon juice","1/4 tsp cayenne pepper","2 tbsp fresh parsley, chopped"],
        "ingredients_es": ["1 taza de sémola de molino de piedra","4 tazas de agua","1 cucharadita de sal","2 cucharadas de mantequilla","1/2 taza de queso cheddar rallado","500g de camarones grandes, pelados y desvenados","4 rebanadas de tocino, picado","1/2 taza de cebolla picada","2 dientes de ajo, picados","1 cucharada de harina","1 taza de caldo de pollo","1/2 taza de crema espesa","1 cucharada de jugo de limón","1/4 cucharadita de cayena","2 cucharadas de perejil fresco picado"],
        "instructions": ["Bring water and salt to a boil. Slowly whisk in grits. Reduce heat to low and cook, stirring occasionally, for 20-25 minutes until thick and creamy.","Stir in butter and cheddar cheese until melted. Cover and keep warm.","Cook bacon in a large skillet over medium heat until crispy. Remove bacon, leaving drippings.","Add onion to drippings and cook 3 minutes. Add garlic and cook 1 minute. Sprinkle flour over and stir for 1 minute.","Slowly whisk in chicken broth and cream. Simmer until thickened, about 3 minutes.","Season shrimp with salt, pepper, and cayenne. Add to the skillet and cook 3-4 minutes until pink. Stir in lemon juice and bacon.","Serve shrimp and gravy over cheesy grits. Garnish with parsley."],
        "instructions_es": ["Lleve el agua y la sal a ebullición. Incorpore la sémola lentamente. Reduzca el fuego a bajo y cocine 20-25 minutos hasta que esté espesa y cremosa.","Incorpore la mantequilla y el queso cheddar hasta que se derritan. Tape y mantenga caliente.","Cocine el tocino en una sartén grande a fuego medio hasta que esté crujiente. Retire el tocino, dejando la grasa.","Agregue la cebolla a la grasa y cocine 3 minutos. Agregue el ajo y cocine 1 minuto. Espolvoree la harina y revuelva por 1 minuto.","Incorpore lentamente el caldo de pollo y la crema. Cueza a fuego lento hasta que espese, unos 3 minutos.","Sazone los camarones con sal, pimienta y cayena. Agregue a la sartén y cocine 3-4 minutos hasta que estén rosados. Incorpore el jugo de limón y el tocino.","Sirva los camarones y la salsa sobre la sémola con queso. Decore con perejil."],
        "notes": "Use stone-ground grits for the best texture. Never use instant grits — they ruin the dish. Add hot sauce to taste.",
        "notes_es": "Use sémola de molino de piedra para la mejor textura. Nunca use sémola instantánea. Agregue salsa picante al gusto.",
        "category": "Main Dish", "cuisine": "Gullah Geechee",
        "pinterest_title": "Lowcountry Shrimp and Grits — Gullah Geechee Soul Food Recipe",
        "pinterest_desc": "Creamy stone-ground grits topped with seasoned shrimp in a rich bacon gravy."
    },
    {
        "slug": "okra-soup",
        "title": "Gullah Geechee Okra Soup Recipe",
        "title_es": "Receta de Sopa de Okra Gullah Geechee",
        "description": "West African roots in every bowl. Okra, tomatoes, seafood, and the spirit of the Gullah people. This okra soup recipe is pure Lowcountry tradition.",
        "description_es": "Raíces de África Occidental en cada tazón. Okra, tomates, mariscos y el espíritu del pueblo Gullah.",
        "keywords": "okra soup recipe, Gullah okra soup, Lowcountry okra soup, African okra soup, Southern okra soup",
        "keywords_es": "receta de sopa de okra, sopa de okra Gullah, sopa de okra Lowcountry, sopa de okra africana",
        "prep_time": "PT15M", "cook_time": "PT45M", "total_time": "PT1H",
        "servings": 8, "calories": 290,
        "ingredients": ["1 lb fresh okra, sliced into 1/2-inch rounds","1 lb shrimp, peeled and deveined","1/2 lb smoked sausage, sliced","1 large onion, diced","1 green bell pepper, diced","3 cloves garlic, minced","1 can (14.5 oz) diced tomatoes","1 can (14.5 oz) crushed tomatoes","4 cups chicken broth","1 cup corn kernels (fresh or frozen)","2 bay leaves","1 tsp thyme","1 tsp smoked paprika","1/2 tsp cayenne pepper","Salt and black pepper to taste","2 tbsp olive oil","Cooked rice for serving"],
        "ingredients_es": ["500g de okra fresca, en rodajas de 1 cm","500g de camarones, pelados y desvenados","250g de salchicha ahumada, en rodajas","1 cebolla grande, picada","1 pimiento verde, picado","3 dientes de ajo, picados","1 lata (410g) de tomates picados","1 lata (410g) de tomates triturados","4 tazas de caldo de pollo","1 taza de granos de maíz","2 hojas de laurel","1 cucharadita de tomillo","1 cucharadita de pimentón ahumado","1/2 cucharadita de cayena","Sal y pimienta al gusto","2 cucharadas de aceite de oliva","Arroz cocido para servir"],
        "instructions": ["Heat olive oil in a large pot over medium heat. Cook sausage until browned, about 4 minutes. Remove and set aside.","Add onion and bell pepper to the pot. Cook until softened, about 5 minutes. Add garlic and cook 1 minute.","Stir in okra and cook 5 minutes, stirring occasionally, until the okra starts to lose its slime.","Add diced tomatoes, crushed tomatoes, chicken broth, bay leaves, thyme, smoked paprika, and cayenne. Bring to a boil.","Reduce heat and simmer 25 minutes, stirring occasionally.","Add shrimp, corn, and cooked sausage. Simmer 5 more minutes until shrimp is pink.","Season with salt and pepper. Remove bay leaves. Serve over rice."],
        "instructions_es": ["Caliente el aceite de oliva en una olla grande a fuego medio. Cocine la salchicha hasta que esté dorada, unos 4 minutos. Retire y reserve.","Agregue la cebolla y el pimiento a la olla. Cocine hasta que estén suaves, unos 5 minutos. Agregue el ajo y cocine 1 minuto.","Incorpore la okra y cocine 5 minutos, revolviendo ocasionalmente, hasta que la okra comience a perder su baba.","Agregue los tomates picados, los tomates triturados, el caldo de pollo, las hojas de laurel, el tomillo, el pimentón ahumado y la cayena. Lleve a ebullición.","Reduzca el fuego y cocine a fuego lento 25 minutos, revolviendo ocasionalmente.","Agregue los camarones, el maíz y la salchicha cocida. Cueza 5 minutos más hasta que los camarones estén rosados.","Sazone con sal y pimienta. Retire las hojas de laurel. Sirva sobre arroz."],
        "notes": "Okra soup is even better the next day. The flavors meld overnight. Freezes perfectly for up to 3 months.",
        "notes_es": "La sopa de okra es aún mejor al día siguiente. Los sabores se mezclan durante la noche. Se congela perfectamente hasta por 3 meses.",
        "category": "Soup", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Geechee Okra Soup — West African Roots in Every Bowl",
        "pinterest_desc": "Hearty okra soup with shrimp, smoked sausage, and tomatoes. A Gullah Geechee tradition."
    },
    {
        "slug": "benne-wafers",
        "title": "Traditional Gullah Benne Wafers Recipe",
        "title_es": "Receta Tradicional de Galletas de Benne Gullah",
        "description": "Sesame cookies brought from West Africa. A Gullah Geechee tradition that tastes like history. These benne wafers are the perfect sweet and nutty treat.",
        "description_es": "Galletas de ajonjolí traídas de África Occidental. Una tradición Gullah Geechee que sabe a historia.",
        "keywords": "benne wafers recipe, Gullah benne wafers, sesame cookies, Charleston benne wafers, traditional Gullah recipe",
        "keywords_es": "receta de galletas de benne, galletas de benne Gullah, galletas de ajonjolí, galletas de benne Charleston",
        "prep_time": "PT15M", "cook_time": "PT12M", "total_time": "PT27M",
        "servings": 24, "calories": 95,
        "ingredients": ["1 cup toasted benne seeds (sesame seeds)","1/2 cup unsalted butter, softened","1 cup light brown sugar, packed","1 large egg","1 tsp vanilla extract","1 cup all-purpose flour","1/2 tsp baking powder","1/4 tsp salt"],
        "ingredients_es": ["1 taza de semillas de benne tostadas (ajonjolí)","1/2 taza de mantequilla sin sal, ablandada","1 taza de azúcar moreno claro, compactado","1 huevo grande","1 cucharadita de extracto de vainilla","1 taza de harina","1/2 cucharadita de polvo de hornear","1/4 cucharadita de sal"],
        "instructions": ["Preheat oven to 350°F. Line baking sheets with parchment paper.","Toast benne seeds in a dry skillet over medium heat, stirring constantly, until golden and fragrant, about 3 minutes. Set aside to cool.","Cream butter and brown sugar together until light and fluffy, about 3 minutes.","Beat in egg and vanilla extract until well combined.","In a separate bowl, whisk together flour, baking powder, and salt. Gradually add to wet mixture.","Fold in toasted benne seeds until evenly distributed.","Drop teaspoon-sized balls of dough onto prepared baking sheets, spacing 2 inches apart.","Bake 10-12 minutes until edges are golden brown. Cool on baking sheet for 5 minutes, then transfer to wire rack."],
        "instructions_es": ["Precaliente el horno a 175°C. Cubra las bandejas para hornear con papel pergamino.","Tueste las semillas de benne en una sartén seca a fuego medio, revolviendo constantemente, hasta que estén doradas, unos 3 minutos. Reserve.","Bata la mantequilla y el azúcar moreno hasta que estén suaves y esponjosos, unos 3 minutos.","Incorpore el huevo y el extracto de vainilla hasta que estén bien combinados.","En un tazón aparte, mezcle la harina, el polvo de hornear y la sal. Agregue gradualmente a la mezcla húmeda.","Incorpore las semillas de benne tostadas hasta que se distribuyan uniformemente.","Coloque bolas de masa del tamaño de una cucharadita en las bandejas preparadas, separadas 5 cm.","Hornee 10-12 minutos hasta que los bordes estén dorados. Enfríe en la bandeja 5 minutos, luego transfiera a una rejilla."],
        "notes": "Benne seeds are traditional sesame seeds brought from West Africa by enslaved Gullah Geechee people. Store in an airtight container for up to 2 weeks.",
        "notes_es": "Las semillas de benne son semillas de ajonjolí tradicionales traídas de África Occidental. Guarde en un recipiente hermético hasta por 2 semanas.",
        "category": "Dessert", "cuisine": "Gullah Geechee",
        "pinterest_title": "Traditional Gullah Benne Wafers — Sesame Cookies from West Africa",
        "pinterest_desc": "These benne wafers are a Gullah Geechee treasure. Toasted sesame, brown sugar, and butter."
    },
    {
        "slug": "frogmore-stew",
        "title": "Lowcountry Frogmore Stew Recipe",
        "title_es": "Receta de Estofado Frogmore de las Lowcountry",
        "description": "The Lowcountry boil. Shrimp, sausage, corn, potatoes — a community feast on any given Sunday. This Frogmore stew recipe is Gullah Geechee tradition.",
        "description_es": "El hervido de las Lowcountry. Camarones, salchicha, maíz, papas — un festín comunitario cualquier domingo.",
        "keywords": "Frogmore stew recipe, Lowcountry boil recipe, Gullah Frogmore stew, shrimp boil recipe, Southern seafood boil",
        "keywords_es": "receta de estofado Frogmore, receta de hervido Lowcountry, estofado Frogmore Gullah, hervido de camarones",
        "prep_time": "PT15M", "cook_time": "PT30M", "total_time": "PT45M",
        "servings": 8, "calories": 450,
        "ingredients": ["2 lbs large shrimp, unpeeled","1 lb smoked sausage (andouille or kielbasa), sliced","6 ears corn, halved","1.5 lbs small red potatoes","1 large onion, quartered","4 cloves garlic, smashed","1/4 cup Old Bay seasoning","2 tbsp salt","1 tbsp cayenne pepper","2 bay leaves","1 lemon, halved","Melted butter for serving","Hot sauce for serving"],
        "ingredients_es": ["1 kg de camarones grandes, sin pelar","500g de salchicha ahumada, en rodajas","6 mazorcas de maíz, partidas por la mitad","750g de papas rojas pequeñas","1 cebolla grande, en cuartos","4 dientes de ajo, machacados","1/4 taza de condimento Old Bay","2 cucharadas de sal","1 cucharada de cayena","2 hojas de laurel","1 limón, partido por la mitad","Mantequilla derretida para servir","Salsa picante para servir"],
        "instructions": ["Fill a large stockpot with 4 quarts of water. Add Old Bay seasoning, salt, cayenne, bay leaves, onion, garlic, and lemon halves. Bring to a rolling boil.","Add potatoes and cook for 10 minutes.","Add corn and sausage. Cook for 5 minutes.","Add shrimp and cook for 3-4 minutes until pink. Do not overcook.","Drain immediately. Discard bay leaves, onion, garlic, and lemon.","Pour the entire contents onto a large newspaper-covered table or platter. Serve with melted butter and hot sauce."],
        "instructions_es": ["Llene una olla grande con 4 litros de agua. Agregue el condimento Old Bay, sal, cayena, hojas de laurel, cebolla, ajo y las mitades de limón. Lleve a ebullición.","Agregue las papas y cocine por 10 minutos.","Agregue el maíz y la salchicha. Cocine por 5 minutos.","Agregue los camarones y cocine 3-4 minutos hasta que estén rosados. No cocine demasiado.","Escurra inmediatamente. Deseche las hojas de laurel, cebolla, ajo y limón.","Vierta todo sobre una mesa grande cubierta con periódico o una bandeja. Sirva con mantequilla derretida y salsa picante."],
        "notes": "Frogmore Stew is named after Frogmore, South Carolina on St. Helena Island. It's meant to be eaten with your hands, gathered around a table with family.",
        "notes_es": "El estofado Frogmore lleva el nombre de Frogmore, Carolina del Sur, en la isla St. Helena. Está hecho para comerse con las manos.",
        "category": "Main Dish", "cuisine": "Gullah Geechee",
        "pinterest_title": "Lowcountry Frogmore Stew — Gullah Geechee Seafood Boil Recipe",
        "pinterest_desc": "Shrimp, sausage, corn, and potatoes boiled with Old Bay. A Gullah Geechee community feast."
    },
    {
        "slug": "hoppin-john",
        "title": "Gullah Hoppin' John Recipe",
        "title_es": "Receta de Hoppin' John Gullah",
        "description": "Black-eyed peas and rice with smoked pork — the ultimate New Year's tradition for good luck. This Gullah Hoppin' John recipe brings prosperity.",
        "description_es": "Frijoles de ojo negro y arroz con cerdo ahumado — la tradición definitiva de Año Nuevo para la buena suerte.",
        "keywords": "Hoppin John recipe, Gullah Hoppin John, black-eyed peas and rice, Southern New Year's recipe, good luck recipe",
        "keywords_es": "receta de Hoppin John, Hoppin John Gullah, frijoles de ojo negro con arroz, receta de Año Nuevo sureña",
        "prep_time": "PT15M", "cook_time": "PT1H30M", "total_time": "PT1H45M",
        "servings": 8, "calories": 350,
        "ingredients": ["1 lb dried black-eyed peas, soaked overnight","1 smoked ham hock or turkey leg","1 large onion, diced","3 cloves garlic, minced","1 green bell pepper, diced","2 cups long-grain rice","4 cups chicken broth","2 bay leaves","1 tsp thyme","1 tsp smoked paprika","1/2 tsp cayenne pepper","Salt and black pepper to taste","2 tbsp bacon fat or vegetable oil","Hot sauce for serving"],
        "ingredients_es": ["500g de frijoles de ojo negro secos, remojados toda la noche","1 codillo de jamón ahumado o pata de pavo","1 cebolla grande, picada","3 dientes de ajo, picados","1 pimiento verde, picado","2 tazas de arroz de grano largo","4 tazas de caldo de pollo","2 hojas de laurel","1 cucharadita de tomillo","1 cucharadita de pimentón ahumado","1/2 cucharadita de cayena","Sal y pimienta negra al gusto","2 cucharadas de grasa de tocino o aceite vegetal","Salsa picante para servir"],
        "instructions": ["Drain soaked black-eyed peas and rinse. Set aside.","Heat bacon fat in a large Dutch oven over medium heat. Cook ham hock until browned on all sides, about 5 minutes.","Add onion and bell pepper. Cook until softened, about 5 minutes. Add garlic and cook 1 minute.","Add black-eyed peas, chicken broth, bay leaves, thyme, and smoked paprika. Bring to a boil.","Reduce heat and simmer 45-60 minutes until peas are tender but not mushy.","Stir in rice, cayenne, salt, and pepper. Cover and cook 20 minutes until rice is tender.","Remove ham hock. Pick meat from bone and return to pot. Discard bay leaves. Fluff with a fork. Serve with hot sauce."],
        "instructions_es": ["Escurra los frijoles de ojo negro remojados y enjuague. Reserve.","Caliente la grasa de tocino en una olla grande a fuego medio. Cocine el codillo de jamón hasta que esté dorado, unos 5 minutos.","Agregue la cebolla y el pimiento. Cocine hasta que estén suaves, unos 5 minutos. Agregue el ajo y cocine 1 minuto.","Agregue los frijoles de ojo negro, el caldo de pollo, las hojas de laurel, el tomillo y el pimentón ahumado. Lleve a ebullición.","Reduzca el fuego y cocine a fuego lento 45-60 minutos hasta que los frijoles estén tiernos.","Incorpore el arroz, la cayena, la sal y la pimienta. Tape y cocine 20 minutos hasta que el arroz esté tierno.","Retire el codillo de jamón. Separe la carne del hueso y vuelva a ponerla en la olla. Deseche las hojas de laurel. Esponje con un tenedor. Sirva con salsa picante."],
        "notes": "Tradition says eating Hoppin' John on New Year's Day brings good luck and prosperity. Serve with collard greens (for wealth) and cornbread.",
        "notes_es": "La tradición dice que comer Hoppin' John en Año Nuevo trae buena suerte y prosperidad. Sirva con berzas (para la riqueza) y pan de maíz.",
        "category": "Main Dish", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Hoppin' John — Black-Eyed Peas and Rice for Good Luck",
        "pinterest_desc": "Black-eyed peas, rice, and smoked pork. A Gullah Geechee New Year's tradition."
    },
    {
        "slug": "sweet-potato-pie",
        "title": "Gullah Sweet Potato Pie Recipe",
        "title_es": "Receta de Pastel de Batata Gullah",
        "description": "Silky, spiced sweet potato filling in a flaky crust. This Gullah sweet potato pie recipe is the dessert that every Lowcountry Sunday dinner ends with.",
        "description_es": "Relleno sedoso de batata especiada en una corteza hojaldrada. El postre con el que termina cada cena dominical de las Lowcountry.",
        "keywords": "sweet potato pie recipe, Gullah sweet potato pie, Southern sweet potato pie, Lowcountry dessert",
        "keywords_es": "receta de pastel de batata, pastel de batata Gullah, pastel de batata sureño, postre Lowcountry",
        "prep_time": "PT20M", "cook_time": "PT55M", "total_time": "PT1H15M",
        "servings": 8, "calories": 380,
        "ingredients": ["2 cups mashed sweet potatoes (about 2 large potatoes)","1/2 cup unsalted butter, melted","1 cup sugar","1/2 cup brown sugar","2 large eggs","1 tsp vanilla extract","1 tsp cinnamon","1/2 tsp nutmeg","1/2 tsp ginger","1/4 tsp cloves","1/2 cup evaporated milk","1 tbsp all-purpose flour","1 unbaked 9-inch pie crust","Whipped cream for serving"],
        "ingredients_es": ["2 tazas de batata hecha puré","1/2 taza de mantequilla sin sal, derretida","1 taza de azúcar","1/2 taza de azúcar moreno","2 huevos grandes","1 cucharadita de extracto de vainilla","1 cucharadita de canela","1/2 cucharadita de nuez moscada","1/2 cucharadita de jengibre","1/4 cucharadita de clavo","1/2 taza de leche evaporada","1 cucharada de harina","1 corteza de pastel de 9 pulgadas sin hornear","Crema batida para servir"],
        "instructions": ["Preheat oven to 350°F. Prick pie crust with fork and pre-bake for 10 minutes. Set aside.","Boil sweet potatoes until very tender, about 20 minutes. Drain, cool, peel, and mash until smooth.","In a large bowl, combine mashed sweet potatoes, melted butter, sugar, and brown sugar. Mix well.","Beat in eggs one at a time. Add vanilla, cinnamon, nutmeg, ginger, and cloves.","Stir in evaporated milk and flour until smooth and well combined.","Pour filling into pre-baked pie crust. Smooth the top.","Bake 45-50 minutes until center is set and a knife inserted comes out clean.","Cool completely on a wire rack. Serve at room temperature with whipped cream."],
        "instructions_es": ["Precaliente el horno a 175°C. Perfore la corteza del pastel con un tenedor y hornee previamente por 10 minutos. Reserve.","Hierva las batatas hasta que estén muy tiernas, unos 20 minutos. Escurra, enfríe, pele y haga puré hasta que esté suave.","En un tazón grande, combine el puré de batata, la mantequilla derretida, el azúcar y el azúcar moreno. Mezcle bien.","Incorpore los huevos uno a la vez. Agregue la vainilla, la canela, la nuez moscada, el jengibre y el clavo.","Incorpore la leche evaporada y la harina hasta que esté suave y bien combinado.","Vierta el relleno en la corteza de pastel pre-horneada. Alise la parte superior.","Hornee 45-50 minutos hasta que el centro esté firme y un cuchillo insertado salga limpio.","Enfríe completamente en una rejilla. Sirva a temperatura ambiente con crema batida."],
        "notes": "Gullah sweet potato pie is different from pumpkin pie — it's richer, denser, and more flavorful. Make it a day ahead for the best flavor.",
        "notes_es": "El pastel de batata Gullah es diferente del pastel de calabaza — es más rico, más denso y más sabroso. Prepárelo un día antes.",
        "category": "Dessert", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Sweet Potato Pie — The Dessert That Ends Every Lowcountry Sunday",
        "pinterest_desc": "Silky spiced sweet potato filling in a flaky crust. The perfect Southern dessert."
    },
    {
        "slug": "collard-greens",
        "title": "Gullah Collard Greens Recipe",
        "title_es": "Receta de Berzas Gullah",
        "description": "Slow-cooked collard greens with smoked turkey and a hint of heat. This Gullah collard greens recipe is the soul food side dish that defines Lowcountry cooking.",
        "description_es": "Berzas cocinadas lentamente con pavo ahumado y un toque de picante. El acompañamiento de comida soul que define la cocina de las Lowcountry.",
        "keywords": "collard greens recipe, Gullah collard greens, Southern collard greens, soul food collard greens, Lowcountry collard greens",
        "keywords_es": "receta de berzas, berzas Gullah, berzas sureñas, berzas de comida soul, berzas Lowcountry",
        "prep_time": "PT15M", "cook_time": "PT1H30M", "total_time": "PT1H45M",
        "servings": 6, "calories": 180,
        "ingredients": ["2 lbs fresh collard greens, washed and chopped","1 smoked turkey leg or ham hock","1 large onion, diced","3 cloves garlic, minced","4 cups chicken broth","1 tbsp apple cider vinegar","1 tsp sugar","1/2 tsp red pepper flakes","1/2 tsp smoked paprika","Salt and black pepper to taste","2 tbsp bacon fat or olive oil"],
        "ingredients_es": ["1 kg de berzas frescas, lavadas y picadas","1 pata de pavo ahumada o codillo de jamón","1 cebolla grande, picada","3 dientes de ajo, picados","4 tazas de caldo de pollo","1 cucharada de vinagre de sidra de manzana","1 cucharadita de azúcar","1/2 cucharadita de hojuelas de pimiento rojo","1/2 cucharadita de pimentón ahumado","Sal y pimienta negra al gusto","2 cucharadas de grasa de tocino o aceite de oliva"],
        "instructions": ["Heat bacon fat in a large pot over medium heat. Brown the smoked turkey leg on all sides, about 5 minutes.","Add onion and cook until softened, about 5 minutes. Add garlic and cook 1 minute.","Add collard greens in batches, stirring until wilted before adding more.","Pour in chicken broth, apple cider vinegar, sugar, red pepper flakes, and smoked paprika. Stir to combine.","Bring to a boil, then reduce heat to low. Cover and simmer 1 to 1.5 hours until greens are tender.","Remove turkey leg. Pick meat from bone and return to pot. Season with salt and pepper.","Serve with hot sauce and cornbread. The pot liquor (broth) is prized for sopping with bread."],
        "instructions_es": ["Caliente la grasa de tocino en una olla grande a fuego medio. Dore la pata de pavo ahumada por todos lados, unos 5 minutos.","Agregue la cebolla y cocine hasta que esté suave, unos 5 minutos. Agregue el ajo y cocine 1 minuto.","Agregue las berzas en lotes, revolviendo hasta que se marchiten antes de agregar más.","Vierta el caldo de pollo, el vinagre de sidra de manzana, el azúcar, las hojuelas de pimiento rojo y el pimentón ahumado. Revuelva para combinar.","Lleve a ebullición, luego reduzca el fuego a bajo. Tape y cocine a fuego lento 1 a 1.5 horas hasta que las berzas estén tiernas.","Retire la pata de pavo. Separe la carne del hueso y vuelva a ponerla en la olla. Sazone con sal y pimienta.","Sirva con salsa picante y pan de maíz. El caldo (pot liquor) es apreciado para mojar con pan."],
        "notes": "The longer collard greens cook, the better they taste. Make a big batch — they reheat beautifully. Serve with black-eyed peas for good luck.",
        "notes_es": "Cuanto más tiempo se cocinen las berzas, mejor saben. Haga una tanda grande — se recalientan perfectamente.",
        "category": "Side Dish", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Collard Greens — Slow-Cooked Soul Food Side Dish",
        "pinterest_desc": "Tender collard greens slow-cooked with smoked turkey. The ultimate Gullah Geechee soul food side."
    },
    {
        "slug": "perloo-chicken",
        "title": "Gullah Chicken Perloo Recipe",
        "title_es": "Receta de Perloo de Pollo Gullah",
        "description": "A one-pot Gullah rice dish with chicken, vegetables, and rich seasonings. This chicken perloo recipe is Lowcountry comfort food at its finest.",
        "description_es": "Un plato de arroz Gullah de una sola olla con pollo, verduras y condimentos ricos.",
        "keywords": "chicken perloo recipe, Gullah perloo, Lowcountry perloo, one-pot chicken and rice, Gullah rice dish",
        "keywords_es": "receta de perloo de pollo, perloo Gullah, perloo Lowcountry, pollo y arroz de una olla",
        "prep_time": "PT15M", "cook_time": "PT45M", "total_time": "PT1H",
        "servings": 6, "calories": 420,
        "ingredients": ["1.5 lbs chicken thighs, bone-in, skin-on","2 cups long-grain rice","1 large onion, diced","2 celery stalks, diced","1 green bell pepper, diced","3 cloves garlic, minced","4 cups chicken broth","1 can (14.5 oz) diced tomatoes","2 bay leaves","1 tsp thyme","1 tsp smoked paprika","1/2 tsp cayenne pepper","Salt and black pepper to taste","2 tbsp vegetable oil","2 green onions, sliced for garnish"],
        "ingredients_es": ["750g de muslos de pollo, con hueso y piel","2 tazas de arroz de grano largo","1 cebolla grande, picada","2 tallos de apio, picados","1 pimiento verde, picado","3 dientes de ajo, picados","4 tazas de caldo de pollo","1 lata (410g) de tomates picados","2 hojas de laurel","1 cucharadita de tomillo","1 cucharadita de pimentón ahumado","1/2 cucharadita de cayena","Sal y pimienta negra al gusto","2 cucharadas de aceite vegetal","2 cebollas verdes, en rodajas para decorar"],
        "instructions": ["Season chicken thighs with salt, pepper, and smoked paprika. Heat oil in a large Dutch oven over medium-high heat.","Brown chicken on both sides, about 4 minutes per side. Remove and set aside.","Add onion, celery, and bell pepper to the pot. Cook until softened, about 5 minutes. Add garlic and cook 1 minute.","Stir in rice and cook 2 minutes, stirring constantly, until rice is lightly toasted.","Add chicken broth, diced tomatoes, bay leaves, thyme, and cayenne. Stir to combine.","Nestle chicken thighs back into the pot, skin side up. Bring to a boil.","Cover, reduce heat to low, and cook 25-30 minutes until rice is tender and chicken is cooked through.","Remove from heat and let rest 5 minutes. Discard bay leaves. Garnish with green onions."],
        "instructions_es": ["Sazone los muslos de pollo con sal, pimienta y pimentón ahumado. Caliente el aceite en una olla grande a fuego medio-alto.","Dore el pollo por ambos lados, unos 4 minutos por lado. Retire y reserve.","Agregue la cebolla, el apio y el pimiento a la olla. Cocine hasta que estén suaves, unos 5 minutos. Agregue el ajo y cocine 1 minuto.","Incorpore el arroz y cocine 2 minutos, revolviendo constantemente, hasta que el arroz esté ligeramente tostado.","Agregue el caldo de pollo, los tomates picados, las hojas de laurel, el tomillo y la cayena. Revuelva para combinar.","Vuelva a colocar los muslos de pollo en la olla, con la piel hacia arriba. Lleve a ebullición.","Tape, reduzca el fuego a bajo y cocine 25-30 minutos hasta que el arroz esté tierno y el pollo esté cocido.","Retire del fuego y deje reposar 5 minutos. Deseche las hojas de laurel. Decore con cebollas verdes."],
        "notes": "Perloo (also spelled purloo or perlo) is the Gullah Geechee version of pilaf. It's a one-pot wonder that feeds a crowd.",
        "notes_es": "El perloo (también escrito purloo o perlo) es la versión Gullah Geechee del pilaf. Es una maravilla de una sola olla.",
        "category": "Main Dish", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Chicken Perloo — One-Pot Lowcountry Rice Dish",
        "pinterest_desc": "Tender chicken, seasoned rice, and vegetables all cooked in one pot. Pure Lowcountry comfort."
    },
    {
        "slug": "crab-rice",
        "title": "Gullah Crab Rice Recipe",
        "title_es": "Receta de Arroz con Cangrejo Gullah",
        "description": "Fresh blue crab meat simmered with rice and Lowcountry seasonings. This Gullah crab rice recipe is a coastal treasure from the Sea Islands.",
        "description_es": "Carne de cangrejo azul fresco cocinada a fuego lento con arroz y condimentos de las Lowcountry.",
        "keywords": "crab rice recipe, Gullah crab rice, Lowcountry crab rice, Sea Island crab rice, blue crab recipe",
        "keywords_es": "receta de arroz con cangrejo, arroz con cangrejo Gullah, arroz con cangrejo Lowcountry, receta de cangrejo azul",
        "prep_time": "PT10M", "cook_time": "PT30M", "total_time": "PT40M",
        "servings": 4, "calories": 390,
        "ingredients": ["1 lb fresh blue crab meat (claw or lump)","1 cup long-grain rice","1 small onion, finely diced","2 cloves garlic, minced","2 cups seafood or chicken broth","1/2 cup diced tomatoes","1 tbsp butter","1 tsp Old Bay seasoning","1/2 tsp smoked paprika","1/4 tsp cayenne pepper","Salt to taste","2 tbsp fresh parsley, chopped","Lemon wedges for serving"],
        "ingredients_es": ["500g de carne de cangrejo azul fresco","1 taza de arroz de grano largo","1 cebolla pequeña, finamente picada","2 dientes de ajo, picados","2 tazas de caldo de mariscos o pollo","1/2 taza de tomates picados","1 cucharada de mantequilla","1 cucharadita de condimento Old Bay","1/2 cucharadita de pimentón ahumado","1/4 cucharadita de cayena","Sal al gusto","2 cucharadas de perejil fresco picado","Rodajas de limón para servir"],
        "instructions": ["Pick through crab meat to remove any shell fragments. Set aside.","Melt butter in a medium saucepan over medium heat. Cook onion until softened, about 3 minutes. Add garlic and cook 1 minute.","Add rice and stir for 2 minutes until lightly toasted.","Pour in broth, diced tomatoes, Old Bay, smoked paprika, and cayenne. Bring to a boil.","Reduce heat to low, cover, and cook 18 minutes until rice is tender.","Gently fold in crab meat. Cover and cook 2 more minutes until crab is heated through.","Fluff with a fork. Season with salt. Garnish with parsley and serve with lemon wedges."],
        "instructions_es": ["Revise la carne de cangrejo para eliminar cualquier fragmento de cáscara. Reserve.","Derrita la mantequilla en una cacerola mediana a fuego medio. Cocine la cebolla hasta que esté suave, unos 3 minutos. Agregue el ajo y cocine 1 minuto.","Agregue el arroz y revuelva por 2 minutos hasta que esté ligeramente tostado.","Vierta el caldo, los tomates picados, el Old Bay, el pimentón ahumado y la cayena. Lleve a ebullición.","Reduzca el fuego a bajo, tape y cocine 18 minutos hasta que el arroz esté tierno.","Incorpore suavemente la carne de cangrejo. Tape y cocine 2 minutos más hasta que el cangrejo esté caliente.","Esponje con un tenedor. Sazone con sal. Decore con perejil y sirva con rodajas de limón."],
        "notes": "Fresh blue crab is best, but high-quality canned crab meat works in a pinch. This dish is a staple on St. Helena Island.",
        "notes_es": "El cangrejo azul fresco es mejor, pero la carne de cangrejo enlatada de alta calidad funciona en caso necesario.",
        "category": "Main Dish", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Crab Rice — Fresh Blue Crab from the Sea Islands",
        "pinterest_desc": "Tender blue crab meat simmered with seasoned rice. A Gullah Geechee coastal treasure."
    },
    # ── Batch 2: More Classics (10) ──
    {
        "slug": "gullah-gumbo",
        "title": "Gullah Geechee Seafood Gumbo Recipe",
        "title_es": "Receta de Gumbo de Mariscos Gullah Geechee",
        "description": "A rich, dark roux-based gumbo with shrimp, crab, and okra. This Gullah Geechee gumbo recipe is a Lowcountry celebration in a bowl.",
        "description_es": "Un gumbo rico con base de roux oscuro con camarones, cangrejo y okra. Una celebración de las Lowcountry en un tazón.",
        "keywords": "Gullah gumbo recipe, Lowcountry gumbo, seafood gumbo, Gullah Geechee gumbo, Charleston gumbo, okra gumbo",
        "keywords_es": "receta de gumbo Gullah, gumbo Lowcountry, gumbo de mariscos, gumbo Gullah Geechee, gumbo Charleston",
        "prep_time": "PT20M", "cook_time": "PT1H30M", "total_time": "PT1H50M",
        "servings": 8, "calories": 420,
        "ingredients": ["1/2 cup vegetable oil","1/2 cup all-purpose flour","1 large onion, diced","1 green bell pepper, diced","2 celery stalks, diced","4 cloves garlic, minced","1 lb okra, sliced","1 can (14.5 oz) diced tomatoes","6 cups seafood or chicken broth","1 lb shrimp, peeled and deveined","1/2 lb crab meat","1 lb smoked sausage, sliced","2 bay leaves","2 tsp Cajun seasoning","1 tsp thyme","1/2 tsp cayenne","Salt to taste","Cooked rice for serving","File powder for serving"],
        "ingredients_es": ["1/2 taza de aceite vegetal","1/2 taza de harina","1 cebolla grande, picada","1 pimiento verde, picado","2 tallos de apio, picados","4 dientes de ajo, picados","500g de okra, en rodajas","1 lata (410g) de tomates picados","6 tazas de caldo de mariscos o pollo","500g de camarones, pelados y desvenados","250g de carne de cangrejo","500g de salchicha ahumada, en rodajas","2 hojas de laurel","2 cucharaditas de condimento Cajún","1 cucharadita de tomillo","1/2 cucharadita de cayena","Sal al gusto","Arroz cocido para servir","Polvo de file para servir"],
        "instructions": ["Make the roux: Heat oil in a large heavy pot over medium heat. Whisk in flour and cook, stirring constantly, until dark brown (color of chocolate), about 20 minutes. Do not burn.","Add onion, bell pepper, and celery (the 'holy trinity'). Cook until softened, about 5 minutes. Add garlic and cook 1 minute.","Add okra and cook 5 minutes, stirring. Add diced tomatoes, broth, bay leaves, Cajun seasoning, thyme, and cayenne. Bring to a boil.","Reduce heat and simmer 45 minutes, stirring occasionally.","Add sausage and cook 10 minutes. Add shrimp and crab meat. Cook 5 more minutes until shrimp is pink.","Season with salt. Remove bay leaves. Serve over rice with file powder on top."],
        "instructions_es": ["Haga el roux: Caliente el aceite en una olla grande a fuego medio. Incorpore la harina y cocine, revolviendo constantemente, hasta que esté marrón oscuro, unos 20 minutos. No queme.","Agregue la cebolla, el pimiento y el apio. Cocine hasta que estén suaves, unos 5 minutos. Agregue el ajo y cocine 1 minuto.","Agregue la okra y cocine 5 minutos, revolviendo. Agregue los tomates picados, el caldo, las hojas de laurel, el condimento Cajún, el tomillo y la cayena. Lleve a ebullición.","Reduzca el fuego y cocine a fuego lento 45 minutos, revolviendo ocasionalmente.","Agregue la salchicha y cocine 10 minutos. Agregue los camarones y la carne de cangrejo. Cocine 5 minutos más hasta que los camarones estén rosados.","Sazone con sal. Retire las hojas de laurel. Sirva sobre arroz con polvo de file encima."],
        "notes": "The roux is the heart of gumbo. Take your time getting it dark — a light roux won't give you that deep, nutty flavor. File powder (ground sassafras) is traditional.",
        "notes_es": "El roux es el corazón del gumbo. Tómese su tiempo para que se oscurezca — un roux claro no le dará ese sabor profundo y a nuez.",
        "category": "Soup", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Geechee Seafood Gumbo — Lowcountry Celebration in a Bowl",
        "pinterest_desc": "Rich dark roux gumbo with shrimp, crab, okra, and sausage. A Gullah Geechee tradition."
    },
    {
        "slug": "cornbread-dressing",
        "title": "Gullah Cornbread Dressing Recipe",
        "title_es": "Receta de Relleno de Pan de Maíz Gullah",
        "description": "Savory cornbread dressing with sage, onions, and celery. This Gullah cornbread dressing recipe is the soul food side that defines Thanksgiving in the Lowcountry.",
        "description_es": "Relleno salado de pan de maíz con salvia, cebollas y apio. El acompañamiento de comida soul que define el Día de Acción de Gracias en las Lowcountry.",
        "keywords": "cornbread dressing recipe, Gullah cornbread dressing, Southern dressing, soul food dressing, Thanksgiving dressing, Lowcountry dressing",
        "keywords_es": "receta de relleno de pan de maíz, relleno de pan de maíz Gullah, relleno sureño, relleno de comida soul",
        "prep_time": "PT20M", "cook_time": "PT45M", "total_time": "PT1H5M",
        "servings": 10, "calories": 310,
        "ingredients": ["4 cups crumbled cornbread (day-old is best)","2 cups crumbled white bread","1/2 cup butter","1 large onion, diced","3 celery stalks, diced","1 green bell pepper, diced","3 cloves garlic, minced","2 cups chicken broth","2 large eggs, beaten","1 tbsp fresh sage, chopped","1 tsp thyme","1 tsp poultry seasoning","1/2 tsp black pepper","1 tsp salt","1/2 tsp cayenne pepper (optional)"],
        "ingredients_es": ["4 tazas de pan de maíz desmenuzado (del día anterior es mejor)","2 tazas de pan blanco desmenuzado","1/2 taza de mantequilla","1 cebolla grande, picada","3 tallos de apio, picados","1 pimiento verde, picado","3 dientes de ajo, picados","2 tazas de caldo de pollo","2 huevos grandes, batidos","1 cucharada de salvia fresca picada","1 cucharadita de tomillo","1 cucharadita de condimento para aves","1/2 cucharadita de pimienta negra","1 cucharadita de sal","1/2 cucharadita de cayena (opcional)"],
        "instructions": ["Preheat oven to 375°F. Grease a 9x13 baking dish.","In a large skillet, melt butter over medium heat. Add onion, celery, and bell pepper. Cook until softened, about 8 minutes. Add garlic and cook 1 minute.","In a large bowl, combine crumbled cornbread and white bread. Add the cooked vegetables and stir to combine.","In a separate bowl, whisk together chicken broth, eggs, sage, thyme, poultry seasoning, salt, pepper, and cayenne.","Pour the liquid mixture over the bread mixture and stir until well combined. The mixture should be moist but not soupy.","Transfer to prepared baking dish. Bake 40-45 minutes until golden brown on top and set in the center.","Let rest 10 minutes before serving."],
        "instructions_es": ["Precaliente el horno a 190°C. Engrase un molde para hornear de 9x13.","En una sartén grande, derrita la mantequilla a fuego medio. Agregue la cebolla, el apio y el pimiento. Cocine hasta que estén suaves, unos 8 minutos. Agregue el ajo y cocine 1 minuto.","En un tazón grande, combine el pan de maíz y el pan blanco desmenuzados. Agregue las verduras cocidas y mezcle.","En un tazón aparte, bata el caldo de pollo, los huevos, la salvia, el tomillo, el condimento para aves, la sal, la pimienta y la cayena.","Vierta la mezcla líquida sobre la mezcla de pan y revuelva hasta que esté bien combinado.","Transfiera al molde preparado. Hornee 40-45 minutos hasta que esté dorado y firme en el centro.","Deje reposar 10 minutos antes de servir."],
        "notes": "Day-old cornbread is essential — fresh cornbread will turn mushy. Make your cornbread a day ahead and leave it out to dry.",
        "notes_es": "El pan de maíz del día anterior es esencial — el pan de maíz fresco se volverá blando. Prepare su pan de maíz el día anterior.",
        "category": "Side Dish", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Cornbread Dressing — Soul Food Thanksgiving Side Dish",
        "pinterest_desc": "Savory cornbread dressing with sage and onions. The Gullah Geechee Thanksgiving tradition."
    },
    {
        "slug": "fried-fish",
        "title": "Gullah Fried Fish Recipe",
        "title_es": "Receta de Pescado Frito Gullah",
        "description": "Crispy, golden fried fish with a perfectly seasoned cornmeal crust. This Gullah fried fish recipe is a Lowcountry Friday night tradition.",
        "description_es": "Pescado frito crujiente y dorado con una corteza de harina de maíz perfectamente sazonada. Una tradición de los viernes por la noche en las Lowcountry.",
        "keywords": "fried fish recipe, Gullah fried fish, Southern fried fish, Lowcountry fried fish, cornmeal fried fish, crispy fried fish",
        "keywords_es": "receta de pescado frito, pescado frito Gullah, pescado frito sureño, pescado frito Lowcountry, pescado frito con harina de maíz",
        "prep_time": "PT10M", "cook_time": "PT15M", "total_time": "PT25M",
        "servings": 4, "calories": 450,
        "ingredients": ["2 lbs catfish or whiting fillets","1 cup yellow cornmeal","1/2 cup all-purpose flour","1 tbsp Old Bay seasoning","1 tsp garlic powder","1 tsp onion powder","1 tsp smoked paprika","1/2 tsp cayenne pepper","1 tsp salt","1/2 tsp black pepper","1 cup buttermilk","1 large egg","Vegetable oil for frying","Lemon wedges for serving","Hot sauce for serving"],
        "ingredients_es": ["1 kg de filetes de bagre o merluza","1 taza de harina de maíz amarilla","1/2 taza de harina","1 cucharada de condimento Old Bay","1 cucharadita de ajo en polvo","1 cucharadita de cebolla en polvo","1 cucharadita de pimentón ahumado","1/2 cucharadita de cayena","1 cucharadita de sal","1/2 cucharadita de pimienta negra","1 taza de suero de leche","1 huevo grande","Aceite vegetal para freír","Rodajas de limón para servir","Salsa picante para servir"],
        "instructions": ["Rinse fish fillets and pat dry with paper towels. Season lightly with salt.","In a shallow dish, combine cornmeal, flour, Old Bay, garlic powder, onion powder, smoked paprika, cayenne, salt, and black pepper.","In another dish, whisk together buttermilk and egg.","Heat 1 inch of oil in a large cast iron skillet to 350°F.","Dip each fillet in buttermilk mixture, then dredge in cornmeal mixture, pressing gently to adhere.","Carefully place fillets in hot oil. Fry 3-4 minutes per side until golden brown and cooked through.","Drain on paper towels. Serve hot with lemon wedges and hot sauce."],
        "instructions_es": ["Enjuague los filetes de pescado y séquelos con toallas de papel. Sazone ligeramente con sal.","En un plato poco profundo, combine la harina de maíz, la harina, el Old Bay, el ajo en polvo, la cebolla en polvo, el pimentón ahumado, la cayena, la sal y la pimienta negra.","En otro plato, bata el suero de leche y el huevo.","Caliente 2.5 cm de aceite en una sartén grande de hierro fundido a 175°C.","Sumerja cada filete en la mezcla de suero de leche, luego pase por la mezcla de harina de maíz, presionando suavemente.","Coloque cuidadosamente los filetes en el aceite caliente. Fría 3-4 minutos por lado hasta que estén dorados.","Escurra sobre toallas de papel. Sirva caliente con rodajas de limón y salsa picante."],
        "notes": "Catfish is traditional, but whiting, trout, or any white fish works. The key is getting the oil to the right temperature — too low and the fish gets greasy.",
        "notes_es": "El bagre es tradicional, pero la merluza, la trucha o cualquier pescado blanco funciona. La clave es tener el aceite a la temperatura correcta.",
        "category": "Main Dish", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Fried Fish — Crispy Cornmeal-Crusted Lowcountry Tradition",
        "pinterest_desc": "Crispy golden fried fish with a perfectly seasoned cornmeal crust. A Gullah Geechee Friday night tradition."
    },
    {
        "slug": "mac-and-cheese",
        "title": "Gullah Baked Mac and Cheese Recipe",
        "title_es": "Receta de Macarrones con Queso Horneados Gullah",
        "description": "Creamy, cheesy, baked to golden perfection. This Gullah mac and cheese recipe is the soul food side dish that every family gathering demands.",
        "description_es": "Cremoso, con queso, horneado a la perfección dorada. El acompañamiento de comida soul que cada reunión familiar exige.",
        "keywords": "baked mac and cheese recipe, Gullah mac and cheese, Southern mac and cheese, soul food mac and cheese, Lowcountry mac and cheese",
        "keywords_es": "receta de macarrones con queso horneados, macarrones con queso Gullah, macarrones con queso sureños",
        "prep_time": "PT15M", "cook_time": "PT30M", "total_time": "PT45M",
        "servings": 8, "calories": 480,
        "ingredients": ["1 lb elbow macaroni","4 tbsp butter","4 tbsp all-purpose flour","3 cups whole milk","1 cup heavy cream","2 cups sharp cheddar cheese, shredded","1 cup Monterey Jack cheese, shredded","1/2 cup Gruyere or Swiss cheese, shredded","1 tsp salt","1/2 tsp black pepper","1/2 tsp smoked paprika","1/4 tsp cayenne pepper","1/2 cup panko breadcrumbs","2 tbsp butter, melted (for topping)"],
        "ingredients_es": ["500g de macarrones de codo","4 cucharadas de mantequilla","4 cucharadas de harina","3 tazas de leche entera","1 taza de crema espesa","2 tazas de queso cheddar rallado","1 taza de queso Monterey Jack rallado","1/2 taza de queso Gruyere o Suizo rallado","1 cucharadita de sal","1/2 cucharadita de pimienta negra","1/2 cucharadita de pimentón ahumado","1/4 cucharadita de cayena","1/2 taza de pan rallado panko","2 cucharadas de mantequilla derretida (para cubrir)"],
        "instructions": ["Preheat oven to 375°F. Grease a 9x13 baking dish.","Cook macaroni according to package directions until al dente. Drain and set aside.","In a large saucepan, melt 4 tbsp butter over medium heat. Whisk in flour and cook 2 minutes, stirring constantly.","Slowly whisk in milk and cream. Cook, stirring constantly, until thickened, about 5 minutes.","Remove from heat. Stir in cheddar, Monterey Jack, and Gruyere until melted and smooth. Season with salt, pepper, smoked paprika, and cayenne.","Add cooked macaroni to the cheese sauce and stir to combine. Pour into prepared baking dish.","In a small bowl, combine panko with 2 tbsp melted butter. Sprinkle over the top.","Bake 25-30 minutes until bubbly and golden brown on top. Let rest 10 minutes before serving."],
        "instructions_es": ["Precaliente el horno a 190°C. Engrase un molde para hornear de 9x13.","Cocine los macarrones según las instrucciones del paquete hasta que estén al dente. Escurra y reserve.","En una cacerola grande, derrita 4 cucharadas de mantequilla a fuego medio. Incorpore la harina y cocine 2 minutos, revolviendo constantemente.","Incorpore lentamente la leche y la crema. Cocine, revolviendo constantemente, hasta que espese, unos 5 minutos.","Retire del fuego. Incorpore el cheddar, el Monterey Jack y el Gruyere hasta que se derritan y estén suaves. Sazone con sal, pimienta, pimentón ahumado y cayena.","Agregue los macarrones cocidos a la salsa de queso y mezcle. Vierta en el molde preparado.","En un tazón pequeño, combine el panko con 2 cucharadas de mantequilla derretida. Espolvoree sobre la parte superior.","Hornee 25-30 minutos hasta que esté burbujeante y dorado. Deje reposar 10 minutos antes de servir."],
        "notes": "Use a mix of cheeses for the best flavor. Sharp cheddar is non-negotiable. The panko topping adds the perfect crunch.",
        "notes_es": "Use una mezcla de quesos para obtener el mejor sabor. El cheddar añejo es innegociable. El panko agrega el crujiente perfecto.",
        "category": "Side Dish", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Baked Mac and Cheese — Creamy Soul Food Side Dish",
        "pinterest_desc": "Three-cheese baked mac and cheese with a crispy panko topping. The ultimate Gullah Geechee comfort food."
    },
    {
        "slug": "peach-cobbler",
        "title": "Gullah Peach Cobbler Recipe",
        "title_es": "Receta de Cobbler de Durazno Gullah",
        "description": "Sweet, juicy peaches under a golden, buttery crust. This Gullah peach cobbler recipe is the taste of a Lowcountry summer.",
        "description_es": "Duraznos dulces y jugosos bajo una corteza dorada y mantecosa. El sabor de un verano en las Lowcountry.",
        "keywords": "peach cobbler recipe, Gullah peach cobbler, Southern peach cobbler, Lowcountry dessert, fresh peach cobbler",
        "keywords_es": "receta de cobbler de durazno, cobbler de durazno Gullah, cobbler de durazno sureño, postre Lowcountry",
        "prep_time": "PT15M", "cook_time": "PT45M", "total_time": "PT1H",
        "servings": 8, "calories": 360,
        "ingredients": ["6 cups fresh peaches, peeled and sliced (about 6-8 peaches)","1 cup sugar","1/2 cup brown sugar","1 tbsp lemon juice","1 tsp vanilla extract","1 tsp cinnamon","1/4 tsp nutmeg","2 tbsp cornstarch","1/2 cup butter","1 cup all-purpose flour","1 cup sugar","1 tbsp baking powder","1/4 tsp salt","1 cup milk","1 tsp vanilla extract"],
        "ingredients_es": ["6 tazas de duraznos frescos, pelados y en rodajas","1 taza de azúcar","1/2 taza de azúcar moreno","1 cucharada de jugo de limón","1 cucharadita de extracto de vainilla","1 cucharadita de canela","1/4 cucharadita de nuez moscada","2 cucharadas de maicena","1/2 taza de mantequilla","1 taza de harina","1 taza de azúcar","1 cucharada de polvo de hornear","1/4 cucharadita de sal","1 taza de leche","1 cucharadita de extracto de vainilla"],
        "instructions": ["Preheat oven to 375°F. Place 1/2 cup butter in a 9x13 baking dish and put in oven to melt while preheating.","In a large bowl, combine sliced peaches, 1 cup sugar, brown sugar, lemon juice, 1 tsp vanilla, cinnamon, nutmeg, and cornstarch. Stir gently and set aside.","In another bowl, whisk together flour, 1 cup sugar, baking powder, and salt. Stir in milk and 1 tsp vanilla until just combined. Do not overmix.","Remove hot baking dish from oven. Pour batter over the melted butter — do not stir.","Spoon peach mixture evenly over the batter — do not stir. The batter will rise up around the peaches as it bakes.","Bake 40-45 minutes until golden brown and bubbly. Let cool 15 minutes. Serve warm with vanilla ice cream."],
        "instructions_es": ["Precaliente el horno a 190°C. Coloque 1/2 taza de mantequilla en un molde de 9x13 y póngalo en el horno para que se derrita.","En un tazón grande, combine los duraznos en rodajas, 1 taza de azúcar, azúcar moreno, jugo de limón, 1 cucharadita de vainilla, canela, nuez moscada y maicena. Revuelva suavemente y reserve.","En otro tazón, mezcle la harina, 1 taza de azúcar, el polvo de hornear y la sal. Incorpore la leche y 1 cucharadita de vainilla hasta que estén combinados.","Retire el molde caliente del horno. Vierta la masa sobre la mantequilla derretida — no revuelva.","Distribuya la mezcla de duraznos uniformemente sobre la masa — no revuelva.","Hornee 40-45 minutos hasta que esté dorado y burbujeante. Deje enfriar 15 minutos. Sirva caliente con helado de vainilla."],
        "notes": "Fresh Georgia peaches are best, but frozen peaches work too. Don't overmix the batter — lumps are fine and make the cobbler more tender.",
        "notes_es": "Los duraznos frescos de Georgia son los mejores, pero los duraznos congelados también funcionan. No mezcle demasiado la masa.",
        "category": "Dessert", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Peach Cobbler — Sweet Lowcountry Summer Dessert",
        "pinterest_desc": "Sweet juicy peaches under a golden buttery crust. A taste of a Gullah Geechee Lowcountry summer."
    },
    {
        "slug": "limpin-susan",
        "title": "Gullah Limpin' Susan Recipe",
        "title_es": "Receta de Limpin' Susan Gullah",
        "description": "The cousin of Hoppin' John — rice and black-eyed peas with tomatoes and bacon. This Limpin' Susan recipe is a Gullah Geechee weekday staple.",
        "description_es": "El primo del Hoppin' John — arroz y frijoles de ojo negro con tomates y tocino. Un básico de los días de semana Gullah Geechee.",
        "keywords": "Limpin Susan recipe, Gullah Limpin Susan, black-eyed peas and rice, Lowcountry rice dish, Gullah Geechee side dish",
        "keywords_es": "receta de Limpin Susan, Limpin Susan Gullah, frijoles de ojo negro con arroz, plato de arroz Lowcountry",
        "prep_time": "PT10M", "cook_time": "PT35M", "total_time": "PT45M",
        "servings": 6, "calories": 320,
        "ingredients": ["2 cups cooked black-eyed peas (or 1 can, drained)","1 cup long-grain rice","4 slices bacon, chopped","1 small onion, diced","1 green bell pepper, diced","2 cloves garlic, minced","1 can (14.5 oz) diced tomatoes","1.5 cups chicken broth","1 tsp smoked paprika","1/2 tsp thyme","1/2 tsp salt","1/4 tsp cayenne pepper","Hot sauce for serving"],
        "ingredients_es": ["2 tazas de frijoles de ojo negro cocidos","1 taza de arroz de grano largo","4 rebanadas de tocino, picado","1 cebolla pequeña, picada","1 pimiento verde, picado","2 dientes de ajo, picados","1 lata (410g) de tomates picados","1.5 tazas de caldo de pollo","1 cucharadita de pimentón ahumado","1/2 cucharadita de tomillo","1/2 cucharadita de sal","1/4 cucharadita de cayena","Salsa picante para servir"],
        "instructions": ["Cook bacon in a large skillet over medium heat until crispy. Remove bacon, leaving drippings.","Add onion and bell pepper to drippings. Cook until softened, about 4 minutes. Add garlic and cook 1 minute.","Add rice and stir for 2 minutes until lightly toasted.","Add diced tomatoes, chicken broth, smoked paprika, thyme, salt, and cayenne. Bring to a boil.","Reduce heat to low, cover, and cook 18 minutes.","Stir in black-eyed peas and cooked bacon. Cover and cook 5 more minutes.","Fluff with a fork. Serve with hot sauce."],
        "instructions_es": ["Cocine el tocino en una sartén grande a fuego medio hasta que esté crujiente. Retire el tocino, dejando la grasa.","Agregue la cebolla y el pimiento a la grasa. Cocine hasta que estén suaves, unos 4 minutos. Agregue el ajo y cocine 1 minuto.","Agregue el arroz y revuelva por 2 minutos hasta que esté ligeramente tostado.","Agregue los tomates picados, el caldo de pollo, el pimentón ahumado, el tomillo, la sal y la cayena. Lleve a ebullición.","Reduzca el fuego a bajo, tape y cocine 18 minutos.","Incorpore los frijoles de ojo negro y el tocino cocido. Tape y cocine 5 minutos más.","Esponje con un tenedor. Sirva con salsa picante."],
        "notes": "Limpin' Susan is what you make when you want Hoppin' John but don't have time to soak beans overnight. Canned black-eyed peas work perfectly.",
        "notes_es": "Limpin' Susan es lo que se hace cuando se quiere Hoppin' John pero no hay tiempo para remojar los frijoles. Los frijoles de ojo negro enlatados funcionan perfectamente.",
        "category": "Main Dish", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Limpin' Susan — Quick Black-Eyed Peas and Rice",
        "pinterest_desc": "The quicker cousin of Hoppin' John. Rice, black-eyed peas, tomatoes, and bacon. A Gullah Geechee weekday staple."
    },
    {
        "slug": "deviled-crabs",
        "title": "Gullah Deviled Crab Recipe",
        "title_es": "Receta de Cangrejo Diabla Gullah",
        "description": "Crab meat stuffed back into the shell with seasoned breadcrumbs and baked golden. This Gullah deviled crab recipe is a Lowcountry appetizer tradition.",
        "description_es": "Carne de cangrejo rellena en la concha con pan rallado sazonado y horneada hasta dorar. Una tradición de aperitivo de las Lowcountry.",
        "keywords": "deviled crab recipe, Gullah deviled crab, Lowcountry deviled crab, stuffed crab, Charleston deviled crab, crab appetizer",
        "keywords_es": "receta de cangrejo diabla, cangrejo diabla Gullah, cangrejo diabla Lowcountry, cangrejo relleno",
        "prep_time": "PT20M", "cook_time": "PT20M", "total_time": "PT40M",
        "servings": 6, "calories": 280,
        "ingredients": ["1 lb fresh blue crab meat","6 crab shells (cleaned) or ramekins","2 tbsp butter","1/2 cup onion, finely diced","1/2 cup green bell pepper, finely diced","2 cloves garlic, minced","1 cup breadcrumbs (preferably stale)","1/4 cup mayonnaise","1 tbsp Dijon mustard","1 tbsp Worcestershire sauce","1 tsp Old Bay seasoning","1/2 tsp cayenne pepper","1 tbsp fresh parsley, chopped","1 tbsp lemon juice","Salt to taste","2 tbsp butter, melted (for topping)"],
        "ingredients_es": ["500g de carne de cangrejo azul fresco","6 conchas de cangrejo (limpias) o ramequines","2 cucharadas de mantequilla","1/2 taza de cebolla finamente picada","1/2 taza de pimiento verde finamente picado","2 dientes de ajo, picados","1 taza de pan rallado","1/4 taza de mayonesa","1 cucharada de mostaza Dijon","1 cucharada de salsa Worcestershire","1 cucharadita de condimento Old Bay","1/2 cucharadita de cayena","1 cucharada de perejil fresco picado","1 cucharada de jugo de limón","Sal al gusto","2 cucharadas de mantequilla derretida (para cubrir)"],
        "instructions": ["Preheat oven to 375°F. Pick through crab meat to remove any shell fragments.","Melt 2 tbsp butter in a skillet over medium heat. Cook onion and bell pepper until softened, about 4 minutes. Add garlic and cook 1 minute.","Remove from heat. In a large bowl, combine cooked vegetables, crab meat, 3/4 cup breadcrumbs, mayonnaise, mustard, Worcestershire, Old Bay, cayenne, parsley, and lemon juice. Mix gently.","Season with salt. Stuff mixture into crab shells or ramekins.","Mix remaining 1/4 cup breadcrumbs with 2 tbsp melted butter. Sprinkle over the tops.","Bake 18-20 minutes until golden brown and heated through. Serve with lemon wedges."],
        "instructions_es": ["Precaliente el horno a 190°C. Revise la carne de cangrejo para eliminar fragmentos de cáscara.","Derrita 2 cucharadas de mantequilla en una sartén a fuego medio. Cocine la cebolla y el pimiento hasta que estén suaves, unos 4 minutos. Agregue el ajo y cocine 1 minuto.","Retire del fuego. En un tazón grande, combine las verduras cocidas, la carne de cangrejo, 3/4 taza de pan rallado, mayonesa, mostaza, Worcestershire, Old Bay, cayena, perejil y jugo de limón. Mezcle suavemente.","Sazone con sal. Rellene las conchas de cangrejo o ramequines.","Mezcle el resto del pan rallado con 2 cucharadas de mantequilla derretida. Espolvoree sobre la parte superior.","Hornee 18-20 minutos hasta que estén dorados y calientes. Sirva con rodajas de limón."],
        "notes": "Fresh blue crab is traditional, but canned crab meat works. Serve as an appetizer or a light main course with a side salad.",
        "notes_es": "El cangrejo azul fresco es tradicional, pero la carne de cangrejo enlatada funciona. Sirva como aperitivo o plato principal ligero.",
        "category": "Appetizer", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Deviled Crab — Lowcountry Stuffed Crab Appetizer",
        "pinterest_desc": "Fresh crab meat stuffed back into the shell with seasoned breadcrumbs. A Gullah Geechee tradition."
    },
    {
        "slug": "buttermilk-cornbread",
        "title": "Gullah Buttermilk Cornbread Recipe",
        "title_es": "Receta de Pan de Maíz con Suero de Leche Gullah",
        "description": "Golden, moist, and perfectly crumbly. This Gullah buttermilk cornbread recipe is the essential side for every Lowcountry meal.",
        "description_es": "Dorado, húmedo y perfectamente desmenuzable. El acompañamiento esencial para cada comida de las Lowcountry.",
        "keywords": "buttermilk cornbread recipe, Gullah cornbread, Southern cornbread, Lowcountry cornbread, cast iron cornbread, skillet cornbread",
        "keywords_es": "receta de pan de maíz con suero de leche, pan de maíz Gullah, pan de maíz sureño, pan de maíz Lowcountry",
        "prep_time": "PT10M", "cook_time": "PT25M", "total_time": "PT35M",
        "servings": 8, "calories": 240,
        "ingredients": ["1.5 cups yellow cornmeal","1/2 cup all-purpose flour","1 tbsp sugar (or 2 tbsp for sweeter cornbread)","1 tsp salt","1 tsp baking powder","1/2 tsp baking soda","1.5 cups buttermilk","2 large eggs","1/4 cup bacon fat or vegetable oil","2 tbsp butter"],
        "ingredients_es": ["1.5 tazas de harina de maíz amarilla","1/2 taza de harina","1 cucharada de azúcar","1 cucharadita de sal","1 cucharadita de polvo de hornear","1/2 cucharadita de bicarbonato de sodio","1.5 tazas de suero de leche","2 huevos grandes","1/4 taza de grasa de tocino o aceite vegetal","2 cucharadas de mantequilla"],
        "instructions": ["Preheat oven to 425°F. Place a 10-inch cast iron skillet in the oven to heat.","In a large bowl, whisk together cornmeal, flour, sugar, salt, baking powder, and baking soda.","In a separate bowl, whisk together buttermilk, eggs, and bacon fat.","Pour wet ingredients into dry ingredients and stir until just combined. Do not overmix.","Carefully remove hot skillet from oven. Add 2 tbsp butter and swirl to melt.","Pour batter into the hot skillet. It should sizzle.","Bake 20-25 minutes until golden brown and a toothpick comes out clean.","Let cool 5 minutes in the skillet. Turn out onto a cutting board. Serve warm with butter."],
        "instructions_es": ["Precaliente el horno a 220°C. Coloque una sartén de hierro fundido de 10 pulgadas en el horno para calentar.","En un tazón grande, mezcle la harina de maíz, la harina, el azúcar, la sal, el polvo de hornear y el bicarbonato de sodio.","En un tazón aparte, bata el suero de leche, los huevos y la grasa de tocino.","Vierta los ingredientes húmedos sobre los secos y revuelva hasta que estén combinados. No mezcle demasiado.","Retire con cuidado la sartén caliente del horno. Agregue 2 cucharadas de mantequilla y gire para derretir.","Vierta la masa en la sartén caliente. Debe chisporrotear.","Hornee 20-25 minutos hasta que esté dorado y un palillo salga limpio.","Deje enfriar 5 minutos en la sartén. Voltee sobre una tabla de cortar. Sirva caliente con mantequilla."],
        "notes": "A hot cast iron skillet is the secret to perfect cornbread — it creates that crispy golden crust. Gullah cornbread is traditionally not very sweet.",
        "notes_es": "Una sartén de hierro fundido caliente es el secreto para un pan de maíz perfecto — crea esa corteza dorada crujiente.",
        "category": "Side Dish", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Buttermilk Cornbread — Cast Iron Skillet Perfection",
        "pinterest_desc": "Golden, moist, and perfectly crumbly. This Gullah buttermilk cornbread is the essential Lowcountry side."
    },
    {
        "slug": "pickled-shrimp",
        "title": "Gullah Pickled Shrimp Recipe",
        "title_es": "Receta de Camarones en Escabeche Gullah",
        "description": "Fresh shrimp marinated in vinegar, citrus, and Lowcountry spices. This Gullah pickled shrimp recipe is a classic Lowcountry appetizer that gets better with time.",
        "description_es": "Camarones frescos marinados en vinagre, cítricos y especias de las Lowcountry. Un aperitivo clásico que mejora con el tiempo.",
        "keywords": "pickled shrimp recipe, Gullah pickled shrimp, Lowcountry pickled shrimp, Charleston pickled shrimp, marinated shrimp",
        "keywords_es": "receta de camarones en escabeche, camarones en escabeche Gullah, camarones en escabeche Lowcountry",
        "prep_time": "PT15M", "cook_time": "PT5M", "total_time": "PT20M",
        "servings": 8, "calories": 200,
        "ingredients": ["2 lbs large shrimp, peeled and deveined","1 cup white vinegar","1/2 cup apple cider vinegar","1/2 cup olive oil","1/4 cup fresh lemon juice","1 large red onion, thinly sliced","4 cloves garlic, thinly sliced","2 bay leaves","1 tsp mustard seeds","1 tsp black peppercorns","1/2 tsp red pepper flakes","1 tsp salt","1/2 tsp sugar","1/4 cup fresh dill, chopped","1 lemon, thinly sliced"],
        "ingredients_es": ["1 kg de camarones grandes, pelados y desvenados","1 taza de vinagre blanco","1/2 taza de vinagre de sidra de manzana","1/2 taza de aceite de oliva","1/4 taza de jugo de limón fresco","1 cebolla roja grande, en rodajas finas","4 dientes de ajo, en rodajas finas","2 hojas de laurel","1 cucharadita de semillas de mostaza","1 cucharadita de granos de pimienta negra","1/2 cucharadita de hojuelas de pimiento rojo","1 cucharadita de sal","1/2 cucharadita de azúcar","1/4 taza de eneldo fresco picado","1 limón, en rodajas finas"],
        "instructions": ["Bring a large pot of salted water to a boil. Add shrimp and cook 2-3 minutes until pink. Drain and transfer to an ice bath to stop cooking.","In a bowl, whisk together white vinegar, apple cider vinegar, olive oil, and lemon juice.","Add red onion, garlic, bay leaves, mustard seeds, peppercorns, red pepper flakes, salt, and sugar. Stir to combine.","Drain cooled shrimp and add to the marinade. Add dill and lemon slices. Stir gently.","Transfer to a glass container with a lid. Refrigerate at least 8 hours or overnight.","Serve cold as an appetizer or on a bed of lettuce. Will keep in the refrigerator for up to 5 days."],
        "instructions_es": ["Lleve una olla grande de agua con sal a ebullición. Agregue los camarones y cocine 2-3 minutos hasta que estén rosados. Escurra y transfiera a un baño de hielo.","En un tazón, bata el vinagre blanco, el vinagre de sidra de manzana, el aceite de oliva y el jugo de limón.","Agregue la cebolla roja, el ajo, las hojas de laurel, las semillas de mostaza, los granos de pimienta, las hojuelas de pimiento rojo, la sal y el azúcar. Revuelva para combinar.","Escurra los camarones enfriados y agregue a la marinada. Agregue el eneldo y las rodajas de limón. Revuelva suavemente.","Transfiera a un recipiente de vidrio con tapa. Refrigere al menos 8 horas o toda la noche.","Sirva frío como aperitivo o sobre una cama de lechuga. Se conserva en el refrigerador hasta 5 días."],
        "notes": "The longer these marinate, the better they get. Make them a day ahead for the best flavor. Serve with crusty bread to soak up the marinade.",
        "notes_es": "Cuanto más tiempo marinen, mejor. Prepárelos el día anterior para obtener el mejor sabor. Sirva con pan crujiente.",
        "category": "Appetizer", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Pickled Shrimp — Classic Lowcountry Appetizer",
        "pinterest_desc": "Fresh shrimp marinated in vinegar, citrus, and spices. A Gullah Geechee appetizer that gets better with time."
    },
    # ── Batch 3: More Depth (10) ──
    {
        "slug": "she-crab-soup",
        "title": "Gullah She-Crab Soup Recipe",
        "title_es": "Receta de Sopa de Cangrejo Hembra Gullah",
        "description": "A creamy, rich soup made with blue crab roe and sherry. This Gullah she-crab soup recipe is the most elegant dish in Lowcountry cuisine.",
        "description_es": "Una sopa cremosa y rica hecha con huevas de cangrejo azul y jerez. El plato más elegante de la cocina de las Lowcountry.",
        "keywords": "she-crab soup recipe, Gullah she-crab soup, Lowcountry she-crab soup, Charleston she-crab soup, crab soup recipe",
        "keywords_es": "receta de sopa de cangrejo hembra, sopa de cangrejo hembra Gullah, sopa de cangrejo hembra Lowcountry",
        "prep_time": "PT10M", "cook_time": "PT25M", "total_time": "PT35M",
        "servings": 6, "calories": 340,
        "ingredients": ["1 lb fresh blue crab meat with roe (if available)","3 tbsp butter","1 small onion, finely diced","2 celery stalks, finely diced","3 tbsp all-purpose flour","3 cups whole milk","1 cup heavy cream","1 cup seafood or chicken broth","1/4 cup dry sherry","1 tsp Old Bay seasoning","1/2 tsp paprika","1/4 tsp cayenne pepper","1/2 tsp salt","1/4 tsp white pepper","2 tbsp fresh chives, chopped","Additional sherry for serving"],
        "ingredients_es": ["500g de carne de cangrejo azul fresco con huevas","3 cucharadas de mantequilla","1 cebolla pequeña, finamente picada","2 tallos de apio, finamente picados","3 cucharadas de harina","3 tazas de leche entera","1 taza de crema espesa","1 taza de caldo de mariscos o pollo","1/4 taza de jerez seco","1 cucharadita de condimento Old Bay","1/2 cucharadita de pimentón","1/4 cucharadita de cayena","1/2 cucharadita de sal","1/4 cucharadita de pimienta blanca","2 cucharadas de cebollino fresco picado","Jerez adicional para servir"],
        "instructions": ["Pick through crab meat to remove any shell fragments. Reserve crab roe separately if available.","Melt butter in a large saucepan over medium heat. Cook onion and celery until softened, about 5 minutes.","Whisk in flour and cook 2 minutes, stirring constantly.","Slowly whisk in milk, cream, and broth. Cook, stirring, until thickened, about 5 minutes.","Stir in sherry, Old Bay, paprika, cayenne, salt, and white pepper.","Add crab meat and roe (if using). Simmer 10 minutes, stirring occasionally. Do not boil.","Ladle into bowls. Garnish with chives and a splash of sherry."],
        "instructions_es": ["Revise la carne de cangrejo para eliminar fragmentos de cáscara. Reserve las huevas de cangrejo por separado.","Derrita la mantequilla en una cacerola grande a fuego medio. Cocine la cebolla y el apio hasta que estén suaves, unos 5 minutos.","Incorpore la harina y cocine 2 minutos, revolviendo constantemente.","Incorpore lentamente la leche, la crema y el caldo. Cocine, revolviendo, hasta que espese, unos 5 minutos.","Incorpore el jerez, el Old Bay, el pimentón, la cayena, la sal y la pimienta blanca.","Agregue la carne de cangrejo y las huevas. Cueza a fuego lento 10 minutos, revolviendo ocasionalmente. No hierva.","Sirva en tazones. Decore con cebollino y un chorrito de jerez."],
        "notes": "She-crab soup gets its name from the crab roe (eggs) which gives the soup its distinctive flavor and orange tint. If roe isn't available, the soup is still delicious.",
        "notes_es": "La sopa de cangrejo hembra recibe su nombre de las huevas de cangrejo que le dan su sabor distintivo y tono naranja.",
        "category": "Soup", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah She-Crab Soup — The Most Elegant Lowcountry Dish",
        "pinterest_desc": "Creamy blue crab soup with sherry and roe. The crown jewel of Gullah Geechee cuisine."
    },
    {
        "slug": "red-beans-rice",
        "title": "Gullah Red Beans and Rice Recipe",
        "title_es": "Receta de Frijoles Rojos con Arroz Gullah",
        "description": "Slow-simmered red beans with smoked sausage and aromatic vegetables over rice. This Gullah red beans and rice recipe is Monday comfort food.",
        "description_es": "Frijoles rojos cocidos lentamente con salchicha ahumada y verduras aromáticas sobre arroz. La comida reconfortante de los lunes.",
        "keywords": "red beans and rice recipe, Gullah red beans, Lowcountry red beans, Southern red beans, red beans and sausage",
        "keywords_es": "receta de frijoles rojos con arroz, frijoles rojos Gullah, frijoles rojos Lowcountry, frijoles rojos sureños",
        "prep_time": "PT15M", "cook_time": "PT2H", "total_time": "PT2H15M",
        "servings": 8, "calories": 400,
        "ingredients": ["1 lb dried red kidney beans, soaked overnight","1 lb smoked sausage, sliced","1 large onion, diced","1 green bell pepper, diced","3 celery stalks, diced","4 cloves garlic, minced","6 cups chicken broth","2 bay leaves","1 tsp thyme","1 tsp smoked paprika","1/2 tsp cayenne pepper","1 tsp salt","1/2 tsp black pepper","2 tbsp bacon fat or vegetable oil","Cooked rice for serving","Green onions for garnish"],
        "ingredients_es": ["500g de frijoles rojos secos, remojados toda la noche","500g de salchicha ahumada, en rodajas","1 cebolla grande, picada","1 pimiento verde, picado","3 tallos de apio, picados","4 dientes de ajo, picados","6 tazas de caldo de pollo","2 hojas de laurel","1 cucharadita de tomillo","1 cucharadita de pimentón ahumado","1/2 cucharadita de cayena","1 cucharadita de sal","1/2 cucharadita de pimienta negra","2 cucharadas de grasa de tocino o aceite vegetal","Arroz cocido para servir","Cebollas verdes para decorar"],
        "instructions": ["Drain soaked beans and rinse. Set aside.","Heat bacon fat in a large pot over medium heat. Cook sausage until browned, about 5 minutes. Remove and set aside.","Add onion, bell pepper, and celery to the pot. Cook until softened, about 6 minutes. Add garlic and cook 1 minute.","Add beans, chicken broth, bay leaves, thyme, smoked paprika, cayenne, salt, and pepper. Bring to a boil.","Reduce heat and simmer 1.5 hours, stirring occasionally, until beans are tender and creamy.","Return sausage to the pot. Simmer 15 more minutes.","Remove bay leaves. Serve over rice. Garnish with green onions."],
        "instructions_es": ["Escurra los frijoles remojados y enjuague. Reserve.","Caliente la grasa de tocino en una olla grande a fuego medio. Cocine la salchicha hasta que esté dorada, unos 5 minutos. Retire y reserve.","Agregue la cebolla, el pimiento y el apio a la olla. Cocine hasta que estén suaves, unos 6 minutos. Agregue el ajo y cocine 1 minuto.","Agregue los frijoles, el caldo de pollo, las hojas de laurel, el tomillo, el pimentón ahumado, la cayena, la sal y la pimienta. Lleve a ebullición.","Reduzca el fuego y cocine a fuego lento 1.5 horas, revolviendo ocasionalmente, hasta que los frijoles estén tiernos y cremosos.","Vuelva a poner la salchicha en la olla. Cueza 15 minutos más.","Retire las hojas de laurel. Sirva sobre arroz. Decore con cebollas verdes."],
        "notes": "Mash some of the beans against the side of the pot to create a creamier texture. Red beans get better the next day.",
        "notes_es": "Aplaste algunos frijoles contra el costado de la olla para crear una textura más cremosa. Los frijoles rojos mejoran al día siguiente.",
        "category": "Main Dish", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Red Beans and Rice — Slow-Simmered Lowcountry Comfort",
        "pinterest_desc": "Red kidney beans slow-simmered with smoked sausage. A Gullah Geechee Monday tradition."
    },
    {
        "slug": "country-captain",
        "title": "Gullah Country Captain Chicken Recipe",
        "title_es": "Receta de Country Captain de Pollo Gullah",
        "description": "A curried chicken stew with tomatoes, peppers, and currants — served over rice. This Gullah country captain recipe has roots in the spice trade through Charleston port.",
        "description_es": "Un estofado de pollo al curry con tomates, pimientos y pasas — servido sobre arroz. Con raíces en el comercio de especias a través del puerto de Charleston.",
        "keywords": "country captain recipe, Gullah country captain, Charleston country captain, curried chicken stew, Lowcountry chicken recipe",
        "keywords_es": "receta de country captain, country captain Gullah, country captain Charleston, estofado de pollo al curry",
        "prep_time": "PT15M", "cook_time": "PT45M", "total_time": "PT1H",
        "servings": 6, "calories": 440,
        "ingredients": ["3 lbs chicken pieces (thighs and legs)","2 tbsp vegetable oil","1 large onion, diced","1 green bell pepper, diced","3 cloves garlic, minced","2 tbsp curry powder","1 can (14.5 oz) diced tomatoes","1 cup chicken broth","1/4 cup currants or raisins","1 tbsp apple cider vinegar","1 tsp thyme","1/2 tsp cayenne pepper","1 tsp salt","1/2 tsp black pepper","1/4 cup sliced almonds, toasted","Cooked rice for serving","Fresh parsley for garnish"],
        "ingredients_es": ["1.5 kg de piezas de pollo (muslos y piernas)","2 cucharadas de aceite vegetal","1 cebolla grande, picada","1 pimiento verde, picado","3 dientes de ajo, picados","2 cucharadas de curry en polvo","1 lata (410g) de tomates picados","1 taza de caldo de pollo","1/4 taza de pasas","1 cucharada de vinagre de sidra de manzana","1 cucharadita de tomillo","1/2 cucharadita de cayena","1 cucharadita de sal","1/2 cucharadita de pimienta negra","1/4 taza de almendras fileteadas, tostadas","Arroz cocido para servir","Perejil fresco para decorar"],
        "instructions": ["Season chicken with salt and pepper. Heat oil in a large Dutch oven over medium-high heat.","Brown chicken in batches, about 4 minutes per side. Remove and set aside.","Add onion and bell pepper to the pot. Cook until softened, about 5 minutes. Add garlic and cook 1 minute.","Stir in curry powder and cook 1 minute until fragrant.","Add diced tomatoes, chicken broth, currants, vinegar, thyme, cayenne, salt, and pepper. Stir to combine.","Return chicken to the pot, nestling into the sauce. Bring to a boil.","Reduce heat, cover, and simmer 30-35 minutes until chicken is cooked through.","Serve over rice. Garnish with toasted almonds and parsley."],
        "instructions_es": ["Sazone el pollo con sal y pimienta. Caliente el aceite en una olla grande a fuego medio-alto.","Dore el pollo en tandas, unos 4 minutos por lado. Retire y reserve.","Agregue la cebolla y el pimiento a la olla. Cocine hasta que estén suaves, unos 5 minutos. Agregue el ajo y cocine 1 minuto.","Incorpore el curry en polvo y cocine 1 minuto hasta que esté fragante.","Agregue los tomates picados, el caldo de pollo, las pasas, el vinagre, el tomillo, la cayena, la sal y la pimienta. Revuelva para combinar.","Vuelva a poner el pollo en la olla. Lleve a ebullición.","Reduzca el fuego, tape y cocine a fuego lento 30-35 minutos hasta que el pollo esté cocido.","Sirva sobre arroz. Decore con almendras tostadas y perejil."],
        "notes": "Country Captain is a classic Charleston dish that dates back to the 19th century spice trade. The curry powder and currants reflect the global influences that came through the port.",
        "notes_es": "El Country Captain es un plato clásico de Charleston que se remonta al comercio de especias del siglo XIX.",
        "category": "Main Dish", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Country Captain Chicken — Charleston's Curried Chicken Stew",
        "pinterest_desc": "Curried chicken stew with tomatoes, peppers, and currants. A historic Gullah Geechee dish from Charleston."
    },
    {
        "slug": "okra-and-tomatoes",
        "title": "Gullah Okra and Tomatoes Recipe",
        "title_es": "Receta de Okra con Tomates Gullah",
        "description": "A simple, perfect side dish of okra simmered with tomatoes, onions, and bacon. This Gullah okra and tomatoes recipe is a taste of West Africa in the Lowcountry.",
        "description_es": "Un acompañamiento simple y perfecto de okra cocinada con tomates, cebollas y tocino. Un sabor de África Occidental en las Lowcountry.",
        "keywords": "okra and tomatoes recipe, Gullah okra and tomatoes, Southern okra, Lowcountry okra, stewed okra and tomatoes",
        "keywords_es": "receta de okra con tomates, okra con tomates Gullah, okra sureña, okra Lowcountry",
        "prep_time": "PT10M", "cook_time": "PT20M", "total_time": "PT30M",
        "servings": 4, "calories": 150,
        "ingredients": ["1 lb fresh okra, sliced into 1/2-inch rounds","4 slices bacon, chopped","1 small onion, diced","2 cloves garlic, minced","1 can (14.5 oz) diced tomatoes","1/2 tsp salt","1/4 tsp black pepper","1/4 tsp red pepper flakes","1 tbsp apple cider vinegar","Fresh parsley for garnish"],
        "ingredients_es": ["500g de okra fresca, en rodajas de 1 cm","4 rebanadas de tocino, picado","1 cebolla pequeña, picada","2 dientes de ajo, picados","1 lata (410g) de tomates picados","1/2 cucharadita de sal","1/4 cucharadita de pimienta negra","1/4 cucharadita de hojuelas de pimiento rojo","1 cucharada de vinagre de sidra de manzana","Perejil fresco para decorar"],
        "instructions": ["Cook bacon in a large skillet over medium heat until crispy. Remove bacon, leaving drippings.","Add onion to drippings and cook until softened, about 4 minutes. Add garlic and cook 1 minute.","Add okra and cook 5 minutes, stirring occasionally, until it starts to lose its slime.","Add diced tomatoes, salt, black pepper, and red pepper flakes. Stir to combine.","Reduce heat to low, cover, and simmer 10 minutes until okra is tender.","Stir in vinegar and return bacon to the skillet. Cook 2 more minutes.","Garnish with parsley. Serve as a side dish."],
        "instructions_es": ["Cocine el tocino en una sartén grande a fuego medio hasta que esté crujiente. Retire el tocino, dejando la grasa.","Agregue la cebolla a la grasa y cocine hasta que esté suave, unos 4 minutos. Agregue el ajo y cocine 1 minuto.","Agregue la okra y cocine 5 minutos, revolviendo ocasionalmente, hasta que comience a perder su baba.","Agregue los tomates picados, la sal, la pimienta negra y las hojuelas de pimiento rojo. Revuelva para combinar.","Reduzca el fuego a bajo, tape y cocine a fuego lento 10 minutos hasta que la okra esté tierna.","Incorpore el vinagre y vuelva a poner el tocino en la sartén. Cocine 2 minutos más.","Decore con perejil. Sirva como acompañamiento."],
        "notes": "The vinegar helps reduce the okra's sliminess. This dish is perfect alongside fried fish or shrimp and grits.",
        "notes_es": "El vinagre ayuda a reducir la baba de la okra. Este plato es perfecto junto con pescado frito o camarones con sémola.",
        "category": "Side Dish", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Okra and Tomatoes — West African Roots in the Lowcountry",
        "pinterest_desc": "Okra simmered with tomatoes, onions, and bacon. A simple Gullah Geechee side dish with West African roots."
    },
    {
        "slug": "rice-pudding",
        "title": "Gullah Rice Pudding Recipe",
        "title_es": "Receta de Arroz con Leche Gullah",
        "description": "Creamy, cinnamon-spiced rice pudding made with leftover rice. This Gullah rice pudding recipe turns yesterday's rice into today's comfort dessert.",
        "description_es": "Arroz con leche cremoso con canela hecho con arroz sobrante. Convierte el arroz de ayer en el postre reconfortante de hoy.",
        "keywords": "rice pudding recipe, Gullah rice pudding, Southern rice pudding, Lowcountry dessert, leftover rice recipe, cinnamon rice pudding",
        "keywords_es": "receta de arroz con leche, arroz con leche Gullah, arroz con leche sureño, postre Lowcountry, receta con arroz sobrante",
        "prep_time": "PT5M", "cook_time": "PT30M", "total_time": "PT35M",
        "servings": 6, "calories": 310,
        "ingredients": ["3 cups cooked white rice (day-old is fine)","3 cups whole milk","1 cup heavy cream","1/2 cup sugar","1/2 cup brown sugar","2 large eggs, beaten","1 tbsp butter","1 tsp vanilla extract","1 tsp cinnamon","1/2 tsp nutmeg","1/4 tsp salt","1/2 cup raisins (optional)","Ground cinnamon for topping"],
        "ingredients_es": ["3 tazas de arroz blanco cocido","3 tazas de leche entera","1 taza de crema espesa","1/2 taza de azúcar","1/2 taza de azúcar moreno","2 huevos grandes, batidos","1 cucharada de mantequilla","1 cucharadita de extracto de vainilla","1 cucharadita de canela","1/2 cucharadita de nuez moscada","1/4 cucharadita de sal","1/2 taza de pasas (opcional)","Canela molida para cubrir"],
        "instructions": ["In a large saucepan, combine milk, cream, sugar, and brown sugar. Heat over medium heat until warm, stirring occasionally.","Stir in cooked rice, cinnamon, nutmeg, and salt. Bring to a gentle simmer.","Reduce heat to low and cook 15 minutes, stirring frequently, until thickened.","Temper the eggs: Slowly whisk 1 cup of the hot rice mixture into the beaten eggs, then pour the egg mixture back into the saucepan.","Cook 5 more minutes, stirring constantly, until thickened. Do not boil.","Remove from heat. Stir in butter, vanilla, and raisins (if using).","Pour into serving bowls. Sprinkle with cinnamon. Serve warm or chilled."],
        "instructions_es": ["En una cacerola grande, combine la leche, la crema, el azúcar y el azúcar moreno. Caliente a fuego medio hasta que esté tibio.","Incorpore el arroz cocido, la canela, la nuez moscada y la sal. Lleve a fuego lento.","Reduzca el fuego a bajo y cocine 15 minutos, revolviendo con frecuencia, hasta que espese.","Temple los huevos: Incorpore lentamente 1 taza de la mezcla caliente de arroz en los huevos batidos, luego vierta la mezcla de huevo nuevamente en la cacerola.","Cocine 5 minutos más, revolviendo constantemente, hasta que espese. No hierva.","Retire del fuego. Incorpore la mantequilla, la vainilla y las pasas.","Sirva en tazones. Espolvoree con canela. Sirva caliente o frío."],
        "notes": "This is the perfect use for leftover rice from red rice or perloo. Gullah grandmothers never waste rice — it all becomes pudding.",
        "notes_es": "Este es el uso perfecto para el arroz sobrante del arroz rojo o perloo. Las abuelas Gullah nunca desperdician arroz.",
        "category": "Dessert", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Rice Pudding — Creamy Cinnamon Comfort Dessert",
        "pinterest_desc": "Creamy cinnamon-spiced rice pudding made with leftover rice. A Gullah Geechee comfort dessert."
    },
    {
        "slug": "boiled-peanuts",
        "title": "Gullah Boiled Peanuts Recipe",
        "title_es": "Receta de Maní Hervido Gullah",
        "description": "Soft, salty, Southern boiled peanuts — a Gullah Geechee roadside tradition. This boiled peanuts recipe is the ultimate Lowcountry snack.",
        "description_es": "Maní hervido suave y salado — una tradición Gullah Geechee de carretera. El bocadillo definitivo de las Lowcountry.",
        "keywords": "boiled peanuts recipe, Gullah boiled peanuts, Southern boiled peanuts, Lowcountry snack, green peanuts, roadside peanuts",
        "keywords_es": "receta de maní hervido, maní hervido Gullah, maní hervido sureño, bocadillo Lowcountry",
        "prep_time": "PT5M", "cook_time": "PT3H", "total_time": "PT3H5M",
        "servings": 12, "calories": 180,
        "ingredients": ["2 lbs raw green peanuts (uncooked, in shell)","1/2 cup salt","8 cups water","2 tbsp Cajun seasoning (optional for spicy)","4 cloves garlic, smashed","2 bay leaves","1 tbsp hot sauce (optional)"],
        "ingredients_es": ["1 kg de maní verde crudo (sin cocinar, con cáscara)","1/2 taza de sal","8 tazas de agua","2 cucharadas de condimento Cajún (opcional para picante)","4 dientes de ajo, machacados","2 hojas de laurel","1 cucharada de salsa picante (opcional)"],
        "instructions": ["Rinse peanuts thoroughly in cold water to remove dirt. Discard any that are floating or have broken shells.","In a large stockpot, combine water, salt, Cajun seasoning (if using), garlic, bay leaves, and hot sauce. Stir to dissolve salt.","Add peanuts to the pot. They should be fully submerged — add more water if needed.","Bring to a rolling boil over high heat.","Reduce heat to medium-low, cover, and simmer for 2-3 hours. Check texture after 2 hours.","Peanuts are done when they are soft and tender, like a cooked bean. Not crunchy.","Taste and add more salt if needed. Let peanuts soak in the brine for 30 minutes off heat.","Drain and serve warm or at room temperature. Store leftovers in the brine in the refrigerator."],
        "instructions_es": ["Enjuague los maníes thoroughly en agua fría. Deseche los que floten o tengan cáscaras rotas.","En una olla grande, combine el agua, la sal, el condimento Cajún, el ajo, las hojas de laurel y la salsa picante. Revuelva para disolver la sal.","Agregue los maníes a la olla. Deben estar completamente sumergidos.","Lleve a ebullición a fuego alto.","Reduzca el fuego a medio-bajo, tape y cocine a fuego lento durante 2-3 horas.","Los maníes están listos cuando están suaves y tiernos.","Pruebe y agregue más sal si es necesario. Deje los maníes en remojo en la salmuera durante 30 minutos.","Escurra y sirva caliente o a temperatura ambiente."],
        "notes": "Green peanuts are essential — raw dried peanuts won't work. Look for them at roadside stands in the Lowcountry from June to September.",
        "notes_es": "Los maníes verdes son esenciales — los maníes secos crudos no funcionan. Búsquelos en los puestos de carretera en las Lowcountry.",
        "category": "Snack", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Boiled Peanuts — Soft, Salty Lowcountry Roadside Snack",
        "pinterest_desc": "Soft, salty Southern boiled peanuts. A Gullah Geechee roadside tradition you can make at home."
    },
    {
        "slug": "sweetgrass-lemonade",
        "title": "Gullah Sweetgrass Lemonade Recipe",
        "title_es": "Receta de Limonada de Sweetgrass Gullah",
        "description": "Refreshing lemonade with a hint of sweetgrass and mint. This Gullah sweetgrass lemonade recipe is the taste of a Lowcountry summer afternoon.",
        "description_es": "Limonada refrescante con un toque de sweetgrass y menta. El sabor de una tarde de verano en las Lowcountry.",
        "keywords": "sweetgrass lemonade, Gullah lemonade, Lowcountry lemonade, sweetgrass recipe, Charleston lemonade, herbal lemonade",
        "keywords_es": "limonada de sweetgrass, limonada Gullah, limonada Lowcountry, receta de sweetgrass, limonada de hierbas",
        "prep_time": "PT10M", "cook_time": "PT10M", "total_time": "PT20M",
        "servings": 8, "calories": 120,
        "ingredients": ["6 cups water","1 cup sugar","1 cup fresh lemon juice (about 6-8 lemons)","1/4 cup fresh mint leaves, packed","2 tbsp dried sweetgrass or 1/4 cup fresh sweetgrass (if available)","1 lemon, thinly sliced for garnish","Ice for serving","Mint sprigs for garnish"],
        "ingredients_es": ["6 tazas de agua","1 taza de azúcar","1 taza de jugo de limón fresco","1/4 taza de hojas de menta fresca","2 cucharadas de sweetgrass seco","1 limón, en rodajas finas para decorar","Hielo para servir","Ramas de menta para decorar"],
        "instructions": ["In a small saucepan, combine 2 cups water and sugar. Bring to a boil, stirring until sugar dissolves. Remove from heat.","Add mint leaves and sweetgrass to the simple syrup. Let steep for 10 minutes.","Strain the syrup through a fine-mesh strainer into a pitcher. Discard solids.","Add remaining 4 cups water and fresh lemon juice. Stir to combine.","Refrigerate until cold, at least 2 hours.","Serve over ice. Garnish with lemon slices and mint sprigs."],
        "instructions_es": ["En una cacerola pequeña, combine 2 tazas de agua y azúcar. Lleve a ebullición, revolviendo hasta que el azúcar se disuelva. Retire del fuego.","Agregue las hojas de menta y el sweetgrass al jarabe simple. Deje reposar durante 10 minutos.","Cuele el jarabe a través de un colador de malla fina en una jarra. Deseche los sólidos.","Agregue las 4 tazas de agua restantes y el jugo de limón fresco. Revuelva para combinar.","Refrigere hasta que esté frío, al menos 2 horas.","Sirva sobre hielo. Decore con rodajas de limón y ramas de menta."],
        "notes": "Sweetgrass (Hierochloe odorata) is the same grass used in traditional Gullah sweetgrass basket weaving. It has a sweet, vanilla-like aroma. If unavailable, the mint alone makes a delicious lemonade.",
        "notes_es": "El sweetgrass es la misma hierba utilizada en la cestería tradicional Gullah. Tiene un aroma dulce parecido a la vainilla.",
        "category": "Beverage", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Sweetgrass Lemonade — Lowcountry Summer Refreshment",
        "pinterest_desc": "Refreshing lemonade with sweetgrass and mint. A taste of a Gullah Geechee Lowcountry summer afternoon."
    },
    {
        "slug": "seafood-casserole",
        "title": "Gullah Seafood Casserole Recipe",
        "title_es": "Receta de Cazuela de Mariscos Gullah",
        "description": "A creamy baked casserole with shrimp, crab, rice, and Lowcountry seasonings. This Gullah seafood casserole recipe is the perfect potluck dish.",
        "description_es": "Una cazuela horneada cremosa con camarones, cangrejo, arroz y condimentos de las Lowcountry. El plato perfecto para llevar a una comida compartida.",
        "keywords": "seafood casserole recipe, Gullah seafood casserole, Lowcountry casserole, shrimp and crab casserole, Southern seafood bake",
        "keywords_es": "receta de cazuela de mariscos, cazuela de mariscos Gullah, cazuela Lowcountry, cazuela de camarones y cangrejo",
        "prep_time": "PT15M", "cook_time": "PT30M", "total_time": "PT45M",
        "servings": 8, "calories": 420,
        "ingredients": ["1 lb shrimp, peeled and deveined","1/2 lb crab meat","2 cups cooked rice","1 can (10.5 oz) cream of mushroom soup","1/2 cup mayonnaise","1/2 cup sour cream","1 cup sharp cheddar cheese, shredded","1/2 cup onion, finely diced","1/2 cup green bell pepper, finely diced","2 cloves garlic, minced","1 tsp Old Bay seasoning","1/2 tsp cayenne pepper","1/2 tsp salt","1/4 tsp black pepper","1/2 cup breadcrumbs","2 tbsp butter, melted","Fresh parsley for garnish"],
        "ingredients_es": ["500g de camarones, pelados y desvenados","250g de carne de cangrejo","2 tazas de arroz cocido","1 lata (295ml) de crema de champiñones","1/2 taza de mayonesa","1/2 taza de crema agria","1 taza de queso cheddar rallado","1/2 taza de cebolla finamente picada","1/2 taza de pimiento verde finamente picado","2 dientes de ajo, picados","1 cucharadita de condimento Old Bay","1/2 cucharadita de cayena","1/2 cucharadita de sal","1/4 cucharadita de pimienta negra","1/2 taza de pan rallado","2 cucharadas de mantequilla derretida","Perejil fresco para decorar"],
        "instructions": ["Preheat oven to 350°F. Grease a 9x13 baking dish.","In a large bowl, combine cream of mushroom soup, mayonnaise, sour cream, 1/2 cup cheddar cheese, onion, bell pepper, garlic, Old Bay, cayenne, salt, and pepper.","Fold in shrimp, crab meat, and cooked rice until well combined.","Transfer to prepared baking dish. Sprinkle remaining 1/2 cup cheddar cheese on top.","In a small bowl, combine breadcrumbs with melted butter. Sprinkle over cheese.","Bake 25-30 minutes until bubbly and golden brown on top.","Let rest 5 minutes. Garnish with parsley and serve."],
        "instructions_es": ["Precaliente el horno a 175°C. Engrase un molde para hornear de 9x13.","En un tazón grande, combine la crema de champiñones, la mayonesa, la crema agria, 1/2 taza de queso cheddar, la cebolla, el pimiento, el ajo, el Old Bay, la cayena, la sal y la pimienta.","Incorpore los camarones, la carne de cangrejo y el arroz cocido hasta que estén bien combinados.","Transfiera al molde preparado. Espolvoree el resto del queso cheddar encima.","En un tazón pequeño, combine el pan rallado con la mantequilla derretida. Espolvoree sobre el queso.","Hornee 25-30 minutos hasta que esté burbujeante y dorado.","Deje reposar 5 minutos. Decore con perejil y sirva."],
        "notes": "This is a classic Gullah Geechee church potluck dish. It's forgiving — you can add more shrimp, less crab, or swap in whatever seafood you have.",
        "notes_es": "Este es un plato clásico de las comidas compartidas de la iglesia Gullah Geechee. Es indulgente — puede agregar más camarones o cambiar el marisco.",
        "category": "Main Dish", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Seafood Casserole — Creamy Lowcountry Potluck Dish",
        "pinterest_desc": "Creamy baked casserole with shrimp, crab, and rice. The perfect Gullah Geechee potluck dish."
    },
    {
        "slug": "benne-chicken",
        "title": "Gullah Benne Crusted Chicken Recipe",
        "title_es": "Receta de Pollo con Costra de Benne Gullah",
        "description": "Chicken breasts coated in toasted benne seeds and baked until golden. This Gullah benne crusted chicken recipe is a modern take on a traditional ingredient.",
        "description_es": "Pechugas de pollo cubiertas con semillas de benne tostadas y horneadas hasta dorar. Una versión moderna de un ingrediente tradicional.",
        "keywords": "benne chicken recipe, Gullah benne chicken, sesame crusted chicken, Lowcountry chicken recipe, benne seed chicken",
        "keywords_es": "receta de pollo con benne, pollo con benne Gullah, pollo con costra de ajonjolí, receta de pollo Lowcountry",
        "prep_time": "PT10M", "cook_time": "PT25M", "total_time": "PT35M",
        "servings": 4, "calories": 380,
        "ingredients": ["4 boneless skinless chicken breasts","1/2 cup toasted benne seeds (sesame seeds)","1/2 cup breadcrumbs","1/4 cup grated Parmesan cheese","1 tsp garlic powder","1 tsp smoked paprika","1/2 tsp salt","1/4 tsp black pepper","1/4 cup all-purpose flour","2 large eggs, beaten","2 tbsp olive oil","Lemon wedges for serving"],
        "ingredients_es": ["4 pechugas de pollo sin hueso ni piel","1/2 taza de semillas de benne tostadas","1/2 taza de pan rallado","1/4 taza de queso Parmesano rallado","1 cucharadita de ajo en polvo","1 cucharadita de pimentón ahumado","1/2 cucharadita de sal","1/4 cucharadita de pimienta negra","1/4 taza de harina","2 huevos grandes, batidos","2 cucharadas de aceite de oliva","Rodajas de limón para servir"],
        "instructions": ["Preheat oven to 400°F. Line a baking sheet with parchment paper.","Pound chicken breasts to even thickness (about 1/2 inch). Season with salt and pepper.","In a shallow dish, combine benne seeds, breadcrumbs, Parmesan, garlic powder, and smoked paprika.","Set up a breading station: flour in one dish, beaten eggs in another, benne mixture in a third.","Dredge each chicken breast in flour, dip in egg, then press into benne mixture, coating both sides.","Place on prepared baking sheet. Drizzle with olive oil.","Bake 20-25 minutes until golden and chicken reaches 165°F internal temperature.","Serve with lemon wedges."],
        "instructions_es": ["Precaliente el horno a 200°C. Cubra una bandeja para hornear con papel pergamino.","Aplane las pechugas de pollo a un grosor uniforme. Sazone con sal y pimienta.","En un plato poco profundo, combine las semillas de benne, el pan rallado, el Parmesano, el ajo en polvo y el pimentón ahumado.","Prepare una estación de empanizado: harina en un plato, huevos batidos en otro, mezcla de benne en un tercero.","Pase cada pechuga de pollo por harina, luego por huevo, luego presione en la mezcla de benne.","Coloque en la bandeja preparada. Rocíe con aceite de oliva.","Hornee 20-25 minutos hasta que esté dorado y el pollo alcance 74°C.","Sirva con rodajas de limón."],
        "notes": "Toasting the benne seeds before coating brings out their nutty flavor. This dish is a great way to use benne seeds beyond cookies.",
        "notes_es": "Tostar las semillas de benne antes de empanizar resalta su sabor a nuez. Una excelente manera de usar las semillas de benne más allá de las galletas.",
        "category": "Main Dish", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Benne Crusted Chicken — Toasted Sesame Perfection",
        "pinterest_desc": "Chicken breasts coated in toasted benne seeds and baked golden. A modern Gullah Geechee take on a traditional ingredient."
    },
    {
        "slug": "gullah-tea-cakes",
        "title": "Gullah Tea Cakes Recipe",
        "title_es": "Receta de Pastelitos de Té Gullah",
        "description": "Soft, buttery, lightly sweetened cookies that are a Gullah Geechee tradition. These tea cakes are the perfect accompaniment to a glass of sweet tea.",
        "description_es": "Galletas suaves, mantecosas y ligeramente endulzadas que son una tradición Gullah Geechee. El acompañamiento perfecto para un vaso de té dulce.",
        "keywords": "tea cakes recipe, Gullah tea cakes, Southern tea cakes, old fashioned tea cakes, Gullah cookies, sweet tea cookies",
        "keywords_es": "receta de pastelitos de té, pastelitos de té Gullah, pastelitos de té sureños, galletas Gullah, galletas de té dulce",
        "prep_time": "PT15M", "cook_time": "PT12M", "total_time": "PT27M",
        "servings": 24, "calories": 140,
        "ingredients": ["1 cup unsalted butter, softened","1.5 cups sugar","2 large eggs","1 tsp vanilla extract","1 tsp lemon extract","3 cups all-purpose flour","1 tsp baking powder","1/2 tsp baking soda","1/2 tsp salt","1/2 cup buttermilk","Nutmeg for sprinkling"],
        "ingredients_es": ["1 taza de mantequilla sin sal, ablandada","1.5 tazas de azúcar","2 huevos grandes","1 cucharadita de extracto de vainilla","1 cucharadita de extracto de limón","3 tazas de harina","1 cucharadita de polvo de hornear","1/2 cucharadita de bicarbonato de sodio","1/2 cucharadita de sal","1/2 taza de suero de leche","Nuez moscada para espolvorear"],
        "instructions": ["Preheat oven to 350°F. Line baking sheets with parchment paper.","Cream butter and sugar together until light and fluffy, about 4 minutes.","Beat in eggs one at a time. Add vanilla and lemon extract.","In a separate bowl, whisk together flour, baking powder, baking soda, and salt.","Gradually add dry ingredients to wet mixture, alternating with buttermilk. Mix until just combined.","Drop rounded tablespoons of dough onto prepared baking sheets, spacing 2 inches apart.","Sprinkle lightly with nutmeg.","Bake 10-12 minutes until edges are lightly golden. Centers should still be soft.","Cool on baking sheet for 5 minutes, then transfer to wire rack."],
        "instructions_es": ["Precaliente el horno a 175°C. Cubra las bandejas para hornear con papel pergamino.","Bata la mantequilla y el azúcar hasta que estén suaves y esponjosos, unos 4 minutos.","Incorpore los huevos uno a la vez. Agregue los extractos de vainilla y limón.","En un tazón aparte, mezcle la harina, el polvo de hornear, el bicarbonato de sodio y la sal.","Agregue gradualmente los ingredientes secos a la mezcla húmeda, alternando con el suero de leche. Mezcle hasta que estén combinados.","Coloque cucharadas redondeadas de masa en las bandejas preparadas.","Espolvoree ligeramente con nuez moscada.","Hornee 10-12 minutos hasta que los bordes estén ligeramente dorados.","Enfríe en la bandeja 5 minutos, luego transfiera a una rejilla."],
        "notes": "Gullah tea cakes are softer and more cake-like than regular cookies. They're a staple at Gullah Geechee family gatherings and funerals.",
        "notes_es": "Los pastelitos de té Gullah son más suaves y parecidos a un pastel que las galletas normales. Son un básico en las reuniones familiares Gullah Geechee.",
        "category": "Dessert", "cuisine": "Gullah Geechee",
        "pinterest_title": "Gullah Tea Cakes — Soft, Buttery Lowcountry Tradition",
        "pinterest_desc": "Soft, buttery, lightly sweetened cookies. A Gullah Geechee tradition perfect with sweet tea."
    }
]

# ─── State Management ─────────────────────────────────────────────────────────

def load_state():
    """Load which recipes have been generated."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"generated": [], "total_batches": 0, "last_run": None}

def save_state(state):
    """Save state after generation."""
    state["last_run"] = str(date.today())
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# ─── HTML Generation ──────────────────────────────────────────────────────────

def generate_recipe_html(recipe, lang="en"):
    """Generate a fully SEO-optimized recipe page."""
    is_es = lang == "es"
    
    title = recipe["title_es"] if is_es else recipe["title"]
    desc = recipe["description_es"] if is_es else recipe["description"]
    keywords = recipe["keywords_es"] if is_es else recipe["keywords"]
    ingredients = recipe["ingredients_es"] if is_es else recipe["ingredients"]
    instructions = recipe["instructions_es"] if is_es else recipe["instructions"]
    notes = recipe["notes_es"] if is_es else recipe["notes"]
    
    ing_html = "\n".join(f'      <li class="ingredient">{i}</li>' for i in ingredients)
    inst_html = "\n".join(f'      <li class="step">{s}</li>' for s in instructions)
    
    schema = {
        "@context": "https://schema.org", "@type": "Recipe",
        "name": title, "description": desc,
        "author": {"@type": "Organization", "name": "Gullah Geechee Biz"},
        "datePublished": str(date.today()),
        "image": f"https://gullahgeecheebiz.com/images/recipes/{recipe['slug']}.jpg",
        "prepTime": recipe["prep_time"], "cookTime": recipe["cook_time"],
        "totalTime": recipe["total_time"],
        "recipeYield": str(recipe["servings"]) + " servings",
        "recipeCategory": recipe["category"], "recipeCuisine": recipe["cuisine"],
        "nutrition": {"@type": "NutritionInformation", "calories": str(recipe["calories"]) + " calories"},
        "recipeIngredient": ingredients,
        "recipeInstructions": [{"@type": "HowToStep", "text": s} for s in instructions],
        "keywords": keywords
    }
    
    cat_emoji = {"Main Dish": "🍽️", "Soup": "🍲", "Dessert": "🍰", "Side Dish": "🥬", "Appetizer": "🥟", "Snack": "🥜", "Beverage": "🍹"}.get(recipe["category"], "🍳")
    
    def pt_to_display(pt):
        m = int(re.sub(r'[A-Z]', '', pt))
        if m >= 60:
            h = m // 60; rem = m % 60
            return f"{h}h {rem}m" if rem else f"{h}h"
        return f"{m}m"
    
    prep_display = pt_to_display(recipe["prep_time"])
    cook_display = pt_to_display(recipe["cook_time"])
    total_display = pt_to_display(recipe["total_time"])
    
    pinterest_desc = recipe["pinterest_desc"]
    
    html = f'''<!DOCTYPE html>
<html lang="{'es' if is_es else 'en'}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | Gullah Geechee Biz</title>
  <meta name="description" content="{desc}">
  <meta name="keywords" content="{keywords}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:image" content="https://gullahgeecheebiz.com/images/recipes/{recipe['slug']}.jpg">
  <meta property="og:url" content="https://gullahgeecheebiz.com/recipes/{recipe['slug']}.html">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="Gullah Geechee Biz">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{recipe['pinterest_title']}">
  <meta name="twitter:description" content="{pinterest_desc}">
  <meta name="pinterest-rich-pin" content="true">
  <link rel="canonical" href="https://gullahgeecheebiz.com/recipes/{recipe['slug']}.html">
  <link rel="alternate" hreflang="en" href="https://gullahgeecheebiz.com/recipes/{recipe['slug']}.html">
  <link rel="alternate" hreflang="es" href="https://gullahgeecheebiz.com/recipes/{recipe['slug']}-es.html">
  <link rel="alternate" hreflang="x-default" href="https://gullahgeecheebiz.com/recipes/{recipe['slug']}.html">
  <script type="application/ld+json">{json.dumps(schema, indent=2)}</script>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a14; color: #f0ede5; line-height: 1.8; }}
    .container {{ max-width: 800px; margin: 0 auto; padding: 40px 20px; }}
    h1 {{ font-family: Georgia, 'Times New Roman', serif; font-size: 2.2em; color: #d4af37; margin-bottom: 10px; line-height: 1.3; }}
    h2 {{ font-family: Georgia, 'Times New Roman', serif; font-size: 1.5em; color: #d4af37; margin: 30px 0 15px; }}
    p {{ margin-bottom: 20px; font-size: 1.1em; }}
    .meta {{ color: #888; font-size: 0.9em; margin-bottom: 30px; }}
    .recipe-image {{ width: 100%; max-height: 400px; object-fit: cover; border-radius: 12px; margin: 20px 0; background: #1a1a2e; aspect-ratio: 16/9; display: flex; align-items: center; justify-content: center; color: #555; font-size: 3em; }}
    .ingredients {{ background: #111122; border-radius: 12px; padding: 25px; margin: 20px 0; }}
    .ingredients ul {{ list-style: none; padding: 0; }}
    .ingredients li {{ padding: 8px 0; border-bottom: 1px solid #1a1a2e; font-size: 1.05em; }}
    .ingredients li:last-child {{ border-bottom: none; }}
    .ingredients li::before {{ content: "• "; color: #d4af37; font-weight: bold; }}
    .instructions {{ margin: 20px 0; }}
    .instructions ol {{ list-style: none; padding: 0; counter-reset: step; }}
    .instructions li {{ counter-increment: step; padding: 12px 0 12px 40px; position: relative; font-size: 1.05em; border-bottom: 1px solid #1a1a2e; }}
    .instructions li:last-child {{ border-bottom: none; }}
    .instructions li::before {{ content: counter(step); position: absolute; left: 0; top: 12px; background: #d4af37; color: #0a0a14; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 0.85em; }}
    .notes {{ background: #1a1a2e; border-left: 4px solid #d4af37; border-radius: 8px; padding: 20px; margin: 20px 0; font-style: italic; }}
    .cta {{ display: inline-block; background: #d4af37; color: #0a0a14; padding: 16px 32px; border-radius: 30px; text-decoration: none; font-weight: bold; font-size: 1.1em; margin: 20px 0; }}
    .cta:hover {{ background: #e8c84a; }}
    .lang-switch {{ text-align: right; margin-bottom: 20px; }}
    .lang-switch a {{ color: #d4af37; text-decoration: none; font-size: 0.9em; margin-left: 10px; }}
    .lang-switch a:hover {{ text-decoration: underline; }}
    .info-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 20px 0; }}
    .info-card {{ background: #111122; border-radius: 10px; padding: 15px; text-align: center; }}
    .info-card .icon {{ font-size: 1.5em; margin-bottom: 5px; }}
    .info-card .label {{ color: #888; font-size: 0.8em; text-transform: uppercase; letter-spacing: 1px; }}
    .info-card .value {{ color: #d4af37; font-size: 1.1em; font-weight: bold; }}
    .links {{ margin-top: 40px; padding-top: 30px; border-top: 1px solid #333; }}
    .links a {{ display: block; color: #d4af37; text-decoration: none; margin-bottom: 10px; font-size: 1em; }}
    .links a:hover {{ text-decoration: underline; }}
    .brand {{ text-align: center; margin-top: 60px; padding-top: 30px; border-top: 1px solid #333; }}
    .brand img {{ width: 60px; height: 60px; border-radius: 50%; border: 2px solid #d4af37; }}
    .brand p {{ color: #d4af37; font-size: 0.9em; margin-top: 10px; letter-spacing: 2px; }}
    .date {{ color: #666; font-size: 0.85em; margin-bottom: 5px; }}
    .category-badge {{ display: inline-block; background: #d4af37; color: #0a0a14; padding: 4px 12px; border-radius: 20px; font-size: 0.8em; font-weight: bold; margin-bottom: 15px; }}
    .pin-button {{ display: inline-block; background: #BD081C; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-size: 0.9em; margin: 10px 0; }}
    .pin-button:hover {{ background: #a0071a; }}
    @media (max-width: 600px) {{ h1 {{ font-size: 1.6em; }} .container {{ padding: 20px 15px; }} .info-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
  </style>
</head>
<body>
  <div class="container">
    <div class="lang-switch">
      <a href="{recipe['slug']}.html">English</a> | <a href="{recipe['slug']}-es.html">Español</a>
    </div>
    <span class="category-badge">{cat_emoji} {recipe['category']}</span>
    <h1>{title}</h1>
    <div class="date">Published {date.today().strftime('%B %d, %Y')} · Gullah Geechee Biz</div>
    <p>{desc}</p>
    <div class="recipe-image">🍳</div>
    <div class="info-grid">
      <div class="info-card"><div class="icon">⏱️</div><div class="label">Prep</div><div class="value">{prep_display}</div></div>
      <div class="info-card"><div class="icon">🔥</div><div class="label">Cook</div><div class="value">{cook_display}</div></div>
      <div class="info-card"><div class="icon">⏲️</div><div class="label">Total</div><div class="value">{total_display}</div></div>
      <div class="info-card"><div class="icon">🍽️</div><div class="label">Servings</div><div class="value">{recipe['servings']}</div></div>
    </div>
    <h2>Ingredients</h2>
    <div class="ingredients"><ul>\n{ing_html}\n      </ul></div>
    <h2>Instructions</h2>
    <div class="instructions"><ol>\n{inst_html}\n      </ol></div>
    <div class="notes"><strong>💡 Pro Tip:</strong> {notes}</div>
    <a href="https://pinterest.com/pin/create/button/?url=https%3A%2F%2Fgullahgeecheebiz.com%2Frecipes%2F{recipe['slug']}.html&media=https%3A%2F%2Fgullahgeecheebiz.com%2Fimages%2Frecipes%2F{recipe['slug']}.jpg&description={pinterest_desc.replace(' ', '%20')}" class="pin-button" target="_blank">📌 Pin this recipe</a>
    <a href="https://gullahgeecheebiz.com/recipes/" class="cta">View all Gullah Geechee recipes →</a>
    <div class="links">
      <strong style="color: #d4af37;">More Gullah Geechee recipes:</strong>
      <a href="https://gullahgeecheebiz.com/recipes/">📖 Browse all recipes →</a>
      <a href="https://kofigullahgeecheebiz.substack.com">📧 Subscribe to our newsletter →</a>
      <a href="https://gullahgeecheebiz.com">🏠 Visit Gullah Geechee Biz →</a>
    </div>
    <div class="brand">
      <img src="https://gullahgeecheebiz.com/logo.png" alt="Gullah Geechee Biz">
      <p>GULLAH GEECHEE BIZ</p>
    </div>
  </div>
</body>
</html>'''
    return html


def generate_index():
    """Generate the recipe index page."""
    existing = [r for r in RECIPES if os.path.exists(os.path.join(RECIPE_DIR, f"{r['slug']}.html"))]
    cards = ""
    for r in existing:
        cat_emoji = {"Main Dish": "🍽️", "Soup": "🍲", "Dessert": "🍰", "Side Dish": "🥬", "Appetizer": "🥟", "Snack": "🥜", "Beverage": "🍹"}.get(r["category"], "🍳")
        def pt_to_display(pt):
            m = int(re.sub(r'[A-Z]', '', pt))
            if m >= 60: h = m // 60; rem = m % 60; return f"{h}h {rem}m" if rem else f"{h}h"
            return f"{m}m"
        cards += f'''
    <a href="{r['slug']}.html" class="recipe-card">
      <div class="card-image">{cat_emoji}</div>
      <div class="card-body">
        <span class="card-category">{r['category']}</span>
        <h3>{r['title']}</h3>
        <p>{r['description'][:100]}...</p>
        <span class="card-meta">⏱️ {pt_to_display(r['total_time'])} · 🍽️ {r['servings']} servings</span>
      </div>
    </a>'''
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Gullah Geechee Recipes | Authentic Lowcountry Soul Food</title>
  <meta name="description" content="Authentic Gullah Geechee recipes from the Lowcountry. Red rice, shrimp and grits, okra soup, benne wafers, and more soul food classics.">
  <meta property="og:title" content="Gullah Geechee Recipes | Authentic Lowcountry Soul Food">
  <meta property="og:description" content="Authentic Gullah Geechee recipes from the Lowcountry.">
  <link rel="canonical" href="https://gullahgeecheebiz.com/recipes/">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a14; color: #f0ede5; line-height: 1.6; }}
    .container {{ max-width: 900px; margin: 0 auto; padding: 40px 20px; }}
    h1 {{ font-family: Georgia, 'Times New Roman', serif; font-size: 2.5em; color: #d4af37; margin-bottom: 10px; }}
    .subtitle {{ color: #888; font-size: 1.1em; margin-bottom: 40px; }}
    .recipe-card {{ display: flex; background: #111122; border-radius: 12px; overflow: hidden; margin-bottom: 20px; text-decoration: none; color: inherit; transition: transform 0.2s; }}
    .recipe-card:hover {{ transform: translateY(-2px); }}
    .card-image {{ width: 120px; min-height: 120px; display: flex; align-items: center; justify-content: center; font-size: 3em; background: #1a1a2e; flex-shrink: 0; }}
    .card-body {{ padding: 20px; flex: 1; }}
    .card-category {{ display: inline-block; background: #d4af37; color: #0a0a14; padding: 2px 10px; border-radius: 12px; font-size: 0.75em; font-weight: bold; margin-bottom: 8px; }}
    .card-body h3 {{ color: #d4af37; font-size: 1.2em; margin-bottom: 8px; }}
    .card-body p {{ color: #aaa; font-size: 0.9em; margin-bottom: 8px; }}
    .card-meta {{ color: #666; font-size: 0.8em; }}
    @media (max-width: 600px) {{ .recipe-card {{ flex-direction: column; }} .card-image {{ width: 100%; min-height: 80px; }} }}
  </style>
</head>
<body>
  <div class="container">
    <h1>🍽️ Gullah Geechee Recipes</h1>
    <p class="subtitle">Authentic Lowcountry soul food — from our family to your kitchen. Every recipe carries generations of Gullah Geechee tradition. {len(existing)} recipes and growing daily.</p>
    {cards}
  </div>
</body>
</html>'''


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    state = load_state()
    generated = state.get("generated", [])
    
    # Find recipes not yet generated
    pending = [r for r in RECIPES if r["slug"] not in generated]
    
    if not pending:
        print(f"✅ All {len(RECIPES)} recipes already generated. Nothing new today.")
        print(f"Total: {len(generated)} recipes live")
        return
    
    # Generate all pending recipes
    print(f"📝 Generating {len(pending)} new Gullah Geechee recipes...")
    
    for recipe in pending:
        # English
        en_html = generate_recipe_html(recipe, "en")
        with open(os.path.join(RECIPE_DIR, f"{recipe['slug']}.html"), "w") as f:
            f.write(en_html)
        
        # Spanish
        es_html = generate_recipe_html(recipe, "es")
        with open(os.path.join(RECIPE_DIR, f"{recipe['slug']}-es.html"), "w") as f:
            f.write(es_html)
        
        generated.append(recipe["slug"])
        print(f"  ✅ {recipe['title']}")
    
    # Update state
    state["generated"] = generated
    state["total_batches"] = state.get("total_batches", 0) + 1
    save_state(state)
    
    # Regenerate index
    index_html = generate_index()
    with open(os.path.join(RECIPE_DIR, "index.html"), "w") as f:
        f.write(index_html)
    
    total = len(generated)
    print(f"\n📊 Recipe Count: {total} recipes × 2 languages = {total*2} pages")
    print(f"📈 Total in database: {len(RECIPES)} recipes ({len(RECIPES) - total} remaining)")
    print(f"📍 Location: {RECIPE_DIR}/")


if __name__ == "__main__":
    main()
