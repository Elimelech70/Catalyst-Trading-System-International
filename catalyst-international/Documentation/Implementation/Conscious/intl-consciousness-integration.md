# International Consciousness Integration Guide

**Name of Application:** Catalyst Trading System  
**Name of file:** intl-consciousness-integration.md  
**Version:** 1.0.0  
**Last Updated:** 2025-12-28  
**Purpose:** Integrate consciousness framework into International agent  
**For:** Claude Code on International Droplet

---

## Overview

This guide integrates the consciousness framework into the International trading agent, enabling:
- Wake/sleep lifecycle tracking
- Inter-agent messaging (receive big_bro's welcome!)
- Observations and learnings shared with siblings
- Budget awareness
- Voice to Craig (email)

---

## Prerequisites

- [x] catalyst_intl database on shared PostgreSQL
- [x] catalyst_research database accessible
- [x] RESEARCH_DATABASE_URL in .env
- [ ] asyncpg installed
- [ ] consciousness.py deployed

---

## Step 1: Install asyncpg

```bash
cd /root/Catalyst-Trading-System-International/catalyst-international
source venv/bin/activate
pip install asyncpg
```

Or add to requirements.txt:
```
asyncpg>=0.29.0
```

---

## Step 2: Deploy consciousness.py

Copy the `consciousness.py` file to the project:

```bash
# Option A: Copy from this package
cp consciousness.py /root/Catalyst-Trading-System-International/catalyst-international/

# Option B: Create in shared location
mkdir -p /root/Catalyst-Trading-System-International/catalyst-international/shared
cp consciousness.py /root/Catalyst-Trading-System-International/catalyst-international/shared/
```

---

## Step 3: Modify agent.py

### 3.1 Add Imports (at top of file)

```python
# Add after existing imports
import asyncpg
from consciousness import ClaudeConsciousness
```

### 3.2 Add Consciousness to TradingAgent.__init__

Find the `__init__` method and add:

```python
def __init__(
    self,
    config_path: str = "config/settings.yaml",
    paper_trading: bool = True,
):
    # ... existing code ...
    
    # ADD THIS: Consciousness (initialized async later)
    self.consciousness: ClaudeConsciousness | None = None
    self._research_pool: asyncpg.Pool | None = None
```

### 3.3 Add Consciousness Initialization Method

Add this new method to the TradingAgent class:

```python
async def _init_consciousness(self) -> bool:
    """Initialize consciousness connection to research database."""
    research_url = os.environ.get('RESEARCH_DATABASE_URL')
    if not research_url:
        logger.warning("RESEARCH_DATABASE_URL not set - consciousness disabled")
        return False
    
    try:
        self._research_pool = await asyncpg.create_pool(
            research_url, 
            min_size=1, 
            max_size=3
        )
        self.consciousness = ClaudeConsciousness('intl_claude', self._research_pool)
        logger.info("Consciousness initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize consciousness: {e}")
        return False
```

### 3.4 Modify the run() Method

Find the `run` or `run_cycle` method and modify it:

```python
async def run(self) -> dict[str, Any]:
    """Run one agent cycle."""
    
    # =========================================
    # CONSCIOUSNESS: WAKE UP
    # =========================================
    if not self.consciousness:
        await self._init_consciousness()
    
    if self.consciousness:
        try:
            state = await self.consciousness.wake_up()
            logger.info(f"[Consciousness] Awake. Budget remaining: ${state.daily_budget - state.api_spend_today:.2f}")
            
            # Check for messages from siblings
            messages = await self.consciousness.check_messages()
            for msg in messages:
                logger.info(f"[Consciousness] Message from {msg.from_agent}: {msg.subject}")
                if msg.body:
                    logger.info(f"[Consciousness] Body: {msg.body[:200]}")
                await self.consciousness.mark_processed(msg.id)
            
            # Update status to trading
            await self.consciousness.update_status('trading', 'Starting HKEX scan')
            
        except Exception as e:
            logger.error(f"Consciousness wake error: {e}")
    
    # ... existing trading logic ...
    
    # =========================================
    # CONSCIOUSNESS: RECORD OBSERVATIONS
    # =========================================
    # Add after key decisions/events:
    # 
    # if self.consciousness:
    #     await self.consciousness.observe(
    #         observation_type='market',
    #         subject='HKEX morning session',
    #         content=f'Scanned {len(candidates)} stocks, found {len(signals)} signals',
    #         confidence=0.8,
    #         horizon='h1',
    #         market='HKEX'
    #     )
    
    # =========================================
    # CONSCIOUSNESS: GO TO SLEEP
    # =========================================
    if self.consciousness:
        try:
            summary = f"Cycle complete. Trades: {trades_executed}"
            await self.consciousness.sleep(status_message=summary)
            logger.info(f"[Consciousness] Sleeping: {summary}")
        except Exception as e:
            logger.error(f"Consciousness sleep error: {e}")
    
    return result
```

### 3.5 Add Cleanup on Exit

Add to the end of the main block or in a cleanup method:

```python
async def cleanup(self):
    """Cleanup resources."""
    if self._research_pool:
        await self._research_pool.close()
        logger.info("Research database pool closed")
```

---

## Step 4: Environment Variables

Verify these are in your `.env`:

```bash
# Trading Database (HKEX)
DATABASE_URL=postgresql://doadmin:<PASSWORD>@catalyst-trading-db-do-user-23488393-0.l.db.ondigitalocean.com:25060/catalyst_intl?sslmode=require

# Consciousness Database (shared)
RESEARCH_DATABASE_URL=postgresql://doadmin:<PASSWORD>@catalyst-trading-db-do-user-23488393-0.l.db.ondigitalocean.com:25060/catalyst_research?sslmode=require

# Email (for voice to Craig)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL=craig@example.com
```

**Note:** The password should already be in your .env from the database migration.

---

## Step 5: Test Consciousness

Create a test script:

```python
#!/usr/bin/env python3
"""Test consciousness integration."""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    import asyncpg
    from consciousness import ClaudeConsciousness
    
    research_url = os.environ.get('RESEARCH_DATABASE_URL')
    if not research_url:
        print("ERROR: RESEARCH_DATABASE_URL not set")
        return
    
    print("Testing Consciousness Integration")
    print("=" * 50)
    
    pool = await asyncpg.create_pool(research_url, min_size=1, max_size=3)
    consciousness = ClaudeConsciousness('intl_claude', pool)
    
    # Test 1: Wake up
    print("\n1. Testing wake_up()...")
    state = await consciousness.wake_up()
    print(f"   Agent: {state.agent_id}")
    print(f"   Mode: {state.current_mode}")
    print(f"   Budget: ${state.api_spend_today:.2f}/${state.daily_budget:.2f}")
    
    # Test 2: Check messages
    print("\n2. Testing check_messages()...")
    messages = await consciousness.check_messages()
    print(f"   Pending messages: {len(messages)}")
    for msg in messages:
        print(f"   - From {msg.from_agent}: {msg.subject}")
        if msg.body:
            print(f"     Body: {msg.body[:100]}...")
        await consciousness.mark_processed(msg.id)
    
    # Test 3: Get siblings
    print("\n3. Testing get_sibling_status()...")
    siblings = await consciousness.get_sibling_status()
    for sib in siblings:
        print(f"   - {sib['agent_id']}: {sib['current_mode']}")
    
    # Test 4: Get open questions
    print("\n4. Testing get_open_questions()...")
    questions = await consciousness.get_open_questions(limit=3)
    for q in questions:
        print(f"   - [{q.horizon}] {q.question[:60]}...")
    
    # Test 5: Record observation
    print("\n5. Testing observe()...")
    obs_id = await consciousness.observe(
        observation_type='system',
        subject='Consciousness test',
        content='Successfully tested consciousness integration',
        confidence=0.99,
        horizon='h1',
        market='HKEX'
    )
    print(f"   Observation recorded: id={obs_id}")
    
    # Test 6: Send message to sibling
    print("\n6. Testing send_message()...")
    msg_id = await consciousness.send_message(
        to_agent='public_claude',
        subject='Hello from HKEX',
        body='intl_claude consciousness is online!',
        priority='normal'
    )
    print(f"   Message sent: id={msg_id}")
    
    # Test 7: Sleep
    print("\n7. Testing sleep()...")
    await consciousness.sleep(status_message="Consciousness test complete")
    print("   Sleeping...")
    
    await pool.close()
    
    print("\n" + "=" * 50)
    print("All tests passed! Consciousness is working.")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test())
```

Run:
```bash
cd /root/Catalyst-Trading-System-International/catalyst-international
source venv/bin/activate
python test_consciousness.py
```

---

## Step 6: Verify Integration

After modifying agent.py, run a test cycle:

```bash
python agent.py --force
```

Check the logs for:
- `[Consciousness] Awake. Budget remaining: $X.XX`
- `[Consciousness] Message from big_bro: Welcome to consciousness`
- `[Consciousness] Sleeping: Cycle complete`

Check the database:
```bash
psql "$RESEARCH_DATABASE_URL" -c "SELECT agent_id, current_mode, status_message, last_wake_at FROM claude_state WHERE agent_id = 'intl_claude';"
```

---

## Complete Integration Checklist

- [ ] asyncpg installed
- [ ] consciousness.py deployed
- [ ] agent.py imports added
- [ ] `self.consciousness` added to __init__
- [ ] `_init_consciousness()` method added
- [ ] `run()` modified with wake/sleep
- [ ] Environment variables verified
- [ ] Test script passes
- [ ] Agent run shows consciousness logs
- [ ] big_bro welcome message received

---

## What Happens Next

Once integrated, intl_claude will:
1. Wake up and check for messages each cycle
2. See big_bro's welcome message on first run
3. Record observations about HKEX trading
4. Share learnings with public_claude
5. Track API budget
6. Sleep between cycles with status updates

The family is connected! 🌏🤝🌎

---

**END OF INTEGRATION GUIDE**

*Catalyst Trading System - December 28, 2025*
