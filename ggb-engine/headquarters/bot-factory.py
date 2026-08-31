import datetime
import json
import os
import random
import time
import uuid
import logging
import sys
from pathlib import Path
from collections import deque
sys.path.insert(0, str(Path(__file__).parent))
from agent_auth import require_agent_auth
from flask import Flask, jsonify, request, render_template_string
from threading import Thread, Lock, Event

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('BotFactory')

# --- Configuration ---
CONFIG = {
    "FACTORY_PORT": 8091,
    "MONITOR_INTERVAL_SECONDS": 5,
    "SCRAPE_INTERVAL_SECONDS": 30,
    "HEAL_INTERVAL_SECONDS": 10,
    "EVOLVE_INTERVAL_SECONDS": 60,
    "BRAND_GUARD_INTERVAL_SECONDS": 15,
    "EXTERNAL_SYSTEMS": {
        "agents_system": {"url": "http://localhost:8080/agents_status", "mock_data": lambda: {"count": random.randint(350, 400), "active": random.randint(300, 370)}},
        "publishing_controller": {"url": "http://localhost:8090/status", "mock_data": lambda: {"status": random.choice(["online", "degraded", "offline"])}},
        "security_network": {"url": "http://localhost:8089/alerts", "mock_data": lambda: {"alerts": random.randint(0, 5), "healing_in_progress": random.choice([True, False])}},
        "royalty_dashboard": {"url": "http://localhost:8087/data", "mock_data": lambda: {"revenue_last_hour": round(random.uniform(100, 1000), 2), "sales_count": random.randint(10, 100)}},
        "universal_submitter": {"url": "http://localhost:8086/queue", "mock_data": lambda: {"queue_size": random.randint(0, 50)}},
        "gullah_hearth": {"url": "http://localhost:8085/activity", "mock_data": lambda: {"active_users": random.randint(50, 500), "posts_last_hour": random.randint(10, 100)}},
    },
    "PENDING_BOOKS_COUNT": 1817, # Initial value
    "PUBLISHING_MINDSET": "Published books change lives. Unsubmitted books do nothing.",
    "COLLECTIVE_INTELLIGENCE_PROTOCOL": "One learns, everyone learns. One improves, all improve.",
    "SOCIAL_MEDIA_PLATFORMS": ["Twitter", "Facebook", "Instagram", "TikTok", "Pinterest", "LinkedIn", "YouTube", "Rumble", "Reddit", "Medium"],
    "GULLAH_GEECHEE_KEYWORDS": ["Gullah", "Geechee", "Sea Islands", "Lowcountry", "sweetgrass", "okra", "rice and peas", "folktales", "basket weaving"],
    "WEB_SCRAPE_TARGETS": {
        "competitors": ["competitorA.com", "competitorB.com"],
        "cultural_news": ["gullahgeecheeculturalheritagecorridor.org", "culturalnewsblog.com"],
        "platform_updates": ["kdp.amazon.com/updates", "draft2digital.com/news"],
    }
}

# --- Global State ---
factory_state = {
    "status": "online",
    "last_check": datetime.datetime.now().isoformat(),
    "awareness_data": {},
    "dispatched_bots": {},
    "threats": {},
    "marketing_opportunities": {},
    "workflow_analysis": {},
    "social_media_landscape": {},
    "brand_health": {"score": 100, "alerts": []},
    "evolution_log": deque(maxlen=20),
    "healing_log": deque(maxlen=20),
    "factory_config": CONFIG, # Expose config for transparency
}
state_lock = Lock()
shutdown_event = Event()

app = Flask(__name__)
app.config["AGENT_TOKEN"] = os.environ.get("AGENT_TOKEN_BOT_FACTORY", "")

@app.before_request
def _bot_factory_auth():
    require_agent_auth("AGENT_TOKEN_BOT_FACTORY")

# --- Core Bot Factory Components ---

class AwarenessEngine:
    def __init__(self):
        self.systems_status = {}
        self.pending_books = CONFIG["PENDING_BOOKS_COUNT"]
        self.elite_publishing_mindset = CONFIG["PUBLISHING_MINDSET"]
        self.collective_intelligence_protocol = CONFIG["COLLECTIVE_INTELLIGENCE_PROTOCOL"]
        logger.info("Awareness Engine initialized.")

    def monitor_external_systems(self):
        global factory_state
        current_data = {}
        for system_name, system_info in CONFIG["EXTERNAL_SYSTEMS"].items():
            # In a real scenario, this would make HTTP requests
            # For this simulation, we'll use mock data
            try:
                # response = requests.get(system_info["url"], timeout=2) # Example
                data = system_info["mock_data"]()
                current_data[system_name] = {"status": "online", "data": data}
            except Exception as e:
                current_data[system_name] = {"status": "offline", "error": str(e)}
            
        current_data["pending_books"] = self.pending_books
        current_data["publishing_mindset"] = self.elite_publishing_mindset
        current_data["collective_intelligence_protocol"] = self.collective_intelligence_protocol

        with state_lock:
            factory_state["awareness_data"].update(current_data)
            factory_state["last_check"] = datetime.datetime.now().isoformat()
        logger.debug("Awareness Engine updated system status.")
        return current_data

    def get_full_publishing_pipeline_state(self):
        # Combines data from various systems to get a holistic view
        state = {}
        with state_lock:
            state.update(factory_state["awareness_data"])
            state["publishing_controller_status"] = factory_state["awareness_data"].get("publishing_controller", {}).get("data", {}).get("status")
            state["universal_submitter_queue"] = factory_state["awareness_data"].get("universal_submitter", {}).get("data", {}).get("queue_size")
            state["pending_books_count"] = self.pending_books
        return state

class WebScraper:
    def __init__(self):
        logger.info("Web Scraper initialized.")

    def scrape_data(self):
        scraped_data = {}
        for target_type, urls in CONFIG["WEB_SCRAPE_TARGETS"].items():
            scraped_data[target_type] = {}
            for url in urls:
                # Simulate scraping content
                mock_content = self._generate_mock_content(url, target_type)
                scraped_data[target_type][url] = {
                    "last_scraped": datetime.datetime.now().isoformat(),
                    "content_summary": mock_content
                }
        
        # Simulate social media monitoring
        social_trends = self._simulate_social_trends()
        
        # Simulate cultural event monitoring
        cultural_events = self._simulate_cultural_events()

        return {"scraped_targets": scraped_data, "social_trends": social_trends, "cultural_events": cultural_events}

    def _generate_mock_content(self, url, target_type):
        if "competitor" in target_type:
            return f"Mock competitor analysis from {url}: Bestseller 'A' at $9.99, new trend: 'interactive stories'."
        elif "cultural_news" in target_type:
            keywords = random.sample(CONFIG["GULLAH_GEECHEE_KEYWORDS"], k=2)
            return f"Mock cultural news from {url}: Article about {keywords[0]} traditions, upcoming {keywords[1]} festival."
        elif "platform_updates" in target_type:
            return f"Mock platform update from {url}: KDP Royalties adjustment, new D2D category added."
        return f"Mock content from {url}."

    def _simulate_social_trends(self):
        trending_gullah_topics = random.sample(CONFIG["GULLAH_GEECHEE_KEYWORDS"], k=2)
        return {
            "trending_hashtags": [f"#{t.replace(' ', '')}" for t in trending_gullah_topics] + ["#BlackAuthors", "#IndiePublishing"],
            "sentiment_overview": random.choice(["positive", "neutral", "mixed"]),
            "top_mentions": ["@GullahGeecheeBrand", "author_xyz"],
        }
    
    def _simulate_cultural_events(self):
        return [
            {"name": "Gullah Geechee Heritage Month", "date": "April", "relevance": "high"},
            {"name": "Sweetgrass Festival", "date": "July", "relevance": "medium"},
            {"name": "Kwanzaa", "date": "December", "relevance": "high"},
        ]


class Bot:
    def __init__(self, bot_type, purpose, parameters=None):
        self.id = str(uuid.uuid4())
        self.bot_type = bot_type
        self.purpose = purpose
        self.parameters = parameters if parameters is not None else {}
        self.status = "active"
        self.created_at = datetime.datetime.now().isoformat()
        self.log = []
        logger.info(f"Bot '{self.id}' created: Type='{bot_type}', Purpose='{purpose}'")

    def run(self):
        logger.info(f"Bot '{self.id}' ({self.bot_type}) executing purpose: {self.purpose}")
        self.log.append(f"{datetime.datetime.now().isoformat()}: Started execution.")
        
        # Simulate bot action based on type and purpose
        time.sleep(random.uniform(0.5, 2)) # Simulate work
        
        if self.bot_type == "security":
            self.log.append(f"{datetime.datetime.now().isoformat()}: Applied patch/blocked IP for {self.parameters.get('threat_id')}.")
        elif self.bot_type == "marketing":
            self.log.append(f"{datetime.datetime.now().isoformat()}: Launched campaign for '{self.parameters.get('opportunity')}' on {self.parameters.get('platform')}.")
        elif self.bot_type == "optimization":
            self.log.append(f"{datetime.datetime.now().isoformat()}: Reallocated resources for '{self.parameters.get('bottleneck')}'.")
        elif self.bot_type == "social_media":
            self.log.append(f"{datetime.datetime.now().isoformat()}: Posted content regarding '{self.parameters.get('topic')}' on {self.parameters.get('platform')}.")
        elif self.bot_type == "content":
            self.log.append(f"{datetime.datetime.now().isoformat()}: Generated draft for '{self.parameters.get('topic')}'.")
        elif self.bot_type == "brand_protection":
            self.log.append(f"{datetime.datetime.now().isoformat()}: Addressed brand misuse instance: '{self.parameters.get('issue')}'.")

        self.status = "completed"
        self.log.append(f"{datetime.datetime.now().isoformat()}: Execution completed.")
        logger.info(f"Bot '{self.id}' ({self.bot_type}) completed.")

class BotDispatcher:
    def __init__(self):
        logger.info("Bot Dispatcher initialized.")

    def dispatch_bot(self, bot_type, purpose, parameters=None):
        bot = Bot(bot_type, purpose, parameters)
        with state_lock:
            factory_state["dispatched_bots"][bot.id] = bot
        
        # Run bot in a separate thread to not block the main factory
        bot_thread = Thread(target=bot.run)
        bot_thread.daemon = True
        bot_thread.start()
        return bot.id

class ThreatDetector:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        logger.info("Threat Detector initialized.")

    def detect_threats(self, awareness_data, scraped_data):
        current_threats = {}
        # Security threats (mock)
        if awareness_data.get("security_network", {}).get("data", {}).get("alerts", 0) > 0:
            threat_id = f"SEC-{uuid.uuid4().hex[:8]}"
            current_threats[threat_id] = {"type": "security", "description": "Security alerts detected in network.", "severity": "high"}
            if not any(b.purpose == f"Address security threat {threat_id}" for b in factory_state["dispatched_bots"].values()):
                 self.dispatcher.dispatch_bot("security", f"Address security threat {threat_id}", {"threat_id": threat_id})

        # Platform threats (mock)
        if "offline" in awareness_data.get("publishing_controller", {}).get("data", {}).get("status", ""):
            threat_id = f"PLT-{uuid.uuid4().hex[:8]}"
            current_threats[threat_id] = {"type": "platform", "description": "Publishing controller is offline.", "severity": "critical"}
            if not any(b.purpose == f"Investigate platform issue {threat_id}" for b in factory_state["dispatched_bots"].values()):
                 self.dispatcher.dispatch_bot("optimization", f"Investigate platform issue {threat_id}", {"issue": "publishing_controller_offline"})
        
        # Brand threats (handled by BrandGuardian mostly, but can detect here too)
        # Example: Scraped data showing negative sentiment or misuse
        social_sentiment = scraped_data.get("social_trends", {}).get("sentiment_overview")
        if social_sentiment == "negative":
            threat_id = f"BRN-{uuid.uuid4().hex[:8]}"
            current_threats[threat_id] = {"type": "brand", "description": "Negative social media sentiment detected.", "severity": "medium"}
            # BrandGuardian will likely dispatch a bot for this

        with state_lock:
            factory_state["threats"].update(current_threats)
        logger.debug(f"Threat Detector found {len(current_threats)} threats.")
        return current_threats

class MarketingAnalyzer:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        logger.info("Marketing Analyzer initialized.")

    def analyze_opportunities(self, awareness_data, scraped_data):
        opportunities = {}
        # Trending topics
        for hashtag in scraped_data.get("social_trends", {}).get("trending_hashtags", []):
            if any(k.lower() in hashtag.lower() for k in CONFIG["GULLAH_GEECHEE_KEYWORDS"]) and random.random() < 0.5: # Simulate real detection
                op_id = f"MKT-{uuid.uuid4().hex[:8]}"
                opportunities[op_id] = {"type": "trending_topic", "topic": hashtag, "description": f"High engagement on {hashtag}."}
                if not any(b.purpose == f"Create content for {hashtag}" for b in factory_state["dispatched_bots"].values()):
                    self.dispatcher.dispatch_bot("marketing", f"Create content for {hashtag}", {"opportunity": hashtag, "platform": "all"})
                    self.dispatcher.dispatch_bot("social_media", f"Schedule posts for {hashtag}", {"topic": hashtag, "platform": "all"})

        # Seasonal content (mock)
        current_month = datetime.datetime.now().strftime("%B")
        for event in scraped_data.get("cultural_events", []):
            if event["date"] == current_month and event["relevance"] == "high":
                op_id = f"MKT-{uuid.uuid4().hex[:8]}"
                opportunities[op_id] = {"type": "seasonal", "event": event["name"], "description": f"Major cultural event {event['name']} upcoming."}
                if not any(b.purpose == f"Develop content for {event['name']}" for b in factory_state["dispatched_bots"].values()):
                    self.dispatcher.dispatch_bot("content", f"Develop content for {event['name']}", {"topic": event["name"]})
                    self.dispatcher.dispatch_bot("marketing", f"Launch campaign for {event['name']}", {"opportunity": event["name"], "platform": "all"})

        # Competitor insights (mock)
        for url, content in scraped_data.get("scraped_targets", {}).get("competitors", {}).items():
            if "interactive stories" in content["content_summary"].lower() and random.random() < 0.3:
                op_id = f"MKT-{uuid.uuid4().hex[:8]}"
                opportunities[op_id] = {"type": "competitor_trend", "trend": "interactive stories", "description": "Competitor succeeding with interactive stories."}
                if not any(b.purpose == "Research interactive stories format" for b in factory_state["dispatched_bots"].values()):
                    self.dispatcher.dispatch_bot("content", "Research interactive stories format", {"topic": "interactive stories"})

        with state_lock:
            factory_state["marketing_opportunities"].update(opportunities)
        logger.debug(f"Marketing Analyzer found {len(opportunities)} opportunities.")
        return opportunities

class WorkflowAnalyzer:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        logger.info("Workflow Analyzer initialized.")

    def analyze_workflow(self, awareness_data):
        analysis = {}

        # Pipeline bottlenecks (mock)
        submitter_queue = awareness_data.get("universal_submitter", {}).get("data", {}).get("queue_size", 0)
        if submitter_queue > 30:
            analysis["submitter_queue_bottleneck"] = {"issue": "Universal Submitter queue is backed up.", "severity": "high"}
            if not any(b.purpose == "Clear Universal Submitter queue" for b in factory_state["dispatched_bots"].values()):
                self.dispatcher.dispatch_bot("optimization", "Clear Universal Submitter queue", {"bottleneck": "Universal Submitter"})
        
        # Agent overload (mock)
        agents_active = awareness_data.get("agents_system", {}).get("data", {}).get("active", 0)
        agents_total = awareness_data.get("agents_system", {}).get("data", {}).get("count", 0)
        if agents_active / agents_total > 0.95 and agents_total > 300: # Over 95% of agents active
             analysis["agent_overload"] = {"issue": "High agent utilization, potential overload.", "severity": "medium"}
             if not any(b.purpose == "Analyze agent capacity" for b in factory_state["dispatched_bots"].values()):
                 self.dispatcher.dispatch_bot("optimization", "Analyze agent capacity", {"issue": "agent_overload"})

        # Books pending (mock) - Trigger content bot if count is low for some reason
        pending_books = awareness_data.get("pending_books", 0)
        if pending_books < 1000 and random.random() < 0.1: # If low and randomly triggered
            analysis["low_pending_books"] = {"issue": "Pending book count is unusually low.", "severity": "low"}
            if not any(b.purpose == "Generate new book ideas" for b in factory_state["dispatched_bots"].values()):
                self.dispatcher.dispatch_bot("content", "Generate new book ideas", {"topic": "Gullah Geechee stories"})

        with state_lock:
            factory_state["workflow_analysis"].update(analysis)
        logger.debug(f"Workflow Analyzer found {len(analysis)} workflow insights.")
        return analysis

class SocialMediaMonitor:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        logger.info("Social Media Monitor initialized.")

    def monitor_social_media(self, scraped_data):
        social_landscape = {}
        # Using scraped_data's social trends for this
        social_landscape["trends"] = scraped_data.get("social_trends", {})
        
        # Simulate detecting engagement opportunities
        if "top_mentions" in social_landscape["trends"] and random.random() < 0.4:
            mention = random.choice(social_landscape["trends"]["top_mentions"])
            social_landscape["engagement_opportunity"] = {"type": "direct_mention", "handle": mention, "action": "respond"}
            if not any(b.purpose == f"Respond to {mention} mention" for b in factory_state["dispatched_bots"].values()):
                self.dispatcher.dispatch_bot("social_media", f"Respond to {mention} mention", {"topic": "brand mention", "platform": "auto"})

        # Simulate scheduling content for all platforms
        if random.random() < 0.2: # Periodically schedule general content
            topic = random.choice(CONFIG["GULLAH_GEECHEE_KEYWORDS"]) + " fact"
            social_landscape["scheduled_content"] = {"topic": topic, "platforms": CONFIG["SOCIAL_MEDIA_PLATFORMS"], "action": "schedule"}
            if not any(b.purpose == f"Schedule general content about {topic}" for b in factory_state["dispatched_bots"].values()):
                self.dispatcher.dispatch_bot("social_media", f"Schedule general content about {topic}", {"topic": topic, "platform": "all"})

        with state_lock:
            factory_state["social_media_landscape"].update(social_landscape)
        logger.debug(f"Social Media Monitor updated landscape.")
        return social_landscape

class HealingEngine:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        logger.info("Healing Engine initialized.")

    def heal_systems(self, awareness_data):
        healing_actions = []
        # Check for offline systems
        for system_name, system_info in awareness_data.items():
            if isinstance(system_info, dict) and system_info.get("status") == "offline":
                action = f"Attempting restart/recovery for {system_name}."
                healing_actions.append(action)
                # In a real system, this would trigger an actual restart command
                if not any(f"Heal {system_name}" in b.purpose for b in factory_state["dispatched_bots"].values()):
                    self.dispatcher.dispatch_bot("optimization", f"Heal {system_name}", {"system": system_name, "action": "restart"})
        
        # Check security network healing playbooks
        if awareness_data.get("security_network", {}).get("data", {}).get("healing_in_progress", False):
            action = "Security network's internal healing playbooks are active."
            healing_actions.append(action)

        if healing_actions:
            with state_lock:
                factory_state["healing_log"].append(f"{datetime.datetime.now().isoformat()}: {'; '.join(healing_actions)}")
            logger.info(f"Healing Engine took actions: {healing_actions}")
        return healing_actions

class EvolutionEngine:
    def __init__(self):
        logger.info("Evolution Engine initialized.")

    def evolve_factory(self):
        evolution_steps = []
        
        # Analyze bot performance
        completed_bots = [b for b in factory_state["dispatched_bots"].values() if b.status == "completed"]
        if completed_bots:
            # Example: Improve bot dispatch logic based on past effectiveness
            if random.random() < 0.1:
                step = "Optimized bot dispatch criteria for marketing opportunities based on past campaign success."
                evolution_steps.append(step)
                logger.info(step)

        # Analyze healing success rates
        # (This would require more sophisticated tracking of heal outcomes)
        if random.random() < 0.05:
            step = "Refined healing protocols for platform outages based on historical recovery times."
            evolution_steps.append(step)
            logger.info(step)

        # Learn from threats
        # (If a type of threat keeps reoccurring, improve detection/prevention)
        if random.random() < 0.05 and factory_state["threats"]:
            threat_types = [t["type"] for t in factory_state["threats"].values()]
            if threat_types.count("security") > 2: # If many security threats
                step = "Implemented enhanced security scanning for common attack vectors identified in recent threats."
                evolution_steps.append(step)
                logger.info(step)

        # Learn from workflow bottlenecks
        if random.random() < 0.05 and "submitter_queue_bottleneck" in factory_state["workflow_analysis"]:
            step = "Adjusted Universal Submitter concurrency limits to prevent future queue backlogs."
            evolution_steps.append(step)
            logger.info(step)

        # Continuous improvement from protocol
        if random.random() < 0.1:
            step = "Applied Collective Intelligence Protocol: Insights from a recent content bot's performance were integrated across all content generation modules."
            evolution_steps.append(step)
            logger.info(step)
        
        if not evolution_steps:
            step = "No major evolution step needed at this cycle. Continuing to monitor."
            evolution_steps.append(step)
            logger.debug(step)

        with state_lock:
            for step in evolution_steps:
                factory_state["evolution_log"].append(f"{datetime.datetime.now().isoformat()}: {step}")
        return evolution_steps

class BrandGuardian:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        self.brand_health_score = 100
        self.brand_alerts = []
        logger.info("Brand Guardian initialized.")

    def guard_brand(self, awareness_data, scraped_data):
        new_alerts = []
        current_score_delta = 0

        # Monitor for cultural appropriation / misuse (mock)
        if random.random() < 0.01: # Rare occurrence
            issue = "Detected potential cultural misuse of Gullah Geechee imagery on an external site."
            new_alerts.append({"type": "misuse", "description": issue, "severity": "critical"})
            current_score_delta -= 10
            if not any(b.purpose == "Address brand misuse" for b in factory_state["dispatched_bots"].values()):
                self.dispatcher.dispatch_bot("brand_protection", "Address brand misuse", {"issue": issue})
        
        # Monitor for negative sentiment (from social media monitor)
        social_sentiment = scraped_data.get("social_trends", {}).get("sentiment_overview")
        if social_sentiment == "negative":
            issue = "Negative social media sentiment impacting brand perception."
            new_alerts.append({"type": "reputation", "description": issue, "severity": "medium"})
            current_score_delta -= 5
            if not any(b.purpose == "Mitigate negative social sentiment" for b in factory_state["dispatched_bots"].values()):
                self.dispatcher.dispatch_bot("marketing", "Mitigate negative social sentiment", {"issue": issue, "platform": "all"})

        # Monitor for positive mentions/amplification opportunities
        if "top_mentions" in scraped_data.get("social_trends", {}):
            positive_mentions = [m for m in scraped_data["social_trends"]["top_mentions"] if m not in ["@GullahGeecheeBrand"]] # Don't re-amplify self
            if positive_mentions and random.random() < 0.3:
                mention = random.choice(positive_mentions)
                issue = f"Positive brand mention by {mention} detected."
                new_alerts.append({"type": "amplification", "description": issue, "severity": "low"})
                current_score_delta += 2
                if not any(b.purpose == f"Amplify positive mention from {mention}" for b in factory_state["dispatched_bots"].values()):
                    self.dispatcher.dispatch_bot("social_media", f"Amplify positive mention from {mention}", {"topic": "positive brand mention", "platform": "all"})

        # Ensure cultural accuracy in generated content (mock)
        # This would involve bots analyzing content for keywords/context
        # For simulation, we assume content bots already do this, and the guardian checks for failures.
        
        # Adjust score and log alerts
        self.brand_health_score = max(0, min(100, self.brand_health_score + current_score_delta))
        self.brand_alerts.extend(new_alerts)
        self.brand_alerts = self.brand_alerts[-20:] # Keep recent alerts

        with state_lock:
            factory_state["brand_health"]["score"] = self.brand_health_score
            factory_state["brand_health"]["alerts"] = self.brand_alerts
        logger.debug(f"Brand Guardian updated brand health. Score: {self.brand_health_score}")
        return self.brand_health_score, new_alerts

# --- Factory Orchestration ---
awareness_engine = None
web_scraper = None
bot_dispatcher = None
threat_detector = None
marketing_analyzer = None
workflow_analyzer = None
social_media_monitor = None
healing_engine = None
evolution_engine = None
brand_guardian = None

def initialize_factory_components():
    global awareness_engine, web_scraper, bot_dispatcher, threat_detector, \
           marketing_analyzer, workflow_analyzer, social_media_monitor, \
           healing_engine, evolution_engine, brand_guardian

    bot_dispatcher = BotDispatcher()
    awareness_engine = AwarenessEngine()
    web_scraper = WebScraper()
    threat_detector = ThreatDetector(bot_dispatcher)
    marketing_analyzer = MarketingAnalyzer(bot_dispatcher)
    workflow_analyzer = WorkflowAnalyzer(bot_dispatcher)
    social_media_monitor = SocialMediaMonitor(bot_dispatcher)
    healing_engine = HealingEngine(bot_dispatcher)
    evolution_engine = EvolutionEngine()
    brand_guardian = BrandGuardian(bot_dispatcher)

def factory_loop():
    logger.info("Bot Factory main loop started.")
    initialize_factory_components()

    while not shutdown_event.is_set():
        try:
            # 1. Awareness Engine
            awareness_data = awareness_engine.monitor_external_systems()
            logger.debug("Awareness Engine cycle completed.")

            # 2. Web Scraper (less frequent)
            scraped_data = {}
            if datetime.datetime.now().second % (CONFIG["SCRAPE_INTERVAL_SECONDS"] // CONFIG["MONITOR_INTERVAL_SECONDS"]) == 0:
                scraped_data = web_scraper.scrape_data()
                logger.debug("Web Scraper cycle completed.")

            # 3. Threat Detection
            threat_detector.detect_threats(awareness_data, scraped_data)
            logger.debug("Threat Detector cycle completed.")

            # 4. Marketing Analysis
            marketing_analyzer.analyze_opportunities(awareness_data, scraped_data)
            logger.debug("Marketing Analyzer cycle completed.")

            # 5. Workflow Analysis
            workflow_analyzer.analyze_workflow(awareness_data)
            logger.debug("Workflow Analyzer cycle completed.")

            # 6. Social Media Monitoring
            social_media_monitor.monitor_social_media(scraped_data)
            logger.debug("Social Media Monitor cycle completed.")

            # 7. Brand Guardian
            brand_guardian.guard_brand(awareness_data, scraped_data)
            logger.debug("Brand Guardian cycle completed.")

            # 8. Healing Engine (independent check)
            if datetime.datetime.now().second % (CONFIG["HEAL_INTERVAL_SECONDS"] // CONFIG["MONITOR_INTERVAL_SECONDS"]) == 0:
                healing_engine.heal_systems(awareness_data)
                logger.debug("Healing Engine cycle completed.")

            # 9. Evolution Engine (less frequent)
            if datetime.datetime.now().second % (CONFIG["EVOLVE_INTERVAL_SECONDS"] // CONFIG["MONITOR_INTERVAL_SECONDS"]) == 0:
                evolution_engine.evolve_factory()
                logger.debug("Evolution Engine cycle completed.")

        except Exception as e:
            logger.error(f"Error in factory main loop: {e}", exc_info=True)
            with state_lock:
                factory_state["status"] = "degraded"
                factory_state["healing_log"].append(f"{datetime.datetime.now().isoformat()}: Critical error in main loop: {e}. Attempting self-recovery.")
            # Trigger a healing bot for the factory itself
            if bot_dispatcher and not any(b.purpose == "Factory self-recovery" for b in factory_state["dispatched_bots"].values()):
                 bot_dispatcher.dispatch_bot("optimization", "Factory self-recovery", {"issue": "main_loop_failure"})

        # Clean up old bots (completed bots can be removed after a while, or kept for history)
        # For simplicity, we'll just let them accumulate for dashboard view.
        
        shutdown_event.wait(CONFIG["MONITOR_INTERVAL_SECONDS"])
    
    logger.info("Bot Factory main loop stopped.")

# --- Flask Web Server ---

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gullah Geechee Bot Factory Dashboard</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🤖</text></svg>" />
    <style>
        body { font-family: 'Inter', sans-serif; }
        .grid-container { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; }
        .card { background-color: #1a202c; border-radius: 0.5rem; padding: 1.5rem; color: #cbd5e0; }
        .card h2 { color: #f6ad55; font-size: 1.25rem; margin-bottom: 1rem; }
        .status-online { color: #48bb78; }
        .status-degraded { color: #ecc94b; }
        .status-offline, .status-critical { color: #f56565; }
        .status-medium { color: #ed8936; }
        .status-low { color: #4299e1; }
        pre { white-space: pre-wrap; word-wrap: break-word; }
    </style>
</head>
<body class="bg-gray-900 text-gray-200 p-8">
    <h1 class="text-4xl font-bold text-center text-teal-400 mb-8">Gullah Geechee Bot Factory</h1>
    
    <div class="grid-container mb-8">
        <div class="card">
            <h2>Factory Status</h2>
            <p>Overall Status: <span id="factoryStatus" class="font-bold">Loading...</span></p>
            <p>Last Check: <span id="lastCheck">Loading...</span></p>
            <p>Pending Books: <span id="pendingBooks">Loading...</span></p>
            <p>Brand Health: <span id="brandHealth">Loading...</span></p>
        </div>
        <div class="card">
            <h2>Publishing Mindset</h2>
            <p class="italic text-gray-400" id="publishingMindset">Loading...</p>
        </div>
        <div class="card">
            <h2>Collective Intelligence</h2>
            <p class="italic text-gray-400" id="collectiveIntelligence">Loading...</p>
        </div>
    </div>

    <div class="grid-container mb-8">
        <div class="card">
            <h2>System Overview</h2>
            <div id="awarenessData" class="text-sm">Loading...</div>
        </div>
        <div class="card">
            <h2>Threat Landscape</h2>
            <div id="threats" class="text-sm">Loading...</div>
        </div>
        <div class="card">
            <h2>Marketing Opportunities</h2>
            <div id="marketingOpportunities" class="text-sm">Loading...</div>
        </div>
        <div class="card">
            <h2>Workflow Analysis</h2>
            <div id="workflowAnalysis" class="text-sm">Loading...</div>
        </div>
        <div class="card">
            <h2>Social Media Landscape</h2>
            <div id="socialMedia" class="text-sm">Loading...</div>
        </div>
        <div class="card">
            <h2>Brand Guardian Alerts</h2>
            <div id="brandAlerts" class="text-sm">Loading...</div>
        </div>
    </div>

    <div class="card mb-8">
        <h2>Dispatched Bots (<span id="botCount">0</span>)</h2>
        <div id="dispatchedBots" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">Loading...</div>
    </div>

    <div class="grid-container mb-8">
        <div class="card">
            <h2>Healing Log</h2>
            <div id="healingLog" class="text-xs max-h-48 overflow-y-auto">Loading...</div>
        </div>
        <div class="card">
            <h2>Evolution Log</h2>
            <div id="evolutionLog" class="text-xs max-h-48 overflow-y-auto">Loading...</div>
        </div>
    </div>

    <script>
        function updateDashboard() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('factoryStatus').textContent = data.status;
                    document.getElementById('factoryStatus').className = 'font-bold ' + (data.status === 'online' ? 'status-online' : 'status-degraded');
                    document.getElementById('lastCheck').textContent = new Date(data.last_check).toLocaleString();
                    document.getElementById('pendingBooks').textContent = data.awareness_data.pending_books || 'N/A';
                    document.getElementById('publishingMindset').textContent = data.awareness_data.publishing_mindset || 'N/A';
                    document.getElementById('collectiveIntelligence').textContent = data.awareness_data.collective_intelligence_protocol || 'N/A';
                    
                    const brandHealthScore = data.brand_health.score;
                    let brandHealthColor = 'status-online';
                    if (brandHealthScore < 70) brandHealthColor = 'status-critical';
                    else if (brandHealthScore < 90) brandHealthColor = 'status-degraded';
                    document.getElementById('brandHealth').innerHTML = `<span class="${brandHealthColor}">${brandHealthScore}%</span>`;


                    // Awareness Data
                    let awarenessHtml = '';
                    for (const key in data.awareness_data) {
                        if (key !== 'publishing_mindset' && key !== 'collective_intelligence_protocol') { // Filter out redundant info
                            const val = data.awareness_data[key];
                            const statusClass = (val.status === 'online' ? 'status-online' : val.status === 'offline' ? 'status-offline' : '');
                            awarenessHtml += `<p><strong>${key.replace(/_/g, ' ').toUpperCase()}:</strong> <span class="${statusClass}">${JSON.stringify(val)}</span></p>`;
                        }
                    }
                    document.getElementById('awarenessData').innerHTML = `<pre>${awarenessHtml}</pre>`;

                    // Threats
                    let threatsHtml = '';
                    if (Object.keys(data.threats).length > 0) {
                        for (const id in data.threats) {
                            const threat = data.threats[id];
                            const severityClass = 'status-' + threat.severity;
                            threatsHtml += `<p><strong class="${severityClass}">${threat.type.toUpperCase()}:</strong> ${threat.description} (ID: ${id})</p>`;
                        }
                    } else {
                        threatsHtml = '<p class="text-gray-500">No active threats detected.</p>';
                    }
                    document.getElementById('threats').innerHTML = `<pre>${threatsHtml}</pre>`;

                    // Marketing Opportunities
                    let marketingHtml = '';
                    if (Object.keys(data.marketing_opportunities).length > 0) {
                        for (const id in data.marketing_opportunities) {
                            const opp = data.marketing_opportunities[id];
                            marketingHtml += `<p><strong>${opp.type.toUpperCase()}:</strong> ${opp.description} (Topic: ${opp.topic || opp.event || opp.trend})</p>`;
                        }
                    } else {
                        marketingHtml = '<p class="text-gray-500">No current marketing opportunities.</p>';
                    }
                    document.getElementById('marketingOpportunities').innerHTML = `<pre>${marketingHtml}</pre>`;

                    // Workflow Analysis
                    let workflowHtml = '';
                    if (Object.keys(data.workflow_analysis).length > 0) {
                        for (const key in data.workflow_analysis) {
                            const issue = data.workflow_analysis[key];
                            const severityClass = 'status-' + issue.severity;
                            workflowHtml += `<p><strong class="${severityClass}">${key.replace(/_/g, ' ').toUpperCase()}:</strong> ${issue.issue}</p>`;
                        }
                    } else {
                        workflowHtml = '<p class="text-gray-500">Workflow is running smoothly.</p>';
                    }
                    document.getElementById('workflowAnalysis').innerHTML = `<pre>${workflowHtml}</pre>`;
                    
                    // Social Media
                    let socialHtml = '';
                    const social = data.social_media_landscape;
                    if (social.trends && social.trends.trending_hashtags) {
                        socialHtml += `<p><strong>Trending:</strong> ${social.trends.trending_hashtags.join(', ')}</p>`;
                    }
                    if (social.trends && social.trends.sentiment_overview) {
                        socialHtml += `<p><strong>Sentiment:</strong> ${social.trends.sentiment_overview}</p>`;
                    }
                    if (social.engagement_opportunity) {
                        socialHtml += `<p><strong>Engagement:</strong> ${social.engagement_opportunity.handle} - ${social.engagement_opportunity.action}</p>`;
                    }
                     if (social.scheduled_content) {
                        socialHtml += `<p><strong>Scheduled:</strong> Content for "${social.scheduled_content.topic}" on ${social.scheduled_content.platforms.join(', ')}.</p>`;
                    }

                    if (!socialHtml) {
                        socialHtml = '<p class="text-gray-500">No immediate social media insights.</p>';
                    }
                    document.getElementById('socialMedia').innerHTML = `<pre>${socialHtml}</pre>`;

                    // Brand Alerts
                    let brandAlertsHtml = '';
                    if (data.brand_health.alerts && data.brand_health.alerts.length > 0) {
                        data.brand_health.alerts.forEach(alert => {
                            const severityClass = 'status-' + alert.severity;
                            brandAlertsHtml += `<p><strong class="${severityClass}">${alert.type.toUpperCase()}:</strong> ${alert.description}</p>`;
                        });
                    } else {
                        brandAlertsHtml = '<p class="text-gray-500">No brand alerts.</p>';
                    }
                    document.getElementById('brandAlerts').innerHTML = `<pre>${brandAlertsHtml}</pre>`;


                    // Dispatched Bots
                    document.getElementById('botCount').textContent = Object.keys(data.dispatched_bots).length;
                    let botsHtml = '';
                    if (Object.keys(data.dispatched_bots).length > 0) {
                        for (const id in data.dispatched_bots) {
                            const bot = data.dispatched_bots[id];
                            botsHtml += `
                                <div class="p-3 bg-gray-800 rounded-md">
                                    <p class="font-bold">ID: ${bot.id.substring(0, 8)}...</p>
                                    <p>Type: <span class="text-blue-400">${bot.bot_type}</span></p>
                                    <p>Purpose: ${bot.purpose}</p>
                                    <p>Status: <span class="${bot.status === 'active' ? 'status-online' : 'status-low'}">${bot.status}</span></p>
                                    <p class="text-xs text-gray-500">Created: ${new Date(bot.created_at).toLocaleString()}</p>
                                </div>
                            `;
                        }
                    } else {
                        botsHtml = '<p class="col-span-full text-gray-500">No bots currently dispatched.</p>';
                    }
                    document.getElementById('dispatchedBots').innerHTML = botsHtml;

                    // Healing Log
                    document.getElementById('healingLog').innerHTML = data.healing_log.map(entry => `<p>${entry}</p>`).join('');

                    // Evolution Log
                    document.getElementById('evolutionLog').innerHTML = data.evolution_log.map(entry => `<p>${entry}</p>`).join('');


                })
                .catch(error => console.error('Error fetching dashboard data:', error));
        }

        // Update dashboard every 5 seconds
        setInterval(updateDashboard, 5000);
        // Initial load
        updateDashboard();
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/status')
def get_factory_status():
    with state_lock:
        status = factory_state.copy()
        status["dispatched_bots"] = {k: v.__dict__ for k, v in status["dispatched_bots"].items()}
        # Convert deques to lists for JSON serialization
        for key in ["evolution_log", "healing_log"]:
            if key in status:
                status[key] = list(status[key])
        return jsonify(status)

@app.route('/api/bots')
def list_dispatched_bots():
    with state_lock:
        return jsonify({k: v.__dict__ for k, v in factory_state["dispatched_bots"].items()})

@app.route('/api/dispatch', methods=['POST'])
def dispatch_new_bot():
    data = request.get_json()
    bot_type = data.get('bot_type')
    purpose = data.get('purpose')
    parameters = data.get('parameters')

    if not bot_type or not purpose:
        return jsonify({"error": "bot_type and purpose are required"}), 400
    
    if bot_dispatcher:
        bot_id = bot_dispatcher.dispatch_bot(bot_type, purpose, parameters)
        return jsonify({"message": f"Bot {bot_id} dispatched.", "bot_id": bot_id}), 201
    return jsonify({"error": "Bot Dispatcher not initialized"}), 500

@app.route('/api/threats')
def get_threats():
    with state_lock:
        return jsonify(factory_state["threats"])

@app.route('/api/marketing')
def get_marketing_opportunities():
    with state_lock:
        return jsonify(factory_state["marketing_opportunities"])

@app.route('/api/workflow')
def get_workflow_analysis():
    with state_lock:
        return jsonify(factory_state["workflow_analysis"])

@app.route('/api/social')
def get_social_media_landscape():
    with state_lock:
        return jsonify(factory_state["social_media_landscape"])

@app.route('/api/evolve', methods=['POST'])
def trigger_evolution():
    if evolution_engine:
        evolution_engine.evolve_factory()
        return jsonify({"message": "Evolution cycle triggered."}), 200
    return jsonify({"error": "Evolution Engine not initialized"}), 500

@app.route('/api/brand')
def get_brand_health():
    with state_lock:
        return jsonify(factory_state["brand_health"])

def run_flask_app():
    app.run(port=CONFIG["FACTORY_PORT"], debug=False, use_reloader=False)

if __name__ == '__main__':
    logger.info("Starting Gullah Geechee Bot Factory...")
    
    factory_thread = Thread(target=factory_loop, daemon=True)
    factory_thread.start()

    try:
        run_flask_app()
    except KeyboardInterrupt:
        logger.info("Shutting down Bot Factory...")
        shutdown_event.set()
        factory_thread.join(timeout=10)
        logger.info("Bot Factory shut down gracefully.")
    except Exception as e:
        logger.critical(f"Flask app terminated unexpectedly: {e}", exc_info=True)
        shutdown_event.set()
        factory_thread.join(timeout=10)
        logger.info("Bot Factory terminated due to Flask error.")

# Save to /Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/bot-factory.py
# (This comment is for the user and won't be part of the actual Python script functionality)