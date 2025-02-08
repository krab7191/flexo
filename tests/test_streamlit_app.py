import uuid
import json
import requests
import streamlit as st
from typing import List, Dict, Optional

# Set the new endpoint URL
STREAMING_URL = "http://localhost:8000/v1/chat/completions"

st.title("For Testing - Chat Interface")

# Initialize messages in session state
if "messages" not in st.session_state:
    st.session_state.messages = []


# Function to display messages with appropriate styling
def get_status_icon(status: str) -> str:
    """Get the appropriate icon for a status message."""
    status_icons = {
        "starting_generation": "🟢",
        "tool_call_detected": "🔍",
        "tools_executed": "⚡",
        "continuing_generation": "📝",
        "generation_complete": "✅"
    }
    return status_icons.get(status, "🔧")


def display_message(message: dict):
    """Display a message with appropriate styling and icons."""
    if message.get("is_status"):
        status = message.get("status", "unknown")
        icon = get_status_icon(status)

        with st.chat_message("assistant", avatar=icon):
            st.markdown(message["content"])
    else:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


# Display existing messages, filtering out status updates for the API
def get_api_messages() -> List[Dict[str, str]]:
    """Filter and return messages suitable for the API."""
    return [
        {"role": msg["role"], "content": msg["content"]}
        for msg in st.session_state.messages
        if not msg.get("is_status", False)
    ]


# Display all messages in the UI
for message in st.session_state.messages:
    display_message(message)

# Sidebar configuration
with st.sidebar:
    st.header("Example Additional Context")
    field1 = st.text_input("Example Value 1", value="Context Value")
    field2 = st.text_input("Example Value 2", value="Context Value")
    include_status = st.checkbox("Show status updates", value=False)

    context = {
        "values": [
            {"key": "example field1", "value": field1},
            {"key": "example field2", "value": field2}
        ]
    }

# Generate a unique thread ID for the session
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())


def stream_response(conversation_input: Dict[str, any]) -> Optional[str]:
    """Stream the response from the /chat/completions API."""
    headers = {"X-IBM-THREAD-ID": st.session_state.thread_id}

    # Create placeholder for status messages
    status_placeholder = st.empty()
    response_container = st.empty()

    try:
        with requests.post(STREAMING_URL, json=conversation_input, headers=headers, stream=True) as response:
            if response.status_code == 200:
                assistant_response = ""

                for line in response.iter_lines(chunk_size=5, decode_unicode=True):
                    if line and line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            delta = data["choices"][0]["delta"]

                            # Handle status updates
                            if "metadata" in delta and "status" in delta["metadata"]:
                                status = delta["metadata"]["status"]
                                if include_status:
                                    # Build status message content
                                    content = status
                                    tools = None

                                    # Handle tool calls if present
                                    if status == "tool_call_detected" and "tools" in delta["metadata"]:
                                        tools = delta["metadata"]["tools"]
                                        tools_list = "\n".join([f"- 🛠 {tool}" for tool in tools])
                                        content = f"{status}\n{tools_list}"

                                    status_msg = {
                                        "role": "assistant",
                                        "content": content,
                                        "is_status": True,
                                        "status": status,
                                        "tools": tools if tools else None
                                    }

                                    status_placeholder.markdown(content)

                                    # Add status to message history
                                    st.session_state.messages.append(status_msg)

                            # Handle content updates
                            elif "content" in delta:
                                content = delta["content"]
                                assistant_response += content
                                response_container.markdown(assistant_response)

                        except (json.JSONDecodeError, KeyError) as e:
                            st.error(f"Error processing response: {e}")

                # Clear status placeholder after completion
                status_placeholder.empty()
                return assistant_response
            else:
                st.error(f"Error: {response.status_code} - {response.reason}")
                return None
    except requests.RequestException as e:
        st.error(f"Request error: {e}")
        return None


# Handle user input from chat
if prompt := st.chat_input("Type your message here..."):
    # Add user's message to session state and display it
    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)
    display_message(user_message)

    # Prepare conversation input
    conversation_input = {
        "model": "agent-01",
        "messages": get_api_messages(),
        "stream": True
    }

    # Stream the response
    full_response = stream_response(conversation_input)

    # Add assistant's final response to conversation history
    if full_response:
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "is_status": False
        })

        # Force a rerun to update the message history display
        st.rerun()
