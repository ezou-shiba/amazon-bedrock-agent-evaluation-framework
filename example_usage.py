#!/usr/bin/env python3
"""
Example Usage of Enhanced Agent Evaluation Framework

This script demonstrates how to use the enhanced features:
1. Concurrent multi-turn conversations
2. Hooks system for integration testing
3. CI/CD pipeline integration
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Import enhanced components
from enhanced_run import EnhancedEvaluationFramework
from hooks_system import HookType, HookContext
from cicd_integration import QualityGate
from concurrent_evaluator import run_concurrent_evaluation

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def example_custom_hook(context: HookContext):
    """Example custom hook that logs evaluation progress"""
    logger.info(f"Custom hook executed for {context.hook_type.value}")
    if context.data:
        logger.info(f"Data: {context.data}")
    return {
        'status': 'success',
        'message': f'Custom hook executed at {datetime.now().isoformat()}',
        'hook_type': context.hook_type.value
    }

def example_performance_hook(context: HookContext):
    """Example hook that monitors performance"""
    if context.results and 'execution_time' in context.results:
        execution_time = context.results['execution_time']
        logger.info(f"Evaluation completed in {execution_time:.2f} seconds")
        
        if execution_time > 300:  # 5 minutes
            return {
                'status': 'warning',
                'message': f'Execution time ({execution_time:.2f}s) exceeds 5 minutes'
            }
    
    return {
        'status': 'success',
        'message': 'Performance check passed'
    }

def run_basic_example():
    """Run basic concurrent evaluation example"""
    logger.info("=== Running Basic Concurrent Evaluation Example ===")
    
    # Load environment and setup
    load_dotenv('config.env')
    from single_run import setup_environment, get_config
    
    setup_environment()
    config = get_config()
    
    # Create enhanced framework
    framework = EnhancedEvaluationFramework(config)
    
    # Add custom hooks
    framework.add_custom_hook(
        'example_logging_hook',
        HookType.PRE_EVALUATION,
        example_custom_hook,
        priority=5
    )
    
    framework.add_custom_hook(
        'performance_monitor_hook',
        HookType.POST_EVALUATION,
        example_performance_hook,
        priority=3
    )
    
    # Run concurrent evaluation
    data_file = os.getenv('DATA_FILE_PATH', 'data_files/data_file.json')
    results = framework.run_concurrent_mode(data_file, max_workers=3)
    
    # Print results
    print("\n=== Basic Example Results ===")
    if 'summary' in results:
        summary = results['summary']
        print(f"Total Sessions: {summary.get('total_sessions', 'N/A')}")
        print(f"Total Turns: {summary.get('total_turns', 'N/A')}")
        print(f"Success Rate: {summary.get('success_rate', 0.0):.2%}")
        print(f"Execution Time: {results.get('execution_time', 0.0):.2f} seconds")
    
    return results

def run_cicd_example():
    """Run CI/CD pipeline example"""
    logger.info("=== Running CI/CD Pipeline Example ===")
    
    # Load environment and setup
    load_dotenv('config.env')
    from single_run import setup_environment, get_config
    
    setup_environment()
    config = get_config()
    
    # Create quality gate
    quality_gate = QualityGate(
        min_success_rate=0.7,        # 70% minimum success rate
        min_average_score=0.6,       # 0.6 minimum average score
        max_execution_time=600.0,    # 10 minutes maximum
        max_failed_turns=10,         # Maximum 10 failed turns
        required_metrics=['helpfulness', 'faithfulness', 'instruction_following']
    )
    
    # Create enhanced framework
    framework = EnhancedEvaluationFramework(config)
    
    # Run CI/CD pipeline
    data_file = os.getenv('DATA_FILE_PATH', 'data_files/data_file.json')
    results = framework.run_cicd_mode(data_file, quality_gate)
    
    # Print results
    print("\n=== CI/CD Pipeline Results ===")
    print(f"Pipeline Status: {results.get('status', 'unknown')}")
    
    if 'evaluation_summary' in results:
        summary = results['evaluation_summary']
        print(f"Total Sessions: {summary.get('total_sessions', 'N/A')}")
        print(f"Total Turns: {summary.get('total_turns', 'N/A')}")
        print(f"Success Rate: {summary.get('success_rate', 0.0):.2%}")
    
    if 'quality_gate' in results:
        qg = results['quality_gate']
        print(f"Quality Gate Passed: {qg.get('passed', False)}")
        
        if not qg.get('passed', True):
            print("Quality Gate Failures:")
            for check, passed in qg.get('checks', {}).items():
                if not passed:
                    print(f"  - {check}: FAILED")
    
    return results

def run_hooks_example():
    """Run hooks system example"""
    logger.info("=== Running Hooks System Example ===")
    
    # Load environment and setup
    load_dotenv('config.env')
    from single_run import setup_environment, get_config
    from hooks_system import HooksManager, CustomHook
    
    setup_environment()
    config = get_config()
    
    # Create hooks manager
    hooks_manager = HooksManager()
    
    # Add custom hooks
    pre_hook = CustomHook(
        'pre_evaluation_logger',
        HookType.PRE_EVALUATION,
        example_custom_hook,
        priority=10
    )
    hooks_manager.register_hook(pre_hook)
    
    post_hook = CustomHook(
        'post_evaluation_performance',
        HookType.POST_EVALUATION,
        example_performance_hook,
        priority=5
    )
    hooks_manager.register_hook(post_hook)
    
    # Execute hooks
    pre_context = HookContext(
        hook_type=HookType.PRE_EVALUATION,
        data={'example': 'data', 'timestamp': datetime.now().isoformat()},
        timestamp=datetime.now()
    )
    
    pre_results = hooks_manager.execute_hooks(HookType.PRE_EVALUATION, pre_context)
    
    post_context = HookContext(
        hook_type=HookType.POST_EVALUATION,
        results={'execution_time': 245.67, 'status': 'completed'},
        timestamp=datetime.now()
    )
    
    post_results = hooks_manager.execute_hooks(HookType.POST_EVALUATION, post_context)
    
    # Print results
    print("\n=== Hooks System Results ===")
    print("Pre-evaluation hooks:")
    for result in pre_results:
        print(f"  - {result['hook_name']}: {result['status']}")
    
    print("\nPost-evaluation hooks:")
    for result in post_results:
        print(f"  - {result['hook_name']}: {result['status']}")
    
    # Get summary
    summary = hooks_manager.get_execution_summary()
    print(f"\nHook Execution Summary:")
    print(f"  Total Executions: {summary['total_executions']}")
    print(f"  Success Rate: {summary['success_rate']:.2%}")
    
    return {
        'pre_results': pre_results,
        'post_results': post_results,
        'summary': summary
    }

def run_comprehensive_example():
    """Run comprehensive example combining all features"""
    logger.info("=== Running Comprehensive Example ===")
    
    # Load environment and setup
    load_dotenv('config.env')
    from single_run import setup_environment, get_config
    
    setup_environment()
    config = get_config()
    
    # Create enhanced framework with custom hooks
    framework = EnhancedEvaluationFramework(config)
    
    # Add multiple custom hooks
    framework.add_custom_hook(
        'comprehensive_pre_hook',
        HookType.PRE_EVALUATION,
        example_custom_hook,
        priority=10
    )
    
    framework.add_custom_hook(
        'comprehensive_performance_hook',
        HookType.POST_EVALUATION,
        example_performance_hook,
        priority=5
    )
    
    # Create quality gate for CI/CD mode
    quality_gate = QualityGate(
        min_success_rate=0.6,
        min_average_score=0.5,
        max_execution_time=900.0,  # 15 minutes
        max_failed_turns=15
    )
    
    # Run comprehensive evaluation
    data_file = os.getenv('DATA_FILE_PATH', 'data_files/data_file.json')
    
    print("Running comprehensive evaluation...")
    results = framework.run_cicd_mode(data_file, quality_gate)
    
    # Print comprehensive results
    print("\n=== Comprehensive Example Results ===")
    print(f"Pipeline Status: {results.get('status', 'unknown')}")
    
    if 'evaluation_summary' in results:
        summary = results['evaluation_summary']
        print(f"Total Sessions: {summary.get('total_sessions', 'N/A')}")
        print(f"Total Turns: {summary.get('total_turns', 'N/A')}")
        print(f"Success Rate: {summary.get('success_rate', 0.0):.2%}")
        print(f"Execution Time: {results.get('execution_time', 0.0):.2f} seconds")
    
    if 'quality_gate' in results:
        qg = results['quality_gate']
        print(f"Quality Gate Passed: {qg.get('passed', False)}")
    
    if 'performance_regression' in results:
        pr = results['performance_regression']
        if pr.get('regression_detected', False):
            print("⚠️ Performance regression detected!")
            for metric, details in pr.get('regressions', {}).items():
                print(f"  - {metric}: {details['degradation']:.3f} degradation")
        else:
            print("✅ No performance regression detected")
    
    # Get execution summary
    execution_summary = framework.get_execution_summary()
    print(f"\nExecution Summary:")
    print(f"  Duration: {execution_summary['duration']:.2f} seconds")
    print(f"  Hook Success Rate: {execution_summary['hook_summary']['success_rate']:.2%}")
    
    return results

def main():
    """Main function to run examples"""
    print("Enhanced Agent Evaluation Framework - Example Usage")
    print("=" * 60)
    
    try:
        # Check if data file exists
        data_file = os.getenv('DATA_FILE_PATH', 'data_files/data_file.json')
        if not os.path.exists(data_file):
            print(f"❌ Data file not found: {data_file}")
            print("Please ensure your data file exists and is configured in config.env")
            sys.exit(1)
        
        # Run examples
        print("\n1. Running Basic Concurrent Evaluation Example...")
        basic_results = run_basic_example()
        
        print("\n2. Running Hooks System Example...")
        hooks_results = run_hooks_example()
        
        print("\n3. Running CI/CD Pipeline Example...")
        cicd_results = run_cicd_example()
        
        print("\n4. Running Comprehensive Example...")
        comprehensive_results = run_comprehensive_example()
        
        print("\n" + "=" * 60)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        # Summary
        print("\nSummary:")
        print(f"✅ Basic Example: {basic_results.get('summary', {}).get('success_rate', 0.0):.2%} success rate")
        print(f"✅ Hooks Example: {hooks_results['summary']['success_rate']:.2%} hook success rate")
        print(f"✅ CI/CD Example: {cicd_results.get('status', 'unknown')} pipeline status")
        print(f"✅ Comprehensive Example: {comprehensive_results.get('status', 'unknown')} pipeline status")
        
    except KeyboardInterrupt:
        print("\n❌ Examples interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Examples failed: {str(e)}")
        logger.exception("Error running examples")
        sys.exit(1)

if __name__ == "__main__":
    main() 