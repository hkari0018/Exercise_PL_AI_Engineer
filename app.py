"""
Optional Streamlit interface for the Portfolio Analytics Agent.
Usage:
    streamlit run app.py
"""

import os
import sys

import streamlit as st
from dotenv import load_dotenv
from google import genai

from database import build_database
from agent import PortfolioAgent


load_dotenv()

st.set_page_config(
    page_title="Portfolio Analytics Agent",
    page_icon=None,
    layout="wide",
)

st.title("Portfolio Analytics Agent")
st.caption("Ask natural language questions about portfolio data.")


@st.cache_resource(show_spinner="Loading database...")
def get_agent():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error(
            "GEMINI_API_KEY not set. Create a .env file with your key."
        )
        st.stop()
    client = genai.Client(api_key=api_key)
    conn = build_database()
    return PortfolioAgent(conn, client)


agent = get_agent()

# --- Sidebar: example questions ---
st.sidebar.header("Example Questions")
examples = [
    "How many portfolios do we have in total?",
    "What are the names of all active portfolios?",
    "Which securities are in the Technology sector?",
    "What are the sector exposures for the Tech Innovation Fund?",
    "Calculate the sector exposure breakdown for International Equity Fund",
    "Show me the top 5 holdings by cost basis in the Growth Equity Fund",
    "What is the total AUM for portfolios with high target risk level?",
    "What is the average current price of securities in each sector?",
]

for ex in examples:
    if st.sidebar.button(ex, use_container_width=True):
        st.session_state["question_input"] = ex

# --- Main input ---
question = st.text_input(
    "Your question",
    value=st.session_state.get("question_input", ""),
    placeholder="e.g. How many portfolios do we have?",
    key="question_input",
)

if st.button("Ask", type="primary") and question.strip():
    with st.spinner("Thinking..."):
        result = agent.answer_question(question.strip())

    if result.get("error"):
        st.error(f"Error: {result['error']}")
    else:
        st.subheader("Answer")
        st.write(result["answer"])

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"Tool used: `{result['tool_used']}`")

        tool_result = result.get("tool_result", {})

        if result["tool_used"] == "sql_query":
            with st.expander("SQL Query", expanded=False):
                st.code(tool_result.get("sql", ""), language="sql")
            rows = tool_result.get("rows", [])
            if rows:
                import pandas as pd
                with st.expander(f"Raw results ({len(rows)} rows)", expanded=False):
                    st.dataframe(pd.DataFrame(rows), use_container_width=True)

        if result["tool_used"] == "exposure_calculator":
            exposures = tool_result.get("sector_exposures", {})
            if exposures:
                import pandas as pd
                df = pd.DataFrame(
                    [{"Sector": k, "Exposure (%)": v} for k, v in exposures.items()]
                )
                with st.expander("Sector Exposures", expanded=True):
                    st.dataframe(df, use_container_width=True)
                    st.bar_chart(df.set_index("Sector"))