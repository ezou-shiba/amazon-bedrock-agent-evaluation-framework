import os
import uuid
import boto3
import sys
import json
from typing import Dict, Any, List
from evaluators.rag_evaluator import RAGEvaluator
from evaluators.cot_evaluator import COTEvaluator
from evaluators.text2sql_evaluator import Text2SQLEvaluator
from evaluators.custom_evaluator import CustomEvaluator
from botocore.client import Config
from helpers.agent_info_extractor import AgentInfoExtractor
import time

from dotenv import load_dotenv
from langfuse import Langfuse

# Load environment variables from config.env
load_dotenv('config.env')

# Get environment variables

#AGENT SETUP
AGENT_ID = os.getenv('AGENT_ID')
AGENT_ALIAS_ID = os.getenv('AGENT_ALIAS_ID')

#LANGFUSE SETUP
LANGFUSE_PUBLIC_KEY = os.getenv('LANGFUSE_PUBLIC_KEY')
LANGFUSE_SECRET_KEY = os.getenv('LANGFUSE_SECRET_KEY')
LANGFUSE_HOST = os.getenv('LANGFUSE_HOST')

#MODEL HYPERPARAMETERS
MAX_TOKENS = int(os.getenv('MAX_TOKENS'))
TEMPERATURE = float(os.getenv('TEMPERATURE'))
TOP_P = float(os.getenv('TOP_P'))

#EVALUATION MODELS
MODEL_ID_EVAL = os.getenv('MODEL_ID_EVAL')
EMBEDDING_MODEL_ID = os.getenv('EMBEDDING_MODEL_ID')
MODEL_ID_EVAL_COT = os.getenv('MODEL_ID_EVAL_COT')

#DATA
DATA_FILE_PATH = os.getenv('DATA_FILE_PATH')

def setup_environment() -> None:
    """Set up the environment and initialize clients."""
    print("Initializing Langfuse client...")
    
    # Initialize Langfuse client with debug mode
    langfuse_client = Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST"),
        debug=True  # Enable debug mode
    )
    
    print(f"Langfuse client initialized with host: {os.getenv('LANGFUSE_HOST')}")
    
    # Test Langfuse connection with more detailed logging
    try:
        print("Creating test trace...")
        test_trace = langfuse_client.trace(
            name="test_connection",
            metadata={"test": "connection_check"}
        )
        print(f"Test trace created with ID: {test_trace.id}")
        
        print("Creating test span...")
        test_span = test_trace.span(
            name="test_span",
            metadata={"test": "span_check"}
        )
        print(f"Test span created with ID: {test_span.id}")
        
        print("Updating test span...")
        test_span.update(
            status_message="test_complete",
            metadata={"status": "success"}
        )
        print("Test span updated")
        
        print("Updating test trace status...")
        test_trace.update(
            status_message="test_complete",
            metadata={"status": "success"}
        )
        print("Test trace updated")
        
        # Force flush to ensure data is sent
        print("Flushing Langfuse client...")
        langfuse_client.flush()
        
        print("✅ Successfully connected to Langfuse")
        return langfuse_client
    except Exception as e:
        print(f"❌ Error connecting to Langfuse: {str(e)}")
        print(f"Debug info - Host: {os.getenv('LANGFUSE_HOST')}")
        print(f"Debug info - Public Key: {os.getenv('LANGFUSE_PUBLIC_KEY')}")
        raise

def get_config() -> Dict[str, Any]:
    """Get configuration settings"""

    # Create shared clients
    bedrock_config = Config(
        connect_timeout=120, 
        read_timeout=120, 
        retries={'max_attempts': 0}
    )

    shared_clients = {
        'bedrock_agent_client': boto3.client('bedrock-agent'),
        'bedrock_agent_runtime': boto3.client(
            'bedrock-agent-runtime',
            config=bedrock_config
        ),
        'bedrock_runtime': boto3.client('bedrock-runtime')
    }

    return {
        'AGENT_ID': AGENT_ID,
        'AGENT_ALIAS_ID': AGENT_ALIAS_ID,
        'MODEL_ID_EVAL': MODEL_ID_EVAL,
        'EMBEDDING_MODEL_ID': EMBEDDING_MODEL_ID,
        'TEMPERATURE': TEMPERATURE,
        'MAX_TOKENS': MAX_TOKENS,
        'MODEL_ID_EVAL_COT': MODEL_ID_EVAL_COT,
        'TOP_P': TOP_P,
        'ENABLE_TRACE': True,
        'clients': shared_clients
    }


def create_evaluator(eval_type: str, config: Dict[str, Any], 
                    agent_info: Dict[str, Any], data: Dict[str, Any], trace_id: str, 
                    session_id: str, trajectory_id: str) -> Any:
    """Create appropriate evaluator based on evaluation type"""
    evaluator_map = {
        'RAG': RAGEvaluator,
        'TEXT2SQL': Text2SQLEvaluator,
        'COT': COTEvaluator,
        'CUSTOM': CustomEvaluator
        # Add other evaluator types here
    }
    
    evaluator_class = evaluator_map.get(eval_type)
    if not evaluator_class:
        raise ValueError(f"Unknown evaluation type: {eval_type}")
        
    return evaluator_class(
        config=config,
        agent_info=agent_info,
        eval_type=eval_type,
        question=data['question'],
        ground_truth=data['ground_truth'],
        trace_id=trace_id,
        session_id=session_id,
        trajectory_id = trajectory_id,
        question_id=data['question_id']
    )

def run_evaluation(data_file: str) -> None:
    """Main evaluation function"""
    # Setup
    setup_environment()
    config = get_config()
    
    # Initialize clients and extractors
    extractor = AgentInfoExtractor(config['clients']['bedrock_agent_client'])
    agent_info = extractor.extract_agent_info(AGENT_ID, AGENT_ALIAS_ID)
    
    # Load and process data
    with open(data_file, 'r') as f:
        data_dict = json.load(f)
        
        #For each data file, go into each trajectory
        for trajectoryID, questions in data_dict.items():
            #Iterate through all the questions in each trajectory
            
            # Create unqiue session ID for trajectory
            session_id = str(uuid.uuid4())
            print(f"Session ID for {trajectoryID}: {session_id}")

            #go through each question in each trajectory
            for question in questions:
                #get the evaluation type for the question
                eval_type = question.get('question_type')
                question_id = question['question_id']

                print(f"Running {trajectoryID} - {eval_type} - Q{question_id} evaluation")

                trace_id = str(uuid.uuid1())
                              
                try:
                    evaluator = create_evaluator(
                        eval_type=eval_type,
                        config=config,
                        agent_info=agent_info,
                        data=question,
                        trace_id=trace_id,
                        session_id=session_id,
                        trajectory_id= trajectoryID
                    )


                    results = evaluator.run_evaluation()
                    if results is None:
                        print(f"Skipping {trajectoryID} question {question_id} due to evaluation failure")
                        time.sleep(90)
                        continue
                        
                    print(f"Successfully evaluated {trajectoryID} question {question_id}")
                    # print(results)
                    time.sleep(90)
                    
                except Exception as e:
                    print(f"Failed to evalute for {trajectoryID} question {question_id}: {str(e)}")
                    #if not a bedrock error, continue to next question
                    time.sleep(90)
                    continue
                
                except KeyboardInterrupt:
                    sys.exit(0)
            
# Driver
if __name__ == "__main__":
    #Name of the data file
    run_evaluation(DATA_FILE_PATH)