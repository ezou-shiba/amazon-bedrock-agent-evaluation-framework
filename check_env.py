import os
from dotenv import load_dotenv
from langfuse import Langfuse
import requests

def check_environment():
    # Load environment variables
    load_dotenv()
    
    # Check required environment variables
    required_vars = [
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_HOST"
    ]
    
    print("\n=== Environment Variables Check ===")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Set")
        else:
            print(f"❌ {var}: Not Set")
    
    # Test network connectivity
    print("\n=== Network Connectivity Check ===")
    try:
        host = os.getenv("LANGFUSE_HOST")
        if not host:
            print("❌ LANGFUSE_HOST not set")
            return
        
        # Remove protocol if present
        host = host.replace("https://", "").replace("http://", "")
        
        print(f"Testing connection to {host}...")
        response = requests.get(f"https://{host}/api/public/health", timeout=5)
        print(f"✅ Connection successful (Status: {response.status_code})")
        
        # Initialize Langfuse client
        print("\n=== Langfuse Client Test ===")
        langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST"),
            debug=True
        )
        
        # Create test trace
        print("Creating test trace...")
        trace = langfuse.trace(
            name="connection_test",
            metadata={"test": "connection_check"}
        )
        print(f"Trace created with ID: {trace.id}")
        
        # Create test span
        print("Creating test span...")
        span = trace.span(
            name="test_span",
            metadata={"test": "span_check"}
        )
        print(f"Span created with ID: {span.id}")
        
        # Update span
        print("Updating span...")
        span.update(
            status_message="test_complete",
            metadata={"status": "success"}
        )
        
        # Update trace
        print("Updating trace...")
        trace.update(
            status_message="test_complete",
            metadata={"status": "success"}
        )
        
        # Force flush
        print("Flushing client...")
        langfuse.flush()
        
        print("\n✅ All tests completed successfully!")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {str(e)}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    check_environment() 