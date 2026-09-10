import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from crewai import Crew
from agents import property_researcher, property_analyst
from tasks import create_research_task, create_analysis_task

st.set_page_config(
    page_title="Real Estate Investment AI Agent",
    page_icon="🏢",
    layout="centered",
)

st.title("🏢 Real Estate Investment AI Agent")
st.markdown("Two specialized AI agents research and analyze real estate opportunities, delivering investor-grade reports in minutes.")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.markdown("**🔍 Agent 1 — Property Researcher**")
    st.caption("Searches the web for market data, rental yields, ROI potential, and evaluates investment locations.")

with col2:
    st.markdown("**📊 Agent 2 — Property Analyst**")
    st.caption("Synthesizes research into a structured investment report with rankings, risk analysis, and recommendations.")

st.divider()

with st.form("analysis_form"):
    location = st.text_input("Location", placeholder="e.g., Mumbai, Berlin, New York")
    property_type = st.selectbox(
        "Property Type",
        ["Residential", "Commercial", "Retail", "Industrial", "Mixed-Use"],
    )

    submitted = st.form_submit_button("🚀 Analyze Properties", use_container_width=True)

if submitted:
    if not location:
        st.error("Please enter a location.")
    else:
        with st.status("🤖 AI Agents are working...", expanded=True) as status:
            st.write("🔍 Researcher agent searching the web...")
            research_task = create_research_task(location, property_type)

            st.write("📈 Analyzing market data and financials...")
            analysis_task = create_analysis_task(location, property_type, research_task)

            crew = Crew(
                agents=[property_researcher, property_analyst],
                tasks=[research_task, analysis_task],
                verbose=True,
            )

            st.write("📝 Analyst agent compiling the report...")
            result = crew.kickoff()

            status.update(label="✅ Analysis complete!", state="complete", expanded=False)

        st.subheader(f"📋 Investment Report — {property_type.title()} in {location.title()}")
        st.markdown(str(result))

        st.download_button(
            label="📥 Download Report",
            data=str(result),
            file_name=f"investment_report_{location.lower().replace(' ', '_')}.txt",
            mime="text/plain",
        )
