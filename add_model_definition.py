import os
from dotenv import load_dotenv
import requests
import json

def add_model_definition():
    # Load environment variables
    load_dotenv('config.env')
    
    # Langfuse API details
    host = os.getenv('LANGFUSE_HOST').replace('https://', 'http://')  # Force HTTP
    public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
    secret_key = os.getenv('LANGFUSE_SECRET_KEY')
    
    # Model definition for Claude 3 Sonnet
    model_definition = {
        "modelName": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        "matchPattern": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        "startDate": None,
        "tokenizerId": "claude",
        "tokenizerConfig": None,
        "unit": "TOKENS",
        "inputPrice": 0.000024,
        "outputPrice": 0.000080,
        "totalPrice": None,
        "isLangfuseManaged": False
    }
    
    try:
        # Create model definition
        url = f"{host}/api/public/models"
        
        # Use Basic Auth with public and secret keys
        auth = (public_key, secret_key)
        headers = {
            "Content-Type": "application/json"
        }
        
        print("\n=== Adding Model Definition ===")
        print(f"Host: {host}")
        print(f"Model: {model_definition['modelName']}")
        print(f"Input Price: ${model_definition['inputPrice'] * 1000}/1K tokens")
        print(f"Output Price: ${model_definition['outputPrice'] * 1000}/1K tokens")
        
        # First try POST to create
        print("\nAttempting to create model...")
        response = requests.post(url, json=model_definition, auth=auth, headers=headers, verify=False)
        
        if response.status_code in [200, 201]:
            print("✅ Model definition created successfully!")
        elif response.status_code == 409:
            # Model exists, try PUT to update
            print("Model already exists. Attempting to update...")
            response = requests.put(url, json=model_definition, auth=auth, headers=headers, verify=False)
            if response.status_code in [200, 201]:
                print("✅ Model definition updated successfully!")
            else:
                print(f"❌ Error updating model:")
                print(f"Status code: {response.status_code}")
                print(f"Response: {response.text}")
        else:
            print(f"❌ Error creating model:")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            
        # Print response details for debugging
        print("\nResponse Details:")
        print(f"Status Code: {response.status_code}")
        print("Headers:", response.headers)
        print("Response Body:", response.text)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    add_model_definition()