"""Early-alert page - question D (whom to follow up first?): Q8."""
import plotly.express as px
import streamlit as st

from db import REFERENCE, check_connection, footer, global_rate, view

st.set_page_config(page_title="Early alert", page_icon="🚨", layout="wide")
check_connection()

st.title("Early-alert rule")
st.markdown(
    "**Question D:** a simple rule to decide whom to follow up first. Each client gets one point per signal:\n"
    "- **+1** if they were late by more than 7 days at least once;\n"
    "- **+1** if their external score is in the lowest quarter of clients.\n\n"
    "Score 0 = no signal, score 2 = both. This is an illustrative rule, not a validated model."
)

a = view("v_dash_q8_alerte").sort_values("score_alerte")
g = global_rate()
a["label"] = "Score " + a["score_alerte"].astype(int).astype(str)

lo, hi = a.iloc[0], a.iloc[-1]
monotone = a["taux_difficulte_pct"].is_monotonic_increasing
if monotone and hi.taux_difficulte_pct > lo.taux_difficulte_pct:
    st.subheader(f"The difficulty rate rises with the score: from {lo.taux_difficulte_pct:.1f} % "
                 f"at score {int(lo.score_alerte)} to {hi.taux_difficulte_pct:.1f} % at score {int(hi.score_alerte)}")
else:
    st.subheader("The difficulty rate does not rise steadily with the score: the rule needs review")

c = st.columns(len(a))
for col, (_, r) in zip(c, a.iterrows()):
    col.metric(r.label, f"{r.taux_difficulte_pct:.2f} %")
    col.caption(f"{int(r.n_clients):,} clients · {int(r.nb_difficulte)} in difficulty")

# Darker red as the score rises: the colour follows the risk level.
shades = ["#F5B7B1", "#E57367", "#C0392B", "#922B21"]
fig = px.bar(a, x="label", y="taux_difficulte_pct",
             text=a["taux_difficulte_pct"].map(lambda v: f"{v:.2f} %"),
             hover_data={"n_clients": True, "nb_difficulte": True, "label": False},
             labels={"label": "", "taux_difficulte_pct": "Clients in difficulty (%)",
                     "n_clients": "Clients", "nb_difficulte": "In difficulty"})
fig.update_traces(marker_color=shades[: len(a)], textposition="outside", cliponaxis=False)
fig.add_hline(y=g, line_dash="dash", line_color=REFERENCE,
              annotation_text=f"All clients: {g:.2f} %", annotation_position="top left")
fig.update_layout(margin=dict(t=40))
st.plotly_chart(fig, width="stretch")

flagged = a[a["score_alerte"] >= 1]
if not flagged.empty:
    n_flag, d_flag = int(flagged["n_clients"].sum()), int(flagged["nb_difficulte"].sum())
    n_all, d_all = int(a["n_clients"].sum()), int(a["nb_difficulte"].sum())
    st.info(f"Following up clients with score ≥ 1 means contacting {n_flag:,} of {n_all:,} clients "
            f"({100 * n_flag / n_all:.0f} %), a group that contains {d_flag} of the {d_all} "
            f"clients in difficulty ({100 * d_flag / d_all:.0f} %).")

small = a[a["nb_difficulte"] < 10]
if not small.empty:
    st.caption("Indicative only for: " + ", ".join(small["label"]) + " (fewer than 10 clients in difficulty).")

footer()