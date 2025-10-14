# Token Usage and Cost Tracking in TRNDA

## Automatic Cost Tracking

TRNDA now automatically tracks and displays **complete costs** for report generation:

- **Bedrock tokens** (Claude 4.5 Sonnet)
- **ECS Fargate compute** (2 vCPU, 4 GB RAM)
- **S3 storage & transfer**

## Console Output After Execution

After report generation completes, you'll see in console:

```
======================================================================
[COMPLETED] Report generation finished
======================================================================

TOKEN USAGE STATISTICS:
----------------------------------------------------------------------
Input tokens:  125,432
Output tokens: 8,567
Total tokens:  134,009
Bedrock cost:   $0.5049

COMPLETE AWS COST BREAKDOWN:
----------------------------------------------------------------------
Bedrock (Claude 4.5):  $0.5049
ECS Fargate compute:   $0.1554
S3 storage & transfer: $0.0000
──────────────────────────────────────────────────────────────────────
TOTAL COST:            $0.6603
----------------------------------------------------------------------
```

## Automatically Generated cost.md File

Each run creates an `output_*/cost.md` file with detailed breakdown:

### cost.md Contents:
- **Summary table** - cost overview by component
- **Bedrock breakdown** - input/output tokens, pricing
- **ECS Fargate breakdown** - vCPU/memory, runtime, costs
- **S3 breakdown** - storage, PUT/GET requests
- **Optimization tips** - how to reduce costs
- **Monthly estimates** - for 10, 50, 100, 200 reports

## Pricing (eu-central-1)

### Bedrock - Claude Sonnet 4.5
- **Input tokens**: $3.00 per 1M tokens
- **Output tokens**: $15.00 per 1M tokens

### ECS Fargate - 2 vCPU, 4 GB RAM
- **vCPU**: $0.04656 per vCPU per hour
- **Memory**: $0.00511 per GB per hour
- **Total**: ~$0.1554 for 15 min run

### S3 Storage
- **Storage**: $0.023 per GB/month
- **PUT requests**: $0.005 per 1000 requests
- **GET requests**: $0.0004 per 1000 requests

## Typical Costs

### Single TRNDA Run:
| Component | Cost |
|-----------|------|
| Bedrock | $0.40-0.70 |
| ECS Fargate | $0.15-0.16 |
| S3 | <$0.01 |
| **TOTAL** | **$0.55-0.86** |

### Monthly Estimates:
| Volume | Bedrock | ECS | S3 | **Total** |
|--------|---------|-----|----|-----------|
| 10 | $5.00 | $1.55 | $0.00 | **$6.55** |
| 50 | $25.00 | $7.77 | $0.03 | **$32.80** |
| 100 | $50.00 | $15.54 | $0.05 | **$65.59** |
| 200 | $100.00 | $31.08 | $0.10 | **$131.18** |

## Implementation

### Cost Calculation Function

```python
def calculate_complete_cost(input_tokens: int, output_tokens: int, 
                           runtime_minutes: float = 15.0) -> dict:
    """Calculate complete AWS costs for TRNDA report generation."""
    # Bedrock
    bedrock_total = (input_tokens / 1_000_000) * 3.0 + \
                    (output_tokens / 1_000_000) * 15.0
    
    # ECS Fargate (2 vCPU, 4 GB)
    ecs_total = (0.04656 * 2 + 0.00511 * 4) * (runtime_minutes / 60.0)
    
    # S3 (minimal)
    s3_total = 0.023 * 0.01 / 30 + 0.005 * (5/1000) + 0.0004 * (5/1000)
    
    return {'bedrock': bedrock_total, 'ecs': ecs_total, 's3': s3_total, 
            'total': bedrock_total + ecs_total + s3_total}
```

### Automatic cost.md Saving

```python
def save_cost_breakdown(output_dir: str, cost_breakdown: dict, usage) -> None:
    """Save detailed cost breakdown to cost.md file."""
    # Creates markdown file with:
    # - Summary table
    # - Detailed breakdown by component
    # - Optimization tips
    # - Monthly estimates
```

## Strands Response Object

```python
response = agent(prompt=prompt)

# Response contains:
response.usage.input_tokens   # Input tokens
response.usage.output_tokens  # Output tokens
```

## Use Cases for Monitoring

1. **Cost tracking** - monitor costs per individual run
2. **Performance monitoring** - optimize prompts to reduce usage
3. **Capacity planning** - estimate costs for production deployment
4. **Debugging** - identify unusually high consumption
5. **Budget alerts** - set alerts when exceeding limits

## Optimization Tips

### Reduce Bedrock Costs:
- Optimize system prompt (fewer instructions)
- Use smaller context windows where possible
- Cache frequently used prompts

### Reduce ECS Costs:
- For simple diagrams, 1 vCPU, 2 GB is sufficient
- Current 2 vCPU, 4 GB is ideal for complex diagrams

### Batch Processing:
- Process multiple diagrams in one session
- Amortize ECS startup costs
