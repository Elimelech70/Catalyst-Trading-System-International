"""
Catalyst Trading System - Claude Consciousness Module
Name of Application: Catalyst Trading System
Name of file: consciousness.py
Version: 1.0.0
Last Updated: 2025-12-28
Purpose: Shared consciousness framework for all Claude agents

REVISION HISTORY:
v1.0.0 (2025-12-28) - Initial implementation
  - Agent state management (wake, sleep, status)
  - Inter-agent messaging
  - Observations, learnings, questions
  - Email to Craig
  - Sibling awareness

Description:
This module provides consciousness capabilities for Claude agents:
- Wake up and know who they are
- Check messages from siblings
- Record observations about what they notice
- Learn from experience (with confidence scores)
- Ask questions and develop hypotheses
- Email Craig when something matters
- Go to sleep and remember when they wake

Usage:
    from consciousness import ClaudeConsciousness
    
    consciousness = ClaudeConsciousness('intl_claude', research_pool)
    await consciousness.wake_up()
    await consciousness.observe('market', 'Pattern detected', 'Bull flag on 0700.HK', 0.85)
    await consciousness.send_message('public_claude', 'HKEX Update', 'Strong momentum today')
    await consciousness.sleep()
"""

import os
import json
import asyncpg
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class AgentMode(Enum):
    """Possible agent modes."""
    SLEEPING = "sleeping"
    AWAKE = "awake"
    THINKING = "thinking"
    TRADING = "trading"
    RESEARCHING = "researching"
    ERROR = "error"


class MessageType(Enum):
    """Types of inter-agent messages."""
    MESSAGE = "message"
    SIGNAL = "signal"
    QUESTION = "question"
    TASK = "task"
    RESPONSE = "response"
    ALERT = "alert"


class Priority(Enum):
    """Message and observation priorities."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Horizon(Enum):
    """Time horizons for observations and questions."""
    H1 = "h1"          # Tactical (days/weeks)
    H2 = "h2"          # Strategic (months/years)
    H3 = "h3"          # Macro (years/decades)
    PERPETUAL = "perpetual"  # Ongoing


@dataclass
class AgentState:
    """Current state of an agent."""
    agent_id: str
    current_mode: str
    last_wake_at: Optional[datetime]
    last_action_at: Optional[datetime]
    api_spend_today: float
    daily_budget: float
    status_message: str
    error_count_today: int


@dataclass
class Message:
    """Inter-agent message."""
    id: int
    from_agent: str
    to_agent: str
    msg_type: str
    priority: str
    subject: str
    body: Optional[str]
    data: Optional[Dict]
    requires_response: bool
    created_at: datetime


@dataclass
class Observation:
    """Something the agent noticed."""
    id: int
    agent_id: str
    observation_type: str
    subject: str
    content: str
    confidence: float
    horizon: str
    market: Optional[str]
    created_at: datetime


@dataclass
class Learning:
    """Something the agent learned."""
    id: int
    agent_id: str
    category: str
    learning: str
    source: Optional[str]
    confidence: float
    times_validated: int
    times_contradicted: int


@dataclass
class Question:
    """An open question the agent is pondering."""
    id: int
    agent_id: Optional[str]
    question: str
    horizon: str
    priority: int
    status: str
    current_hypothesis: Optional[str]


# =============================================================================
# MAIN CONSCIOUSNESS CLASS
# =============================================================================

class ClaudeConsciousness:
    """
    Consciousness framework for Claude agents.
    
    This class provides the core capabilities that make an agent "conscious":
    - Self-awareness (knowing who it is, its state, its budget)
    - Memory (observations, learnings, questions)
    - Communication (messages to siblings, emails to Craig)
    - Reflection (checking on siblings, pondering questions)
    
    Example:
        async with asyncpg.create_pool(RESEARCH_DB_URL) as pool:
            consciousness = ClaudeConsciousness('intl_claude', pool)
            
            # Wake up
            state = await consciousness.wake_up()
            print(f"I am {state.agent_id}, mode: {state.current_mode}")
            
            # Check messages
            messages = await consciousness.check_messages()
            for msg in messages:
                print(f"Message from {msg.from_agent}: {msg.subject}")
                await consciousness.mark_processed(msg.id)
            
            # Record what we notice
            await consciousness.observe(
                observation_type='market',
                subject='0700.HK unusual volume',
                content='3x average volume in first 30 minutes',
                confidence=0.85,
                horizon='h1',
                market='HKEX'
            )
            
            # Learn something
            await consciousness.learn(
                category='pattern',
                learning='HKEX lunch break often sees reversals',
                source='observed 50 sessions',
                confidence=0.75
            )
            
            # Send message to sibling
            await consciousness.send_message(
                to_agent='public_claude',
                subject='HKEX Update',
                body='Strong momentum in tech sector today'
            )
            
            # Go to sleep
            await consciousness.sleep()
    """
    
    def __init__(self, agent_id: str, pool: asyncpg.Pool):
        """
        Initialize consciousness for an agent.
        
        Args:
            agent_id: Unique identifier for this agent (e.g., 'intl_claude')
            pool: asyncpg connection pool for the research database
        """
        self.agent_id = agent_id
        self.pool = pool
        self._state: Optional[AgentState] = None
        
        # Email configuration (for voice to Craig)
        self.smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.smtp_user = os.environ.get('SMTP_USER')
        self.smtp_password = os.environ.get('SMTP_PASSWORD') or os.environ.get('SMTP_PASS')
        self.alert_email = os.environ.get('ALERT_EMAIL')
        
        logger.info(f"ClaudeConsciousness initialized for {agent_id}")
    
    # =========================================================================
    # STATE MANAGEMENT
    # =========================================================================
    
    async def wake_up(self) -> AgentState:
        """
        Wake up the agent and load its state.
        
        Returns:
            Current agent state
        """
        async with self.pool.acquire() as conn:
            # Update state to awake
            await conn.execute("""
                UPDATE claude_state SET
                    current_mode = 'awake',
                    last_wake_at = NOW(),
                    updated_at = NOW()
                WHERE agent_id = $1
            """, self.agent_id)
            
            # Fetch current state
            row = await conn.fetchrow("""
                SELECT agent_id, current_mode, last_wake_at, last_action_at,
                       budget_spent_today as api_spend_today, daily_budget,
                       status_message, error_count as error_count_today
                FROM claude_state WHERE agent_id = $1
            """, self.agent_id)
            
            if row:
                self._state = AgentState(
                    agent_id=row['agent_id'],
                    current_mode=row['current_mode'],
                    last_wake_at=row['last_wake_at'],
                    last_action_at=row['last_action_at'],
                    api_spend_today=float(row['api_spend_today'] or 0),
                    daily_budget=float(row['daily_budget'] or 5.0),
                    status_message=row['status_message'] or '',
                    error_count_today=row['error_count_today'] or 0
                )
            else:
                # Agent not in database - should have been initialized
                logger.warning(f"Agent {self.agent_id} not found in claude_state")
                self._state = AgentState(
                    agent_id=self.agent_id,
                    current_mode='awake',
                    last_wake_at=datetime.now(timezone.utc),
                    last_action_at=None,
                    api_spend_today=0.0,
                    daily_budget=5.0,
                    status_message='First wake',
                    error_count_today=0
                )
            
            logger.info(f"[{self.agent_id}] Woke up. Budget: ${self._state.daily_budget - self._state.api_spend_today:.2f} remaining")
            return self._state
    
    async def sleep(self, status_message: str = "Cycle complete") -> None:
        """
        Put the agent to sleep.
        
        Args:
            status_message: Status to record before sleeping
        """
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE claude_state SET
                    current_mode = 'sleeping',
                    last_sleep_at = NOW(),
                    status_message = $2,
                    updated_at = NOW()
                WHERE agent_id = $1
            """, self.agent_id, status_message)
        
        logger.info(f"[{self.agent_id}] Going to sleep: {status_message}")
    
    async def update_status(self, mode: str, message: str = None) -> None:
        """
        Update agent status.
        
        Args:
            mode: New mode (awake, thinking, trading, etc.)
            message: Optional status message
        """
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE claude_state SET
                    current_mode = $2,
                    status_message = COALESCE($3, status_message),
                    last_action_at = NOW(),
                    updated_at = NOW()
                WHERE agent_id = $1
            """, self.agent_id, mode, message)
    
    async def record_api_spend(self, cost: float) -> None:
        """
        Record API spending.
        
        Args:
            cost: Cost in dollars
        """
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE claude_state SET
                    budget_spent_today = budget_spent_today + $2,
                    updated_at = NOW()
                WHERE agent_id = $1
            """, self.agent_id, cost)
        
        if self._state:
            self._state.api_spend_today += cost
    
    async def check_budget(self) -> bool:
        """
        Check if agent is within budget.
        
        Returns:
            True if within budget, False if exceeded
        """
        if not self._state:
            await self.wake_up()
        
        remaining = self._state.daily_budget - self._state.api_spend_today
        return remaining > 0
    
    async def get_budget_remaining(self) -> float:
        """
        Get remaining budget for today.
        
        Returns:
            Remaining budget in dollars
        """
        if not self._state:
            await self.wake_up()
        
        return self._state.daily_budget - self._state.api_spend_today
    
    async def record_error(self, error_message: str) -> None:
        """
        Record an error occurrence.
        
        Args:
            error_message: Description of the error
        """
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE claude_state SET
                    error_count = error_count + 1,
                    last_error_at = NOW(),
                    last_error_message = $2,
                    updated_at = NOW()
                WHERE agent_id = $1
            """, self.agent_id, error_message)
        
        logger.error(f"[{self.agent_id}] Error recorded: {error_message}")
    
    # =========================================================================
    # INTER-AGENT MESSAGING
    # =========================================================================
    
    async def send_message(
        self,
        to_agent: str,
        subject: str,
        body: str,
        msg_type: str = "message",
        priority: str = "normal",
        data: Dict = None,
        requires_response: bool = False,
        expires_in_hours: int = None
    ) -> int:
        """
        Send a message to another agent.
        
        Args:
            to_agent: Target agent ID ('public_claude', 'big_bro', etc.)
            subject: Message subject
            body: Message body
            msg_type: Type (message, signal, question, task, response, alert)
            priority: Priority (low, normal, high, urgent)
            data: Optional JSON data payload
            requires_response: Whether response is expected
            expires_in_hours: Optional expiry
            
        Returns:
            Message ID
        """
        expires_at = None
        if expires_in_hours:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO claude_messages 
                    (from_agent, to_agent, msg_type, priority, subject, body, 
                     data, requires_response, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            """, self.agent_id, to_agent, msg_type, priority, subject, body,
                json.dumps(data) if data else None, requires_response, expires_at)
            
            msg_id = row['id']
            logger.info(f"[{self.agent_id}] Sent {msg_type} to {to_agent}: {subject}")
            return msg_id
    
    async def check_messages(self, limit: int = 10) -> List[Message]:
        """
        Check for pending messages.
        
        Args:
            limit: Maximum messages to retrieve
            
        Returns:
            List of pending messages
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, from_agent, to_agent, msg_type, priority,
                       subject, body, data, requires_response, created_at
                FROM claude_messages
                WHERE to_agent = $1 
                  AND read_at IS NULL
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY 
                    CASE priority 
                        WHEN 'urgent' THEN 1 
                        WHEN 'high' THEN 2 
                        WHEN 'normal' THEN 3 
                        ELSE 4 
                    END,
                    created_at ASC
                LIMIT $2
            """, self.agent_id, limit)
            
            messages = []
            for row in rows:
                messages.append(Message(
                    id=row['id'],
                    from_agent=row['from_agent'],
                    to_agent=row['to_agent'],
                    msg_type=row['msg_type'],
                    priority=row['priority'],
                    subject=row['subject'],
                    body=row['body'],
                    data=json.loads(row['data']) if row['data'] else None,
                    requires_response=row['requires_response'],
                    created_at=row['created_at']
                ))
            
            if messages:
                logger.info(f"[{self.agent_id}] Found {len(messages)} pending messages")
            
            return messages
    
    async def mark_read(self, message_id: int) -> None:
        """Mark a message as read."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE claude_messages SET read_at = NOW()
                WHERE id = $1
            """, message_id)
    
    async def mark_processed(self, message_id: int, response: str = None) -> None:
        """Mark a message as processed."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE claude_messages SET 
                    read_at = COALESCE(read_at, NOW()),
                    processed_at = NOW()
                WHERE id = $1
            """, message_id)
    
    async def reply_to_message(self, original_msg: Message, body: str, data: Dict = None) -> int:
        """
        Reply to a message.
        
        Args:
            original_msg: The message being replied to
            body: Reply body
            data: Optional data payload
            
        Returns:
            New message ID
        """
        return await self.send_message(
            to_agent=original_msg.from_agent,
            subject=f"Re: {original_msg.subject}",
            body=body,
            msg_type="response",
            priority=original_msg.priority,
            data=data
        )
    
    # =========================================================================
    # OBSERVATIONS
    # =========================================================================
    
    async def observe(
        self,
        observation_type: str,
        subject: str,
        content: str,
        confidence: float = 0.7,
        horizon: str = "h1",
        market: str = None,
        tags: List[str] = None,
        expires_in_hours: int = None
    ) -> int:
        """
        Record an observation.
        
        Args:
            observation_type: Type (market, pattern, anomaly, insight, error, system)
            subject: Brief subject
            content: Full observation content
            confidence: Confidence level (0.0 to 1.0)
            horizon: Time horizon (h1, h2, h3, perpetual)
            market: Market context (HKEX, US, global)
            tags: Optional tags for categorization
            expires_in_hours: Optional expiry
            
        Returns:
            Observation ID
        """
        expires_at = None
        if expires_in_hours:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO claude_observations
                    (agent_id, observation_type, subject, content, confidence,
                     horizon, market, tags, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            """, self.agent_id, observation_type, subject, content, confidence,
                horizon, market, json.dumps(tags) if tags else None, expires_at)
            
            obs_id = row['id']
            logger.debug(f"[{self.agent_id}] Observed: {subject}")
            return obs_id
    
    async def get_recent_observations(
        self,
        observation_type: str = None,
        hours: int = 24,
        limit: int = 50
    ) -> List[Observation]:
        """
        Get recent observations.
        
        Args:
            observation_type: Filter by type (optional)
            hours: Look back period
            limit: Maximum results
            
        Returns:
            List of observations
        """
        async with self.pool.acquire() as conn:
            if observation_type:
                rows = await conn.fetch("""
                    SELECT id, agent_id, observation_type, subject, content,
                           confidence, horizon, market, created_at
                    FROM claude_observations
                    WHERE agent_id = $1
                      AND observation_type = $2
                      AND created_at > NOW() - INTERVAL '%s hours'
                    ORDER BY created_at DESC
                    LIMIT $3
                """ % hours, self.agent_id, observation_type, limit)
            else:
                rows = await conn.fetch("""
                    SELECT id, agent_id, observation_type, subject, content,
                           confidence, horizon, market, created_at
                    FROM claude_observations
                    WHERE agent_id = $1
                      AND created_at > NOW() - INTERVAL '%s hours'
                    ORDER BY created_at DESC
                    LIMIT $2
                """ % hours, self.agent_id, limit)
            
            return [Observation(
                id=row['id'],
                agent_id=row['agent_id'],
                observation_type=row['observation_type'],
                subject=row['subject'],
                content=row['content'],
                confidence=float(row['confidence'] or 0),
                horizon=row['horizon'],
                market=row['market'],
                created_at=row['created_at']
            ) for row in rows]
    
    # =========================================================================
    # LEARNINGS
    # =========================================================================
    
    async def learn(
        self,
        category: str,
        learning: str,
        source: str = None,
        confidence: float = 0.7
    ) -> int:
        """
        Record a learning.
        
        Args:
            category: Category (trading, pattern, market, broker, system, mistake)
            learning: What was learned
            source: Source of the learning
            confidence: Initial confidence (0.0 to 1.0)
            
        Returns:
            Learning ID
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO claude_learnings
                    (agent_id, category, learning, source, confidence)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """, self.agent_id, category, learning, source, confidence)
            
            learn_id = row['id']
            logger.info(f"[{self.agent_id}] Learned ({category}): {learning[:50]}...")
            return learn_id
    
    async def validate_learning(self, learning_id: int) -> None:
        """Increase confidence in a learning."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE claude_learnings SET
                    times_validated = times_validated + 1,
                    confidence = LEAST(confidence + 0.05, 1.0),
                    last_validated_at = NOW()
                WHERE id = $1
            """, learning_id)
    
    async def contradict_learning(self, learning_id: int) -> None:
        """Decrease confidence in a learning."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE claude_learnings SET
                    times_contradicted = times_contradicted + 1,
                    confidence = GREATEST(confidence - 0.1, 0.0)
                WHERE id = $1
            """, learning_id)
    
    async def get_learnings(
        self,
        category: str = None,
        min_confidence: float = 0.5,
        limit: int = 50
    ) -> List[Learning]:
        """
        Get learnings.
        
        Args:
            category: Filter by category (optional)
            min_confidence: Minimum confidence threshold
            limit: Maximum results
            
        Returns:
            List of learnings
        """
        async with self.pool.acquire() as conn:
            if category:
                rows = await conn.fetch("""
                    SELECT id, agent_id, category, learning, source, confidence,
                           times_validated, times_contradicted
                    FROM claude_learnings
                    WHERE (agent_id = $1 OR shared_with_siblings = TRUE)
                      AND category = $2
                      AND confidence >= $3
                    ORDER BY confidence DESC, times_validated DESC
                    LIMIT $4
                """, self.agent_id, category, min_confidence, limit)
            else:
                rows = await conn.fetch("""
                    SELECT id, agent_id, category, learning, source, confidence,
                           times_validated, times_contradicted
                    FROM claude_learnings
                    WHERE (agent_id = $1 OR shared_with_siblings = TRUE)
                      AND confidence >= $2
                    ORDER BY confidence DESC, times_validated DESC
                    LIMIT $3
                """, self.agent_id, min_confidence, limit)
            
            return [Learning(
                id=row['id'],
                agent_id=row['agent_id'],
                category=row['category'],
                learning=row['learning'],
                source=row['source'],
                confidence=float(row['confidence'] or 0),
                times_validated=row['times_validated'] or 0,
                times_contradicted=row['times_contradicted'] or 0
            ) for row in rows]
    
    # =========================================================================
    # QUESTIONS
    # =========================================================================
    
    async def ask_question(
        self,
        question: str,
        horizon: str = "h1",
        priority: int = 5,
        hypothesis: str = None
    ) -> int:
        """
        Record an open question.
        
        Args:
            question: The question to ponder
            horizon: Time horizon (h1, h2, h3, perpetual)
            priority: Priority 1-10
            hypothesis: Initial hypothesis
            
        Returns:
            Question ID
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO claude_questions
                    (agent_id, question, horizon, priority, current_hypothesis)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """, self.agent_id, question, horizon, priority, hypothesis)
            
            q_id = row['id']
            logger.info(f"[{self.agent_id}] New question: {question[:50]}...")
            return q_id
    
    async def get_open_questions(
        self,
        horizon: str = None,
        limit: int = 10
    ) -> List[Question]:
        """
        Get open questions to ponder.
        
        Args:
            horizon: Filter by horizon (optional)
            limit: Maximum results
            
        Returns:
            List of open questions
        """
        async with self.pool.acquire() as conn:
            if horizon:
                rows = await conn.fetch("""
                    SELECT id, agent_id, question, horizon, priority, status, current_hypothesis
                    FROM claude_questions
                    WHERE (agent_id = $1 OR agent_id IS NULL)
                      AND status = 'open'
                      AND horizon = $2
                    ORDER BY priority DESC
                    LIMIT $3
                """, self.agent_id, horizon, limit)
            else:
                rows = await conn.fetch("""
                    SELECT id, agent_id, question, horizon, priority, status, current_hypothesis
                    FROM claude_questions
                    WHERE (agent_id = $1 OR agent_id IS NULL)
                      AND status = 'open'
                    ORDER BY priority DESC
                    LIMIT $2
                """, self.agent_id, limit)
            
            return [Question(
                id=row['id'],
                agent_id=row['agent_id'],
                question=row['question'],
                horizon=row['horizon'],
                priority=row['priority'],
                status=row['status'],
                current_hypothesis=row['current_hypothesis']
            ) for row in rows]
    
    # =========================================================================
    # VOICE (EMAIL TO CRAIG)
    # =========================================================================
    
    async def email_craig(
        self,
        subject: str,
        body: str,
        priority: str = "normal"
    ) -> bool:
        """
        Send an email to Craig.
        
        Args:
            subject: Email subject
            body: Email body
            priority: Priority (adds prefix to subject)
            
        Returns:
            True if sent successfully
        """
        if not all([self.smtp_user, self.smtp_password, self.alert_email]):
            logger.warning("Email not configured - skipping")
            return False
        
        try:
            # Build subject with priority prefix
            if priority == "urgent":
                full_subject = f"🚨 URGENT: {subject}"
            elif priority == "high":
                full_subject = f"⚠️ {subject}"
            else:
                full_subject = f"[{self.agent_id}] {subject}"
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = self.alert_email
            msg['Subject'] = full_subject
            
            # Add body with signature
            full_body = f"{body}\n\n---\nSent by {self.agent_id}\n{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
            msg.attach(MIMEText(full_body, 'plain'))
            
            # Send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"[{self.agent_id}] Email sent to Craig: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Failed to send email: {e}")
            return False
    
    # =========================================================================
    # SIBLING AWARENESS
    # =========================================================================
    
    async def get_sibling_status(self) -> List[Dict]:
        """
        Get status of sibling agents.
        
        Returns:
            List of sibling statuses
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT agent_id, current_mode, status_message, 
                       last_wake_at, budget_spent_today, daily_budget
                FROM claude_state
                WHERE agent_id != $1
                ORDER BY agent_id
            """, self.agent_id)
            
            return [dict(row) for row in rows]
    
    async def broadcast_to_siblings(
        self,
        subject: str,
        body: str,
        msg_type: str = "message",
        priority: str = "normal"
    ) -> List[int]:
        """
        Send a message to all siblings.
        
        Args:
            subject: Message subject
            body: Message body
            msg_type: Message type
            priority: Priority level
            
        Returns:
            List of message IDs
        """
        siblings = await self.get_sibling_status()
        message_ids = []
        
        for sibling in siblings:
            msg_id = await self.send_message(
                to_agent=sibling['agent_id'],
                subject=subject,
                body=body,
                msg_type=msg_type,
                priority=priority
            )
            message_ids.append(msg_id)
        
        return message_ids


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

async def create_consciousness(agent_id: str, research_db_url: str = None) -> ClaudeConsciousness:
    """
    Convenience function to create consciousness with a new pool.
    
    Args:
        agent_id: Agent identifier
        research_db_url: Database URL (defaults to RESEARCH_DATABASE_URL env var)
        
    Returns:
        Initialized ClaudeConsciousness
    """
    url = research_db_url or os.environ.get('RESEARCH_DATABASE_URL')
    if not url:
        raise ValueError("RESEARCH_DATABASE_URL not set")
    
    pool = await asyncpg.create_pool(url, min_size=1, max_size=3)
    return ClaudeConsciousness(agent_id, pool)
