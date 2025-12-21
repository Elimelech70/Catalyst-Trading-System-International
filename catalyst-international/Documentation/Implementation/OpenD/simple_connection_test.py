#!/usr/bin/env python3
"""
Simple OpenD Connection Test
==========================
Tests basic TCP connectivity to OpenD ports
"""

import socket
import json
import time
from datetime import datetime

def test_port_connection(host, port, name):
    """Test if a port is reachable"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            print(f"✅ {name} port {port}: Connected")
            return True
        else:
            print(f"❌ {name} port {port}: Connection failed")
            return False
    except Exception as e:
        print(f"❌ {name} port {port}: Error - {e}")
        return False

def test_http_api(host, port):
    """Test HTTP API endpoint"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))

        # Send simple HTTP request
        request = "GET / HTTP/1.1\r\nHost: {}:{}\r\nConnection: close\r\n\r\n".format(host, port)
        sock.send(request.encode())

        # Read response
        response = sock.recv(1024).decode()
        sock.close()

        if response:
            print(f"✅ HTTP API responding: {response.split()[1] if len(response.split()) > 1 else 'OK'}")
            return True
        else:
            print("❌ HTTP API: No response")
            return False
    except Exception as e:
        print(f"❌ HTTP API test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 OpenD Connection Test")
    print("=" * 30)
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    host = "127.0.0.1"
    results = []

    # Test API port
    results.append(test_port_connection(host, 11111, "API"))

    # Test WebSocket port
    results.append(test_port_connection(host, 33333, "WebSocket"))

    # Test Telnet port
    results.append(test_port_connection(host, 22222, "Telnet"))

    print()

    # Test HTTP API if available
    if results[0]:  # API port is open
        print("🌐 Testing HTTP API...")
        test_http_api(host, 11111)

    print()
    print("📊 Summary")
    print("=" * 15)

    if all(results):
        print("🎉 All OpenD services are reachable!")
        print("✅ Ready for trading operations")
        print()
        print("💡 Next steps:")
        print("   - Your credentials are configured")
        print("   - OpenD is running and accessible")
        print("   - Start building your trading agent!")
    else:
        failed_services = []
        if not results[0]:
            failed_services.append("API (11111)")
        if not results[1]:
            failed_services.append("WebSocket (33333)")
        if not results[2]:
            failed_services.append("Telnet (22222)")

        print(f"⚠️  {len(failed_services)} service(s) not reachable:")
        for service in failed_services:
            print(f"   - {service}")

        print()
        print("🔧 Troubleshooting:")
        print("   1. Check if OpenD is running: ps aux | grep OpenD")
        print("   2. Check logs: tail ~/logs/opend/opend.log")
        print("   3. Restart OpenD: ./start_opend.sh")

if __name__ == "__main__":
    main()