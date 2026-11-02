import os
import secrets

import streamlit as st

from pipeline import run_analysis
from schemas import FinancialAssumptions

# Set on public deployments, so strangers cannot spend the Gemini and Serper quotas.
demo_password = os.getenv("DEMO_PASSWORD")

st.set_page_config(
    page_title="EstateMind",
    page_icon="🏢",
    layout="centered",
)

st.title("🏢 EstateMind")
st.markdown("Three specialized AI agents research, model and analyze real estate opportunities, with every financial metric calculated in code.")

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**🔍 Agent 1 — Researcher**")
    st.caption("Searches the web for market data, prices, rents and risks.")

with col2:
    st.markdown("**🧮 Agent 2 — Financial Modeler**")
    st.caption("Runs the finance tool on each candidate, including a downside case.")

with col3:
    st.markdown("**📊 Agent 3 — Analyst**")
    st.caption("Turns the findings into a ranked report with a clear recommendation.")

st.divider()

defaults = FinancialAssumptions()

with st.form("analysis_form"):
    location = st.text_input("Location", placeholder="e.g., Mumbai, Berlin, New York")
    property_type = st.selectbox(
        "Property Type",
        ["Residential", "Commercial", "Retail", "Industrial", "Mixed-Use"],
    )

    with st.expander("⚙️ Financing assumptions"):
        st.caption("Illustrative defaults. Change them to match your own loan and costs.")
        left, right = st.columns(2)
        down_payment_pct = left.number_input("Down payment (%)", 1.0, 100.0, defaults.down_payment_pct)
        annual_interest_rate = right.number_input("Interest rate (%)", 0.0, 30.0, defaults.annual_interest_rate)
        loan_term_years = left.number_input("Loan term (years)", 1, 40, defaults.loan_term_years)
        vacancy_rate_pct = right.number_input("Vacancy (%)", 0.0, 100.0, defaults.vacancy_rate_pct)
        operating_expense_pct = left.number_input("Operating costs (% of rent)", 0.0, 100.0, defaults.operating_expense_pct)

    entered_password = st.text_input("Demo password", type="password") if demo_password else ""

    submitted = st.form_submit_button("🚀 Analyze Properties", use_container_width=True)

if submitted:
    if not location:
        st.error("Please enter a location.")
    elif demo_password and not secrets.compare_digest(entered_password.encode(), demo_password.encode()):
        st.error("Incorrect demo password.")
    else:
        assumptions = FinancialAssumptions(
            down_payment_pct=down_payment_pct,
            annual_interest_rate=annual_interest_rate,
            loan_term_years=loan_term_years,
            vacancy_rate_pct=vacancy_rate_pct,
            operating_expense_pct=operating_expense_pct,
        )

        with st.status("🤖 AI Agents are working...", expanded=True) as status:
            st.write("🔍 Researcher, 🧮 Modeler and 📊 Analyst are running in order...")
            st.write("⏳ This usually takes several minutes on the free Gemini tier.")
            try:
                result = run_analysis(location, property_type, assumptions)
            except Exception as error:
                status.update(label="❌ Analysis failed", state="error")
                st.error(f"The analysis could not finish. Please try again in a minute.\n\nDetails: {error}")
                st.stop()

            status.update(label="✅ Analysis complete!", state="complete", expanded=False)

        st.subheader(f"📋 Investment Report — {property_type.title()} in {location.title()}")

        if result.report:
            report = result.report
            top_pick = report.picks[0]

            st.caption(f"Top pick: {top_pick.name}")
            if report.rejected_picks:
                st.warning(f"Excluded for implausible price and rent data: {', '.join(report.rejected_picks)}")

            roi_col, cap_col, risk_col, emi_col = st.columns(4)
            roi_col.metric("ROI (Cash-on-Cash)", f"{report.roi_pct:.2f}%")
            cap_col.metric("Cap Rate", f"{report.cap_rate_pct:.2f}%")
            risk_col.metric("Risk Score", f"{report.risk_score}/10")
            emi_col.metric(f"Monthly EMI ({top_pick.currency})", f"{top_pick.metrics.monthly_emi:,.0f}")

            st.caption(
                f"Downside (lower rent, higher interest): ROI {report.downside.cash_on_cash_return_pct:.2f}%, "
                f"Cap Rate {report.downside.cap_rate_pct:.2f}%"
            )

            pros_col, cons_col = st.columns(2)
            with pros_col:
                st.markdown("**✅ Key Pros**")
                st.markdown("\n".join(f"- {pro}" for pro in report.pros))
            with cons_col:
                st.markdown("**⚠️ Key Cons**")
                st.markdown("\n".join(f"- {con}" for con in report.cons))

            st.divider()
        else:
            st.warning("Metric cards are unavailable for this run, so the raw report is shown below.")

        st.markdown(result.markdown)

        st.download_button(
            label="📥 Download Report",
            data=result.markdown,
            file_name=f"investment_report_{location.lower().replace(' ', '_')}.txt",
            mime="text/plain",
        )

        if result.telemetry:
            telemetry = result.telemetry

            with st.expander("📈 MLOps Pipeline Telemetry"):
                latency_col, tokens_col, requests_col, cost_col = st.columns(4)
                latency_col.metric("Latency", f"{telemetry.latency_seconds:.1f}s")
                tokens_col.metric("Tokens", f"{telemetry.total_tokens:,}")
                requests_col.metric("LLM Requests", telemetry.llm_requests)
                cost = telemetry.estimated_cost_usd
                cost_col.metric("Est. Paid Cost", "n/a" if cost is None else f"${cost:.4f}")

                st.markdown("**Agent steps completed**")
                for step in telemetry.steps:
                    st.markdown(f"- {step.agent} ({step.finished_after_seconds:.1f}s)")

                st.markdown("**Run details**")
                st.caption(
                    f"Run {telemetry.run_id} · Model {telemetry.model} · "
                    f"Prompt v{telemetry.prompt_version} · Code {telemetry.git_sha}"
                )

                st.markdown("**Saved artifacts**")
                for location_saved in result.artifacts.values():
                    st.code(location_saved, language=None)
