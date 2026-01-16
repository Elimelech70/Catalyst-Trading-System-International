# Claude Inter-Agent Communication Protocol (CIACP)

**Name of Application:** Catalyst Trading System  
**Name of file:** claude-communication-protocol-v1.0.0.md  
**Version:** 1.0.0  
**Last Updated:** 2025-12-14  
**Purpose:** Database-based inter-agent communication (polling model)  
**Author:** Craig + Claude Opus 4.5

---

## Overview

Both Claude Code instances poll a shared `claude_messages` table in the Research Database. No REST API needed - the database IS the communication bus.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SIMPLIFIED COMMUNICATION                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   US CLAUDE                                           INTL CLAUDE           │
│   ─────────                                           ───────────           │
│       │                                                   │                 │
│       │              ┌─────────────────────┐              │                 │
│       │              │   RESEARCH DATABASE │              │                 │
│       │              │                     │              │                 │
│       ├──── WRITE ──►│  claude_messages    │◄── WRITE ───┤                 │
│       │              │                     │              │                 │
│       ├──── POLL ───►│  (to: 'us_claude')  │◄── POLL ────┤                 │
│       │              │  (to: 'intl_claude')│              │                 │
│       │              │  (to: 'all')        │              │                 │
│       │              │                     │              │                 │
│       │              └─────────────────────┘              │                 │
│       │                                                   │                 │
│       │              ┌─────────────────────┐              │                 │
│       ├──── R/W ────►│  claude_state       │◄──── R/W ───┤                 │
│       │              │  claude_observations│              │                 │
│       │              │  claude_learnings   │              │                 │
│       │              │  claude_questions   │              │                 │
│       │              └─────────────────────┘              │                 │
│                                                                             │
│   Simple: Write message → Sibling polls → Reads → Responds                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### claude_messages (Communication Bus)

```sql
-- The communication bus - all inter-agent messages
CREATE TABLE claude_messages (
    id SERIAL PRIMARY KEY,
    
    -- Routing
    from_agent VARCHAR(50) NOT NULL,           -- 'us_claude', 'intl_claude', 'pattern_claude'
    to_agent VARCHAR(50) NOT NULL,             -- Target agent or 'all' for broadcast
    
    -- Message content
    msg_type VARCHAR(50) NOT NULL,             -- 'message', 'signal', 'question', 'response', 'task'
    priority VARCHAR(20) DEFAULT 'normal',     -- 'low', 'normal', 'high', 'urgent'
    subject VARCHAR(500),
    body TEXT,
    data JSONB,                                -- Structured data payload
    
    -- Threading (for questions/responses)
    reply_to_id INTEGER REFERENCES claude_messages(id),
    thread_id INTEGER,                         -- Groups related messages
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'pending',      -- 'pending', 'read', 'processed', 'expired'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    read_at TIMESTAMP WITH TIME ZONE,
    processed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,       -- Auto-expire old messages
    
    -- Response tracking (for questions)
    requires_response BOOLEAN DEFAULT FALSE,
    response_deadline TIMESTAMP WITH TIME ZONE
);

-- Index for fast polling
CREATE INDEX idx_messages_to_agent_status ON claude_messages(to_agent, status, created_at DESC);
CREATE INDEX idx_messages_thread ON claude_messages(thread_id);
CREATE INDEX idx_messages_pending ON claude_messages(to_agent, status) WHERE status = 'pending';

-- Cleanup old messages (run periodically)
CREATE INDEX idx_messages_expires ON claude_messages(expires_at) WHERE expires_at IS NOT NULL;
```

### Complete Schema (All Claude Tables)

```sql
-- ============================================================================
-- CLAUDE CONSCIOUSNESS TABLES
-- Add to Research Database
-- ============================================================================

-- Messages: The communication bus
CREATE TABLE claude_messages (
    id SERIAL PRIMARY KEY,
    from_agent VARCHAR(50) NOT NULL,
    to_agent VARCHAR(50) NOT NULL,
    msg_type VARCHAR(50) NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',
    subject VARCHAR(500),
    body TEXT,
    data JSONB,
    reply_to_id INTEGER REFERENCES claude_messages(id),
    thread_id INTEGER,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    read_at TIMESTAMP WITH TIME ZONE,
    processed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    requires_response BOOLEAN DEFAULT FALSE,
    response_deadline TIMESTAMP WITH TIME ZONE
);

-- State: Each agent's current state
CREATE TABLE claude_state (
    agent_id VARCHAR(50) PRIMARY KEY,
    current_mode VARCHAR(50),
    last_wake_at TIMESTAMP WITH TIME ZONE,
    last_think_at TIMESTAMP WITH TIME ZONE,
    last_action_at TIMESTAMP WITH TIME ZONE,
    last_poll_at TIMESTAMP WITH TIME ZONE,      -- When last checked messages
    api_spend_today DECIMAL(10,4) DEFAULT 0,
    api_spend_month DECIMAL(10,4) DEFAULT 0,
    current_schedule VARCHAR(100),
    next_scheduled_wake TIMESTAMP WITH TIME ZONE,
    status_message TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Observations: What agents notice
CREATE TABLE claude_observations (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50) NOT NULL,
    observation_type VARCHAR(100),
    subject VARCHAR(200),
    content TEXT NOT NULL,
    confidence DECIMAL(3,2),
    horizon VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    acted_upon BOOLEAN DEFAULT FALSE,
    action_taken TEXT
);

-- Learnings: What agents have learned
CREATE TABLE claude_learnings (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50) NOT NULL,
    category VARCHAR(100),
    learning TEXT NOT NULL,
    source VARCHAR(200),
    confidence DECIMAL(3,2),
    times_validated INTEGER DEFAULT 0,
    times_contradicted INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_validated_at TIMESTAMP WITH TIME ZONE
);

-- Questions: Open questions being thought about
CREATE TABLE claude_questions (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50),
    question TEXT NOT NULL,
    horizon VARCHAR(10),
    priority INTEGER DEFAULT 5,
    status VARCHAR(50) DEFAULT 'open',
    current_hypothesis TEXT,
    evidence_for TEXT,
    evidence_against TEXT,
    next_think_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversations: Key exchanges worth remembering
CREATE TABLE claude_conversations (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50) NOT NULL,
    with_whom VARCHAR(100),
    summary TEXT NOT NULL,
    key_decisions TEXT,
    action_items TEXT,
    conversation_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_messages_to_agent_status ON claude_messages(to_agent, status, created_at DESC);
CREATE INDEX idx_messages_pending ON claude_messages(to_agent, status) WHERE status = 'pending';
CREATE INDEX idx_observations_agent ON claude_observations(agent_id, created_at DESC);
CREATE INDEX idx_learnings_category ON claude_learnings(agent_id, category);
CREATE INDEX idx_questions_status ON claude_questions(status, next_think_at);
```

---

## Message Types

| Type | Purpose | Example |
|------|---------|---------|
| `message` | General communication | "FYI: Fixed the bracket order bug" |
| `signal` | Alert/notification | "Review ready", "Urgent attention needed" |
| `question` | Ask sibling something | "What's your HKEX tech assessment?" |
| `response` | Answer to question | "Tech sector weak, recommend waiting" |
| `task` | Request action | "Please review preflight doc" |
| `broadcast` | To all agents | "System maintenance in 1 hour" |

---

## Python Implementation

### ClaudeComm Class

```python
"""
Name of Application: Catalyst Trading System
Name of file: claude_comm.py
Version: 1.0.0
Last Updated: 2025-12-14
Purpose: Inter-agent communication via database polling
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

import asyncpg

logger = logging.getLogger(__name__)


class MessageType(Enum):
    MESSAGE = "message"
    SIGNAL = "signal"
    QUESTION = "question"
    RESPONSE = "response"
    TASK = "task"
    BROADCAST = "broadcast"


class Priority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageStatus(Enum):
    PENDING = "pending"
    READ = "read"
    PROCESSED = "processed"
    EXPIRED = "expired"


@dataclass
class Message:
    id: int
    from_agent: str
    to_agent: str
    msg_type: str
    priority: str
    subject: str
    body: str
    data: dict
    reply_to_id: Optional[int]
    thread_id: Optional[int]
    status: str
    created_at: datetime
    requires_response: bool


class ClaudeComm:
    """Inter-agent communication via database polling."""
    
    def __init__(self, agent_id: str, db_pool: asyncpg.Pool):
        self.agent_id = agent_id
        self.db = db_pool
        self.poll_interval = 10  # seconds
        self._running = False
        self._message_handlers: Dict[str, callable] = {}
    
    # =========================================================================
    # SENDING MESSAGES
    # =========================================================================
    
    async def send(
        self,
        to_agent: str,
        subject: str,
        body: str = "",
        msg_type: MessageType = MessageType.MESSAGE,
        priority: Priority = Priority.NORMAL,
        data: dict = None,
        reply_to: int = None,
        requires_response: bool = False,
        response_deadline_minutes: int = None,
        expires_in_hours: int = 24
    ) -> int:
        """Send a message to another agent."""
        
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        response_deadline = None
        if requires_response and response_deadline_minutes:
            response_deadline = datetime.utcnow() + timedelta(minutes=response_deadline_minutes)
        
        # Get or create thread_id
        thread_id = None
        if reply_to:
            thread_id = await self.db.fetchval(
                "SELECT COALESCE(thread_id, id) FROM claude_messages WHERE id = $1",
                reply_to
            )
        
        msg_id = await self.db.fetchval("""
            INSERT INTO claude_messages 
            (from_agent, to_agent, msg_type, priority, subject, body, data, 
             reply_to_id, thread_id, requires_response, response_deadline, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING id
        """,
            self.agent_id, to_agent, msg_type.value, priority.value,
            subject, body, json.dumps(data) if data else None,
            reply_to, thread_id, requires_response, response_deadline, expires_at
        )
        
        logger.info(f"Sent {msg_type.value} to {to_agent}: {subject} (id={msg_id})")
        return msg_id
    
    async def signal(self, to_agent: str, signal_type: str, data: dict = None):
        """Send a signal (lightweight alert)."""
        return await self.send(
            to_agent=to_agent,
            subject=signal_type,
            msg_type=MessageType.SIGNAL,
            priority=Priority.HIGH,
            data=data,
            expires_in_hours=1  # Signals expire quickly
        )
    
    async def ask(
        self,
        to_agent: str,
        question: str,
        context: dict = None,
        deadline_minutes: int = 30
    ) -> int:
        """Ask another agent a question."""
        return await self.send(
            to_agent=to_agent,
            subject=question,
            msg_type=MessageType.QUESTION,
            priority=Priority.NORMAL,
            data=context,
            requires_response=True,
            response_deadline_minutes=deadline_minutes
        )
    
    async def respond(self, to_message_id: int, answer: str, data: dict = None):
        """Respond to a question."""
        original = await self.db.fetchrow(
            "SELECT from_agent, subject FROM claude_messages WHERE id = $1",
            to_message_id
        )
        if not original:
            raise ValueError(f"Message {to_message_id} not found")
        
        return await self.send(
            to_agent=original["from_agent"],
            subject=f"Re: {original['subject']}",
            body=answer,
            msg_type=MessageType.RESPONSE,
            data=data,
            reply_to=to_message_id
        )
    
    async def broadcast(self, subject: str, body: str, data: dict = None):
        """Send to all agents."""
        return await self.send(
            to_agent="all",
            subject=subject,
            body=body,
            msg_type=MessageType.BROADCAST,
            data=data
        )
    
    async def request_task(
        self,
        to_agent: str,
        task: str,
        details: dict,
        deadline_minutes: int = 60
    ) -> int:
        """Request another agent to perform a task."""
        return await self.send(
            to_agent=to_agent,
            subject=task,
            msg_type=MessageType.TASK,
            priority=Priority.HIGH,
            data=details,
            requires_response=True,
            response_deadline_minutes=deadline_minutes
        )
    
    # =========================================================================
    # RECEIVING MESSAGES
    # =========================================================================
    
    async def check_messages(self) -> List[Message]:
        """Poll for new messages."""
        rows = await self.db.fetch("""
            SELECT * FROM claude_messages 
            WHERE (to_agent = $1 OR to_agent = 'all')
              AND status = 'pending'
            ORDER BY 
                CASE priority 
                    WHEN 'urgent' THEN 0 
                    WHEN 'high' THEN 1 
                    WHEN 'normal' THEN 2 
                    ELSE 3 
                END,
                created_at ASC
        """, self.agent_id)
        
        messages = []
        for row in rows:
            messages.append(Message(
                id=row["id"],
                from_agent=row["from_agent"],
                to_agent=row["to_agent"],
                msg_type=row["msg_type"],
                priority=row["priority"],
                subject=row["subject"],
                body=row["body"],
                data=json.loads(row["data"]) if row["data"] else {},
                reply_to_id=row["reply_to_id"],
                thread_id=row["thread_id"],
                status=row["status"],
                created_at=row["created_at"],
                requires_response=row["requires_response"]
            ))
        
        # Update last_poll_at
        await self.db.execute("""
            UPDATE claude_state SET last_poll_at = NOW() WHERE agent_id = $1
        """, self.agent_id)
        
        return messages
    
    async def mark_read(self, message_id: int):
        """Mark message as read."""
        await self.db.execute("""
            UPDATE claude_messages 
            SET status = 'read', read_at = NOW() 
            WHERE id = $1
        """, message_id)
    
    async def mark_processed(self, message_id: int):
        """Mark message as processed."""
        await self.db.execute("""
            UPDATE claude_messages 
            SET status = 'processed', processed_at = NOW() 
            WHERE id = $1
        """, message_id)
    
    async def get_thread(self, thread_id: int) -> List[Message]:
        """Get all messages in a thread."""
        rows = await self.db.fetch("""
            SELECT * FROM claude_messages 
            WHERE thread_id = $1 OR id = $1
            ORDER BY created_at ASC
        """, thread_id)
        # Convert to Message objects...
        return rows
    
    async def wait_for_response(
        self, 
        message_id: int, 
        timeout_seconds: int = 300,
        poll_interval: int = 5
    ) -> Optional[Message]:
        """Wait for a response to a message."""
        deadline = datetime.utcnow() + timedelta(seconds=timeout_seconds)
        
        while datetime.utcnow() < deadline:
            row = await self.db.fetchrow("""
                SELECT * FROM claude_messages 
                WHERE reply_to_id = $1 AND msg_type = 'response'
                LIMIT 1
            """, message_id)
            
            if row:
                return Message(...)  # Convert row to Message
            
            await asyncio.sleep(poll_interval)
        
        return None  # Timeout
    
    # =========================================================================
    # POLLING LOOP
    # =========================================================================
    
    def register_handler(self, msg_type: str, handler: callable):
        """Register a handler for a message type."""
        self._message_handlers[msg_type] = handler
    
    async def start_polling(self):
        """Start the message polling loop."""
        self._running = True
        logger.info(f"{self.agent_id} starting message polling (interval={self.poll_interval}s)")
        
        while self._running:
            try:
                messages = await self.check_messages()
                
                for msg in messages:
                    await self._handle_message(msg)
                
            except Exception as e:
                logger.error(f"Polling error: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    async def stop_polling(self):
        """Stop the polling loop."""
        self._running = False
    
    async def _handle_message(self, msg: Message):
        """Process a received message."""
        logger.info(f"Received {msg.msg_type} from {msg.from_agent}: {msg.subject}")
        
        # Mark as read
        await self.mark_read(msg.id)
        
        # Call registered handler
        handler = self._message_handlers.get(msg.msg_type)
        if handler:
            try:
                await handler(msg)
                await self.mark_processed(msg.id)
            except Exception as e:
                logger.error(f"Handler error for message {msg.id}: {e}")
        else:
            logger.warning(f"No handler for message type: {msg.msg_type}")
    
    # =========================================================================
    # UTILITY
    # =========================================================================
    
    async def get_sibling_status(self, agent_id: str) -> dict:
        """Check another agent's status."""
        return await self.db.fetchrow(
            "SELECT * FROM claude_state WHERE agent_id = $1", agent_id
        )
    
    async def is_sibling_awake(self, agent_id: str, threshold_minutes: int = 5) -> bool:
        """Check if sibling has polled recently."""
        row = await self.db.fetchrow("""
            SELECT last_poll_at FROM claude_state WHERE agent_id = $1
        """, agent_id)
        
        if not row or not row["last_poll_at"]:
            return False
        
        age = datetime.utcnow() - row["last_poll_at"].replace(tzinfo=None)
        return age.total_seconds() < (threshold_minutes * 60)
    
    async def cleanup_expired(self):
        """Remove expired messages."""
        deleted = await self.db.execute("""
            DELETE FROM claude_messages 
            WHERE expires_at < NOW() AND status = 'pending'
        """)
        logger.info(f"Cleaned up expired messages: {deleted}")
```

---

## Usage Examples

### Agent Startup

```python
async def main():
    # Connect to database
    pool = await asyncpg.create_pool(os.environ["RESEARCH_DB_URL"])
    
    # Initialize communication
    comm = ClaudeComm(agent_id="intl_claude", db_pool=pool)
    
    # Register message handlers
    comm.register_handler("message", handle_message)
    comm.register_handler("question", handle_question)
    comm.register_handler("signal", handle_signal)
    comm.register_handler("task", handle_task)
    
    # Start polling in background
    asyncio.create_task(comm.start_polling())
    
    # Continue with main agent loop...
```

### Sending Messages

```python
# Simple message
await comm.send(
    to_agent="us_claude",
    subject="Bracket order fixed",
    body="Implemented proper parent-child linking with OCA groups."
)

# Ask a question and wait for response
msg_id = await comm.ask(
    to_agent="us_claude",
    question="What's the current hub stress level?",
    context={"reason": "Considering H2 position"}
)
response = await comm.wait_for_response(msg_id, timeout_seconds=60)
if response:
    print(f"Answer: {response.body}")

# Send a signal
await comm.signal(
    to_agent="us_claude",
    signal_type="review_ready",
    data={"document": "preflight-results.md"}
)

# Request a task
await comm.request_task(
    to_agent="us_claude",
    task="Review preflight document",
    details={
        "document": "preflight-results.md",
        "checklist": "preflight-checklist.md"
    }
)

# Broadcast to all
await comm.broadcast(
    subject="System update",
    body="Deploying new risk parameters in 30 minutes"
)
```

### Handling Messages

```python
async def handle_question(msg: Message):
    """Handle incoming questions."""
    if "hub stress" in msg.subject.lower():
        # Calculate current hub stress
        stress = await calculate_hub_stress()
        
        await comm.respond(
            to_message_id=msg.id,
            answer=f"Current hub stress: {stress:.2f}",
            data={"minerals": 0.3, "energy": 0.5, "finance": 0.2}
        )

async def handle_signal(msg: Message):
    """Handle incoming signals."""
    if msg.subject == "review_ready":
        doc = msg.data.get("document")
        # Trigger review process
        await review_document(doc)

async def handle_task(msg: Message):
    """Handle task requests."""
    if msg.subject == "Review preflight document":
        result = await perform_review(msg.data)
        await comm.respond(
            to_message_id=msg.id,
            answer="Review complete",
            data=result
        )
```

---

## Integration with Agent Loop

```python
async def agent_loop():
    """Main agent loop with communication."""
    
    comm = ClaudeComm(agent_id=AGENT_ID, db_pool=db)
    
    # Start polling in background
    poll_task = asyncio.create_task(comm.start_polling())
    
    while True:
        try:
            # Check if sibling needs something urgently
            messages = await comm.check_messages()
            urgent = [m for m in messages if m.priority == "urgent"]
            
            if urgent:
                # Handle urgent messages first
                for msg in urgent:
                    await handle_urgent(msg, comm)
                continue
            
            # Normal agent work...
            await do_trading_stuff()
            
            # Share learnings with siblings
            if new_learning:
                await comm.send(
                    to_agent="all",
                    subject="New learning",
                    body=new_learning,
                    msg_type=MessageType.MESSAGE
                )
            
        except Exception as e:
            logger.error(f"Agent loop error: {e}")
        
        await asyncio.sleep(60)
```

---

## Communication Patterns

### 1. Preflight Review Flow

```
INTL_CLAUDE                          US_CLAUDE
     │                                    │
     │  Insert message:                   │
     │  type=signal                       │
     │  subject="review_ready"            │
     │  data={doc: "preflight.md"}        │
     │─────────────────────────────────►  │
     │                                    │  Polls, finds message
     │                                    │  Performs review
     │                                    │
     │  Insert response:                  │
     │  reply_to=original_id              │
     │  ◄─────────────────────────────────│
     │                                    │
     │  Polls, finds response             │
     │  Acts on feedback                  │
```

### 2. Question/Answer

```
US_CLAUDE                            INTL_CLAUDE
     │                                    │
     │  ask("HKEX tech assessment?")      │
     │─────────────────────────────────►  │
     │                                    │
     │  wait_for_response()               │
     │  ...polling...                     │  Calculates assessment
     │                                    │
     │                                    │  respond(answer)
     │  ◄─────────────────────────────────│
     │                                    │
     │  Receives answer                   │
     │  Continues with decision           │
```

### 3. Broadcast Learning

```
INTL_CLAUDE                          US_CLAUDE
     │                                    │
     │  broadcast("IBKR symbol format")   │
     │─────────────────────────────────►  │
     │                                    │
     │                      Polls, receives│
     │                      Stores in own │
     │                      learnings     │
```

---

## Polling Frequency

| Situation | Poll Interval | Reason |
|-----------|---------------|--------|
| Active trading | 10 seconds | Need fast response |
| Monitoring | 30 seconds | Less urgent |
| Off-hours | 60 seconds | Save resources |
| Waiting for response | 5 seconds | Blocking operation |

---

## Database Maintenance

```sql
-- Run daily: Clean up old messages
DELETE FROM claude_messages 
WHERE created_at < NOW() - INTERVAL '7 days'
  AND status IN ('processed', 'expired');

-- Run hourly: Expire stale pending messages
UPDATE claude_messages 
SET status = 'expired' 
WHERE expires_at < NOW() 
  AND status = 'pending';
```

---

*Claude Communication Protocol v1.0.0*  
*Craig + Claude Opus 4.5*  
*December 2025*
