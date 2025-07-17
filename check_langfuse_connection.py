import os
import requests
import socket
from urllib3.exceptions import NewConnectionError
from dotenv import load_dotenv

def check_load_balancer():
    load_dotenv()
    host = os.getenv("LANGFUSE_HOST")
    
    if not host:
        print("❌ LANGFUSE_HOST not set")
        return
    
    # Remove protocol if present
    host = host.replace("https://", "").replace("http://", "")
    
    print(f"\n=== Testing Load Balancer Connection ===")
    print(f"Host: {host}")
    
    # Test 1: Basic TCP connection
    try:
        print("\n1. Testing basic TCP connection...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, 443))
        sock.close()
        print("✅ TCP connection successful")
    except Exception as e:
        print(f"❌ TCP connection failed: {str(e)}")
    
    # Test 2: HTTP connection
    try:
        print("\n2. Testing HTTP connection...")
        response = requests.get(f"http://{host}/api/public/health", timeout=5, verify=False)
        print(f"✅ HTTP connection successful (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ HTTP connection failed: {str(e)}")
    
    # Test 3: HTTPS connection
    try:
        print("\n3. Testing HTTPS connection...")
        response = requests.get(f"https://{host}/api/public/health", timeout=5, verify=False)
        print(f"✅ HTTPS connection successful (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ HTTPS connection failed: {str(e)}")
    
    # Test 4: Different endpoints
    endpoints = [
        "/health",
        "/api/health",
        "/api/public/health",
        "/"
    ]
    
    print("\n4. Testing different endpoints...")
    for endpoint in endpoints:
        try:
            response = requests.get(f"https://{host}{endpoint}", timeout=5, verify=False)
            print(f"✅ {endpoint}: Success (Status: {response.status_code})")
        except Exception as e:
            print(f"❌ {endpoint}: Failed ({str(e)})")
    
    print("\n=== Troubleshooting Steps ===")
    print("1. Check if the load balancer is in the same VPC as your notebook")
    print("2. Verify the security group rules:")
    print("   - Inbound: Allow TCP 443 from your notebook's IP")
    print("   - Outbound: Allow all traffic")
    print("3. Check if the load balancer's target group is healthy")
    print("4. Verify the load balancer's listeners are configured for HTTPS")
    print("5. Check if there are any network ACLs blocking the traffic")

if __name__ == "__main__":
    check_load_balancer() 