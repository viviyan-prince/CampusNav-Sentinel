# Nebius × NVIDIA Integration

CampusNav Sentinel now integrates with **Nebius AI Cloud** to provide advanced scene analysis using NVIDIA-powered language models.

## Features

- **Real-time Scene Analysis**: Leverages Nebius AI (NVIDIA models) to interpret detection results and provide contextual safety assessments
- **Risk Assessment**: AI-powered evaluation of scene safety (low/medium/high risk)
- **Actionable Recommendations**: Specific guidance for shuttle operators based on detected hazards
- **Configurable**: Enable/disable AI analysis, adjust model selection, and control analysis frequency

## Configuration

Set these environment variables to enable Nebius integration:

```bash
# Required: Your Nebius AI API key
NEBIUS_API_KEY=your_api_key_here

# Optional: Model selection (default: meta-llama/Llama-3.3-70B-Instruct)
NEBIUS_MODEL=meta-llama/Llama-3.3-70B-Instruct

# Optional: Enable/disable (default: true)
NEBIUS_ENABLED=true

# Optional: Analyze every Nth processed frame (default: 5)
NEBIUS_INTERVAL=5
```

## Obtaining a Nebius API Key

1. Visit [Nebius AI Studio](https://studio.nebius.ai/)
2. Sign up or log in to your account
3. Navigate to API Keys section
4. Generate a new API key
5. Copy the key and set it as `NEBIUS_API_KEY` environment variable

## Supported Models

The integration uses OpenAI-compatible API format and supports various NVIDIA models available through Nebius:

- `meta-llama/Llama-3.3-70B-Instruct` (default)
- `meta-llama/Meta-Llama-3.1-405B-Instruct`
- `mistralai/Mixtral-8x7B-Instruct-v0.1`
- Other models available in your Nebius account

## How It Works

1. **Detection Phase**: YOLOv8 detects pedestrians, vehicles, and obstacles
2. **Context Building**: Detection results and frame metadata are structured
3. **AI Analysis**: Every Nth frame, the system sends detection context to Nebius AI
4. **Response Parsing**: AI response is parsed for scene description, risk level, and recommendations
5. **Visualization**: Analysis is overlaid on the annotated video output
6. **Reporting**: All AI analyses are included in the JSON report

## Example Output

```json
{
  "nebius_analyses": [
    {
      "frame": 5,
      "time_ms": 333.3,
      "scene": "Pedestrian crossing in front of shuttle with moderate speed",
      "risk": "Medium - pedestrian in path, shuttle should slow",
      "action": "Reduce speed and prepare to stop if pedestrian continues",
      "model": "meta-llama/Llama-3.3-70B-Instruct"
    }
  ]
}
```

## Fallback Behavior

If `NEBIUS_API_KEY` is not set or invalid:
- System continues to work normally with OpenCV + YOLO detection
- AI analysis section shows "Nebius AI disabled (no API key)"
- All other features remain functional
- No errors or failures occur

## Performance

- **Latency**: ~1-3 seconds per AI call (depends on model and scene complexity)
- **Frequency Control**: Use `NEBIUS_INTERVAL` to balance insight vs. speed
- **Timeout**: 30-second timeout prevents hanging on slow responses
- **Error Handling**: Failures are logged but don't stop pipeline execution

## Testing

Test with a sample video:

```bash
# With Nebius disabled (default if no key)
PYTHONPATH=. python app/cli.py data/sample/test_campus.mp4 -o data/output --max-frames 30

# With Nebius enabled
NEBIUS_API_KEY=your_key PYTHONPATH=. python app/cli.py data/sample/test_campus.mp4 -o data/output --max-frames 30
```

The output will show:
- Number of Nebius AI calls made
- Success count
- Model used
- AI analysis for selected frames

## Cost Considerations

Nebius AI Cloud charges based on:
- Model selected (larger models cost more)
- Number of tokens processed
- API call frequency

Use `NEBIUS_INTERVAL` to control costs:
- `NEBIUS_INTERVAL=1` - Analyze every frame (expensive, most detailed)
- `NEBIUS_INTERVAL=5` - Analyze every 5th frame (balanced, default)
- `NEBIUS_INTERVAL=10` - Analyze every 10th frame (economical)

## Troubleshooting

**No AI analysis appearing:**
- Check `NEBIUS_API_KEY` is set correctly
- Verify `NEBIUS_ENABLED=true`
- Ensure `openai` package is installed: `pip install openai`

**API errors:**
- Verify API key is valid
- Check network connectivity
- Review Nebius AI Cloud status

**Slow processing:**
- Increase `NEBIUS_INTERVAL` to analyze fewer frames
- Consider using a smaller/faster model
- Check network latency to Nebius servers

## Integration Architecture

```
Frame → YOLO Detection → Detection Results
                              ↓
                         Frame Metadata
                              ↓
        [Every Nth Frame] → Nebius Client
                              ↓
                      OpenAI-compatible API
                              ↓
                      Nebius AI Cloud (NVIDIA)
                              ↓
                         AI Analysis
                              ↓
                    Overlay on Video + Report
```

## License

This integration uses:
- **Nebius AI Cloud**: Subject to Nebius terms of service
- **OpenAI Python SDK**: MIT License
- **CampusNav Sentinel**: MIT License
