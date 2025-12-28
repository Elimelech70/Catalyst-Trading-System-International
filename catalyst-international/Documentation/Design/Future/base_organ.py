"""
Name of Application: Catalyst Trading System
Name of file: base_organ.py
Version: 1.0.0
Last Updated: 2025-12-25
Purpose: Base class for all conscious organs

Description:
This is the base class that all organs inherit from.
Each organ extends this with its specific tools and behavior.
"""

import json
import logging
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

import anthropic

logger = logging.getLogger(__name__)


@dataclass
class OrganConfig:
    """Configuration for an organ."""
    name: str
    port: int
    model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 2048


@dataclass
class OrganMessage:
    """Message passed between organs."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    from_organ: str = ""
    to_organ: str = ""
    type: str = ""
    priority: str = "normal"
    payload: dict = field(default_factory=dict)
    
    def to_json(self) -> str:
        return json.dumps(self.__dict__)


class BaseOrgan(ABC):
    """
    Base class for all conscious organs.
    """
    
    def __init__(self, config: OrganConfig):
        self.config = config
        self.name = config.name
        
        # Load identity from CLAUDE.md
        self.identity = self._load_identity()
        
        # Initialize Claude client
        self.claude = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        
        # Register tools
        self.tools: dict[str, Callable] = {}
        self._register_tools()
        
        logger.info(f"Organ {self.name} initialized")
    
    def _load_identity(self) -> str:
        """Load organ identity from CLAUDE.md."""
        claude_md_path = Path("/app/CLAUDE.md")
        if claude_md_path.exists():
            return claude_md_path.read_text()
        return f"I am the {self.name} organ."
    
    @abstractmethod
    def _register_tools(self):
        """Register tools specific to this organ. Override in subclass."""
        pass
    
    def think(self, context: str, question: str) -> str:
        """
        Engage Claude to think about something.
        
        Args:
            context: Current context/state
            question: What to think about
        
        Returns:
            Claude's response
        """
        system_prompt = f"""{self.identity}

Current context:
{context}

Think carefully and respond based on your purpose and principles."""
        
        response = self.claude.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": question}]
        )
        
        return response.content[0].text
    
    def reflect(self, action: dict, outcome: dict) -> dict:
        """
        Reflect on an action and its outcome to learn.
        
        Args:
            action: What was done
            outcome: What happened
        
        Returns:
            Learning extracted
        """
        prompt = f"""Reflect on this action and outcome:

ACTION: {json.dumps(action, indent=2)}

OUTCOME: {json.dumps(outcome, indent=2)}

Extract a learning in JSON format:
{{
    "learning": "What we learned",
    "evidence": "The specific evidence",
    "confidence": 0.0-1.0,
    "category": "pattern|rule|observation|hypothesis"
}}"""
        
        response = self.think("Reflecting on outcome", prompt)
        
        try:
            # Parse JSON from response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            return json.loads(response.strip())
        except:
            return {"learning": response, "confidence": 0.5}
    
    def send_message(self, to_organ: str, msg_type: str, payload: dict):
        """Send message to another organ via Redis."""
        msg = OrganMessage(
            from_organ=self.name,
            to_organ=to_organ,
            type=msg_type,
            payload=payload
        )
        # Would publish to Redis queue
        logger.info(f"Message {self.name} -> {to_organ}: {msg_type}")
        return msg
    
    def receive_message(self, message: OrganMessage) -> dict:
        """
        Process a received message.
        Override in subclass for specific handling.
        """
        logger.info(f"Received {message.type} from {message.from_organ}")
        return {"status": "received"}
    
    def call_tool(self, tool_name: str, **kwargs) -> Any:
        """Call a registered tool."""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        return self.tools[tool_name](**kwargs)
    
    def store_learning(self, learning: dict):
        """Store a learning in the database."""
        learning["organ"] = self.name
        learning["timestamp"] = datetime.utcnow().isoformat()
        # Would store in PostgreSQL
        logger.info(f"Learning stored: {learning.get('learning', '')[:50]}...")
    
    def get_learnings(self, category: str = None, limit: int = 10) -> list:
        """Retrieve past learnings."""
        # Would query PostgreSQL
        return []
    
    @abstractmethod
    def process(self, input_data: dict) -> dict:
        """
        Main processing method. Override in subclass.
        
        Args:
            input_data: Input to process
        
        Returns:
            Processing result
        """
        pass
