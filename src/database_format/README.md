# Database Format Module

This module provides automated evaluation and classification of references in the research database using Claude 3.5 Sonnet.

## Features

- **Automatic Reference Classification**: Classifies references into 6 categories based on content
- **Credibility Assessment**: Evaluates reference credibility on a 1-3 scale
- **Relevance Scoring**: Scores relevance to research topic (0.0-1.0)
- **Batch Processing**: Processes references in configurable batches
- **Error Handling**: Robust retry mechanism for API failures

## Installation

Ensure you have set the required environment variable:

```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

## Usage

### Basic Usage

Process all references that need evaluation:

```bash
cd backend
python -m src.database_format.main
```

### Command Line Options

```bash
# Process a limited number of references
python -m src.database_format.main --limit 20

# Set custom batch size
python -m src.database_format.main --batch-size 5

# Show database statistics
python -m src.database_format.main --stats

# Dry run - see what would be processed
python -m src.database_format.main --dry-run

# Enable verbose logging
python -m src.database_format.main --verbose

# Combine options
python -m src.database_format.main --limit 10 --batch-size 5 --verbose
```

## Reference Types

The system classifies references into:

1. **用户输入**: Direct user inputs (product info, company data)
2. **行业研究报告**: Professional reports from consulting firms
3. **同行评审的学术出版物**: Academic journals and papers
4. **竞对公司网站和产品页面**: Competitor websites and product pages
5. **政策与准入数据**: Legal regulations and standards
6. **社交媒体和公共论坛**: Social media and forum discussions

## Evaluation Criteria

### Credibility Levels

- **1 (Low)**: Unverified sources, personal blogs, biased content
- **2 (Medium)**: General business sources, news media
- **3 (High)**: Authoritative institutions, peer-reviewed content

### Relevance Scoring

- **0.0-0.3**: Low relevance to research topic
- **0.3-0.6**: Medium relevance, partially related
- **0.6-0.8**: High relevance, mostly related
- **0.8-1.0**: Very high relevance, directly addresses research

## Database Fields Updated

- `reference_type`: Classification category
- `credibility`: Credibility score (1-3)
- `credibility_assessment`: Detailed credibility explanation
- `related_assessment`: Relevance score (0.0-1.0)
- `related_assessment_text`: Detailed relevance explanation
- `reference_update_time`: Timestamp of evaluation

## Configuration

The module reads configuration from:

- `/database_cfg/evaluation_criteria.json`: Evaluation standards
- `/backend/src/planning_list.md`: Current research topic
- Environment variable: `ANTHROPIC_API_KEY`

## Examples

### Check Statistics Before Processing

```bash
python -m src.database_format.main --stats
```

Output:
```
Database Statistics:
Total references: 70
Unclassified: 70
Credibility distribution:
  - Low: 0
  - Medium: 70
  - High: 0
```

### Process First 10 References

```bash
python -m src.database_format.main --limit 10 --verbose
```

### Dry Run to Preview

```bash
python -m src.database_format.main --dry-run --limit 5
```

## Error Handling

- Automatic retry (up to 3 attempts) for API failures
- Graceful handling of JSON parsing errors
- Transaction-based database updates
- Comprehensive logging of all operations

## Performance

- Default batch size: 10 references
- Processing delay: 0.5s between references (rate limiting)
- Average processing time: ~2-3 seconds per reference