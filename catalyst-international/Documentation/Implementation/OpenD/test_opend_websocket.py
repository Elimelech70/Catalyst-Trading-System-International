#!/usr/bin/env python3
"""
OpenD WebSocket Connection Test Script
=====================================

Tests WebSocket connectivity and real-time data streaming
for the MooMoo OpenD trading gateway.
"""

import asyncio
import websockets
import json
import time
import hashlib
from datetime import datetime

class OpenDWebSocketTester:
    def __init__(self, host="127.0.0.1", port=33333, auth_key="hello"):
        self.host = host
        self.port = port
        self.auth_key = auth_key
        self.auth_key_md5 = hashlib.md5(auth_key.encode()).hexdigest()
        self.uri = f"ws://{host}:{port}"
        self.websocket = None

    async def connect(self):
        """Connect to OpenD WebSocket"""
        try:
            print(f"🔌 Connecting to OpenD WebSocket at {self.uri}")
            self.websocket = await websockets.connect(
                self.uri,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            print("✅ WebSocket connected successfully")
            return True
        except Exception as e:
            print(f"❌ WebSocket connection failed: {e}")
            return False

    async def authenticate(self):
        """Authenticate with OpenD WebSocket"""
        try:
            auth_msg = {
                "Protocol": "QotSub",
                "Version": 1,
                "ReqParam": {
                    "c2s": {
                        "authKey": self.auth_key_md5
                    }
                }
            }

            await self.websocket.send(json.dumps(auth_msg))
            print("🔐 Authentication request sent")

            # Wait for auth response
            response = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=10.0
            )

            auth_response = json.loads(response)
            print(f"📝 Auth response: {auth_response}")

            if auth_response.get("ErrCode", 1) == 0:
                print("✅ Authentication successful")
                return True
            else:
                print(f"❌ Authentication failed: {auth_response.get('ErrMsg', 'Unknown error')}")
                return False

        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

    async def subscribe_quotes(self, symbols=None):
        """Subscribe to real-time quotes"""
        if symbols is None:
            symbols = ["HK.00700", "US.AAPL"]  # Tencent and Apple as test symbols

        try:
            for symbol in symbols:
                sub_msg = {
                    "Protocol": "Qot_Sub",
                    "Version": 1,
                    "ReqParam": {
                        "c2s": {
                            "securityList": [{
                                "market": int(symbol.split('.')[0] == 'HK'),  # 1 for HK, 0 for US
                                "code": symbol.split('.')[1]
                            }],
                            "subTypeList": [1, 2, 3],  # Basic quote, order book, ticker
                            "isSubOrUnSub": True,
                            "isRegOrUnRegPush": True
                        }
                    }
                }

                await self.websocket.send(json.dumps(sub_msg))
                print(f"📡 Subscribed to {symbol}")

            return True

        except Exception as e:
            print(f"❌ Subscription error: {e}")
            return False

    async def listen_data(self, duration=30):
        """Listen for real-time data"""
        print(f"👂 Listening for data for {duration} seconds...")

        start_time = time.time()
        message_count = 0

        try:
            while time.time() - start_time < duration:
                try:
                    # Wait for messages with timeout
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=5.0
                    )

                    message_count += 1
                    data = json.loads(message)

                    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    protocol = data.get('Protocol', 'Unknown')

                    print(f"[{timestamp}] #{message_count} - {protocol}")

                    # Parse quote data if available
                    if 'RetData' in data:
                        ret_data = data['RetData']
                        if 'security' in str(ret_data):
                            print(f"    📊 Quote update: {ret_data}")

                except asyncio.TimeoutError:
                    print("⏱️  No data received (timeout)")
                    continue

        except Exception as e:
            print(f"❌ Data listening error: {e}")

        print(f"📈 Received {message_count} messages in {duration} seconds")
        return message_count > 0

    async def disconnect(self):
        """Disconnect from WebSocket"""
        if self.websocket:
            try:
                await self.websocket.close()
                print("🔌 WebSocket disconnected")
            except Exception as e:
                print(f"❌ Disconnect error: {e}")

    async def test_connection_full(self):
        """Run full connection test"""
        print("🧪 OpenD WebSocket Full Test")
        print("=" * 40)

        # Test 1: Basic connectivity
        if not await self.connect():
            return False

        # Test 2: Authentication
        if not await self.authenticate():
            await self.disconnect()
            return False

        # Test 3: Data subscription
        if not await self.subscribe_quotes():
            await self.disconnect()
            return False

        # Test 4: Real-time data
        data_received = await self.listen_data(30)

        # Cleanup
        await self.disconnect()

        print("\n🏁 Test Results:")
        print("===============")
        print(f"✅ Connection: Success")
        print(f"✅ Authentication: Success")
        print(f"✅ Subscription: Success")
        print(f"{'✅' if data_received else '❌'} Data Reception: {'Success' if data_received else 'Failed'}")

        return data_received

async def main():
    """Main test function"""
    print("🚀 Starting OpenD WebSocket Test")
    print("Configuration:")
    print(f"  Host: 127.0.0.1")
    print(f"  Port: 33333")
    print(f"  Auth Key: hello (MD5: {hashlib.md5('hello'.encode()).hexdigest()})")
    print()

    tester = OpenDWebSocketTester()

    try:
        success = await tester.test_connection_full()

        if success:
            print("\n🎉 All tests passed! OpenD WebSocket is working correctly.")
            print("\n💡 Next steps:")
            print("   - Integrate WebSocket into your trading system")
            print("   - Subscribe to specific symbols you want to trade")
            print("   - Implement error handling and reconnection logic")
        else:
            print("\n⚠️  Some tests failed. Check OpenD configuration:")
            print("   - Ensure OpenD is running")
            print("   - Check WebSocket port (33333) is open")
            print("   - Verify authentication key matches configuration")

    except KeyboardInterrupt:
        print("\n\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")

if __name__ == "__main__":
    # Check for dependencies
    try:
        import websockets
    except ImportError:
        print("❌ websockets library not found")
        print("Install with: pip install websockets")
        exit(1)

    asyncio.run(main())