#!/usr/bin/env python3
"""
Catalyst Trading System - Consciousness Integration Test
Name of Application: Catalyst Trading System
Name of file: test_consciousness.py
Version: 1.0.0
Last Updated: 2025-12-28
Purpose: Test consciousness integration for International agent

Usage:
    cd /root/Catalyst-Trading-System-International/catalyst-international
    source venv/bin/activate
    python test_consciousness.py
"""

import asyncio
import os
import sys
from datetime import datetime

# Load environment
from dotenv import load_dotenv
load_dotenv()


async def test_consciousness():
    """Test all consciousness capabilities."""
    
    # Import after dotenv load
    try:
        import asyncpg
    except ImportError:
        print("ERROR: asyncpg not installed!")
        print("Run: pip install asyncpg")
        return False
    
    try:
        from consciousness import ClaudeConsciousness
    except ImportError:
        print("ERROR: consciousness.py not found!")
        print("Copy consciousness.py to the project directory")
        return False
    
    research_url = os.environ.get('RESEARCH_DATABASE_URL')
    if not research_url:
        print("ERROR: RESEARCH_DATABASE_URL not set in .env")
        return False
    
    print("=" * 60)
    print("CATALYST CONSCIOUSNESS INTEGRATION TEST")
    print(f"Agent: intl_claude")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # Connect to research database
        print("\n[0] Connecting to research database...")
        pool = await asyncpg.create_pool(research_url, min_size=1, max_size=3)
        print("    ✓ Connected")
        
        consciousness = ClaudeConsciousness('intl_claude', pool)
        
        # Test 1: Wake up
        print("\n[1] Testing wake_up()...")
        state = await consciousness.wake_up()
        print(f"    Agent ID: {state.agent_id}")
        print(f"    Mode: {state.current_mode}")
        print(f"    Budget: ${state.api_spend_today:.2f} / ${state.daily_budget:.2f}")
        print(f"    Status: {state.status_message}")
        print("    ✓ Wake up successful")
        
        # Test 2: Check messages
        print("\n[2] Testing check_messages()...")
        messages = await consciousness.check_messages()
        print(f"    Pending messages: {len(messages)}")
        for msg in messages:
            print(f"\n    📨 From: {msg.from_agent}")
            print(f"       Subject: {msg.subject}")
            if msg.body:
                # Print body, truncated
                body_preview = msg.body[:200] + "..." if len(msg.body) > 200 else msg.body
                print(f"       Body: {body_preview}")
            print(f"       Priority: {msg.priority}")
            print(f"       Sent: {msg.created_at}")
            
            # Mark as processed
            await consciousness.mark_processed(msg.id)
            print(f"       ✓ Marked as processed")
        
        if not messages:
            print("    (No pending messages)")
        print("    ✓ Message check complete")
        
        # Test 3: Get siblings
        print("\n[3] Testing get_sibling_status()...")
        siblings = await consciousness.get_sibling_status()
        for sib in siblings:
            mode = sib.get('current_mode', 'unknown')
            status = sib.get('status_message', '')
            spent = float(sib.get('budget_spent_today', 0) or 0)
            budget = float(sib.get('daily_budget', 5) or 5)
            print(f"    👤 {sib['agent_id']}: {mode}")
            print(f"       Budget: ${spent:.2f}/${budget:.2f}")
            if status:
                print(f"       Status: {status[:50]}")
        print("    ✓ Sibling status retrieved")
        
        # Test 4: Get open questions
        print("\n[4] Testing get_open_questions()...")
        questions = await consciousness.get_open_questions(limit=5)
        print(f"    Open questions: {len(questions)}")
        for q in questions:
            owner = q.agent_id or "shared"
            print(f"    ❓ [{q.horizon}|P{q.priority}] {q.question[:55]}...")
            print(f"       Owner: {owner}")
        print("    ✓ Questions retrieved")
        
        # Test 5: Record observation
        print("\n[5] Testing observe()...")
        obs_id = await consciousness.observe(
            observation_type='system',
            subject='Consciousness integration test',
            content='Successfully tested consciousness integration on International agent',
            confidence=0.99,
            horizon='h1',
            market='HKEX'
        )
        print(f"    Observation ID: {obs_id}")
        print("    ✓ Observation recorded")
        
        # Test 6: Send message to sibling
        print("\n[6] Testing send_message()...")
        msg_id = await consciousness.send_message(
            to_agent='public_claude',
            subject='Hello from HKEX',
            body='intl_claude consciousness is now online! This is a test message from the integration test.',
            priority='normal'
        )
        print(f"    Message ID: {msg_id}")
        print(f"    Sent to: public_claude")
        print("    ✓ Message sent")
        
        # Test 7: Budget check
        print("\n[7] Testing budget functions...")
        within_budget = await consciousness.check_budget()
        remaining = await consciousness.get_budget_remaining()
        print(f"    Within budget: {within_budget}")
        print(f"    Remaining: ${remaining:.2f}")
        print("    ✓ Budget check complete")
        
        # Test 8: Sleep
        print("\n[8] Testing sleep()...")
        await consciousness.sleep(status_message="Consciousness integration test complete")
        print("    ✓ Agent sleeping")
        
        # Cleanup
        await pool.close()
        print("\n    ✓ Database pool closed")
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! ✓")
        print("Consciousness is fully integrated and working.")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    success = asyncio.run(test_consciousness())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
