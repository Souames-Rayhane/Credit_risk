"""Risk profiles page - question B (which client profiles carry more difficulty?): Q6a and Q6b."""
import plotly.express as px
import streamlit as st

from db import NEUTRAL, REFERENCE, RISK, check_connection, footer, global_rate, view

st.set_page_config(page_title="Risk profiles", page_icon="👥", layout="wide")
check_connection()

st.title("Client profiles")
st.markdown("**Question B:** which client profiles are more often in payment difficulty than average?")

seg = view("v_dash_q6b_profils")
g = global_rate()

# Sort order for segments that have a natural order; others are sorted by rate.
ORDER = {
    "Quartile de revenu": ["Q1", "Q2", "Q3", "Q4"],
    "Ratio annuite / revenu": ["< 10 %", "10 - 20 %", ">= 20 %", "Inconnu"],
    "Score externe": ["< 0.3", "0.3 - 0.5", "0.5 - 0.7", ">= 0.7", "Score inconnu"],
    "Zone regionale": ["1", "2", "3"],
}
NAMES = {
    "Score externe": "External score", "Ratio annuite / revenu": "Annuity / income ratio",
    "Quartile de revenu": "Income quartile", "Type de revenu": "Income type",
    "Education": "Education", "Zone regionale": "Regional rating",
}
dims = [d for d in NAMES if d in set(seg["dimension"])]
dim = st.selectbox("Profile dimension", dims, format_func=lambda d: NAMES[d])

d = seg[seg["dimension"] == dim].copy()
if dim in ORDER:
    rank = {s: i for i, s in enumerate(ORDER[dim])}
    d = d.sort_values("segment", key=lambda s: s.map(rank).fillna(99))
else:
    d = d.sort_values("taux_difficulte_pct", ascending=False)

d["colour"] = d["taux_difficulte_pct"].map(lambda v: RISK if v > g else NEUTRAL)
d["text"] = d.apply(lambda r: f"{r.taux_difficulte_pct:.1f} %" + (" *" if r.fiabilite != "ok" else ""), axis=1)

top = d.loc[d["taux_difficulte_pct"].idxmax()]
st.subheader(f"{NAMES[dim]}: highest difficulty rate in segment '{top.segment}' — "
             f"{top.taux_difficulte_pct:.1f} % vs {g:.1f} % overall ({top.ecart_vs_global_pts:+.1f} points)")

fig = px.bar(d, x="segment", y="taux_difficulte_pct", text="text",
             hover_data={"n_clients": True, "nb_difficulte": True, "ecart_vs_global_pts": True,
                         "fiabilite": True, "segment": False},
             labels={"segment": "", "taux_difficulte_pct": "Clients in difficulty (%)",
                     "n_clients": "Clients", "nb_difficulte": "In difficulty",
                     "ecart_vs_global_pts": "Gap vs overall (points)", "fiabilite": "Reliability"})
fig.update_traces(marker_color=d["colour"], textposition="outside", cliponaxis=False)
fig.add_hline(y=g, line_dash="dash", line_color=REFERENCE,
              annotation_text=f"All clients: {g:.2f} %", annotation_position="top left")
fig.update_layout(margin=dict(t=40))
st.plotly_chart(fig, width="stretch")
st.caption("Red = above the overall rate. * = fewer than 10 clients in difficulty in the segment: "
           "read as indicative only. Segments under 30 clients are hidden (Q6b).")

with st.expander("Segment table"):
    st.dataframe(d[["segment", "n_clients", "nb_difficulte", "taux_difficulte_pct",
                    "ecart_vs_global_pts", "fiabilite"]].rename(columns={
                        "segment": "Segment", "n_clients": "Clients", "nb_difficulte": "In difficulty",
                        "taux_difficulte_pct": "Rate (%)", "ecart_vs_global_pts": "Gap (points)",
                        "fiabilite": "Reliability"}),
                 width="stretch", hide_index=True)

# --- Q6a: context for the ratio bands ----------------------------------------
if dim == "Ratio annuite / revenu":
    r = view("v_dash_q6a_ratio").iloc[0]
    st.markdown(
        f"**How the ratio bands were chosen (Q6a):** half the clients pay less than "
        f"{r.mediane:.1%} of their income in annuity; 10 % pay less than {r.p10:.1%} and "
        f"10 % more than {r.p90:.1%}. The bands < 10 %, 10–20 % and ≥ 20 % split that range."
    )

footer()