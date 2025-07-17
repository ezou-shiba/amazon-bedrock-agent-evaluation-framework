import boto3
import json
from botocore.exceptions import ClientError

def check_bedrock_permissions():
    # Initialize boto3 clients
    sts = boto3.client('sts')
    iam = boto3.client('iam')
    bedrock = boto3.client('bedrock')
    
    try:
        # Get current identity
        identity = sts.get_caller_identity()
        print("\n=== Current AWS Identity ===")
        print(f"Account: {identity['Account']}")
        print(f"User ID: {identity['UserId']}")
        print(f"ARN: {identity['Arn']}")
        
        # Get user/role name from ARN
        arn_parts = identity['Arn'].split('/')
        if 'assumed-role' in identity['Arn']:
            role_name = arn_parts[-1]
            print(f"\nChecking permissions for role: {role_name}")
            
            # Get role policies
            attached_policies = iam.list_attached_role_policies(RoleName=role_name)
            print("\n=== Attached Policies ===")
            for policy in attached_policies['AttachedPolicies']:
                print(f"- {policy['PolicyName']}")
                
            # Get inline policies
            inline_policies = iam.list_role_policies(RoleName=role_name)
            print("\n=== Inline Policies ===")
            for policy_name in inline_policies['PolicyNames']:
                print(f"- {policy_name}")
                
        else:
            user_name = arn_parts[-1]
            print(f"\nChecking permissions for user: {user_name}")
            
            # Get user policies
            attached_policies = iam.list_attached_user_policies(UserName=user_name)
            print("\n=== Attached Policies ===")
            for policy in attached_policies['AttachedPolicies']:
                print(f"- {policy['PolicyName']}")
                
            # Get inline policies
            inline_policies = iam.list_user_policies(UserName=user_name)
            print("\n=== Inline Policies ===")
            for policy_name in inline_policies['PolicyNames']:
                print(f"- {policy_name}")
        
        # Test Bedrock permissions
        print("\n=== Testing Bedrock Permissions ===")
        try:
            # Try to list foundation models
            response = bedrock.list_foundation_models()
            print("✅ Successfully listed foundation models")
        except ClientError as e:
            print(f"❌ Error listing foundation models: {str(e)}")
            
        try:
            # Try to list agents
            response = bedrock.list_agents()
            print("✅ Successfully listed agents")
        except ClientError as e:
            print(f"❌ Error listing agents: {str(e)}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    check_bedrock_permissions() 