from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import logging
import json
import time
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class HookType(Enum):
    """Types of hooks that can be registered"""
    PRE_EVALUATION = "pre_evaluation"
    POST_EVALUATION = "post_evaluation"
    PRE_SESSION = "pre_session"
    POST_SESSION = "post_session"
    PRE_TURN = "pre_turn"
    POST_TURN = "post_turn"
    ERROR_HANDLER = "error_handler"
    INTEGRATION_TEST = "integration_test"
    CUSTOM = "custom"

@dataclass
class HookContext:
    """Context passed to hooks"""
    hook_type: HookType
    session_id: Optional[str] = None
    turn_id: Optional[int] = None
    trajectory_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None
    timestamp: Optional[datetime] = None

class BaseHook(ABC):
    """Base class for all hooks"""
    
    def __init__(self, name: str, hook_type: HookType, priority: int = 0):
        self.name = name
        self.hook_type = hook_type
        self.priority = priority
        self.enabled = True
    
    @abstractmethod
    def execute(self, context: HookContext) -> Dict[str, Any]:
        """Execute the hook logic"""
        pass
    
    def __lt__(self, other):
        """Sort hooks by priority (higher priority first)"""
        return self.priority > other.priority

class IntegrationTestHook(BaseHook):
    """Hook for running integration tests"""
    
    def __init__(self, name: str, test_function: Callable, priority: int = 0):
        super().__init__(name, HookType.INTEGRATION_TEST, priority)
        self.test_function = test_function
    
    def execute(self, context: HookContext) -> Dict[str, Any]:
        """Execute integration test"""
        try:
            start_time = time.time()
            result = self.test_function(context)
            end_time = time.time()
            
            return {
                'status': 'success',
                'result': result,
                'execution_time': end_time - start_time,
                'hook_name': self.name
            }
        except Exception as e:
            logger.error(f"Integration test {self.name} failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'hook_name': self.name
            }

class DataValidationHook(BaseHook):
    """Hook for validating data before evaluation"""
    
    def __init__(self, name: str, validation_rules: Dict[str, Any], priority: int = 0):
        super().__init__(name, HookType.PRE_EVALUATION, priority)
        self.validation_rules = validation_rules
    
    def execute(self, context: HookContext) -> Dict[str, Any]:
        """Validate data according to rules"""
        validation_results = []
        
        if context.data:
            for field, rule in self.validation_rules.items():
                if field in context.data:
                    value = context.data[field]
                    if rule.get('required', False) and not value:
                        validation_results.append({
                            'field': field,
                            'status': 'failed',
                            'message': f'Required field {field} is empty'
                        })
                    elif rule.get('type') and not isinstance(value, rule['type']):
                        validation_results.append({
                            'field': field,
                            'status': 'failed',
                            'message': f'Field {field} has wrong type'
                        })
                    else:
                        validation_results.append({
                            'field': field,
                            'status': 'passed'
                        })
        
        return {
            'status': 'success',
            'validation_results': validation_results,
            'hook_name': self.name
        }

class PerformanceMonitoringHook(BaseHook):
    """Hook for monitoring performance metrics"""
    
    def __init__(self, name: str, priority: int = 0):
        super().__init__(name, HookType.POST_EVALUATION, priority)
        self.metrics = {}
    
    def execute(self, context: HookContext) -> Dict[str, Any]:
        """Collect performance metrics"""
        if context.results:
            # Extract performance metrics from results
            if 'agent_response' in context.results:
                agent_response = context.results['agent_response']
                if isinstance(agent_response, dict):
                    input_tokens = agent_response.get('input_tokens', 0)
                    output_tokens = agent_response.get('output_tokens', 0)
                    
                    # Store metrics
                    key = f"{context.session_id}_{context.turn_id}"
                    self.metrics[key] = {
                        'input_tokens': input_tokens,
                        'output_tokens': output_tokens,
                        'total_tokens': input_tokens + output_tokens,
                        'timestamp': context.timestamp
                    }
        
        return {
            'status': 'success',
            'metrics': self.metrics,
            'hook_name': self.name
        }

class ErrorHandlingHook(BaseHook):
    """Hook for handling errors during evaluation"""
    
    def __init__(self, name: str, error_handlers: Dict[str, Callable], priority: int = 0):
        super().__init__(name, HookType.ERROR_HANDLER, priority)
        self.error_handlers = error_handlers
    
    def execute(self, context: HookContext) -> Dict[str, Any]:
        """Handle errors based on error type"""
        if context.error:
            error_type = type(context.error).__name__
            
            if error_type in self.error_handlers:
                try:
                    result = self.error_handlers[error_type](context)
                    return {
                        'status': 'handled',
                        'error_type': error_type,
                        'result': result,
                        'hook_name': self.name
                    }
                except Exception as e:
                    logger.error(f"Error handler {self.name} failed: {str(e)}")
                    return {
                        'status': 'failed',
                        'error_type': error_type,
                        'error': str(e),
                        'hook_name': self.name
                    }
            else:
                return {
                    'status': 'unhandled',
                    'error_type': error_type,
                    'message': f'No handler for error type {error_type}',
                    'hook_name': self.name
                }
        
        return {
            'status': 'no_error',
            'hook_name': self.name
        }

class CustomHook(BaseHook):
    """Hook for custom functionality"""
    
    def __init__(self, name: str, hook_type: HookType, custom_function: Callable, priority: int = 0):
        super().__init__(name, hook_type, priority)
        self.custom_function = custom_function
    
    def execute(self, context: HookContext) -> Dict[str, Any]:
        """Execute custom hook function"""
        try:
            result = self.custom_function(context)
            return {
                'status': 'success',
                'result': result,
                'hook_name': self.name
            }
        except Exception as e:
            logger.error(f"Custom hook {self.name} failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'hook_name': self.name
            }

class HooksManager:
    """Manages the execution of hooks"""
    
    def __init__(self):
        self.hooks: Dict[HookType, List[BaseHook]] = {
            hook_type: [] for hook_type in HookType
        }
        self.execution_history = []
        self.max_workers = 5
    
    def register_hook(self, hook: BaseHook) -> None:
        """Register a hook"""
        if hook.enabled:
            self.hooks[hook.hook_type].append(hook)
            # Sort hooks by priority
            self.hooks[hook.hook_type].sort()
            logger.info(f"Registered hook: {hook.name} ({hook.hook_type.value})")
    
    def unregister_hook(self, hook_name: str, hook_type: HookType) -> None:
        """Unregister a hook by name and type"""
        self.hooks[hook_type] = [
            hook for hook in self.hooks[hook_type] 
            if hook.name != hook_name
        ]
        logger.info(f"Unregistered hook: {hook_name}")
    
    def execute_hooks(self, hook_type: HookType, context: HookContext) -> List[Dict[str, Any]]:
        """Execute all hooks of a specific type"""
        if hook_type not in self.hooks:
            return []
        
        hooks = self.hooks[hook_type]
        if not hooks:
            return []
        
        results = []
        
        # Execute hooks concurrently if there are multiple
        if len(hooks) > 1:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_hook = {
                    executor.submit(hook.execute, context): hook 
                    for hook in hooks
                }
                
                for future in future_to_hook:
                    hook = future_to_hook[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Hook {hook.name} execution failed: {str(e)}")
                        results.append({
                            'status': 'exception',
                            'error': str(e),
                            'hook_name': hook.name
                        })
        else:
            # Execute single hook
            hook = hooks[0]
            try:
                result = hook.execute(context)
                results.append(result)
            except Exception as e:
                logger.error(f"Hook {hook.name} execution failed: {str(e)}")
                results.append({
                    'status': 'exception',
                    'error': str(e),
                    'hook_name': hook.name
                })
        
        # Store execution history
        self.execution_history.append({
            'hook_type': hook_type.value,
            'context': context,
            'results': results,
            'timestamp': datetime.now()
        })
        
        return results
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of hook executions"""
        total_executions = len(self.execution_history)
        successful_executions = 0
        failed_executions = 0
        
        for execution in self.execution_history:
            for result in execution['results']:
                if result['status'] == 'success':
                    successful_executions += 1
                else:
                    failed_executions += 1
        
        return {
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'failed_executions': failed_executions,
            'success_rate': successful_executions / total_executions if total_executions > 0 else 0.0
        }

# Example integration test functions
def test_agent_connectivity(context: HookContext) -> Dict[str, Any]:
    """Test if agent is accessible"""
    import boto3
    from botocore.exceptions import ClientError
    
    try:
        # Test Bedrock agent runtime client
        client = boto3.client('bedrock-agent-runtime')
        # You could add a simple test call here
        return {
            'connectivity': 'success',
            'message': 'Agent is accessible'
        }
    except ClientError as e:
        return {
            'connectivity': 'failed',
            'error': str(e)
        }

def test_data_integrity(context: HookContext) -> Dict[str, Any]:
    """Test data integrity"""
    if context.data:
        required_fields = ['question', 'ground_truth']
        missing_fields = [field for field in required_fields if field not in context.data]
        
        if missing_fields:
            return {
                'integrity': 'failed',
                'missing_fields': missing_fields
            }
        else:
            return {
                'integrity': 'passed',
                'message': 'All required fields present'
            }
    
    return {
        'integrity': 'failed',
        'error': 'No data provided'
    }

def test_langfuse_connection(context: HookContext) -> Dict[str, Any]:
    """Test Langfuse connection"""
    try:
        from langfuse import Langfuse
        import os
        
        langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST")
        )
        
        # Create test trace
        test_trace = langfuse.trace(name="integration_test")
        test_trace.update(status_message="test_complete")
        langfuse.flush()
        
        return {
            'langfuse': 'connected',
            'message': 'Langfuse connection successful'
        }
    except Exception as e:
        return {
            'langfuse': 'failed',
            'error': str(e)
        }

# Example custom hook functions
def log_evaluation_start(context: HookContext) -> Dict[str, Any]:
    """Log the start of evaluation"""
    logger.info(f"Starting evaluation for session {context.session_id}, turn {context.turn_id}")
    return {
        'logged': True,
        'message': f'Evaluation started for {context.session_id}'
    }

def log_evaluation_end(context: HookContext) -> Dict[str, Any]:
    """Log the end of evaluation"""
    logger.info(f"Completed evaluation for session {context.session_id}, turn {context.turn_id}")
    return {
        'logged': True,
        'message': f'Evaluation completed for {context.session_id}'
    }

def create_default_hooks() -> HooksManager:
    """Create a HooksManager with default hooks"""
    manager = HooksManager()
    
    # Integration test hooks
    connectivity_hook = IntegrationTestHook(
        "agent_connectivity_test", 
        test_agent_connectivity, 
        priority=10
    )
    manager.register_hook(connectivity_hook)
    
    integrity_hook = IntegrationTestHook(
        "data_integrity_test", 
        test_data_integrity, 
        priority=9
    )
    manager.register_hook(integrity_hook)
    
    langfuse_hook = IntegrationTestHook(
        "langfuse_connection_test", 
        test_langfuse_connection, 
        priority=8
    )
    manager.register_hook(langfuse_hook)
    
    # Data validation hook
    validation_rules = {
        'question': {'required': True, 'type': str},
        'ground_truth': {'required': True, 'type': str},
        'question_id': {'required': True, 'type': int}
    }
    validation_hook = DataValidationHook(
        "data_validation", 
        validation_rules, 
        priority=7
    )
    manager.register_hook(validation_hook)
    
    # Performance monitoring hook
    perf_hook = PerformanceMonitoringHook("performance_monitor", priority=5)
    manager.register_hook(perf_hook)
    
    # Error handling hook
    error_handlers = {
        'ClientError': lambda ctx: {'action': 'retry', 'delay': 30},
        'ThrottlingException': lambda ctx: {'action': 'retry', 'delay': 60},
        'ValidationException': lambda ctx: {'action': 'skip', 'reason': 'invalid_data'}
    }
    error_hook = ErrorHandlingHook("error_handler", error_handlers, priority=10)
    manager.register_hook(error_hook)
    
    # Custom logging hooks
    start_hook = CustomHook("log_start", HookType.PRE_EVALUATION, log_evaluation_start, priority=1)
    manager.register_hook(start_hook)
    
    end_hook = CustomHook("log_end", HookType.POST_EVALUATION, log_evaluation_end, priority=1)
    manager.register_hook(end_hook)
    
    return manager

# Example usage
if __name__ == "__main__":
    # Create hooks manager with default hooks
    hooks_manager = create_default_hooks()
    
    # Example context
    context = HookContext(
        hook_type=HookType.PRE_EVALUATION,
        session_id="test_session",
        turn_id=1,
        trajectory_id="test_trajectory",
        data={
            'question': 'What is the weather?',
            'ground_truth': 'I can help you with weather information.',
            'question_id': 1
        },
        timestamp=datetime.now()
    )
    
    # Execute hooks
    results = hooks_manager.execute_hooks(HookType.PRE_EVALUATION, context)
    
    print("Hook execution results:")
    for result in results:
        print(f"  {result['hook_name']}: {result['status']}")
    
    # Get summary
    summary = hooks_manager.get_execution_summary()
    print(f"\nExecution summary: {summary}") 