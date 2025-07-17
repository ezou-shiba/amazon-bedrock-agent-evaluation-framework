#!/usr/bin/env python3
"""
Enhanced Agent Evaluation Framework

This script integrates the key features from AWS Agent Evaluation framework:
1. Concurrent, multi-turn conversations with evaluation
2. Hooks system for integration testing and additional tasks
3. CI/CD pipeline integration for automated delivery

Usage:
    python enhanced_run.py --mode concurrent --data-file data_files/data_file.json
    python enhanced_run.py --mode sequential --data-file data_files/data_file.json
    python enhanced_run.py --mode cicd --data-file data_files/data_file.json
"""

import os
import sys
import argparse
import logging
from typing import Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Import our enhanced components
from concurrent_evaluator import run_concurrent_evaluation
from hooks_system import create_default_hooks, HookType, HookContext
from cicd_integration import CICDPipeline, QualityGate, create_cicd_workflow

# Import original components
from single_run import setup_environment, get_config, run_evaluation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedEvaluationFramework:
    """
    Enhanced evaluation framework that integrates AWS Agent Evaluation features
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.hooks_manager = create_default_hooks()
        self.start_time = datetime.now()
        
    def run_concurrent_mode(self, data_file: str, max_workers: int = 5) -> Dict[str, Any]:
        """Run evaluation in concurrent mode with multi-turn conversations"""
        logger.info("Starting concurrent evaluation mode")
        
        # Pre-evaluation hooks
        pre_context = HookContext(
            hook_type=HookType.PRE_EVALUATION,
            data={'data_file': data_file, 'max_workers': max_workers},
            timestamp=datetime.now()
        )
        pre_results = self.hooks_manager.execute_hooks(HookType.PRE_EVALUATION, pre_context)
        
        # Run concurrent evaluation
        results = run_concurrent_evaluation(data_file, max_workers)
        
        # Post-evaluation hooks
        post_context = HookContext(
            hook_type=HookType.POST_EVALUATION,
            results=results,
            timestamp=datetime.now()
        )
        post_results = self.hooks_manager.execute_hooks(HookType.POST_EVALUATION, post_context)
        
        # Add hook results to evaluation results
        results['hooks'] = {
            'pre_evaluation': pre_results,
            'post_evaluation': post_results
        }
        
        return results
    
    def run_sequential_mode(self, data_file: str) -> Dict[str, Any]:
        """Run evaluation in sequential mode (original behavior)"""
        logger.info("Starting sequential evaluation mode")
        
        # Pre-evaluation hooks
        pre_context = HookContext(
            hook_type=HookType.PRE_EVALUATION,
            data={'data_file': data_file, 'mode': 'sequential'},
            timestamp=datetime.now()
        )
        pre_results = self.hooks_manager.execute_hooks(HookType.PRE_EVALUATION, pre_context)
        
        # Run original evaluation
        run_evaluation(data_file)
        
        # Post-evaluation hooks
        post_context = HookContext(
            hook_type=HookType.POST_EVALUATION,
            data={'mode': 'sequential'},
            timestamp=datetime.now()
        )
        post_results = self.hooks_manager.execute_hooks(HookType.POST_EVALUATION, post_context)
        
        return {
            'mode': 'sequential',
            'hooks': {
                'pre_evaluation': pre_results,
                'post_evaluation': post_results
            }
        }
    
    def run_cicd_mode(self, data_file: str, quality_gate: QualityGate = None) -> Dict[str, Any]:
        """Run evaluation in CI/CD mode with quality gates"""
        logger.info("Starting CI/CD evaluation mode")
        
        pipeline = CICDPipeline(self.config, quality_gate)
        return pipeline.run_evaluation_pipeline(data_file)
    
    def add_custom_hook(self, hook_name: str, hook_type: HookType, hook_function, priority: int = 0):
        """Add a custom hook to the framework"""
        from hooks_system import CustomHook
        
        custom_hook = CustomHook(hook_name, hook_type, hook_function, priority)
        self.hooks_manager.register_hook(custom_hook)
        logger.info(f"Added custom hook: {hook_name}")
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary including hook statistics"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        hook_summary = self.hooks_manager.get_execution_summary()
        
        return {
            'start_time': self.start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration': duration,
            'hook_summary': hook_summary
        }

def create_quality_gate_from_args(args) -> QualityGate:
    """Create quality gate from command line arguments"""
    return QualityGate(
        min_success_rate=args.min_success_rate,
        min_average_score=args.min_average_score,
        max_execution_time=args.max_execution_time,
        max_failed_turns=args.max_failed_turns
    )

def setup_argument_parser() -> argparse.ArgumentParser:
    """Setup command line argument parser"""
    parser = argparse.ArgumentParser(
        description='Enhanced Agent Evaluation Framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run concurrent evaluation
  python enhanced_run.py --mode concurrent --data-file data_files/data_file.json --max-workers 5
  
  # Run CI/CD pipeline with custom quality gates
  python enhanced_run.py --mode cicd --data-file data_files/data_file.json --min-success-rate 0.9
  
  # Run sequential evaluation (original behavior)
  python enhanced_run.py --mode sequential --data-file data_files/data_file.json
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['concurrent', 'sequential', 'cicd'],
        default='concurrent',
        help='Evaluation mode (default: concurrent)'
    )
    
    parser.add_argument(
        '--data-file',
        required=True,
        help='Path to the data file containing evaluation questions'
    )
    
    parser.add_argument(
        '--max-workers',
        type=int,
        default=5,
        help='Maximum number of concurrent workers (default: 5)'
    )
    
    # Quality gate arguments
    parser.add_argument(
        '--min-success-rate',
        type=float,
        default=0.8,
        help='Minimum success rate for quality gate (default: 0.8)'
    )
    
    parser.add_argument(
        '--min-average-score',
        type=float,
        default=0.7,
        help='Minimum average score for quality gate (default: 0.7)'
    )
    
    parser.add_argument(
        '--max-execution-time',
        type=float,
        default=300.0,
        help='Maximum execution time in seconds (default: 300.0)'
    )
    
    parser.add_argument(
        '--max-failed-turns',
        type=int,
        default=5,
        help='Maximum number of failed turns (default: 5)'
    )
    
    # Output options
    parser.add_argument(
        '--output-dir',
        default='evaluation_results',
        help='Directory to save results (default: evaluation_results)'
    )
    
    parser.add_argument(
        '--output-format',
        choices=['json', 'yaml', 'markdown'],
        default='json',
        help='Output format for reports (default: json)'
    )
    
    parser.add_argument(
        '--ci-platform',
        choices=['github', 'gitlab', 'none'],
        default='none',
        help='CI/CD platform integration (default: none)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser

def save_results(results: Dict[str, Any], output_dir: str, output_format: str = 'json'):
    """Save evaluation results to files"""
    import json
    import yaml
    from pathlib import Path
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save main results
    if output_format == 'json':
        output_file = os.path.join(output_dir, f'evaluation_results_{timestamp}.json')
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
    elif output_format == 'yaml':
        output_file = os.path.join(output_dir, f'evaluation_results_{timestamp}.yaml')
        with open(output_file, 'w') as f:
            yaml.dump(results, f, default_flow_style=False)
    elif output_format == 'markdown':
        output_file = os.path.join(output_dir, f'evaluation_results_{timestamp}.md')
        with open(output_file, 'w') as f:
            f.write(generate_markdown_report(results))
    
    logger.info(f"Results saved to {output_file}")
    return output_file

def generate_markdown_report(results: Dict[str, Any]) -> str:
    """Generate markdown report from results"""
    report = f"""# Agent Evaluation Results

**Timestamp:** {datetime.now().isoformat()}

## Summary
"""
    
    if 'summary' in results:
        summary = results['summary']
        report += f"""
- **Total Sessions:** {summary.get('total_sessions', 'N/A')}
- **Total Turns:** {summary.get('total_turns', 'N/A')}
- **Success Rate:** {summary.get('success_rate', 0.0):.2%}
- **Failed Turns:** {summary.get('failed_turns', 'N/A')}
- **Execution Time:** {results.get('execution_time', 0.0):.2f} seconds

## Average Scores
"""
        
        avg_scores = summary.get('average_scores', {})
        for metric, score in avg_scores.items():
            report += f"- **{metric}:** {score:.3f}\n"
    
    if 'hooks' in results:
        report += "\n## Hook Execution Summary\n"
        hooks = results['hooks']
        
        for hook_type, hook_results in hooks.items():
            report += f"\n### {hook_type.replace('_', ' ').title()}\n"
            for result in hook_results:
                status = "✅" if result['status'] == 'success' else "❌"
                report += f"- {status} {result['hook_name']}: {result['status']}\n"
    
    return report

def main():
    """Main entry point"""
    # Load environment variables
    load_dotenv('config.env')
    
    # Parse arguments
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Setup environment and config
        logger.info("Setting up evaluation environment...")
        setup_environment()
        config = get_config()
        
        # Create enhanced framework
        framework = EnhancedEvaluationFramework(config)
        
        # Run evaluation based on mode
        logger.info(f"Running evaluation in {args.mode} mode...")
        
        if args.mode == 'concurrent':
            results = framework.run_concurrent_mode(args.data_file, args.max_workers)
        elif args.mode == 'sequential':
            results = framework.run_sequential_mode(args.data_file)
        elif args.mode == 'cicd':
            quality_gate = create_quality_gate_from_args(args)
            results = framework.run_cicd_mode(args.data_file, quality_gate)
        
        # Add execution summary
        results['execution_summary'] = framework.get_execution_summary()
        
        # Save results
        output_file = save_results(results, args.output_dir, args.output_format)
        
        # CI/CD platform integration
        if args.ci_platform != 'none':
            logger.info(f"Integrating with {args.ci_platform} CI/CD platform...")
            if args.ci_platform == 'github':
                from cicd_integration import GitHubActionsIntegration
                GitHubActionsIntegration.set_output('status', results.get('status', 'unknown'))
                GitHubActionsIntegration.set_output('success_rate', 
                                                  str(results.get('summary', {}).get('success_rate', 0.0)))
            elif args.ci_platform == 'gitlab':
                from cicd_integration import GitLabCIIntegration
                GitLabCIIntegration.set_variable('EVALUATION_STATUS', results.get('status', 'unknown'))
                GitLabCIIntegration.set_variable('SUCCESS_RATE', 
                                               str(results.get('summary', {}).get('success_rate', 0.0)))
        
        # Print summary
        print("\n" + "="*50)
        print("EVALUATION COMPLETED")
        print("="*50)
        
        if 'summary' in results:
            summary = results['summary']
            print(f"Total Sessions: {summary.get('total_sessions', 'N/A')}")
            print(f"Total Turns: {summary.get('total_turns', 'N/A')}")
            print(f"Success Rate: {summary.get('success_rate', 0.0):.2%}")
            print(f"Execution Time: {results.get('execution_time', 0.0):.2f} seconds")
        
        if 'status' in results:
            print(f"Pipeline Status: {results['status']}")
        
        print(f"Results saved to: {output_file}")
        print("="*50)
        
        # Exit with appropriate code
        if results.get('status') == 'failed':
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("Evaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Evaluation failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 