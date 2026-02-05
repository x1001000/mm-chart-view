import streamlit as st
from google import genai
from google.genai import types
import requests
import re


def extract_chart_id(url: str) -> str | None:
    """Extract chart_id from MacroMicro URL.

    Supports two URL patterns:
    - https://www.macromicro.me/charts/{chart_id}/{slug}
    - https://www.macromicro.me/collections/{collection_id}/{collection_slug}/{chart_id}/{slug}
    """
    patterns = [
        r'macromicro\.me/charts/(\d+)',
        r'macromicro\.me/collections/\d+/[^/]+/(\d+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_preview_image_url(chart_id: str) -> str:
    """Construct preview image URL."""
    return f"https://cdn.macromicro.me/files/charts/{chart_id[-3:].zfill(3)}/{chart_id}-tc.png"


def fetch_chart_data(chart_id: str) -> dict | None:
    """Fetch chart data from proxy API."""
    proxy_url = f"{st.secrets['PROXY_URL']}https://www.macromicro.me/charts/data/{chart_id}"
    try:
        response = requests.get(proxy_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Failed to fetch chart data: {e}")
        return None


def get_series_info(data: dict, chart_id: str) -> list[tuple[str, list]]:
    """Extract series names and latest two values."""
    try:
        chart_data = data['data'][f'c:{chart_id}']
        series_configs = chart_data['info']['chart_config']['seriesConfigs']
        series_data = chart_data['series']

        result = []
        for i, config in enumerate(series_configs):
            name = config.get('name_tc', f'Series {i+1}')
            if i < len(series_data):
                latest_two = series_data[i][-2:] if len(series_data[i]) >= 2 else series_data[i]
                result.append((name, latest_two))
        return result
    except (KeyError, IndexError) as e:
        st.error(f"Failed to parse chart data: {e}")
        return []


def fetch_image_bytes(url: str) -> bytes | None:
    """Fetch image from URL and return as bytes."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        st.error(f"Failed to fetch image: {e}")
        return None


def get_gemini_client():
    """Get Gemini client."""
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


def format_series_info(series_info: list[tuple[str, list]]) -> str:
    """Format series info as text for the prompt."""
    lines = ["Chart Data (Latest Two Values):"]
    for name, values in series_info:
        if len(values) >= 2:
            lines.append(f"- {name}: {values[0]} -> {values[1]}")
        elif len(values) == 1:
            lines.append(f"- {name}: {values[0]}")
    return "\n".join(lines)


def analyze_chart(client, image_bytes: bytes, series_info: list[tuple[str, list]], user_prompt: str):
    """Send multimodal prompt to Gemini."""
    series_text = format_series_info(series_info)

    # Create image part
    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type="image/png"
    )

    contents = [
        image_part,
        series_text,
        user_prompt
    ]

    response = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=contents,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )
    return response.text


def main():
    st.set_page_config(page_title="MacroMicro Chart Analyst", layout="wide")

    # Custom CSS for responsive sidebar
    st.markdown(
        """
        <style>
        /* Desktop: wider sidebar */
        @media (min-width: 768px) {
            [data-testid="stSidebar"] {
                min-width: 550px;
                max-width: 650px;
            }
        }

        /* Mobile: let Streamlit handle sidebar natively */
        @media (max-width: 767px) {
            [data-testid="stSidebar"] {
                min-width: 300px;
                max-width: 85vw;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.title("MM Chart Analyst")

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chart_id" not in st.session_state:
        st.session_state.chart_id = None
    if "series_info" not in st.session_state:
        st.session_state.series_info = []
    if "image_bytes" not in st.session_state:
        st.session_state.image_bytes = None

    # Sidebar for chart URL input
    with st.sidebar:
        st.header("MacroMicro Chart URL")
        url = st.text_input(
            "Input here or try the example:",
            value="https://www.macromicro.me/charts/444/us-mm-gspc"
        )

        if st.button("Load Chart"):
            chart_id = extract_chart_id(url)
            if chart_id:
                with st.spinner("Loading chart..."):
                    st.session_state.chart_id = chart_id
                    st.session_state.messages = []  # Reset chat for new chart

                    # Fetch chart data
                    data = fetch_chart_data(chart_id)
                    if data:
                        st.session_state.series_info = get_series_info(data, chart_id)

                    # Fetch image
                    image_url = get_preview_image_url(chart_id)
                    st.session_state.image_bytes = fetch_image_bytes(image_url)

                st.success(f"Chart {chart_id} loaded!")
            else:
                st.error("Invalid URL. Please enter a valid MacroMicro chart URL.")

        # Display chart info if loaded
        if st.session_state.chart_id:
            st.divider()
            st.subheader(f"Chart ID: {st.session_state.chart_id}")

            # Display preview image
            if st.session_state.image_bytes:
                st.image(st.session_state.image_bytes, use_container_width=True)

            # Display series info
            if st.session_state.series_info:
                st.subheader("Series Data")
                for name, values in st.session_state.series_info:
                    if len(values) >= 2:
                        st.write(f"**{name}**:  \n{values[0]} -> {values[1]}")
                    elif len(values) == 1:
                        st.write(f"**{name}**:  \n{values[0]}")

    # Main chat area
    if not st.session_state.chart_id:
        st.info("Please enter a MacroMicro chart URL in the sidebar to begin analysis.")
        return

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about this chart..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                try:
                    client = get_gemini_client()
                    response = analyze_chart(
                        client,
                        st.session_state.image_bytes,
                        st.session_state.series_info,
                        prompt
                    )
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"Error generating response: {e}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})


if __name__ == "__main__":
    main()
