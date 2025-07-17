import asyncio
import concurrent.futures
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import time
import json
import uuid
from queue import Queue
import logging

from single_run import setup_environment, get_config, create_evaluator
from helpers.agent_info_extractor import AgentInfoExtractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ConversationTurn:
    """Represents a single turn in a multi-turn conversation"""
    turn_id: int
    question: str
    expected_response: str
    evaluation_type: str
    metadata: Dict[str, Any] = None

@dataclass
class ConversationSession:
    """Represents a complete conversation session"""
    session_id: str
    trajectory_id: str
    turns: List[ConversationTurn]
    context: Dict[str, Any] = None
    max_concurrent_turns: int = 3

class ConcurrentEvaluationOrchestrator:
    """
    Orchestrates concurrent, multi-turn conversations with evaluation capabilities.
    
    Features:
    - Concurrent processing of multiple conversation sessions
    - Multi-turn conversation support with context preservation
    - Configurable concurrency limits
    - Real-time evaluation results
    - Integration with existing evaluators
    """
    
    def __init__(self, config: Dict[str, Any], max_workers: int = 5):
        self.config = config
        self.max_workers = max_workers
        self.results_queue = Queue()
        self.active_sessions = {}
        self.session_locks = {}
        
        # Initialize shared resources
        self.extractor = AgentInfoExtractor(config['clients']['bedrock_agent_client'])
        self.agent_info = self.extractor.extract_agent_info(
            config['AGENT_ID'], 
            config['AGENT_ALIAS_ID']
        )
        
        # Setup Langfuse
        self.langfuse_client = setup_environment()
        
    def create_conversation_session(self, trajectory_id: str, turns_data: List[Dict]) -> ConversationSession:
        """Create a conversation session from trajectory data"""
        session_id = str(uuid.uuid4())
        turns = []
        
        for i, turn_data in enumerate(turns_data):
            turn = ConversationTurn(
                turn_id=i,
                question=turn_data['question'],
                expected_response=turn_data.get('ground_truth', ''),
                evaluation_type=turn_data.get('question_type', 'COT'),
                metadata=turn_data.get('metadata', {})
            )
            turns.append(turn)
        
        session = ConversationSession(
            session_id=session_id,
            trajectory_id=trajectory_id,
            turns=turns,
            context={},
            max_concurrent_turns=3
        )
        
        self.active_sessions[session_id] = session
        self.session_locks[session_id] = threading.Lock()
        
        return session
    
    def evaluate_single_turn(self, session: ConversationSession, turn: ConversationTurn) -> Dict[str, Any]:
        """Evaluate a single conversation turn"""
        try:
            # Create evaluator for this turn
            evaluator = create_evaluator(
                eval_type=turn.evaluation_type,
                config=self.config,
                agent_info=self.agent_info,
                data={
                    'question': turn.question,
                    'ground_truth': turn.expected_response,
                    'question_id': turn.turn_id,
                    'metadata': turn.metadata
                },
                trace_id=str(uuid.uuid1()),
                session_id=session.session_id,
                trajectory_id=session.trajectory_id
            )
            
            # Run evaluation
            results = evaluator.run_evaluation()
            
            if results is None:
                logger.warning(f"Evaluation failed for session {session.session_id}, turn {turn.turn_id}")
                return {
                    'session_id': session.session_id,
                    'turn_id': turn.turn_id,
                    'status': 'failed',
                    'error': 'Evaluation returned None'
                }
            
            return {
                'session_id': session.session_id,
                'turn_id': turn.turn_id,
                'status': 'success',
                'results': results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error evaluating turn {turn.turn_id} in session {session.session_id}: {str(e)}")
            return {
                'session_id': session.session_id,
                'turn_id': turn.turn_id,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def process_conversation_session(self, session: ConversationSession) -> List[Dict[str, Any]]:
        """Process a complete conversation session with multi-turn support"""
        results = []
        
        # Process turns with controlled concurrency
        with concurrent.futures.ThreadPoolExecutor(max_workers=session.max_concurrent_turns) as executor:
            # Submit all turns for evaluation
            future_to_turn = {
                executor.submit(self.evaluate_single_turn, session, turn): turn 
                for turn in session.turns
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_turn):
                turn = future_to_turn[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Update session context based on results
                    if result['status'] == 'success':
                        self._update_session_context(session, turn, result)
                    
                    logger.info(f"Completed evaluation for session {session.session_id}, turn {turn.turn_id}")
                    
                except Exception as e:
                    logger.error(f"Exception in turn {turn.turn_id}: {str(e)}")
                    results.append({
                        'session_id': session.session_id,
                        'turn_id': turn.turn_id,
                        'status': 'exception',
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
        
        return results
    
    def _update_session_context(self, session: ConversationSession, turn: ConversationTurn, result: Dict[str, Any]):
        """Update session context based on evaluation results"""
        if 'results' in result and 'agent_response' in result['results']:
            # Store agent response in context for future turns
            session.context[f'turn_{turn.turn_id}_response'] = result['results']['agent_response']
            
            # You can add more sophisticated context management here
            # For example, extracting key information, maintaining conversation state, etc.
    
    def run_concurrent_evaluations(self, data_file: str) -> Dict[str, Any]:
        """Run concurrent evaluations on multiple conversation sessions"""
        # Load conversation data
        with open(data_file, 'r') as f:
            data_dict = json.load(f)
        
        all_results = {}
        session_results = []
        
        # Create conversation sessions
        sessions = []
        for trajectory_id, turns_data in data_dict.items():
            session = self.create_conversation_session(trajectory_id, turns_data)
            sessions.append(session)
        
        logger.info(f"Created {len(sessions)} conversation sessions for evaluation")
        
        # Process sessions concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all sessions for processing
            future_to_session = {
                executor.submit(self.process_conversation_session, session): session 
                for session in sessions
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_session):
                session = future_to_session[future]
                try:
                    session_result = future.result()
                    session_results.append({
                        'session_id': session.session_id,
                        'trajectory_id': session.trajectory_id,
                        'results': session_result,
                        'context': session.context
                    })
                    
                    all_results[session.trajectory_id] = {
                        'session_id': session.session_id,
                        'results': session_result,
                        'context': session.context
                    }
                    
                    logger.info(f"Completed session {session.session_id} ({session.trajectory_id})")
                    
                except Exception as e:
                    logger.error(f"Exception in session {session.session_id}: {str(e)}")
                    session_results.append({
                        'session_id': session.session_id,
                        'trajectory_id': session.trajectory_id,
                        'error': str(e),
                        'status': 'failed'
                    })
        
        # Generate summary statistics
        summary = self._generate_evaluation_summary(session_results)
        
        return {
            'summary': summary,
            'sessions': session_results,
            'all_results': all_results,
            'total_sessions': len(sessions),
            'total_turns': sum(len(session.turns) for session in sessions),
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_evaluation_summary(self, session_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics from evaluation results"""
        total_turns = 0
        successful_turns = 0
        failed_turns = 0
        error_turns = 0
        
        evaluation_scores = {
            'helpfulness': [],
            'faithfulness': [],
            'instruction_following': [],
            'overall': []
        }
        
        for session_result in session_results:
            if 'results' in session_result:
                for turn_result in session_result['results']:
                    total_turns += 1
                    
                    if turn_result['status'] == 'success':
                        successful_turns += 1
                        
                        # Extract evaluation scores if available
                        if 'results' in turn_result and 'evaluation_results' in turn_result['results']:
                            eval_results = turn_result['results']['evaluation_results']
                            if 'metrics_scores' in eval_results:
                                for metric_name, metric_data in eval_results['metrics_scores'].items():
                                    if 'score' in metric_data:
                                        score = metric_data['score']
                                        if metric_name.lower() in evaluation_scores:
                                            evaluation_scores[metric_name.lower()].append(score)
                    
                    elif turn_result['status'] == 'failed':
                        failed_turns += 1
                    elif turn_result['status'] == 'error':
                        error_turns += 1
        
        # Calculate average scores
        avg_scores = {}
        for metric, scores in evaluation_scores.items():
            if scores:
                avg_scores[metric] = sum(scores) / len(scores)
            else:
                avg_scores[metric] = 0.0
        
        return {
            'total_turns': total_turns,
            'successful_turns': successful_turns,
            'failed_turns': failed_turns,
            'error_turns': error_turns,
            'success_rate': successful_turns / total_turns if total_turns > 0 else 0.0,
            'average_scores': avg_scores,
            'total_sessions': len(session_results)
        }

def run_concurrent_evaluation(data_file: str, max_workers: int = 5) -> Dict[str, Any]:
    """Main function to run concurrent evaluations"""
    logger.info("Starting concurrent evaluation framework")
    
    # Setup environment and config
    setup_environment()
    config = get_config()
    
    # Create orchestrator
    orchestrator = ConcurrentEvaluationOrchestrator(config, max_workers)
    
    # Run evaluations
    start_time = time.time()
    results = orchestrator.run_concurrent_evaluations(data_file)
    end_time = time.time()
    
    results['execution_time'] = end_time - start_time
    results['max_workers'] = max_workers
    
    logger.info(f"Concurrent evaluation completed in {results['execution_time']:.2f} seconds")
    logger.info(f"Summary: {results['summary']}")
    
    return results

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv('config.env')
    data_file = os.getenv('DATA_FILE_PATH', 'data_files/data_file.json')
    
    results = run_concurrent_evaluation(data_file, max_workers=3)
    
    # Print summary
    print("\n=== Concurrent Evaluation Summary ===")
    print(f"Total Sessions: {results['summary']['total_sessions']}")
    print(f"Total Turns: {results['summary']['total_turns']}")
    print(f"Success Rate: {results['summary']['success_rate']:.2%}")
    print(f"Execution Time: {results['execution_time']:.2f} seconds")
    
    if results['summary']['average_scores']:
        print("\nAverage Scores:")
        for metric, score in results['summary']['average_scores'].items():
            print(f"  {metric}: {score:.3f}") 