#!/usr/bin/env python3
"""
Gullah Geechee Biz — Daily Pin Generator
Generates 100 unique Pinterest pin descriptions per day about Gullah Geechee culture.
"""

import json
import os
import random
from datetime import date

HOME = os.path.expanduser("~")
OUT_DIR = os.path.join(HOME, "pins-daily")
os.makedirs(OUT_DIR, exist_ok=True)

TOWNS = [
    "Beaufort", "Charleston", "Savannah", "Hilton Head", "St. Helena Island",
    "Edisto Island", "Georgetown", "Daufuskie Island", "Port Royal",
    "Yemassee", "Ridgeland", "Hardeeville", "Bluffton", "Walterboro",
    "Johns Island", "Wadmalaw Island", "James Island", "Mount Pleasant",
    "Folly Beach", "McClellanville", "Moncks Corner", "Brunswick", "Darien",
    "Sapelo Island", "St. Simons Island", "Jekyll Island", "Tybee Island",
    "Mitchelville", "Coosawhatchie", "Sheldon", "Seabrook", "Lobeco",
    "Garden City", "Murrells Inlet", "Pawleys Island", "Andrews",
    "Hemingway", "Kingstree", "St. Stephen", "Bonneau", "Cross",
    "Eutawville", "Holly Hill", "Harleyville", "St. George", "Branchville"
]

CULTURAL_FIGURES = [
    ("Robert Smalls", "The enslaved man who commandeered a Confederate ship and sailed his family to freedom. Later served in the U.S. Congress."),
    ("Philip Simmons", "The legendary Gullah Geechee blacksmith whose wrought iron gates grace Charleston. A National Heritage Fellow."),
    ("Harriet Tubman", "The Moses of her people. Led the Combahee River Raid, freeing 750+ enslaved Gullah Geechee people."),
    ("Edda Fields-Black", "Pulitzer Prize-winning historian. Her work 'Combee' brought Gullah Geechee history to the world stage."),
    ("Queen Quet", "Chieftess of the Gullah Geechee Nation. A tireless advocate for cultural preservation and land rights."),
    ("Emory Campbell", "Former director of Penn Center. A guardian of Gullah Geechee heritage on Hilton Head and St. Helena."),
    ("Mary Rivers", "A master sweetgrass basket weaver. Her hands carry centuries of West African tradition."),
    ("Denmark Vesey", "A free Black man who organized one of the largest slave rebellions in U.S. history in Charleston."),
    ("Septima Poinsette Clark", "The 'Mother of the Civil Rights Movement.' A Gullah Geechee educator who taught citizenship across the South."),
    ("Dr. Lorenzo Dow Turner", "The linguist who first studied and documented the Gullah language, proving its African roots."),
    ("Jonathan Green", "The celebrated Gullah Geechee painter whose vibrant works capture Lowcountry life in oil and watercolor."),
    ("Aunt Pearlie Sue", "A beloved Gullah storyteller and performer who keeps the Gullah language alive through song and story."),
]

FOODS = [
    ("Gullah Red Rice", "The signature dish of the Lowcountry. Tomato, rice, bacon, and love in every bite."),
    ("Shrimp and Grits", "A Lowcountry classic. Fresh shrimp over creamy stone-ground grits. Gullah Geechee soul food."),
    ("Okra Soup", "West African roots in every bowl. Okra, tomatoes, seafood, and the spirit of the Gullah people."),
    ("Benne Wafers", "Sesame cookies brought from West Africa. A Gullah Geechee tradition that tastes like history."),
    ("Frogmore Stew", "The Lowcountry boil. Shrimp, sausage, corn, potatoes. A community feast on any given Sunday."),
    ("Fried Fish", "Fresh from the Atlantic. Gullah Geechee fried fish with hushpuppies and a side of tradition."),
    ("Collard Greens", "Slow-cooked with smoked turkey. A Gullah Geechee staple that nourishes body and soul."),
    ("Hoppin' John", "Black-eyed peas and rice. Eaten on New Year's for good luck. A West African tradition that crossed the ocean."),
    ("Sweet Potato Pie", "Gullah Geechee sweet potato pie. More soul than pumpkin, more history than sugar."),
    ("Peach Cobbler", "Lowcountry peaches in a golden crust. A taste of Gullah Geechee summer."),
    ("Cornbread", "Golden, buttery, and made with love. Gullah Geechee cornbread is a Sunday dinner essential."),
    ("Gumbo", "West African okra meets Lowcountry seafood. Gullah Geechee gumbo is a story in every spoonful."),
    ("She-Crab Soup", "A Charleston classic with Gullah Geechee roots. Creamy, rich, unforgettable."),
    ("Boiled Peanuts", "A Lowcountry roadside staple. Gullah Geechee boiled peanuts are salty, soft, and soulful."),
    ("Deviled Crab", "Fresh crab meat stuffed back into the shell. A Gullah Geechee seafood tradition."),
]

TRADITIONS = [
    ("Sweetgrass Baskets", "A West African art form preserved on the Sea Islands. Each coil tells a story of survival and beauty."),
    ("The Gullah Language", "An English-based Creole with West African grammar and vocabulary. The only African-American Creole language in the U.S."),
    ("Ring Shout", "A sacred dance of West African origin. The oldest African-American performance tradition in North America."),
    ("Praise Houses", "Small wooden churches where Gullah Geechee spirituality was born. The heartbeat of Sea Island faith."),
    ("Heirs' Property", "Land passed down through generations without a will. A Gullah Geechee tradition of family stewardship."),
    ("Indigo Dyeing", "The blue gold of the Lowcountry. Gullah Geechee hands produced the indigo that colored the world."),
    ("Cast Net Fishing", "A West African fishing technique preserved on the Sea Islands. The cast net is a symbol of Gullah Geechee self-sufficiency."),
    ("Oyster Roasts", "A Gullah Geechee community tradition. Oysters on the fire, friends around the table, stories in the air."),
    ("Gullah Storytelling", "Brer Rabbit, the Hag, and the Boo Hag. Gullah Geechee folktales carry the wisdom of West Africa."),
    ("Gullah Cuisine", "West African ingredients + Lowcountry bounty = the original farm-to-table cuisine of America."),
    ("Sea Island Cotton", "The finest cotton in the world, grown by Gullah Geechee hands on the Sea Islands."),
    ("Gullah Geechee Quilting", "Patterns that carry African symbols. Each quilt is a map of memory and identity."),
    ("The Combahee River Raid", "Harriet Tubman's greatest military operation. 750+ Gullah Geechee people freed in one night."),
    ("Penn Center", "One of the first schools for formerly enslaved people. A Gullah Geechee landmark of education and freedom."),
    ("Gullah Spirituals", "Songs that moved from the praise houses to the world. The foundation of American gospel music."),
]

HISTORIC_SITES = [
    ("Penn Center", "St. Helena Island. The first school for formerly enslaved people in the South. A Gullah Geechee treasure."),
    ("The Angel Oak", "Johns Island. A 400-year-old live oak that witnessed Gullah Geechee history unfold beneath its branches."),
    ("Fort Sumter", "Charleston Harbor. Where the Civil War began. Gullah Geechee hands built these walls."),
    ("Mitchelville", "Hilton Head. The first self-governed town of formerly enslaved people in the United States."),
    ("The Combahee River", "Where Harriet Tubman led 150 Black soldiers to free 750+ Gullah Geechee people."),
    ("Drayton Hall", "Charleston. One of the oldest preserved plantations. Gullah Geechee history is etched in every brick."),
    ("St. Helena's Church", "Beaufort. One of the oldest churches in the South. Gullah Geechee worshippers filled these pews."),
    ("The Gullah Museum", "Hilton Head. A small house with a big story. Gullah Geechee history preserved with love."),
    ("Sapelo Island", "Hog Hammock. One of the last remaining Gullah Geechee communities. A living cultural treasure."),
    ("Pin Point Heritage Museum", "Savannah. A Gullah Geechee fishing village turned museum. Where the marsh tells the story."),
    ("Fort Frederica", "St. Simons Island. Gullah Geechee ancestors built this fort. Their fingerprints are in the tabby walls."),
    ("Boone Hall Plantation", "Mount Pleasant. Those oak trees have witnessed 300 years of Gullah Geechee resilience."),
    ("The Heyward-Washington House", "Charleston. Where Gullah Geechee servants shaped the daily life of early America."),
    ("The Old Slave Mart", "Charleston. A haunting reminder of the Gullah Geechee ancestors who were sold here."),
    ("The Owens-Thomas House", "Savannah. Where enslaved Gullah Geechee people lived and worked. Their stories are finally being told."),
]

def get_todays_seed():
    return int(date.today().strftime("%Y%m%d"))

def generate_pin_descriptions():
    rng = random.Random(get_todays_seed())
    pins = []
    
    categories = [
        ("Town Spotlight", TOWNS, lambda t: f"Discover Gullah Geechee heritage in {t}. History, culture, and community in the heart of the Lowcountry."),
        ("Cultural Figure", CULTURAL_FIGURES, lambda f: f"{f[0]}. {f[1]}"),
        ("Gullah Cuisine", FOODS, lambda f: f"{f[0]}. {f[1]}"),
        ("Gullah Tradition", TRADITIONS, lambda t: f"{t[0]}. {t[1]}"),
        ("Historic Site", HISTORIC_SITES, lambda s: f"{s[0]}. {s[1]}"),
    ]
    
    per_category = 20
    for cat_name, items, desc_fn in categories:
        shuffled = items.copy()
        rng.shuffle(shuffled)
        
        for i in range(per_category):
            item = shuffled[i % len(shuffled)]
            
            if isinstance(item, tuple):
                title = item[0]
                subtitle = desc_fn(item)
            else:
                title = item
                subtitle = desc_fn(item)
            
            pin_index = len(pins) + 1
            pins.append({
                "id": f"pin-{get_todays_seed()}-{cat_name.lower().replace(' ', '-')}-{i+1:03d}",
                "category": cat_name,
                "title": title,
                "subtitle": subtitle,
                "filename": f"pin-{get_todays_seed()}-{pin_index:03d}.png"
            })
    
    rng.shuffle(pins)
    return pins

def main():
    print("=" * 60)
    print("  GULLAH GEECHEE BIZ — DAILY PIN GENERATOR")
    print(f"  Date: {date.today().strftime('%B %d, %Y')}")
    print("=" * 60)
    print()
    
    pins = generate_pin_descriptions()
    print(f"  Generated {len(pins)} pin descriptions")
    print()
    
    print("  Sample pins:")
    for pin in pins[:5]:
        print(f"    \u2022 {pin['title']} \u2014 {pin['subtitle'][:60]}...")
    print()
    
    today = date.today().strftime("%Y-%m-%d")
    manifest = {
        "date": today,
        "seed": get_todays_seed(),
        "total_pins": len(pins),
        "pins": pins
    }
    
    manifest_path = os.path.join(OUT_DIR, f"manifest-{today}.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"  \U0001f4cb Manifest saved: {manifest_path}")
    print(f"  \U0001f4c1 Output: {OUT_DIR}")
    print("=" * 60)
    
    print(json.dumps({"manifest": manifest_path, "pin_count": len(pins)}))

if __name__ == "__main__":
    main()
