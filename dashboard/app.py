"""Overview page - question A (how big is the lateness problem?): Q1 and Q4."""
import plotly.express as px
import streamlit as st

from db import NEUTRAL, RISK, check_connection, footer, global_rate, view

st.set_page_config(page_title="Credit risk portal", page_icon="📊", layout="wide")
check_connection()

st.title("Repayment behaviour — overview")
st.markdown(
    "**Question A:** how often are instalments paid late, and how late? "
    "Use the pages on the left for products (A), client profiles (B), "
    "payment history (C) and the early-alert rule (D)."
)

# --- Q1: global KPIs ---------------------------------------------------------
k = view("v_dash_q1_kpi").iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Late instalments", f"{k.taux_retard_pct:.2f} %",
          help="Paid after the due date, among instalments with a payment date (Q1).")
c2.metric("Late by more than 7 days", f"{k.taux_retard_7j_pct:.2f} %")
c3.metric("Late by more than 30 days", f"{k.taux_retard_30j_pct:.2f} %")
c4.metric("Clients in difficulty", f"{global_rate():.2f} %",
          help="Share of clients with target = 1 on their current loan.")
st.caption(f"{int(k.nb_echeances):,} instalments, of which {int(k.nb_avec_date_paiement):,} have a payment date.")

# --- Q4: lateness buckets ----------------------------------------------------
labels = {
    "0 - sans date de paiement": "No payment date",
    "1 - a temps / en avance": "On time or early",
    "2 - 1 a 7 jours": "1–7 days late",
    "3 - 8 a 30 jours": "8–30 days late",
    "4 - plus de 30 jours": "> 30 days late",
}
t = view("v_dash_q4_tranches").sort_values("tranche_retard")
t["bucket"] = t["tranche_retard"].map(labels).fillna(t["tranche_retard"])
t["colour"] = t["tranche_retard"].str[0].map(lambda c: RISK if c in "34" else NEUTRAL)

late_share = t.loc[t["tranche_retard"].str[0].isin(["2", "3", "4"]), "part_pct"].sum()
short_share = t.loc[t["tranche_retard"].str[0] == "2", "part_pct"].sum()
st.subheader(f"Most lateness is short: {short_share:.1f} % of instalments are 1–7 days late, "
             f"out of {late_share:.1f} % late in total")

fig = px.bar(t, x="bucket", y="nb_echeances", text=t["part_pct"].map(lambda v: f"{v:.2f} %"),
             labels={"bucket": "", "nb_echeances": "Instalments"})
fig.update_traces(marker_color=t["colour"], textposition="outside", cliponaxis=False)
fig.update_layout(showlegend=False, margin=dict(t=30), yaxis_type="log",
                  yaxis_title="Instalments (log scale)")
st.plotly_chart(fig, width="stretch")
st.caption("Log scale: on-time payments are about 90 % of instalments, which would flatten the "
           "late buckets on a linear axis. Red = more than 7 days late (Q4).")

footer()