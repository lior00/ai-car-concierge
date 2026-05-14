"""
Streamlit chat UI for the AI Car Concierge.
Connects to FastAPI backend at BACKEND_URL.
"""
import os
import uuid

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def _md(text: str) -> None:
    """Render markdown with dollar signs escaped to prevent Streamlit LaTeX parsing."""
    st.markdown(text.replace("$", r"\$"))

st.set_page_config(
    page_title="AI Car Concierge",
    page_icon="🚗",
    layout="centered",
)

# ── Custom styling ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0f0f1a; color: #f0f0f0; }
    .stChatMessage { border-radius: 12px; }
    .stChatInputContainer { border-top: 1px solid #333; padding-top: 12px; }
    h1 { color: #c9a84c; font-family: Georgia, serif; letter-spacing: 1px; }
    .subtitle { color: #888; font-size: 14px; margin-top: -16px; margin-bottom: 24px; }
</style>
""", unsafe_allow_html=True)

st.title("🚗 AI Car Concierge")
st.markdown('<p class="subtitle">Premium Dealership · Powered by AI</p>', unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Welcome to our premium dealership! I'm your AI Car Concierge. "
                "I can help you explore our inventory, answer questions about our policies, "
                "schedule test drives, or assist with a purchase. How can I help you today?"
            ),
        }
    ]

# ── Render message history ─────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        _md(msg["content"])

# ── Chat input ─────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about our vehicles, policies, or anything else..."):
    # Render immediately (before appending to session state so history loop
    # doesn't re-render these on the next Streamlit rerun)
    with st.chat_message("user"):
        _md(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/chat",
                    json={"message": prompt, "session_id": st.session_state.session_id},
                    timeout=120,
                )
                resp.raise_for_status()
                assistant_reply = resp.json()["response"]
            except requests.exceptions.ConnectionError:
                assistant_reply = (
                    "⚠️ Unable to connect to the backend. "
                    "Please ensure the server is running on port 8000."
                )
            except requests.exceptions.Timeout:
                assistant_reply = "⚠️ The request timed out. Please try again."
            except Exception as e:
                assistant_reply = f"⚠️ An error occurred: {str(e)}"

        _md(assistant_reply)

    # Append after rendering so the history loop won't duplicate them this run
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.messages.append({"role": "assistant", "content": assistant_reply})

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Suggested Questions")
    suggestions = [
        "Show me electric SUVs under $100,000",
        "Do you have any Porsche 911s available?",
        "What is your refund policy?",
        "How do I schedule a test drive?",
        "Do you have any 2020 BMW X5s?",
        "What are the EV maintenance requirements?",
        "How does home delivery work?",
        "Show me the cheapest car you have",
    ]
    for s in suggestions:
        if st.button(s, use_container_width=True, key=f"sug_{s[:20]}"):
            st.session_state.messages.append({"role": "user", "content": s})
            with st.spinner("Thinking..."):
                try:
                    resp = requests.post(
                        f"{BACKEND_URL}/chat",
                        json={"message": s, "session_id": st.session_state.session_id},
                        timeout=120,
                    )
                    resp.raise_for_status()
                    reply = resp.json()["response"]
                except Exception as e:
                    reply = f"⚠️ Error: {str(e)}"
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()

    st.markdown("---")
    if st.button("🗑️ Clear conversation", use_container_width=True):
        try:
            requests.delete(f"{BACKEND_URL}/session/{st.session_state.session_id}", timeout=5)
        except Exception:
            pass
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Conversation cleared. How can I help you today?",
            }
        ]
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

    st.markdown("---")
    st.caption(f"Session: `{st.session_state.session_id[:8]}...`")
