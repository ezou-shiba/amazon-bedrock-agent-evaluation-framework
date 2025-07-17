# Enhanced Agent Evaluation Framework

This enhanced version of the Amazon Bedrock Agent Evaluation Framework incorporates key features from the [AWS Agent Evaluation repository](https://github.com/awslabs/agent-evaluation) to provide:

1. **Concurrent, multi-turn conversations** with evaluation capabilities
2. **Hooks system** for integration testing and additional tasks
3. **CI/CD pipeline integration** for automated delivery while maintaining agent stability

## 🚀 Key Features

### 1. Concurrent Multi-turn Conversations

The framework now supports orchestrating concurrent, multi-turn conversations with your agent while evaluating responses in real-time.

**Features:**
- Parallel processing of multiple conversation sessions
- Multi-turn conversation support with context preservation
- Configurable concurrency limits
- Real-time evaluation results
- Integration with existing evaluators

**Usage:**
```bash
# Run concurrent evaluation
python enhanced_run.py --mode concurrent --data-file data_files/data_file.json --max-workers 5
```

### 2. Hooks System for Integration Testing

A flexible hooks system that allows you to define custom hooks for integration testing and additional tasks.

**Hook Types:**
- `PRE_EVALUATION`: Run before evaluation starts
- `POST_EVALUATION`: Run after evaluation completes
- `PRE_SESSION`: Run before each conversation session
- `POST_SESSION`: Run after each conversation session
- `PRE_TURN`: Run before each conversation turn
- `POST_TURN`: Run after each conversation turn
- `ERROR_HANDLER`: Handle errors during evaluation
- `INTEGRATION_TEST`: Run integration tests
- `CUSTOM`: Custom hook functionality

**Built-in Hooks:**
- **Agent Connectivity Test**: Verifies Bedrock agent accessibility
- **Data Integrity Test**: Validates input data structure
- **Langfuse Connection Test**: Tests observability platform connectivity
- **Data Validation**: Validates required fields and data types
- **Performance Monitoring**: Collects performance metrics
- **Error Handling**: Handles common errors with retry logic

**Adding Custom Hooks:**
```python
from enhanced_run import EnhancedEvaluationFramework
from hooks_system import HookType

def my_custom_hook(context):
    # Your custom logic here
    return {'status': 'success', 'message': 'Custom hook executed'}

# Add custom hook
framework = EnhancedEvaluationFramework(config)
framework.add_custom_hook(
    'my_custom_hook',
    HookType.PRE_EVALUATION,
    my_custom_hook,
    priority=5
)
```

### 3. CI/CD Pipeline Integration

Automated evaluation pipeline that can be incorporated into CI/CD workflows for expedited delivery while maintaining agent stability.

**Features:**
- Automated evaluation runs
- Quality gates and thresholds
- Integration with CI/CD platforms (GitHub Actions, GitLab CI)
- Performance regression detection
- Automated reporting

**Quality Gates:**
- Minimum success rate threshold
- Minimum average score threshold
- Maximum execution time limit
- Maximum failed turns limit

**Usage:**
```bash
# Run CI/CD pipeline with quality gates
python enhanced_run.py --mode cicd --data-file data_files/data_file.json --min-success-rate 0.9
```

## 📁 File Structure

```
├── concurrent_evaluator.py      # Concurrent evaluation orchestrator
├── hooks_system.py             # Hooks system for integration testing
├── cicd_integration.py         # CI/CD pipeline integration
├── enhanced_run.py             # Enhanced main runner
├── run.py                      # Original evaluation runner
├── evaluators/                 # Evaluation modules
├── helpers/                    # Helper utilities
├── data_files/                 # Evaluation data
└── config.env                  # Configuration file
```

## 🛠️ Installation and Setup

### Prerequisites

1. **AWS Bedrock Agent**: Set up your Bedrock agent with the required permissions
2. **Langfuse**: Set up Langfuse for observability (cloud or self-hosted)
3. **Python Dependencies**: Install required packages

### Setup Steps

1. **Install Dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure Environment:**
```bash
cp config.env.tpl config.env
# Edit config.env with your settings
```

3. **Verify Setup:**
```bash
python check_env.py
```

## 🚀 Usage Examples

### Basic Concurrent Evaluation

```bash
# Run concurrent evaluation with 5 workers
python enhanced_run.py \
    --mode concurrent \
    --data-file data_files/data_file.json \
    --max-workers 5 \
    --output-dir results \
    --output-format json
```

### CI/CD Pipeline with Quality Gates

```bash
# Run with strict quality gates
python enhanced_run.py \
    --mode cicd \
    --data-file data_files/data_file.json \
    --min-success-rate 0.9 \
    --min-average-score 0.8 \
    --max-execution-time 300 \
    --max-failed-turns 3 \
    --ci-platform github
```

### Sequential Evaluation (Original Behavior)

```bash
# Run in sequential mode (original behavior)
python enhanced_run.py \
    --mode sequential \
    --data-file data_files/data_file.json
```

## 🔧 Configuration

### Quality Gate Configuration

```python
from cicd_integration import QualityGate

quality_gate = QualityGate(
    min_success_rate=0.8,        # 80% minimum success rate
    min_average_score=0.7,       # 0.7 minimum average score
    max_execution_time=300.0,    # 5 minutes maximum
    max_failed_turns=5,          # Maximum 5 failed turns
    required_metrics=['helpfulness', 'faithfulness', 'instruction_following']
)
```

### Custom Hook Configuration

```python
from hooks_system import HooksManager, CustomHook, HookType

def custom_validation_hook(context):
    # Custom validation logic
    return {'status': 'success', 'validated': True}

hooks_manager = HooksManager()
custom_hook = CustomHook(
    'custom_validation',
    HookType.PRE_EVALUATION,
    custom_validation_hook,
    priority=10
)
hooks_manager.register_hook(custom_hook)
```

## 🔄 CI/CD Integration

### GitHub Actions

Create `.github/workflows/evaluation.yml`:

```yaml
name: Agent Evaluation Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

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
      run: pip install -r requirements.txt
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-west-2
    
    - name: Run evaluation pipeline
      run: |
        python enhanced_run.py \
          --mode cicd \
          --data-file data_files/data_file.json \
          --ci-platform github
      env:
        LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
        LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
        LANGFUSE_HOST: ${{ secrets.LANGFUSE_HOST }}
    
    - name: Upload evaluation results
      uses: actions/upload-artifact@v3
      with:
        name: evaluation-results
        path: evaluation_results/
```

### GitLab CI

Create `.gitlab-ci.yml`:

```yaml
stages:
  - evaluate

evaluate-agent:
  stage: evaluate
  image: python:3.9
  before_script:
    - pip install -r requirements.txt
    - aws configure set aws_access_key_id $AWS_ACCESS_KEY_ID
    - aws configure set aws_secret_access_key $AWS_SECRET_ACCESS_KEY
    - aws configure set region us-west-2
  script:
    - python enhanced_run.py --mode cicd --data-file data_files/data_file.json --ci-platform gitlab
  artifacts:
    paths:
      - evaluation_results/
    reports:
      junit: evaluation_results/*.xml
```

## 📊 Output and Reporting

### Output Formats

The framework supports multiple output formats:

- **JSON**: Structured data for programmatic access
- **YAML**: Human-readable structured data
- **Markdown**: Formatted reports for documentation

### Report Structure

```json
{
  "status": "passed",
  "summary": {
    "total_sessions": 4,
    "total_turns": 12,
    "success_rate": 0.916,
    "failed_turns": 1,
    "average_scores": {
      "helpfulness": 0.85,
      "faithfulness": 0.92,
      "instruction_following": 0.88
    }
  },
  "quality_gate": {
    "passed": true,
    "checks": {
      "success_rate": true,
      "execution_time": true,
      "failed_turns": true
    }
  },
  "performance_regression": {
    "regression_detected": false
  },
  "hooks": {
    "pre_evaluation": [...],
    "post_evaluation": [...]
  }
}
```

## 🔍 Monitoring and Observability

### Langfuse Integration

All evaluations are automatically traced in Langfuse with:

- **Traces**: Complete evaluation sessions
- **Spans**: Individual evaluation steps
- **Scores**: Evaluation metrics and scores
- **Metadata**: Context and configuration information

### Performance Monitoring

The framework automatically collects:

- **Execution time**: Total and per-turn timing
- **Token usage**: Input and output token counts
- **Success rates**: Overall and per-metric success rates
- **Error rates**: Failure and error tracking

## 🐛 Troubleshooting

### Common Issues

1. **Connection Errors**:
   - Verify AWS credentials and permissions
   - Check Bedrock agent status
   - Validate Langfuse connection

2. **Quality Gate Failures**:
   - Review evaluation results in Langfuse
   - Adjust quality gate thresholds
   - Check agent performance

3. **Performance Issues**:
   - Reduce concurrent workers
   - Check AWS service limits
   - Monitor resource usage

### Debug Mode

Enable verbose logging:

```bash
python enhanced_run.py --mode concurrent --data-file data_files/data_file.json --verbose
```

### Hook Debugging

Check hook execution:

```python
# Get hook execution summary
summary = hooks_manager.get_execution_summary()
print(f"Hook success rate: {summary['success_rate']:.2%}")
```

## 🤝 Contributing

To add new features or improvements:

1. **Fork the repository**
2. **Create a feature branch**
3. **Add tests for new functionality**
4. **Update documentation**
5. **Submit a pull request**

### Adding New Hook Types

```python
from hooks_system import BaseHook, HookType

class MyCustomHook(BaseHook):
    def __init__(self, name: str, priority: int = 0):
        super().__init__(name, HookType.CUSTOM, priority)
    
    def execute(self, context):
        # Your custom logic here
        return {'status': 'success', 'result': 'custom_result'}
```

### Adding New Evaluators

```python
from evaluators.cot_evaluator import ToolEvaluator

class MyCustomEvaluator(ToolEvaluator):
    def _initialize_clients(self):
        # Initialize your custom clients
        pass
    
    def invoke_agent(self, tries: int = 1):
        # Your custom agent invocation logic
        pass
    
    def evaluate_response(self, metadata):
        # Your custom evaluation logic
        pass
```

## 📚 Additional Resources

- [AWS Agent Evaluation Documentation](https://awslabs.github.io/agent-evaluation/)
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Langfuse Documentation](https://langfuse.com/docs)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitLab CI Documentation](https://docs.gitlab.com/ee/ci/)

## 📄 License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details. 