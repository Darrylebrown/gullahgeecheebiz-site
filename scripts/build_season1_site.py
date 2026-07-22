"""Generate the Season 1 site refresh for gullahgeecheebiz-site.

Creates:
  - season-1/index.html         (season hub with countdown)
  - season-1/<book-id>.html     (16 episode pages)
  - season-1/season-1.css       (extends existing style.css)
  - season-1/countdown.js       (client-side countdown to premiere 1)
  - index.html patch            (add Season 1 hero band + nav link)
"""
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
S1 = ROOT / "season-1"
S1.mkdir(exist_ok=True)

# ============================================================
# EPISODE DATA — extracted from Season 1 release calendar
# ============================================================
EPISODES = [
    dict(
        num=1,
        date=date(2026, 9, 5),
        book_id='queen-quet-2000',
        title='Queen Quet',
        anchor='GG Nation coronation era',
        runtime=100,
        era='2000–today',
        logline='The first Head-of-State of the Gullah Geechee Nation and the fight for federal cultural recognition.',
        hero='A Nation was declared. Then it went to work.',
        beats=[
            'Marquetta Goodwine crowned Queen Quet Chieftess of the Gullah/Geechee Nation, July 2, 2000.',
            'The federal Cultural Heritage Corridor designation, 2006 — signed into law after a decade of testimony.',
            'The ongoing work: land trust protections, language preservation, and community sovereignty on the Sea Islands today.',
        ],
    ),
    dict(
        num=2,
        date=date(2026, 9, 19),
        book_id='sea-islands-language',
        title='Da Language',
        anchor="Turner's Sept research trips",
        runtime=100,
        era='1932–today',
        logline="Lorenzo Dow Turner's wax cylinders prove Gullah is African, and a Mende song survives 200 years.",
        hero='They said it was broken English. He proved it was West Africa.',
        beats=[
            'Lorenzo Dow Turner arrives on Sapelo Island with a wax cylinder recorder, 1932.',
            'The Amelia Dawley recording — a Mende funeral song sung by a woman who never left Georgia.',
            "Turner's Africanisms in the Gullah Dialect (1949) rewrites American linguistics.",
        ],
    ),
    dict(
        num=3,
        date=date(2026, 10, 3),
        book_id='ring-shout-tradition',
        title='The Ring Turn Ever',
        anchor='McIntosh Shouters season',
        runtime=100,
        era='1700s–today',
        logline="The counterclockwise Kongo dance that outlived slavery and became American gospel's grandmother.",
        hero='Counterclockwise. Never crossing feet. A Kongo cosmogram in Georgia soil.',
        beats=[
            'The Kongo cosmogram (Dikenga) travels the Middle Passage, encoded in the shout.',
            'McIntosh County, Georgia — the last community to keep the shout unbroken from slavery through today.',
            'How the ring shout birthed American gospel, birthed the spiritual, birthed the sermon.',
        ],
    ),
    dict(
        num=4,
        date=date(2026, 10, 17),
        book_id='sweetgrass-basket-tradition',
        title='The Basket Sewers',
        anchor='Mt. Pleasant craft season',
        runtime=95,
        era='1700s–today',
        logline="The Senegambian coiling technique that became the Sea Islands' most enduring living art.",
        hero='Rice fanner in 1720. Museum piece in 2020. Same coil, same hands.',
        beats=[
            'The Senegambian origin — rice-country coiling technique that traveled with the enslaved.',
            'Mount Pleasant, South Carolina — the surviving sweetgrass corridor along Highway 17.',
            'The threats: development, sweetgrass access loss, generational transfer under strain.',
        ],
    ),
    dict(
        num=5,
        date=date(2026, 10, 31),
        book_id='gullah-jack-1822',
        title='The Conjure Man',
        anchor='Samhain / liminal date',
        runtime=95,
        era='1822',
        logline='The Kongo priest who armed the Vesey conspiracy with spiritual protection and paid with his life.',
        hero='Vesey brought the plan. Gullah Jack brought the protection.',
        beats=[
            'Jack Pritchard — Kongo-born, sold into Charleston, keeper of nkisi and ancestor lines.',
            "The role at Vesey's council: crab-claw amulets, parched corn, spiritual coverage for the fighters.",
            'Trial and execution, July 12, 1822 — refusing to give up his people even at the gallows.',
        ],
    ),
    dict(
        num=6,
        date=date(2026, 11, 14),
        book_id='sapelo-hog-hammock',
        title='The Last of Sapelo',
        anchor='Cornelia Bailey b. Nov 12',
        runtime=95,
        era='1945–today',
        logline="Cornelia Bailey and Hog Hammock's fight to hold Sapelo Island against developer erasure.",
        hero='An island of 434. A village of 47. And one woman who kept the stories.',
        beats=[
            'Cornelia Bailey born 1945, raised in Hog Hammock — last Gullah community on Sapelo.',
            'God, Dr. Buzzard, and the Bolito Man (2000) — her memoir, the community record.',
            'The property tax fight, land loss, and the descendants organizing today.',
        ],
    ),
    dict(
        num=7,
        date=date(2026, 11, 28),
        book_id='igbo-landing-1803',
        title='The Water Take Us Home',
        anchor='Thanksgiving counter-story',
        runtime=95,
        era='1803',
        logline='Seventy-five Igbo captives walk into Dunbar Creek singing — the birthplace of Black flight mythology.',
        hero='Dunbar Creek, St. Simons Island, May 1803. They chose the water.',
        beats=[
            'The York, the sale at Savannah, the transfer to Skidaway, the coastal schooner to St. Simons.',
            'The Roswell King letter (only surviving primary source) describing seventy-five walking into the marsh.',
            'How the story became the myth — flying Africans, Toni Morrison, Beyoncé, and the Gullah oral tradition.',
        ],
    ),
    dict(
        num=8,
        date=date(2026, 12, 12),
        book_id='denmark-vesey-1822',
        title='The Fire That Never Came',
        anchor='Kujichagulia prep',
        runtime=105,
        era='1822',
        logline="Charleston's largest planned uprising — betrayed six weeks before July 14, silenced for 200 years.",
        hero='Nine thousand names. One night. Six weeks before it lit.',
        beats=[
            'Denmark Vesey — Caribbean-born, free carpenter, class leader at Emanuel AME.',
            'The plan: July 14, 1822 — armories, ships to Haiti, a general rising across Charleston and the Sea Islands.',
            'The betrayal, the trials, the executions — and the two centuries of official erasure.',
        ],
    ),
    dict(
        num=9,
        date=date(2027, 1, 1),
        book_id='port-royal-experiment-1862',
        title='The Freedmen of Port Royal',
        anchor='Emancipation Proc anniversary',
        runtime=105,
        era='1862–1865',
        logline='The first place in America where enslaved people heard themselves declared free.',
        hero='November 7, 1861. The planters ran. Ten thousand stayed.',
        beats=[
            'The Battle of Port Royal, 1861 — Union takes the Sea Islands, planters flee, 10,000 self-liberate.',
            "The Experiment — northern teachers, missionaries, Black landownership, wage labor, the first Freedmen's schools.",
            'January 1, 1863 — the Emancipation Proclamation read aloud at Camp Saxton to the 1st South Carolina Volunteers.',
        ],
    ),
    dict(
        num=10,
        date=date(2027, 1, 16),
        book_id='robert-smalls-doc',
        title='Robert Smalls',
        anchor='MLK weekend',
        runtime=110,
        era='1839–1915',
        logline='The 23-year-old enslaved pilot who stole the Planter, freed his family, and became a Congressman.',
        hero="May 12, 1862. Three a.m. He put on the captain's straw hat.",
        beats=[
            'The Planter escape — Charleston Harbor, past five Confederate forts, delivered to the Union blockade.',
            "The naval career, the return to Beaufort, the purchase of his former master's house.",
            'The Reconstruction Congressman — five terms, the SC 1868 Constitution, the founder of the Republican Party in the state.',
        ],
    ),
    dict(
        num=11,
        date=date(2027, 1, 30),
        book_id='harriet-jacobs-1861',
        title='The Loophole',
        anchor='Black History Month opener',
        runtime=105,
        era='1832–1842',
        logline="Harriet Jacobs hides in her grandmother's crawlspace for seven years and writes it into a book.",
        hero='A crawlspace nine feet by seven. A single peephole. Seven years.',
        beats=[
            "Edenton, North Carolina — Dr. Norcom's pursuit begins, 1832.",
            "The garret hideaway above her grandmother Molly Horniblow's shed — 1835 to 1842.",
            'Incidents in the Life of a Slave Girl (1861) — published under Linda Brent, authenticated by Jean Fagan Yellin, 1987.',
        ],
    ),
    dict(
        num=12,
        date=date(2027, 2, 13),
        book_id='mother-emanuel-1865',
        title='Mother Emanuel',
        anchor='BHM Charleston anchor',
        runtime=110,
        era='1816–2015',
        logline="Vesey's church, burned twice, rebuilt three times — from conspiracy pew to prayer meeting massacre.",
        hero='Founded by Vesey. Burned by Charleston. Named for the God of freedom.',
        beats=[
            '1816 — Morris Brown and Denmark Vesey found Emanuel AME on Calhoun Street.',
            '1822 — church burned to the ground after the conspiracy discovery. Rebuilt underground for four decades.',
            'June 17, 2015 — nine killed at Wednesday night Bible study. The forgiveness statements that shook the country.',
        ],
    ),
    dict(
        num=13,
        date=date(2027, 2, 27),
        book_id='weeping-time-1859',
        title='The Rain Would Not Stop',
        anchor='March 2–3 auction anniversary',
        runtime=100,
        era='1859',
        logline='Pierce Butler auctions 436 human beings at Ten Broeck racetrack in a two-day rain that never stopped.',
        hero='Two days. Four hundred thirty-six people. A rain that would not stop.',
        beats=[
            "Pierce Butler's gambling debts and the decision to liquidate the Butler estate at Hampton Point and Butler Island.",
            'The auction, March 2–3, 1859 — Ten Broeck racetrack outside Savannah. The largest single slave auction in U.S. history.',
            "Mortimer Thomson's What Became of the Slaves on a Georgia Plantation — the embedded New-York Tribune reporter's account.",
        ],
    ),
    dict(
        num=14,
        date=date(2027, 3, 13),
        book_id='penn-school-1862',
        title='Under the Oaks',
        anchor='St. Helena spring',
        runtime=100,
        era='1862–today',
        logline='Laura Towne opens the first Southern school for the formerly enslaved beneath the Praise House oaks.',
        hero='St. Helena Island, 1862. A tent. A slate. The first Southern school.',
        beats=[
            'Laura Towne, Ellen Murray, and Charlotte Forten arrive on St. Helena, April 1862.',
            'Under the oaks at Brick Baptist Church — the classroom becomes the school becomes the Penn Center.',
            '1948 to today — Penn Center as civil rights training ground (King, SCLC retreats) and Gullah cultural preservation seat.',
        ],
    ),
    dict(
        num=15,
        date=date(2027, 3, 27),
        book_id='harriet-tubman-combahee',
        title='The Combahee',
        anchor='Tubman Day + raid lead-in',
        runtime=100,
        era='1863',
        logline='Tubman leads Union gunboats up the Combahee and frees 750 in a single night.',
        hero='June 2, 1863. Three Union gunboats. She was the scout.',
        beats=[
            "Tubman's intelligence network in Beaufort — Gullah pilots, Black watermen, mapped rice-country channels.",
            'The raid, June 2, 1863 — three gunboats up the Combahee, 750 self-liberated, plantations burned.',
            'The first woman to lead an armed expedition in U.S. military history. She fought for her pension for 30 years.',
        ],
    ),
    dict(
        num=16,
        date=date(2027, 4, 10),
        book_id='gullah-wars-seminole',
        title='The Longest War',
        anchor='Season finale · Fort Mose',
        runtime=115,
        era='1738–1858',
        logline='Fort Mose to Nacimiento — 120 years of armed Gullah resistance and the largest slave rebellion in U.S. history.',
        hero='Fort Mose, 1738. Nacimiento, today. The war lasted 120 years.',
        beats=[
            'Fort Mose, Spanish Florida, 1738 — first free Black settlement in North America, garrisoned by escaped Gullah under Captain Francisco Menendez.',
            'The Negro Fort at Prospect Bluff, 1816 — U.S. Navy destroys a maroon fort, killing 270 in the largest single-day Black massacre of the 19th century.',
            'John Horse and the 1850 exodus — 300 Black Seminoles walk across Texas to Nacimiento, Coahuila, Mexico, where descendants still live and speak Afro-Seminole Creole today.',
        ],
    ),
]

# ============================================================
# TEMPLATES
# ============================================================
def head(title, description, canonical, extra_css=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <meta name="description" content="{description}" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{description}" />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="{canonical}" />
  <meta name="theme-color" content="#0f2f29" />
  <link rel="preconnect" href="https://api.fontshare.com" crossorigin />
  <link href="https://api.fontshare.com/v2/css?f[]=switzer@400,500,600,700&f[]=sentient@400,500,700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="../style.css" />
  <link rel="stylesheet" href="../season-1/season-1.css" />
  {extra_css}
  <link rel="icon" href="../logo.png" type="image/png" />
</head>
<body>
  <a class="skip" href="#main">Skip to content</a>

  <header class="site-header">
    <div class="wrap header-inner">
      <a class="brand" href="../index.html" aria-label="Gullah Geechee Biz home">
        <svg class="mark" viewBox="0 0 40 40" width="36" height="36" aria-hidden="true" fill="none">
          <circle cx="20" cy="20" r="18.5" stroke="currentColor" stroke-width="1.5"/>
          <path d="M10 24c3-8 7-12 10-12s7 4 10 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <path d="M12 20h16M14 16h12" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" opacity="0.7"/>
        </svg>
        <span class="brand-text">Gullah Geechee Biz</span>
      </a>
      <button class="nav-toggle" aria-label="Toggle navigation" aria-expanded="false" aria-controls="primary-nav" onclick="var n=document.getElementById('primary-nav');var open=n.classList.toggle('is-open');this.setAttribute('aria-expanded', open);">
        <span class="nav-toggle-bar"></span>
        <span class="nav-toggle-bar"></span>
        <span class="nav-toggle-bar"></span>
      </button>
      <nav class="nav" id="primary-nav" aria-label="Primary">
        <a href="../index.html#about">About</a>
        <a href="../index.html#works">Books</a>
        <a href="../season-1/">Season 1</a>
        <a href="../index.html#merch">Merch</a>
        <a href="../index.html#substack">Join</a>
        <a href="../index.html#donate">Donate</a>
      </nav>
    </div>
  </header>

  <main id="main">
"""

def foot():
    return """  </main>

  <footer class="site-footer">
    <div class="wrap footer-inner">
      <p class="footer-tag">
        A Gullah Geechee Biz Production · Written &amp; Directed by Darryl Elliott Brown
      </p>
      <p class="footer-fine">
        © 2026 Darryl Elliott Brown · Culture first · Sources: LOC, NARA, community archives, pre-1928 music.
        Every episode carries community attribution.
      </p>
      <nav class="footer-nav" aria-label="Footer">
        <a href="../index.html">Home</a>
        <a href="../season-1/">Season 1</a>
        <a href="../index.html#substack">Newsletter</a>
        <a href="../index.html#donate">Support</a>
        <a href="https://github.com/Darrylebrown/ggb-books">Screenplay repo</a>
      </nav>
    </div>
  </footer>
</body>
</html>
"""

# ------------------------------------------------------------
# SEASON 1 HUB PAGE
# ------------------------------------------------------------
def build_hub():
    cards = ""
    for ep in EPISODES:
        d = ep["date"]
        month_short = d.strftime("%b").upper()
        day = d.strftime("%-d")
        date_full = d.strftime("%a %b %-d, %Y")
        cards += f"""
        <a class="ep-card" href="./{ep['book_id']}.html">
          <div class="ep-date">
            <span class="ep-month">{month_short}</span>
            <span class="ep-day">{day}</span>
          </div>
          <div class="ep-body">
            <p class="ep-num">Episode {ep['num']:02d} · {ep['runtime']} min · {ep['era']}</p>
            <h3 class="ep-title">{ep['title']}</h3>
            <p class="ep-logline">{ep['logline']}</p>
            <p class="ep-anchor">{ep['anchor']}</p>
          </div>
          <span class="ep-arrow" aria-hidden="true">→</span>
        </a>
"""
    return head(
        "Season 1 — Gullah Geechee Biz Documentary Series",
        "Sixteen documentaries across 32 weeks, from Fort Mose 1738 to Queen Quet today. A Gullah Geechee Biz Production.",
        "https://gullahgeecheebiz.com/season-1/"
    ) + f"""
    <section class="s1-hero">
      <div class="wrap">
        <p class="s1-eyebrow">A Gullah Geechee Biz Documentary Season</p>
        <h1 class="s1-title">Season One</h1>
        <p class="s1-sub">Sixteen documentaries. Thirty-two weeks. Two hundred and sixty-two years of Gullah Geechee resistance, memory, and life.</p>

        <div class="countdown" id="countdown" data-target="2026-09-05T20:00:00-04:00">
          <div class="cd-cell"><span class="cd-num" id="cd-days">—</span><span class="cd-label">days</span></div>
          <div class="cd-cell"><span class="cd-num" id="cd-hours">—</span><span class="cd-label">hours</span></div>
          <div class="cd-cell"><span class="cd-num" id="cd-mins">—</span><span class="cd-label">min</span></div>
          <div class="cd-cell"><span class="cd-num" id="cd-secs">—</span><span class="cd-label">sec</span></div>
        </div>
        <p class="cd-caption">Until <strong>Episode 01 · Queen Quet</strong> — Fri Sep 5, 2026, 8pm ET</p>

        <div class="s1-hero-actions">
          <a class="btn btn-primary" href="../index.html#substack">Get the schedule by email</a>
          <a class="btn btn-ghost" href="../index.html#donate">Support the season</a>
        </div>
      </div>
    </section>

    <section class="section s1-arc">
      <div class="wrap narrow">
        <h2>The arc</h2>
        <p>
          Season 1 moves chronologically through Gullah Geechee history — from the founding of Fort Mose in 1738,
          the first free Black settlement in North America, to Queen Quet's coronation of the Gullah Geechee Nation in 2000.
          Sixteen episodes, released every other Friday at 8pm ET, each anchored to a real cultural date so the release
          earns its moment.
        </p>
        <p>
          Every episode is scored with community-attributed traditional music. Every source is public domain or community-controlled.
          Every screenplay carries the standing attribution: written and directed by Darryl Elliott Brown, a Gullah Geechee Biz production.
        </p>
      </div>
    </section>

    <section class="section s1-episodes" id="episodes">
      <div class="wrap">
        <div class="section-head">
          <h2>The sixteen</h2>
          <p class="section-sub">Bi-weekly Fridays · Sept 5, 2026 through April 10, 2027</p>
        </div>
        <div class="ep-grid">
{cards}
        </div>
      </div>
    </section>

    <section class="section s1-support">
      <div class="wrap narrow">
        <h2>Stand with the season</h2>
        <p>
          Season 1 is being produced independently. Every dollar goes to editorial, archival research, community licensing,
          and the ACX audiobook narrations. Support any tier and your name goes in the end credits of the episode you help fund.
        </p>
        <div class="tier-grid">
          <a class="tier" href="../index.html#donate"><span class="tier-amt">$10</span><span class="tier-label">Field Note</span></a>
          <a class="tier" href="../index.html#donate"><span class="tier-amt">$25</span><span class="tier-label">Praise House</span></a>
          <a class="tier" href="../index.html#donate"><span class="tier-amt">$50</span><span class="tier-label">Ring Shout</span></a>
          <a class="tier" href="../index.html#donate"><span class="tier-amt">$100</span><span class="tier-label">Bearer</span></a>
        </div>
      </div>
    </section>

  <script src="../season-1/countdown.js"></script>
""" + foot()

# ------------------------------------------------------------
# EPISODE PAGE
# ------------------------------------------------------------
def build_episode(ep, prev_ep, next_ep):
    d = ep["date"]
    date_full = d.strftime("%A, %B %-d, %Y")
    date_short = d.strftime("%b %-d, %Y")
    beats_html = "\n".join(f"          <li>{b}</li>" for b in ep["beats"])
    prev_link = f'<a class="ep-nav-link" href="./{prev_ep["book_id"]}.html"><span class="ep-nav-dir">← Previous</span><span class="ep-nav-title">{prev_ep["title"]}</span></a>' if prev_ep else '<span></span>'
    next_link = f'<a class="ep-nav-link ep-nav-next" href="./{next_ep["book_id"]}.html"><span class="ep-nav-dir">Next →</span><span class="ep-nav-title">{next_ep["title"]}</span></a>' if next_ep else '<span></span>'

    return head(
        f"{ep['title']} — Episode {ep['num']:02d} · GGB Season 1",
        f"{ep['logline']} A Gullah Geechee Biz documentary. Premieres {date_short}.",
        f"https://gullahgeecheebiz.com/season-1/{ep['book_id']}.html"
    ) + f"""
    <article class="ep-page">
      <header class="ep-hero">
        <div class="wrap">
          <p class="ep-crumb"><a href="./index.html">Season 1</a> · Episode {ep['num']:02d}</p>
          <p class="ep-runtime">{ep['runtime']} min · {ep['era']}</p>
          <h1 class="ep-h1">{ep['title']}</h1>
          <p class="ep-hero-line">{ep['hero']}</p>
          <div class="ep-meta">
            <div>
              <span class="ep-meta-label">Premieres</span>
              <span class="ep-meta-value">{date_full}, 8pm ET</span>
            </div>
            <div>
              <span class="ep-meta-label">Cultural anchor</span>
              <span class="ep-meta-value">{ep['anchor']}</span>
            </div>
          </div>
        </div>
      </header>

      <section class="ep-section">
        <div class="wrap narrow">
          <h2>Logline</h2>
          <p class="ep-lede">{ep['logline']}</p>

          <h2>What the episode covers</h2>
          <ul class="ep-beats">
{beats_html}
          </ul>

          <h2>Production notes</h2>
          <p>
            Community-attributed traditional music only, no post-1928 material. All primary sources public domain
            (Library of Congress, National Archives, community archives) or community-controlled oral history.
            Screenplay filed with U.S. Copyright Office as part of the Gullah Geechee Biz Season 1 deposit.
          </p>

          <h2>Attribution</h2>
          <p class="ep-attribution">
            Written &amp; Directed by <strong>Darryl Elliott Brown</strong><br />
            Produced by <strong>Darryl Elliott Brown</strong><br />
            A <strong>Gullah Geechee Biz</strong> Production<br />
            © 2026 Darryl Elliott Brown
          </p>
        </div>
      </section>

      <section class="ep-cta">
        <div class="wrap narrow">
          <h2>Get this one in your inbox the day it drops</h2>
          <p>Free newsletter sends a reminder the morning of every premiere. Paid members get the companion essay and screenplay PDF the same night.</p>
          <div class="ep-cta-actions">
            <a class="btn btn-primary" href="../index.html#substack">Join the newsletter</a>
            <a class="btn btn-ghost" href="../index.html#donate">Fund this episode</a>
          </div>
        </div>
      </section>

      <nav class="ep-nav" aria-label="Episode navigation">
        <div class="wrap">
          <div class="ep-nav-grid">
            {prev_link}
            <a class="ep-nav-hub" href="./index.html">All 16 episodes</a>
            {next_link}
          </div>
        </div>
      </nav>
    </article>
""" + foot()

# ------------------------------------------------------------
# CSS EXTENSION
# ------------------------------------------------------------
CSS = """/* Season 1 — extends style.css */

/* --- SEASON 1 HERO --- */
.s1-hero {
  background:
    radial-gradient(ellipse 120% 80% at 30% 0%, rgba(196, 138, 26, 0.18), transparent 60%),
    linear-gradient(180deg, var(--marsh-deep), var(--marsh));
  color: var(--surface);
  padding: var(--space-12) 0 var(--space-10);
  text-align: center;
}
.s1-hero .wrap { max-width: 900px; }
.s1-eyebrow {
  font-family: var(--font-body);
  font-size: 13px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--gold-soft);
  margin: 0 0 var(--space-4);
}
.s1-title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: clamp(56px, 9vw, 112px);
  line-height: 0.95;
  margin: 0 0 var(--space-5);
  color: var(--surface);
}
.s1-sub {
  font-size: clamp(18px, 2.2vw, 22px);
  line-height: 1.5;
  color: rgba(250, 246, 236, 0.86);
  max-width: 640px;
  margin: 0 auto var(--space-8);
}

/* --- COUNTDOWN --- */
.countdown {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
  max-width: 520px;
  margin: 0 auto var(--space-4);
}
.cd-cell {
  background: rgba(250, 246, 236, 0.08);
  border: 1px solid rgba(240, 193, 77, 0.28);
  border-radius: var(--radius);
  padding: var(--space-4) var(--space-3);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.cd-num {
  font-family: var(--font-display);
  font-size: clamp(32px, 5vw, 48px);
  font-weight: 700;
  color: var(--gold-hot);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}
.cd-label {
  font-family: var(--font-body);
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(250, 246, 236, 0.72);
}
.cd-caption {
  font-size: 15px;
  color: rgba(250, 246, 236, 0.86);
  margin: 0 0 var(--space-6);
}
.s1-hero-actions {
  display: flex;
  gap: var(--space-3);
  justify-content: center;
  flex-wrap: wrap;
}
.s1-hero-actions .btn-ghost {
  border-color: var(--gold-soft);
  color: var(--gold-soft);
}
.s1-hero-actions .btn-ghost:hover {
  background: rgba(240, 193, 77, 0.12);
}

/* --- ARC SECTION --- */
.s1-arc { padding: var(--space-10) 0; }
.s1-arc h2 {
  font-family: var(--font-display);
  font-size: 32px;
  margin: 0 0 var(--space-4);
  color: var(--marsh);
}
.s1-arc p {
  font-size: 17px;
  line-height: 1.7;
  color: var(--ink-soft);
  margin: 0 0 var(--space-4);
}

/* --- EPISODE GRID --- */
.s1-episodes { padding: var(--space-8) 0 var(--space-10); }
.ep-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-4);
  margin-top: var(--space-6);
}
.ep-card {
  display: grid;
  grid-template-columns: 68px 1fr auto;
  gap: var(--space-4);
  align-items: start;
  padding: var(--space-5);
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  text-decoration: none;
  color: var(--ink);
  transition: transform 200ms var(--ease), border-color 200ms var(--ease), box-shadow 200ms var(--ease);
}
.ep-card:hover {
  transform: translateY(-2px);
  border-color: var(--gold);
  box-shadow: 0 10px 30px rgba(15, 47, 41, 0.14);
}
.ep-date {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-3) 0;
  background: var(--marsh);
  color: var(--surface);
  border-radius: 8px;
  min-height: 68px;
}
.ep-month {
  font-family: var(--font-body);
  font-size: 11px;
  letter-spacing: 0.12em;
  color: var(--gold-soft);
  font-weight: 600;
}
.ep-day {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}
.ep-body { min-width: 0; }
.ep-num {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-faint);
  margin: 0 0 6px;
  font-weight: 500;
}
.ep-title {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  line-height: 1.15;
  color: var(--marsh);
  margin: 0 0 8px;
}
.ep-logline {
  font-size: 14px;
  line-height: 1.5;
  color: var(--ink-soft);
  margin: 0 0 8px;
}
.ep-anchor {
  font-size: 12px;
  color: var(--gold);
  font-weight: 600;
  margin: 0;
  letter-spacing: 0.02em;
}
.ep-arrow {
  color: var(--gold);
  font-size: 24px;
  font-weight: 400;
  align-self: center;
  transition: transform 200ms var(--ease);
}
.ep-card:hover .ep-arrow { transform: translateX(4px); }

/* --- SUPPORT TIERS --- */
.s1-support { padding: var(--space-10) 0 var(--space-12); }
.s1-support h2 {
  font-family: var(--font-display);
  font-size: 32px;
  margin: 0 0 var(--space-4);
  color: var(--marsh);
}
.tier-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: var(--space-3);
  margin-top: var(--space-6);
}
.tier {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-5) var(--space-4);
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  text-decoration: none;
  transition: border-color 200ms var(--ease), transform 200ms var(--ease);
}
.tier:hover {
  border-color: var(--gold-hot);
  transform: translateY(-2px);
}
.tier-amt {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 700;
  color: var(--marsh);
  line-height: 1;
  margin-bottom: 6px;
}
.tier-label {
  font-size: 13px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-faint);
  font-weight: 600;
}

/* --- EPISODE PAGE --- */
.ep-hero {
  background:
    radial-gradient(ellipse 120% 80% at 20% 0%, rgba(196, 138, 26, 0.15), transparent 60%),
    linear-gradient(180deg, var(--marsh-deep), var(--marsh-mid));
  color: var(--surface);
  padding: var(--space-10) 0 var(--space-8);
}
.ep-crumb {
  font-size: 13px;
  letter-spacing: 0.08em;
  color: var(--gold-soft);
  margin: 0 0 var(--space-4);
  text-transform: uppercase;
}
.ep-crumb a { color: var(--gold-soft); }
.ep-crumb a:hover { color: var(--gold-hot); }
.ep-runtime {
  font-size: 13px;
  color: rgba(250, 246, 236, 0.72);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin: 0 0 var(--space-3);
}
.ep-h1 {
  font-family: var(--font-display);
  font-size: clamp(44px, 7vw, 84px);
  font-weight: 700;
  line-height: 0.98;
  margin: 0 0 var(--space-4);
  color: var(--surface);
  max-width: 900px;
}
.ep-hero-line {
  font-family: var(--font-display);
  font-style: italic;
  font-size: clamp(20px, 2.4vw, 26px);
  line-height: 1.4;
  color: var(--gold-soft);
  max-width: 720px;
  margin: 0 0 var(--space-6);
}
.ep-meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-4);
  max-width: 720px;
  padding-top: var(--space-5);
  border-top: 1px solid rgba(240, 193, 77, 0.24);
}
.ep-meta > div { display: flex; flex-direction: column; gap: 4px; }
.ep-meta-label {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--gold-soft);
}
.ep-meta-value {
  font-size: 16px;
  color: var(--surface);
  font-weight: 500;
}

.ep-section { padding: var(--space-10) 0; }
.ep-section h2 {
  font-family: var(--font-display);
  font-size: 26px;
  color: var(--marsh);
  margin: var(--space-8) 0 var(--space-3);
}
.ep-section h2:first-child { margin-top: 0; }
.ep-lede {
  font-size: 20px;
  line-height: 1.6;
  color: var(--ink);
  font-weight: 500;
  margin: 0 0 var(--space-5);
}
.ep-beats {
  list-style: none;
  padding: 0;
  margin: 0 0 var(--space-5);
  counter-reset: beat;
}
.ep-beats li {
  counter-increment: beat;
  position: relative;
  padding: var(--space-3) 0 var(--space-3) 44px;
  border-bottom: 1px solid var(--line);
  font-size: 16px;
  line-height: 1.6;
  color: var(--ink-soft);
}
.ep-beats li:last-child { border-bottom: none; }
.ep-beats li::before {
  content: counter(beat, decimal-leading-zero);
  position: absolute;
  left: 0;
  top: var(--space-3);
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
  color: var(--gold);
  font-variant-numeric: tabular-nums;
}
.ep-attribution {
  font-size: 15px;
  line-height: 1.7;
  color: var(--ink-soft);
  padding: var(--space-5);
  background: var(--surface);
  border-left: 3px solid var(--gold);
  border-radius: 4px;
  margin: 0;
}

.ep-cta {
  background: var(--surface);
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  padding: var(--space-10) 0;
}
.ep-cta h2 {
  font-family: var(--font-display);
  font-size: 30px;
  color: var(--marsh);
  margin: 0 0 var(--space-3);
}
.ep-cta p {
  font-size: 17px;
  color: var(--ink-soft);
  margin: 0 0 var(--space-5);
}
.ep-cta-actions {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
}

/* --- EP NAVIGATION --- */
.ep-nav {
  background: var(--marsh-deep);
  padding: var(--space-6) 0;
  color: var(--surface);
}
.ep-nav-grid {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: var(--space-4);
  align-items: center;
}
.ep-nav-link {
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-decoration: none;
  color: var(--surface);
  padding: var(--space-3);
  border-radius: 8px;
  transition: background 200ms var(--ease);
}
.ep-nav-link:hover { background: rgba(250, 246, 236, 0.06); }
.ep-nav-next { text-align: right; align-items: flex-end; }
.ep-nav-dir {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--gold-soft);
}
.ep-nav-title {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
}
.ep-nav-hub {
  text-decoration: none;
  color: var(--gold-hot);
  font-size: 13px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 600;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--gold-hot);
  border-radius: 999px;
  white-space: nowrap;
}
.ep-nav-hub:hover { background: rgba(232, 168, 32, 0.12); }

/* --- FOOTER --- */
.site-footer {
  background: var(--marsh-deep);
  color: rgba(250, 246, 236, 0.7);
  padding: var(--space-8) 0 var(--space-6);
}
.footer-inner {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  align-items: center;
  text-align: center;
}
.footer-tag {
  font-family: var(--font-display);
  font-size: 16px;
  color: var(--surface);
  margin: 0;
}
.footer-fine {
  font-size: 13px;
  max-width: 640px;
  margin: 0;
  line-height: 1.55;
}
.footer-nav {
  display: flex;
  gap: var(--space-5);
  flex-wrap: wrap;
  justify-content: center;
  margin-top: var(--space-2);
}
.footer-nav a {
  color: var(--gold-soft);
  font-size: 13px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  text-decoration: none;
}
.footer-nav a:hover { color: var(--gold-hot); }

/* --- Mobile --- */
@media (max-width: 640px) {
  .ep-card { grid-template-columns: 56px 1fr; }
  .ep-arrow { display: none; }
  .ep-nav-grid { grid-template-columns: 1fr; text-align: center; }
  .ep-nav-next { text-align: center; align-items: center; }
  .countdown { max-width: 100%; }
  .cd-cell { padding: var(--space-3) 6px; }
}

/* --- QA FIXES baked in --- */
.ep-card { align-items: stretch; }
.ep-card .ep-body { display: flex; flex-direction: column; flex: 1; }
.ep-card .ep-anchor { margin-top: auto; padding-top: 8px; }
@media (min-width: 1100px) {
  .ep-grid { grid-template-columns: repeat(4, 1fr); }
  .ep-card { grid-template-columns: 58px 1fr; }
  .ep-arrow { display: none; }
  .ep-title { font-size: 20px; }
}
@media (min-width: 720px) and (max-width: 1099px) {
  .ep-grid { grid-template-columns: repeat(2, 1fr); }
}
.ep-runtime { color: rgba(250, 246, 236, 0.92); font-weight: 500; }
.ep-meta-value { color: var(--surface); }
.brand-text { white-space: nowrap; }
"""

# ------------------------------------------------------------
# COUNTDOWN JS
# ------------------------------------------------------------
JS = """// Countdown to Episode 01 premiere
(function() {
  var el = document.getElementById('countdown');
  if (!el) return;
  var target = new Date(el.getAttribute('data-target')).getTime();
  var days = document.getElementById('cd-days');
  var hours = document.getElementById('cd-hours');
  var mins = document.getElementById('cd-mins');
  var secs = document.getElementById('cd-secs');

  function tick() {
    var now = Date.now();
    var d = target - now;
    if (d <= 0) {
      days.textContent = '00';
      hours.textContent = '00';
      mins.textContent = '00';
      secs.textContent = '00';
      return;
    }
    var dd = Math.floor(d / 86400000);
    var hh = Math.floor((d % 86400000) / 3600000);
    var mm = Math.floor((d % 3600000) / 60000);
    var ss = Math.floor((d % 60000) / 1000);
    days.textContent = String(dd).padStart(2, '0');
    hours.textContent = String(hh).padStart(2, '0');
    mins.textContent = String(mm).padStart(2, '0');
    secs.textContent = String(ss).padStart(2, '0');
  }
  tick();
  setInterval(tick, 1000);
})();
"""

# ============================================================
# WRITE FILES
# ============================================================
(S1 / "season-1.css").write_text(CSS)
(S1 / "countdown.js").write_text(JS)
(S1 / "index.html").write_text(build_hub())

for i, ep in enumerate(EPISODES):
    prev_ep = EPISODES[i-1] if i > 0 else None
    next_ep = EPISODES[i+1] if i < len(EPISODES)-1 else None
    (S1 / f"{ep['book_id']}.html").write_text(build_episode(ep, prev_ep, next_ep))

print(f"Wrote hub + {len(EPISODES)} episodes + CSS + JS")
print("Files:")
for f in sorted(S1.iterdir()):
    print(f"  {f.name}  ({f.stat().st_size:,} bytes)")
