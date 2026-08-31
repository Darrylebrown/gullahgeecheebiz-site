import os
import sys
import json
import time
import queue
import logging
import threading
import signal
import atexit
from pathlib import Path
from datetime import datetime
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import random
import uuid
from flask import Flask, jsonify, request, abort
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
import joblib

sys.path.insert(0, str(Path(__file__).parent))
from agent_auth import require_agent_auth

# Constants
CONTROLLER_VERSION = "1.0.0"
MAX_RETRIES = 3
LEARNING_WINDOW = 1000  # Last 1000 tasks for performance analysis
HEALING_COOLDOWN = 300  # 5 minutes between healing attempts on same agent
STATE_FILE = "/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/controller_state.json"
MODEL_FILE = "/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/performance_model.joblib"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/controller.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PublishingController")

# Elite Publishing Mindset and Collective Intelligence Protocol
ELITE_PUBLISHING_MINDSET = "Published books change lives. Unsubmitted books do nothing."
COLLECTIVE_INTELLIGENCE_PROTOCOL = "One learns, everyone learns. One improves, all improve."

class AgentStatus(Enum):
    IDLE = auto()
    BUSY = auto()
    FAILED = auto()
    HEALING = auto()
    UPDATING = auto()

class TaskPriority(Enum):
    CRITICAL = 4  # Failed submissions needing retry
    HIGH = 3      # Time-sensitive submissions
    MEDIUM = 2    # Regular publishing tasks
    LOW = 1       # Background/improvement tasks

class TaskType(Enum):
    CONTENT_CREATION = auto()
    VALIDATION = auto()
    PACKAGING = auto()
    SUBMISSION = auto()
    MONITORING = auto()
    HEALING = auto()
    LEARNING = auto()

@dataclass
class Agent:
    id: str
    department: str
    capabilities: List[TaskType]
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    performance_score: float = 1.0  # 0.0-1.0, 1.0 is perfect
    failure_count: int = 0
    success_count: int = 0
    last_active: Optional[float] = None
    load_factor: float = 1.0  # Adjusts how much work this agent gets

@dataclass(order=True)
class Task:
    priority: int
    timestamp: float
    task_type: TaskType = field(compare=False)
    book_id: str = field(compare=False)
    payload: Dict = field(compare=False)
    task_id: str = field(compare=False, default_factory=lambda: str(uuid.uuid4()))
    retries: int = field(compare=False, default=0)
    depends_on: Optional[List[str]] = field(compare=False, default=None)  # Other task IDs

class PublishingController:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.config["AGENT_TOKEN"] = os.environ.get("AGENT_TOKEN_PUBLISHING_CONTROLLER", "")
        self._setup_endpoints()

        @self.app.before_request
        def _auth():
            require_agent_auth("AGENT_TOKEN_PUBLISHING_CONTROLLER")
        
        # Core components
        self.task_queue = queue.PriorityQueue()
        self.agent_registry: Dict[str, Agent] = {}
        self.task_history = deque(maxlen=LEARNING_WINDOW)
        self.failure_history = defaultdict(int)
        self.healing_cooldown: Dict[str, float] = {}
        self.performance_model = None
        self.label_encoders = {}
        
        # Threading
        self.scheduler_thread = None
        self.healing_thread = None
        self.learning_thread = None
        self.brain_thread = None
        self.running = True
        
        # Initialize
        self._initialize_agents()
        self._load_state()
        self._load_performance_model()
        
        # Start background threads
        self._start_background_threads()
        
        # Register shutdown handlers
        atexit.register(self._shutdown)
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        
        logger.info(f"Gullah Geechee Biz Publishing Controller v{CONTROLLER_VERSION} initialized")
        logger.info(f"Elite Publishing Mindset: {ELITE_PUBLISHING_MINDSET}")
        logger.info(f"Collective Intelligence Protocol: {COLLECTIVE_INTELLIGENCE_PROTOCOL}")

    def _setup_endpoints(self):
        @self.app.route('/')
        def dashboard():
            return jsonify({
                "status": "operational",
                "version": CONTROLLER_VERSION,
                "agents": len(self.agent_registry),
                "queue_size": self.task_queue.qsize(),
                "pending_books": self._count_pending_books(),
                "mindset": ELITE_PUBLISHING_MINDSET,
                "protocol": COLLECTIVE_INTELLIGENCE_PROTOCOL
            })
            
        @self.app.route('/api/status')
        def api_status():
            return jsonify(self._get_system_status())
            
        @self.app.route('/api/agents', methods=['GET'])
        def api_agents():
            return jsonify({
                agent_id: {
                    "department": agent.department,
                    "status": agent.status.name,
                    "current_task": agent.current_task,
                    "performance": agent.performance_score,
                    "load": agent.load_factor
                }
                for agent_id, agent in self.agent_registry.items()
            })
            
        @self.app.route('/api/assign', methods=['POST'])
        def api_assign():
            data = request.json
            if not data or 'task_type' not in data or 'book_id' not in data:
                abort(400, "Missing required fields: task_type, book_id")
                
            try:
                task_type = TaskType[data['task_type']]
                priority = TaskPriority[data.get('priority', 'MEDIUM')].value
                payload = data.get('payload', {})
                depends_on = data.get('depends_on', None)
                
                task = Task(
                    priority=priority,
                    timestamp=time.time(),
                    task_type=task_type,
                    book_id=data['book_id'],
                    payload=payload,
                    depends_on=depends_on
                )
                
                self.task_queue.put(task)
                logger.info(f"Assigned new task {task.task_id} for book {task.book_id}")
                return jsonify({"task_id": task.task_id, "status": "queued"})
            except KeyError as e:
                abort(400, f"Invalid enum value: {str(e)}")
                
        @self.app.route('/api/queue', methods=['GET'])
        def api_queue():
            # Note: This is a simplified view since we can't easily inspect the PriorityQueue
            return jsonify({
                "queue_size": self.task_queue.qsize(),
                "recent_tasks": [t.task_id for t in list(self.task_queue.queue)[:10]] if not self.task_queue.empty() else []
            })
            
        @self.app.route('/api/learn', methods=['POST'])
        def api_learn():
            data = request.json
            if not data or 'task_id' not in data or 'outcome' not in data:
                abort(400, "Missing required fields: task_id, outcome")
                
            self._process_learning_signal(data['task_id'], data['outcome'], data.get('details', {}))
            return jsonify({"status": "learning signal processed"})
            
        @self.app.route('/api/analytics', methods=['GET'])
        def api_analytics():
            return jsonify(self._get_analytics())
            
        @self.app.route('/api/heal', methods=['POST'])
        def api_heal():
            data = request.json
            if not data or 'agent_id' not in data:
                abort(400, "Missing required field: agent_id")
                
            agent_id = data['agent_id']
            if agent_id not in self.agent_registry:
                abort(404, "Agent not found")
                
            self._trigger_healing(agent_id, data.get('force', False))
            return jsonify({"status": f"healing initiated for {agent_id}"})

    def _initialize_agents(self):
        """Initialize the 200 new agents and 170 existing agents"""
        # Departments for new agents
        departments = [
            "content_creation", "editing", "design", 
            "formatting", "submission", "monitoring"
        ]
        
        # Create new agents (AGENT-1000 to AGENT-1199)
        for i in range(1000, 1200):
            agent_id = f"AGENT-{i}"
            department = departments[i % len(departments)]
            
            # Assign capabilities based on department
            if department == "content_creation":
                capabilities = [TaskType.CONTENT_CREATION]
            elif department == "editing":
                capabilities = [TaskType.VALIDATION]
            elif department == "design":
                capabilities = [TaskType.PACKAGING]
            elif department == "formatting":
                capabilities = [TaskType.PACKAGING]
            elif department == "submission":
                capabilities = [TaskType.SUBMISSION]
            else:  # monitoring
                capabilities = [TaskType.MONITORING]
                
            self.agent_registry[agent_id] = Agent(
                id=agent_id,
                department=department,
                capabilities=capabilities
            )
        
        # Simulate existing agents (would be loaded from actual systems in production)
        for i in range(1, 171):
            agent_id = f"LEGACY-AGENT-{i:03d}"
            # Existing agents might have multiple capabilities
            capabilities = list(TaskType)
            if i % 5 == 0:  # 20% are specialized
                capabilities = [random.choice(list(TaskType))]
                
            self.agent_registry[agent_id] = Agent(
                id=agent_id,
                department="legacy",
                capabilities=capabilities
            )
        
        logger.info(f"Initialized {len(self.agent_registry)} agents")

    def _start_background_threads(self):
        """Start all background processing threads"""
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.healing_thread = threading.Thread(target=self._healing_loop, daemon=True)
        self.learning_thread = threading.Thread(target=self._learning_loop, daemon=True)
        self.brain_thread = threading.Thread(target=self._brain_loop, daemon=True)
        
        self.scheduler_thread.start()
        self.healing_thread.start()
        self.learning_thread.start()
        self.brain_thread.start()
        
        logger.info("Background threads started")

    def _scheduler_loop(self):
        """Main scheduling loop that assigns tasks to agents"""
        while self.running:
            try:
                if not self.task_queue.empty():
                    task = self.task_queue.get_nowait()
                    
                    # Check dependencies
                    if task.depends_on and not self._check_dependencies(task.depends_on):
                        # Put back in queue with slight delay
                        time.sleep(0.1)
                        self.task_queue.put(task)
                        continue
                    
                    # Find best available agent
                    agent = self._find_best_agent_for_task(task)
                    if agent:
                        agent.status = AgentStatus.BUSY
                        agent.current_task = task.task_id
                        agent.last_active = time.time()
                        
                        # Simulate task execution (in real system, this would call agent)
                        logger.info(f"Assigned task {task.task_id} to {agent.id}")
                        threading.Thread(
                            target=self._execute_task,
                            args=(agent, task),
                            daemon=True
                        ).start()
                    else:
                        # No available agent, requeue with slight priority boost
                        task.priority = min(task.priority + 1, TaskPriority.CRITICAL.value)
                        self.task_queue.put(task)
                        time.sleep(0.5)  # Prevent tight loop
                else:
                    time.sleep(0.1)  # Small sleep when queue is empty
            except Exception as e:
                logger.error(f"Scheduler error: {str(e)}", exc_info=True)
                time.sleep(1)

    def _execute_task(self, agent: Agent, task: Task):
        """Simulate task execution and report outcome"""
        try:
            # Simulate work time based on task type and agent performance
            work_time = self._simulate_work_time(task.task_type, agent.performance_score)
            time.sleep(work_time)
            
            # Random chance of failure based on performance score
            if random() > agent.performance_score:
                raise Exception("Simulated task failure")
                
            # Task succeeded
            agent.status = AgentStatus.IDLE
            agent.current_task = None
            agent.success_count += 1
            self._update_agent_performance(agent.id, True)
            
            # Record task completion
            self.task_history.append({
                "task_id": task.task_id,
                "agent_id": agent.id,
                "task_type": task.task_type.name,
                "book_id": task.book_id,
                "outcome": "success",
                "duration": work_time,
                "timestamp": time.time()
            })
            
            logger.info(f"Task {task.task_id} completed by {agent.id}")
            
            # If this was a submission task, trigger monitoring
            if task.task_type == TaskType.SUBMISSION:
                self._schedule_monitoring(task.book_id)
                
        except Exception as e:
            # Task failed
            logger.warning(f"Task {task.task_id} failed: {str(e)}")
            agent.status = AgentStatus.IDLE
            agent.current_task = None
            agent.failure_count += 1
            self._update_agent_performance(agent.id, False)
            
            # Record failure
            self.task_history.append({
                "task_id": task.task_id,
                "agent_id": agent.id,
                "task_type": task.task_type.name,
                "book_id": task.book_id,
                "outcome": "failure",
                "error": str(e),
                "timestamp": time.time()
            })
            
            # Retry if possible
            if task.retries < MAX_RETRIES:
                task.retries += 1
                task.priority = TaskPriority.CRITICAL.value  # Boost priority for retry
                self.task_queue.put(task)
            else:
                logger.error(f"Task {task.task_id} failed after {MAX_RETRIES} retries")
                # Trigger healing for the agent
                self._trigger_healing(agent.id)

    def _simulate_work_time(self, task_type: TaskType, performance: float) -> float:
        """Simulate realistic work times for different task types"""
        base_times = {
            TaskType.CONTENT_CREATION: 10.0,
            TaskType.VALIDATION: 3.0,
            TaskType.PACKAGING: 5.0,
            TaskType.SUBMISSION: 2.0,
            TaskType.MONITORING: 1.0,
            TaskType.HEALING: 4.0,
            TaskType.LEARNING: 2.0
        }
        
        # Adjust based on performance (better agents work faster)
        time_adjustment = 0.5 + (performance * 0.5)  # 0.5-1.0 multiplier
        return base_times[task_type] * time_adjustment * (0.9 + random() * 0.2)  # Some randomness

    def _find_best_agent_for_task(self, task: Task) -> Optional[Agent]:
        """Find the best available agent for a given task"""
        eligible_agents = [
            agent for agent in self.agent_registry.values()
            if task.task_type in agent.capabilities 
            and agent.status == AgentStatus.IDLE
            and (agent.id not in self.healing_cooldown or 
                 time.time() - self.healing_cooldown[agent.id] > HEALING_COOLDOWN)
        ]
        
        if not eligible_agents:
            return None
            
        # Use performance model if available
        if self.performance_model:
            try:
                # Prepare features for prediction
                features = self._prepare_prediction_features(task, eligible_agents)
                predictions = self.performance_model.predict(features)
                
                # Find agent with highest predicted success probability
                best_idx = np.argmax(predictions)
                return eligible_agents[best_idx]
            except Exception as e:
                logger.warning(f"Performance model prediction failed: {str(e)}")
                # Fall back to simple selection
        
        # Simple selection based on performance score and load factor
        return max(
            eligible_agents,
            key=lambda a: a.performance_score * a.load_factor
        )

    def _prepare_prediction_features(self, task: Task, agents: List[Agent]) -> List[List[float]]:
        """Prepare features for performance prediction model"""
        features = []
        task_type_enc = self.label_encoders['task_type'].transform([task.task_type.name])[0]
        
        for agent in agents:
            agent_dept_enc = self.label_encoders['department'].transform([agent.department])[0]
            
            features.append([
                task_type_enc,
                agent_dept_enc,
                agent.performance_score,
                agent.success_count,
                agent.failure_count,
                agent.load_factor,
                time.time() - (agent.last_active if agent.last_active else 0),
                self._calculate_workload(agent.department)
            ])
            
        return features

    def _calculate_workload(self, department: str) -> float:
        """Calculate current workload for a department"""
        return sum(
            1 for agent in self.agent_registry.values() 
            if agent.department == department and agent.status == AgentStatus.BUSY
        ) / sum(1 for agent in self.agent_registry.values() if agent.department == department)

    def _check_dependencies(self, task_ids: List[str]) -> bool:
        """Check if all dependent tasks have completed"""
        # In a real system, we'd check a task completion database
        # For simulation, we'll assume 90% of dependencies are met
        return random() > 0.1

    def _schedule_monitoring(self, book_id: str):
        """Schedule monitoring tasks for a newly submitted book"""
        for _ in range(3):  # Schedule 3 monitoring tasks spread out
            delay = random() * 24 * 3600  # Within 24 hours
            task = Task(
                priority=TaskPriority.MEDIUM.value,
                timestamp=time.time() + delay,
                task_type=TaskType.MONITORING,
                book_id=book_id,
                payload={"monitoring_type": "post_submission"}
            )
            self.task_queue.put(task)

    def _healing_loop(self):
        """Background loop for monitoring and healing agents"""
        while self.running:
            try:
                # Check for agents needing healing
                for agent_id, agent in self.agent_registry.items():
                    # Skip if recently healed or already being healed
                    if (agent.status == AgentStatus.HEALING or 
                        (agent_id in self.healing_cooldown and 
                         time.time() - self.healing_cooldown[agent_id] < HEALING_COOLDOWN)):
                        continue
                        
                    # Check failure rate
                    total_tasks = agent.success_count + agent.failure_count
                    if total_tasks > 10 and agent.failure_count / total_tasks > 0.3:  # 30% failure rate
                        self._trigger_healing(agent_id)
                        
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Healing loop error: {str(e)}", exc_info=True)
                time.sleep(30)

    def _trigger_healing(self, agent_id: str, force: bool = False):
        """Initiate healing process for an agent"""
        if agent_id not in self.agent_registry:
            logger.warning(f"Attempted to heal unknown agent {agent_id}")
            return
            
        agent = self.agent_registry[agent_id]
        
        # Check cooldown unless forced
        if not force and agent_id in self.healing_cooldown:
            if time.time() - self.healing_cooldown[agent_id] < HEALING_COOLDOWN:
                logger.info(f"Healing for {agent_id} on cooldown")
                return
                
        logger.info(f"Initiating healing for agent {agent_id}")
        agent.status = AgentStatus.HEALING
        self.healing_cooldown[agent_id] = time.time()
        
        # Create healing task
        task = Task(
            priority=TaskPriority.HIGH.value,
            timestamp=time.time(),
            task_type=TaskType.HEALING,
            book_id="system",
            payload={"agent_id": agent_id}
        )
        self.task_queue.put(task)

    def _learning_loop(self):
        """Background loop for continuous learning"""
        while self.running:
            try:
                if len(self.task_history) > 100:  # Wait for sufficient data
                    self._update_performance_model()
                    
                time.sleep(60)  # Update model every minute
            except Exception as e:
                logger.error(f"Learning loop error: {str(e)}", exc_info=True)
                time.sleep(120)

    def _update_performance_model(self):
        """Update the performance prediction model"""
        try:
            if not self.task_history:
                return
                
            # Prepare training data
            X = []
            y = []
            
            for record in self.task_history:
                if 'outcome' not in record:
                    continue
                    
                # Encode categorical features
                if 'task_type' not in self.label_encoders:
                    self.label_encoders['task_type'] = LabelEncoder()
                    task_types = list(set(r['task_type'] for r in self.task_history if 'task_type' in r))
                    self.label_encoders['task_type'].fit(task_types)
                    
                if 'department' not in self.label_encoders:
                    departments = list(set(self.agent_registry[a].department 
                                         for r in self.task_history 
                                         if 'agent_id' in r for a in [r['agent_id']] 
                                         if a in self.agent_registry))
                    self.label_encoders['department'] = LabelEncoder()
                    self.label_encoders['department'].fit(departments)
                
                agent = self.agent_registry.get(record['agent_id'], None)
                if not agent:
                    continue
                    
                task_type_enc = self.label_encoders['task_type'].transform([record['task_type']])[0]
                agent_dept_enc = self.label_encoders['department'].transform([agent.department])[0]
                
                # Features
                X.append([
                    task_type_enc,
                    agent_dept_enc,
                    agent.performance_score,
                    agent.success_count,
                    agent.failure_count,
                    agent.load_factor,
                    record['timestamp'] - (agent.last_active if agent.last_active else 0),
                    self._calculate_workload(agent.department)
                ])
                
                # Target (1 for success, 0 for failure)
                y.append(1 if record['outcome'] == 'success' else 0)
            
            if len(X) < 50:  # Not enough data
                return
                
            # Train model
            self.performance_model = RandomForestRegressor(n_estimators=50, random_state=42)
            self.performance_model.fit(X, y)
            
            # Save model
            joblib.dump({
                'model': self.performance_model,
                'label_encoders': self.label_encoders
            }, MODEL_FILE)
            
            logger.info("Performance model updated")
        except Exception as e:
            logger.error(f"Error updating performance model: {str(e)}", exc_info=True)

    def _brain_loop(self):
        """Central intelligence that analyzes patterns and makes predictions"""
        while self.running:
            try:
                # Analyze bottlenecks
                self._analyze_bottlenecks()
                
                # Predict high-potential books
                self._predict_book_potential()
                
                # Optimize resource allocation
                self._optimize_resource_allocation()
                
                time.sleep(300)  # Run analysis every 5 minutes
            except Exception as e:
                logger.error(f"Brain loop error: {str(e)}", exc_info=True)
                time.sleep(600)

    def _analyze_bottlenecks(self):
        """Identify potential bottlenecks in the workflow"""
        department_load = defaultdict(int)
        department_capacity = defaultdict(int)
        
        for agent in self.agent_registry.values():
            department_capacity[agent.department] += 1
            if agent.status == AgentStatus.BUSY:
                department_load[agent.department] += 1
                
        bottlenecks = []
        for dept, capacity in department_capacity.items():
            load = department_load[dept]
            utilization = load / capacity if capacity > 0 else 0
            if utilization > 0.8:  # 80% utilization
                bottlenecks.append(dept)
                
        if bottlenecks:
            logger.warning(f"Potential bottlenecks detected in departments: {', '.join(bottlenecks)}")
            
            # Adjust priorities to alleviate bottlenecks
            for task in list(self.task_queue.queue):
                if (isinstance(task, Task) and 
                    task.task_type in [TaskType.CONTENT_CREATION, TaskType.VALIDATION, TaskType.PACKAGING]):
                    agent = next(
                        (a for a in self.agent_registry.values() 
                         if a.status == AgentStatus.IDLE and task.task_type in a.capabilities and 
                         a.department in bottlenecks),
                        None
                    )
                    if agent:
                        # Boost priority for tasks that can utilize bottlenecked departments
                        new_priority = min(task.priority + 1, TaskPriority.CRITICAL.value)
                        if new_priority != task.priority:
                            task.priority = new_priority
                            logger.info(f"Boosted priority for task {task.task_id} to alleviate {agent.department} bottleneck")

    def _predict_book_potential(self):
        """Predict which books are likely to perform best"""
        # In a real system, this would analyze book metadata, historical data, etc.
        # For simulation, we'll just log that the analysis ran
        logger.info("Book potential analysis completed")

    def _optimize_resource_allocation(self):
        """Optimize how agents are assigned to departments"""
        # Analyze performance by department
        dept_performance = defaultdict(list)
        for agent in self.agent_registry.values():
            if agent.success_count + agent.failure_count > 0:
                dept_performance[agent.department].append(
                    agent.success_count / (agent.success_count + agent.failure_count)
                )
                
        avg_dept_performance = {
            dept: sum(perfs)/len(perfs) if perfs else 0.5
            for dept, perfs in dept_performance.items()
        }
        
        # Identify strongest and weakest departments
        if not avg_dept_performance:
            logger.info('No performance data available for department optimization')
            return
        strongest_dept = max(avg_dept_performance.items(), key=lambda x: x[1])[0]
        weakest_dept = min(avg_dept_performance.items(), key=lambda x: x[1])[0]
        
        logger.info(f"Performance by department - Strongest: {strongest_dept}, Weakest: {weakest_dept}")
        
        # Consider reassigning agents from weakest to strongest department
        # (In real system, would be more nuanced with capacity analysis)
        if (avg_dept_performance[strongest_dept] - avg_dept_performance[weakest_dept] > 0.2 and 
            len([a for a in self.agent_registry.values() if a.department == weakest_dept]) > 5):
            
            # Find a crossover agent (has capabilities for both departments)
            crossover_agent = next(
                (a for a in self.agent_registry.values() 
                 if a.department == weakest_dept and 
                 any(t in a.capabilities for t in self._get_department_task_types(strongest_dept))),
                None
            )
            
            if crossover_agent:
                logger.info(f"Reassigning {crossover_agent.id} from {weakest_dept} to {strongest_dept}")
                crossover_agent.department = strongest_dept

    def _get_department_task_types(self, department: str) -> List[TaskType]:
        """Get typical task types for a department"""
        if department == "content_creation":
            return [TaskType.CONTENT_CREATION]
        elif department == "editing":
            return [TaskType.VALIDATION]
        elif department in ["design", "formatting"]:
            return [TaskType.PACKAGING]
        elif department == "submission":
            return [TaskType.SUBMISSION]
        elif department == "monitoring":
            return [TaskType.MONITORING]
        else:
            return list(TaskType)  # Legacy agents

    def _process_learning_signal(self, task_id: str, outcome: str, details: Dict):
        """Process an explicit learning signal from a task"""
        # Find the task in history
        task_record = next((t for t in self.task_history if t.get('task_id') == task_id), None)
        if not task_record:
            logger.warning(f"Learning signal for unknown task {task_id}")
            return
            
        # Update the record
        task_record['outcome'] = outcome
        task_record['details'] = details
        
        # Update agent performance
        if 'agent_id' in task_record and task_record['agent_id'] in self.agent_registry:
            agent = self.agent_registry[task_record['agent_id']]
            success = outcome == 'success'
            
            if success:
                agent.success_count += 1
            else:
                agent.failure_count += 1
                
            self._update_agent_performance(agent.id, success)
            
        logger.info(f"Processed learning signal for task {task_id}")

    def _update_agent_performance(self, agent_id: str, success: bool):
        """Update an agent's performance score based on task outcome"""
        if agent_id not in self.agent_registry:
            return
            
        agent = self.agent_registry[agent_id]
        total_tasks = agent.success_count + agent.failure_count
        
        if total_tasks == 0:
            agent.performance_score = 1.0
        else:
            # Simple moving average of success rate
            agent.performance_score = agent.success_count / total_tasks
            
            # Adjust load factor (agents with lower performance get less work)
            if total_tasks > 10:
                agent.load_factor = min(1.0, max(0.1, agent.performance_score))
                
        logger.debug(f"Updated performance for {agent_id}: {agent.performance_score}")

    def _count_pending_books(self) -> int:
        """Count unique books in the pipeline"""
        # In a real system, this would query a database
        # For simulation, we'll return the count of unique book_ids in recent tasks
        unique_books = set()
        for task in list(self.task_queue.queue):
            if isinstance(task, Task):
                unique_books.add(task.book_id)
                
        return len(unique_books)

    def _get_system_status(self) -> Dict:
        """Get overall system status"""
        agent_counts = defaultdict(int)
        for agent in self.agent_registry.values():
            agent_counts[agent.status.name] += 1
            
        return {
            "status": "operational",
            "agents": {
                "total": len(self.agent_registry),
                "by_status": dict(agent_counts)
            },
            "queue": {
                "size": self.task_queue.qsize(),
                "pending_books": self._count_pending_books()
            },
            "performance": {
                "model_ready": self.performance_model is not None,
                "recent_tasks": len(self.task_history),
                "success_rate": self._calculate_overall_success_rate()
            }
        }

    def _calculate_overall_success_rate(self) -> float:
        """Calculate recent task success rate"""
        if not self.task_history:
            return 0.0
            
        successes = sum(1 for t in self.task_history if t.get('outcome') == 'success')
        return successes / len(self.task_history)

    def _get_analytics(self) -> Dict:
        """Get performance analytics"""
        # Success rates by department
        dept_stats = defaultdict(lambda: {'success': 0, 'total': 0})
        for record in self.task_history:
            if 'agent_id' in record and record['agent_id'] in self.agent_registry:
                dept = self.agent_registry[record['agent_id']].department
                dept_stats[dept]['total'] += 1
                if record.get('outcome') == 'success':
                    dept_stats[dept]['success'] += 1
                    
        # Format department stats
        formatted_dept_stats = {}
        for dept, stats in dept_stats.items():
            formatted_dept_stats[dept] = {
                'success_rate': stats['success'] / stats['total'] if stats['total'] > 0 else 0,
                'total_tasks': stats['total']
            }
            
        # Recent failures
        recent_failures = [
            {
                'task_id': r['task_id'],
                'agent_id': r.get('agent_id', 'unknown'),
                'error': r.get('error', 'unknown'),
                'timestamp': r['timestamp']
            }
            for r in self.task_history 
            if r.get('outcome') == 'failure'
        ][-10:]  # Last 10 failures
        
        return {
            "departments": formatted_dept_stats,
            "recent_failures": recent_failures,
            "overall_success_rate": self._calculate_overall_success_rate(),
            "agent_performance": {
                "top_5": sorted(
                    [(a.id, a.performance_score) for a in self.agent_registry.values()],
                    key=lambda x: x[1],
                    reverse=True
                )[:5],
                "bottom_5": sorted(
                    [(a.id, a.performance_score) for a in self.agent_registry.values()],
                    key=lambda x: x[1]
                )[:5]
            }
        }

    def _load_state(self):
        """Load controller state from disk"""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                    
                # Load agent states
                if 'agents' in state:
                    for agent_id, agent_state in state['agents'].items():
                        if agent_id in self.agent_registry:
                            self.agent_registry[agent_id].status = AgentStatus[agent_state['status']]
                            self.agent_registry[agent_id].performance_score = agent_state['performance_score']
                            self.agent_registry[agent_id].success_count = agent_state['success_count']
                            self.agent_registry[agent_id].failure_count = agent_state['failure_count']
                            self.agent_registry[agent_id].load_factor = agent_state.get('load_factor', 1.0)
                
                # Load task queue (simplified - in real system would need more complex serialization)
                logger.info("Loaded controller state from disk")
        except Exception as e:
            logger.error(f"Error loading state: {str(e)}")

    def _save_state(self):
        """Save controller state to disk"""
        try:
            state = {
                'agents': {
                    agent_id: {
                        'status': agent.status.name,
                        'performance_score': agent.performance_score,
                        'success_count': agent.success_count,
                        'failure_count': agent.failure_count,
                        'load_factor': agent.load_factor
                    }
                    for agent_id, agent in self.agent_registry.items()
                },
                'timestamp': time.time()
            }
            
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
                
            logger.debug("Saved controller state to disk")
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")

    def _load_performance_model(self):
        """Load the performance prediction model from disk"""
        try:
            if os.path.exists(MODEL_FILE):
                model_data = joblib.load(MODEL_FILE)
                self.performance_model = model_data['model']
                self.label_encoders = model_data['label_encoders']
                logger.info("Loaded performance model from disk")
        except Exception as e:
            logger.error(f"Error loading performance model: {str(e)}")

    def _shutdown(self):
        """Graceful shutdown procedure"""
        self.running = False
        
        # Wait for threads to finish
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=1)
        if self.healing_thread:
            self.healing_thread.join(timeout=1)
        if self.learning_thread:
            self.learning_thread.join(timeout=1)
        if self.brain_thread:
            self.brain_thread.join(timeout=1)
            
        # Save final state
        self._save_state()
        
        logger.info("Publishing Controller shutdown complete")

    def _handle_signal(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self._shutdown()
        raise SystemExit(0)

    def run(self):
        """Run the controller web server"""
        logger.info("Starting Publishing Controller web server on port 8090")
        self.app.run(host='127.0.0.1', port=8090)

if __name__ == '__main__':
    controller = PublishingController()
    controller.run()