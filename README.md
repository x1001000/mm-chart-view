# MacroMicro ChartView

A Streamlit chatbot that views and analyzes MacroMicro financial charts using Google's Gemini API with Google Search grounding.

## Features

- Load and display MacroMicro charts by URL
- Toggle preview image as image prompt to Gemini
- Chart data (description, bilingual series names, latest values) as text prompt
- Chat interface with customizable default prompt
- Google Search grounding for real-time market information
- Token usage and cost tracking per call and per session

## Setup

1. Install dependencies:
```bash
uv sync
```

2. Create `.streamlit/secrets.toml`:
```toml
GEMINI_API_KEY = "your-api-key-here"
PROXY_URL = "your-proxy-url-here"
```

3. Run the app:
```bash
uv run streamlit run main.py
```

## Usage

1. Enter a MacroMicro chart URL in the sidebar
2. Click "Load Chart" to fetch the chart data and preview
3. Toggle the preview image checkbox to include/exclude it from the AI prompt
4. Edit the default prompt or write your own in the chat input
5. Click "Send" to get AI analysis with Google Search grounding

### Supported URL Formats

- `https://www.macromicro.me/charts/{chart_id}/{slug}`
- `https://www.macromicro.me/collections/{collection_id}/{collection_slug}/{chart_id}/{slug}`

### Examples

- `https://www.macromicro.me/charts/444/us-mm-gspc`
- `https://www.macromicro.me/collections/34/us-stock-relative/444/us-mm-gspc`
