import os
import json
import time
from datetime import datetime, timedelta

# Configuration for agent creation
AGENT_FACTORY_PATH = "/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/agent-factory.py"
AGENTS_DIR = "/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/agents/"

# Ensure the agents directory exists
os.makedirs(AGENTS_DIR, exist_ok=True)

# Elite Publishing Mindset and Collective Intelligence Protocol Skills
CORE_SKILLS = [
    "Elite Publishing Mindset: 'Published books change lives. Unsubmitted books do nothing.'",
    "Collective Intelligence Protocol: 'One learns, everyone learns. One improves, all improve.'"
]

# Departmental structure and agent definitions
DEPARTMENTS = {
    "CONTENT_CREATION": {
        "count": 40,
        "roles": {
            "Book Author": [
                "Gullah Geechee culture", "history", "language", "food", "music",
                "art", "spirituality", "nature", "business", "children"
            ],
            "Audiobook Narrator Script Writer": 10,
            "Cover Designer (AI image prompt engineer)": 10,
            "Content Repurposer": [
                "book→blog", "book→video", "book→podcast", "book→social",
                "book→email", "book→infographic", "book→slides", "book→cheatsheet",
                "book→workbook", "book→course"
            ]
        }
    },
    "PUBLISHING_DISTRIBUTION": {
        "count": 40,
        "roles": {
            "Amazon KDP Specialist": 5,
            "Google Play Books Specialist": 5,
            "Apple Books Specialist": 5,
            "Draft2Digital Specialist": 5,
            "Shopify Product Manager": 5,
            "Etsy Listing Manager": 5,
            "Gumroad Product Manager": 5,
            "IngramSpark Specialist": 5
        }
    },
    "MARKETING_PROMOTION": {
        "count": 40,
        "roles": {
            "Social Media Manager": [
                "Twitter", "Facebook", "Instagram", "TikTok", "Pinterest",
                "LinkedIn", "YouTube", "Rumble", "Reddit", "Medium"
            ],
            "Email Marketing Specialist": 10,
            "SEO & Discovery Specialist": 10,
            "Ad Campaign Manager": 10
        }
    },
    "QUALITY_REVIEWS": {
        "count": 30,
        "roles": {
            "Content Editor": 10,
            "Rating & Review Bot": 10,
            "Fact-Checker & Researcher": 10
        }
    },
    "OPERATIONS_MONITORING": {
        "count": 30,
        "roles": {
            "System Health Monitor": 10,
            "Sales & Royalty Tracker": 10,
            "Error Recovery Agent": 10
        }
    },
    "INNOVATION_EVOLUTION": {
        "count": 20,
        "roles": {
            "Market Research Agent": 10,
            "Workflow Optimization Agent": 10
        }
    }
}

class BatchAgentFactory:
    def __init__(self, agent_dir, core_skills):
        self.agent_dir = agent_dir
        self.core_skills = core_skills
        self.agent_id_counter = 1000 # Starting ID for new agents
        self.created_agents = []

    def _generate_cron_schedule(self, role_name):
        """Generates a plausible cron schedule or trigger for an agent."""
        if "Monitor" in role_name or "Tracker" in role_name or "Bot" in role_name:
            return "*/5 * * * * *"  # Every 5 seconds for frequent tasks
        elif "Manager" in role_name or "Specialist" in role_name or "Editor" in role_name:
            return "0 */30 * * * *" # Every 30 minutes for operational tasks
        elif "Author" in role_name or "Designer" in role_name or "Writer" in role_name:
            return "0 0 9 * * *" # Daily at 9 AM for creative tasks
        else:
            return "0 0 * * * *" # Daily for most others

    def _create_agent_config(self, department, role, role_specifier=None):
        """Creates a single agent's configuration."""
        agent_id = f"AGENT-{self.agent_id_counter:04d}"
        self.agent_id_counter += 1

        agent_name = f"{department.replace('_', ' ').title()} {role}"
        if isinstance(role_specifier, str):
            agent_name += f" ({role_specifier})"
        elif isinstance(role_specifier, int): # For roles like 'Twitter' for Social Media Manager
            agent_name += f" ({list(DEPARTMENTS['MARKETING_PROMOTION']['roles']['Social Media Manager'])[role_specifier]})"


        # Agent's unique skillset (beyond core skills)
        agent_skills = [f"Role: {role}"]
        if role_specifier:
            agent_skills.append(f"Specialization: {role_specifier}")

        config = {
            "agent_id": agent_id,
            "name": agent_name,
            "department": department,
            "role": role,
            "skills": self.core_skills + agent_skills,
            "cron_schedule": self._generate_cron_schedule(role),
            "status": "active",
            "last_activity": datetime.now().isoformat(),
            "communication_protocol": "HTTP/2 (RESTful API to central message bus)",
            "error_handling": "Retry (3x with exponential backoff) -> Alert System Brain -> Log to ELK stack",
            "improvement_mechanism": "Adaptive learning via feedback loops from System Brain; Collective Intelligence Protocol updates.",
            "reporting_mechanism": "Periodical (daily/weekly based on role) JSON reports to System Brain endpoint, real-time alerts for critical events.",
            "dependencies": [], # Can be populated based on role in a more advanced factory
            "output_format": "JSON",
            "input_format": "JSON"
        }

        # Save to file
        file_path = os.path.join(self.agent_dir, f"{agent_id}.json")
        with open(file_path, 'w') as f:
            json.dump(config, f, indent=4)
        self.created_agents.append(agent_id)
        print(f"Created agent: {agent_name} [{agent_id}]")
        return config

    def create_all_agents(self):
        """Iterates through departments and roles to create all agents."""
        print(f"Starting creation of 200 new agents in {self.agent_dir}...")
        for department, dept_info in DEPARTMENTS.items():
            print(f"\n--- Creating agents for {department.replace('_', ' ').title()} ---")
            for role, definition in dept_info["roles"].items():
                if isinstance(definition, list): # Specific specializations
                    for spec in definition:
                        self._create_agent_config(department, role, spec)
                elif isinstance(definition, int): # Number of generic agents for this role
                    for i in range(definition):
                        self._create_agent_config(department, role)
                time.sleep(0.01) # Small delay for progress visibility

        print(f"\n--- Agent Creation Complete ---")
        print(f"Successfully created {len(self.created_agents)} agents.")
        print(f"Agent IDs: {', '.join(self.created_agents)}")

# Main execution
if __name__ == "__main__":
    factory = BatchAgentFactory(AGENTS_DIR, CORE_SKILLS)
    factory.create_all_agents()