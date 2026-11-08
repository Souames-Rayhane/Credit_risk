"""Products page - question A (which products and portfolios to watch?): Q2 and Q5."""
import plotly.express as px
import streamlit as st

from db import NEUTRAL, REFERENCE, RISK, check_connection, footer, view

st.set_page_config(page_title="Products", page_icon="📦", layout="wide")
check_connection()

st.title("Products and portfolios")
st.markdown("**Question A (continued):** which credit sources and portfolios concentrate serious lateness?")

# --- Q2: ranking by > 7 days late -------------------------------------------
p = view("v_dash_q2_produits").sort_values("rang")
overall_7j = float(view("v_dash_q1_kpi").iloc[0]["taux_retard_7j_pct"])

sources = sorted(p["credit_source"].unique())
chosen = st.multiselect("Credit source", sources, default=sources)
p = p[p["credit_source"].isin(chosen)]

if p.empty:
    st.info("No portfolio with at least 100 instalments for this selection.")
else:
    p["label"] = p["portefeuille"] + " · " + p["credit_source"].str.replace("_", " ")
    p["colour"] = p["taux_retard_7j_pct"].map(lambda v: RISK if v > overall_7j else NEUTRAL)
    top = p.iloc[0]
    st.subheader(f"{top['portefeuille']} ({top['credit_source'].replace('_', ' ')}) has the highest "
                 f"rate of lateness > 7 days: {top['taux_retard_7j_pct']:.2f} % vs {overall_7j:.2f} % overall")

    fig = px.bar(p.iloc[::-1], x="taux_retard_7j_pct", y="label", orientation="h",
                 text=p.iloc[::-1]["taux_retard_7j_pct"].map(lambda v: f"{v:.2f} %"),
                 hover_data={"nb_echeances": ":,", "taux_retard_pct": True, "label": False},
                 labels={"taux_retard_7j_pct": "Instalments late > 7 days (%)", "label": "",
                         "nb_echeances": "Instalments", "taux_retard_pct": "Late (any delay, %)"})
    fig.update_traces(marker_color=p.iloc[::-1]["colour"], textposition="outside", cliponaxis=False)
    fig.add_vline(x=overall_7j, line_dash="dash", line_color=REFERENCE,
                  annotation_text=f"All instalments: {overall_7j:.2f} %", annotation_position="top")
    fig.update_layout(height=120 + 40 * len(p), margin=dict(t=40))
    st.plotly_chart(fig, width="stretch")
    st.caption("Red = above the overall rate. Only portfolios with at least 100 instalments are shown (Q2). "
               "Hover a bar for the number of instalments and the rate for any delay.")

# --- Q5: pivot with subtotals ------------------------------------------------
st.subheader("Instalments by source, portfolio and lateness bucket")
pv = view("v_dash_q5_pivot").sort_values(["g_source", "source_credit", "g_portefeuille", "portefeuille"])
pv = pv.drop(columns=["g_source", "g_portefeuille"]).rename(columns={
    "source_credit": "Credit source", "portefeuille": "Portfolio", "nb_echeances": "Instalments",
    "a_temps": "On time", "retard_1_7j": "1–7 d", "retard_8_30j": "8–30 d",
    "retard_plus_30j": "> 30 d", "sans_date_paiement": "No payment date",
})
st.dataframe(pv, width="stretch", hide_index=True,
             column_config={c: st.column_config.NumberColumn(format="%d")
                            for c in ["Instalments", "On time", "1–7 d", "8–30 d", "> 30 d", "No payment date"]})
st.caption("Subtotal rows come from ROLLUP (Q5): 'Tous portefeuilles' = subtotal per source, "
           "'TOTAL' = grand total. Buckets add up to the instalment count.")

footer()