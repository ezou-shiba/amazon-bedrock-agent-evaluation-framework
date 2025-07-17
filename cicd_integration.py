import os
import json
import yaml
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import subprocess
import sys
from pathlib import Path
import requests
from concurrent_evaluator import ConcurrentEvaluationOrchestrator, run_concurrent_evaluation
from hooks_system import HooksManager, create_default_hooks, HookType, HookContext

logger = logging.getLogger(__name__)

@dataclass
class EvaluationMetrics:
    """Structured evaluation metrics for CI/CD"""
    success_rate: float
    average_scores: Dict[str, float]
    total_turns: int
    failed_turns: int
    execution_time: float
    timestamp: str

@dataclass
class QualityGate:
    """Quality gate configuration for CI/CD"""
    min_success_rate: float = 0.8
    min_average_score: float = 0.7
    max_execution_time: float = 300.0  # 5 minutes
    max_failed_turns: int = 5
    required_metrics: List[str] = None
    
    def __post_init__(self):
        if self.required_metrics is None:
            self.required_metrics = ['helpfulness', 'faithfulness', 'instruction_following']

class CICDPipeline:
    """
    CI/CD Pipeline integration for agent evaluation framework.
    
    Features:
    - Automated evaluation runs
    - Quality gates and thresholds
    - Integration with CI/CD platforms
    - Performance regression detection
    - Automated reporting
    """
    
    def __init__(self, config: Dict[str, Any], quality_gate: QualityGate = None):
        self.config = config
        self.quality_gate = quality_gate or QualityGate()
        self.hooks_manager = create_default_hooks()
        self.evaluation_history = []
        self.regression_threshold = 0.1  # 10% degradation threshold
        
    def run_evaluation_pipeline(self, data_file: str, max_workers: int = 5) -> Dict[str, Any]:
        """Run the complete evaluation pipeline"""
        logger.info("Starting CI/CD evaluation pipeline")
        
        # Pre-pipeline hooks
        pre_context = HookContext(
            hook_type=HookType.INTEGRATION_TEST,
            data={'data_file': data_file, 'max_workers': max_workers},
            timestamp=datetime.now()
        )
        pre_results = self.hooks_manager.execute_hooks(HookType.INTEGRATION_TEST, pre_context)
        
        # Check if pre-pipeline tests passed
        if not self._check_pre_pipeline_tests(pre_results):
            return {
                'status': 'failed',
                'stage': 'pre_pipeline',
                'error': 'Pre-pipeline tests failed',
                'results': pre_results
            }
        
        # Run concurrent evaluation
        start_time = time.time()
        evaluation_results = run_concurrent_evaluation(data_file, max_workers)
        end_time = time.time()
        
        evaluation_results['execution_time'] = end_time - start_time
        
        # Post-evaluation hooks
        post_context = HookContext(
            hook_type=HookType.POST_EVALUATION,
            results=evaluation_results,
            timestamp=datetime.now()
        )
        post_results = self.hooks_manager.execute_hooks(HookType.POST_EVALUATION, post_context)
        
        # Quality gate checks
        quality_gate_result = self._check_quality_gates(evaluation_results)
        
        # Performance regression check
        regression_result = self._check_performance_regression(evaluation_results)
        
        # Generate pipeline report
        pipeline_report = self._generate_pipeline_report(
            evaluation_results, 
            quality_gate_result, 
            regression_result,
            pre_results,
            post_results
        )
        
        # Store in history
        self.evaluation_history.append({
            'timestamp': datetime.now().isoformat(),
            'results': evaluation_results,
            'quality_gate': quality_gate_result,
            'regression': regression_result,
            'pipeline_report': pipeline_report
        })
        
        return pipeline_report
    
    def _check_pre_pipeline_tests(self, pre_results: List[Dict[str, Any]]) -> bool:
        """Check if pre-pipeline tests passed"""
        for result in pre_results:
            if result['status'] != 'success':
                logger.error(f"Pre-pipeline test failed: {result['hook_name']}")
                return False
        return True
    
    def _check_quality_gates(self, evaluation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Check if evaluation results meet quality gate requirements"""
        summary = evaluation_results.get('summary', {})
        
        checks = {
            'success_rate': summary.get('success_rate', 0.0) >= self.quality_gate.min_success_rate,
            'execution_time': evaluation_results.get('execution_time', 0.0) <= self.quality_gate.max_execution_time,
            'failed_turns': summary.get('failed_turns', 0) <= self.quality_gate.max_failed_turns
        }
        
        # Check average scores for required metrics
        avg_scores = summary.get('average_scores', {})
        for metric in self.quality_gate.required_metrics:
            score = avg_scores.get(metric, 0.0)
            checks[f'avg_score_{metric}'] = score >= self.quality_gate.min_average_score
        
        all_passed = all(checks.values())
        
        return {
            'passed': all_passed,
            'checks': checks,
            'thresholds': asdict(self.quality_gate),
            'actual_values': {
                'success_rate': summary.get('success_rate', 0.0),
                'execution_time': evaluation_results.get('execution_time', 0.0),
                'failed_turns': summary.get('failed_turns', 0),
                'average_scores': avg_scores
            }
        }
    
    def _check_performance_regression(self, current_results: Dict[str, Any]) -> Dict[str, Any]:
        """Check for performance regression compared to previous runs"""
        if len(self.evaluation_history) < 2:
            return {
                'regression_detected': False,
                'reason': 'Insufficient history for regression detection'
            }
        
        # Get previous results (last 3 runs for stability)
        recent_history = self.evaluation_history[-3:]
        if not recent_history:
            return {
                'regression_detected': False,
                'reason': 'No previous results available'
            }
        
        # Calculate baseline metrics
        baseline_scores = {}
        for metric in self.quality_gate.required_metrics:
            scores = []
            for historical_run in recent_history:
                avg_scores = historical_run['results']['summary'].get('average_scores', {})
                if metric in avg_scores:
                    scores.append(avg_scores[metric])
            
            if scores:
                baseline_scores[metric] = sum(scores) / len(scores)
        
        # Compare with current results
        current_scores = current_results['summary'].get('average_scores', {})
        regressions = {}
        
        for metric, baseline_score in baseline_scores.items():
            current_score = current_scores.get(metric, 0.0)
            degradation = baseline_score - current_score
            
            if degradation > self.regression_threshold:
                regressions[metric] = {
                    'baseline': baseline_score,
                    'current': current_score,
                    'degradation': degradation
                }
        
        regression_detected = len(regressions) > 0
        
        return {
            'regression_detected': regression_detected,
            'regressions': regressions,
            'baseline_scores': baseline_scores,
            'current_scores': current_scores,
            'threshold': self.regression_threshold
        }
    
    def _generate_pipeline_report(self, evaluation_results: Dict[str, Any], 
                                quality_gate_result: Dict[str, Any],
                                regression_result: Dict[str, Any],
                                pre_results: List[Dict[str, Any]],
                                post_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive pipeline report"""
        
        overall_status = 'passed'
        if not quality_gate_result['passed']:
            overall_status = 'failed'
        elif regression_result['regression_detected']:
            overall_status = 'warning'
        
        return {
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'evaluation_summary': evaluation_results['summary'],
            'quality_gate': quality_gate_result,
            'performance_regression': regression_result,
            'pre_pipeline_tests': pre_results,
            'post_pipeline_tests': post_results,
            'execution_time': evaluation_results['execution_time'],
            'total_sessions': evaluation_results['total_sessions'],
            'total_turns': evaluation_results['total_turns']
        }
    
    def generate_ci_report(self, pipeline_report: Dict[str, Any], output_format: str = 'json') -> str:
        """Generate CI/CD compatible report"""
        if output_format == 'json':
            return json.dumps(pipeline_report, indent=2)
        elif output_format == 'yaml':
            return yaml.dump(pipeline_report, default_flow_style=False)
        elif output_format == 'markdown':
            return self._generate_markdown_report(pipeline_report)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def _generate_markdown_report(self, pipeline_report: Dict[str, Any]) -> str:
        """Generate markdown report for CI/CD platforms"""
        status_emoji = {
            'passed': '✅',
            'failed': '❌',
            'warning': '⚠️'
        }
        
        report = f"""
# Agent Evaluation Pipeline Report

**Status:** {status_emoji.get(pipeline_report['status'], '❓')} {pipeline_report['status'].upper()}

**Timestamp:** {pipeline_report['timestamp']}

## Summary
- **Total Sessions:** {pipeline_report['total_sessions']}
- **Total Turns:** {pipeline_report['total_turns']}
- **Execution Time:** {pipeline_report['execution_time']:.2f} seconds

## Quality Gate Results
"""
        
        qg = pipeline_report['quality_gate']
        if qg['passed']:
            report += "✅ **Quality Gate: PASSED**\n\n"
        else:
            report += "❌ **Quality Gate: FAILED**\n\n"
        
        for check_name, passed in qg['checks'].items():
            status = "✅" if passed else "❌"
            report += f"- {status} {check_name}\n"
        
        report += "\n## Performance Regression\n"
        
        pr = pipeline_report['performance_regression']
        if pr['regression_detected']:
            report += "⚠️ **Performance Regression Detected**\n\n"
            for metric, details in pr['regressions'].items():
                report += f"- **{metric}**: {details['degradation']:.3f} degradation\n"
        else:
            report += "✅ **No Performance Regression Detected**\n"
        
        return report
    
    def save_results(self, pipeline_report: Dict[str, Any], output_dir: str = 'cicd_results'):
        """Save pipeline results to files"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save JSON report
        json_file = os.path.join(output_dir, f'pipeline_report_{timestamp}.json')
        with open(json_file, 'w') as f:
            json.dump(pipeline_report, f, indent=2)
        
        # Save markdown report
        md_file = os.path.join(output_dir, f'pipeline_report_{timestamp}.md')
        with open(md_file, 'w') as f:
            f.write(self.generate_ci_report(pipeline_report, 'markdown'))
        
        # Save evaluation history
        history_file = os.path.join(output_dir, 'evaluation_history.json')
        with open(history_file, 'w') as f:
            json.dump(self.evaluation_history, f, indent=2)
        
        logger.info(f"Results saved to {output_dir}")
        return {
            'json_file': json_file,
            'markdown_file': md_file,
            'history_file': history_file
        }

class GitHubActionsIntegration:
    """Integration with GitHub Actions"""
    
    @staticmethod
    def set_output(name: str, value: str):
        """Set GitHub Actions output"""
        if os.getenv('GITHUB_OUTPUT'):
            with open(os.getenv('GITHUB_OUTPUT'), 'a') as f:
                f.write(f'{name}={value}\n')
        else:
            print(f"::set-output name={name}::{value}")
    
    @staticmethod
    def set_status(status: str, conclusion: str = None):
        """Set GitHub Actions status"""
        if conclusion:
            print(f"::set-output name=conclusion::{conclusion}")
        print(f"::set-output name=status::{status}")

class GitLabCIIntegration:
    """Integration with GitLab CI"""
    
    @staticmethod
    def set_variable(name: str, value: str):
        """Set GitLab CI variable"""
        print(f"echo '{name}={value}' >> $GITLAB_ENV")
    
    @staticmethod
    def create_artifact(path: str, name: str):
        """Create GitLab CI artifact"""
        print(f"artifacts:paths: {path}")
        print(f"artifacts:name: {name}")

def create_cicd_workflow(config: Dict[str, Any], 
                        data_file: str,
                        quality_gate: QualityGate = None,
                        ci_platform: str = 'github') -> Dict[str, Any]:
    """Create CI/CD workflow configuration"""
    
    pipeline = CICDPipeline(config, quality_gate)
    
    # Run evaluation
    pipeline_report = pipeline.run_evaluation_pipeline(data_file)
    
    # Save results
    saved_files = pipeline.save_results(pipeline_report)
    
    # Generate reports
    json_report = pipeline.generate_ci_report(pipeline_report, 'json')
    markdown_report = pipeline.generate_ci_report(pipeline_report, 'markdown')
    
    # CI/CD platform integration
    if ci_platform == 'github':
        GitHubActionsIntegration.set_output('status', pipeline_report['status'])
        GitHubActionsIntegration.set_output('success_rate', 
                                          str(pipeline_report['evaluation_summary']['success_rate']))
        GitHubActionsIntegration.set_output('execution_time', 
                                          str(pipeline_report['execution_time']))
        
        if pipeline_report['status'] == 'failed':
            GitHubActionsIntegration.set_status('failure', 'failure')
        elif pipeline_report['status'] == 'warning':
            GitHubActionsIntegration.set_status('success', 'neutral')
        else:
            GitHubActionsIntegration.set_status('success', 'success')
    
    elif ci_platform == 'gitlab':
        GitLabCIIntegration.set_variable('EVALUATION_STATUS', pipeline_report['status'])
        GitLabCIIntegration.set_variable('SUCCESS_RATE', 
                                       str(pipeline_report['evaluation_summary']['success_rate']))
        GitLabCIIntegration.create_artifact('cicd_results/*', 'evaluation-results')
    
    return {
        'pipeline_report': pipeline_report,
        'saved_files': saved_files,
        'json_report': json_report,
        'markdown_report': markdown_report,
        'ci_platform': ci_platform
    }

# Example GitHub Actions workflow YAML
def generate_github_workflow_yaml() -> str:
    """Generate GitHub Actions workflow YAML"""
    return """
name: Agent Evaluation Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  evaluate-agent:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-west-2
    
    - name: Run evaluation pipeline
      run: |
        python cicd_integration.py
      env:
        LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
        LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
        LANGFUSE_HOST: ${{ secrets.LANGFUSE_HOST }}
    
    - name: Upload evaluation results
      uses: actions/upload-artifact@v3
      with:
        name: evaluation-results
        path: cicd_results/
    
    - name: Comment PR with results
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const report = fs.readFileSync('cicd_results/pipeline_report_*.md', 'utf8');
          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: report
          });
"""

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv('config.env')
    
    # Setup environment and config
    from single_run import setup_environment, get_config
    
    setup_environment()
    config = get_config()
    
    # Create quality gate
    quality_gate = QualityGate(
        min_success_rate=0.8,
        min_average_score=0.7,
        max_execution_time=300.0,
        max_failed_turns=5
    )
    
    # Run CI/CD pipeline
    data_file = os.getenv('DATA_FILE_PATH', 'data_files/data_file.json')
    ci_platform = os.getenv('CI_PLATFORM', 'github')
    
    result = create_cicd_workflow(config, data_file, quality_gate, ci_platform)
    
    print(f"Pipeline Status: {result['pipeline_report']['status']}")
    print(f"Success Rate: {result['pipeline_report']['evaluation_summary']['success_rate']:.2%}")
    print(f"Execution Time: {result['pipeline_report']['execution_time']:.2f} seconds")
    
    if result['pipeline_report']['status'] == 'failed':
        sys.exit(1)
    elif result['pipeline_report']['status'] == 'warning':
        print("⚠️ Performance regression detected")
        sys.exit(0)
    else:
        print("✅ Pipeline passed all checks")
        sys.exit(0) 