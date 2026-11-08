"""Payment history page - question C (does past lateness announce current difficulty?): Q7."""
import plotly.express as px
import streamlit as st

from db import NEUTRAL, REFERENCE, RISK, check_connection, footer, global_rate, view

st.set_page_config(page_title="Payment history", page_icon="⏰", layout="wide")
check_connection()

st.title("Payment history")
st.markdown("**Question C:** are clients who were late by more than 7 days in the past "
            "more often in difficulty on their current loan?")

h = view("v_dash_q7_historique")
g = global_rate()
ORDER = ["Pas de retard > 7 j", "Retard > 7 j", "Sans historique"]
LABELS = {"Pas de retard > 7 j": "Never late > 7 days", "Retard > 7 j": "Late > 7 days at least once",
          "Sans historique": "No payment history"}
h = h.set_index("groupe").reindex([o for o in ORDER if o in set(h["groupe"])]).reset_index()
h["label"] = h["groupe"].map(LABELS)
h["colour"] = h["groupe"].map(lambda x: RISK if x == "Retard > 7 j" else NEUTRAL)

late = h[h["groupe"] == "Retard > 7 j"]
ref = h[h["groupe"] == "Pas de retard > 7 j"]
if not late.empty and not ref.empty:
    lr, rr, ratio = late.iloc[0], ref.iloc[0], late.iloc[0].rapport_vs_reference
    if ratio >= 1:
        verdict = f"are {ratio:.2f}× more often in difficulty"
    else:
        verdict = "are not more often in difficulty"
    st.subheader(f"Clients once late by more than 7 days {verdict}: "
                 f"{lr.taux_difficulte_pct:.2f} % vs {rr.taux_difficulte_pct:.2f} % for clients never late > 7 days")

c1, c2, c3 = st.columns(3)
for col, (_, r) in zip([c1, c2, c3], h.iterrows()):
    col.metric(r.label, f"{r.taux_difficulte_pct:.2f} %",
               help=f"{int(r.nb_difficulte)} of {int(r.n_clients)} clients in difficulty")
    col.caption(f"{int(r.n_clients):,} clients · {int(r.nb_difficulte)} in difficulty")

fig = px.bar(h, x="label", y="taux_difficulte_pct",
             text=h["taux_difficulte_pct"].map(lambda v: f"{v:.2f} %"),
             hover_data={"n_clients": True, "nb_difficulte": True, "label": False},
             labels={"label": "", "taux_difficulte_pct": "Clients in difficulty (%)",
                     "n_clients": "Clients", "nb_difficulte": "In difficulty"})
fig.update_traces(marker_color=h["colour"], textposition="outside", cliponaxis=False)
fig.add_hline(y=g, line_dash="dash", line_color=REFERENCE,
              annotation_text=f"All clients: {g:.2f} %", annotation_position="top left")
fig.update_layout(margin=dict(t=40))
st.plotly_chart(fig, width="stretch")

small = h[(h["nb_difficulte"] < 10)]
if not small.empty:
    st.warning("Read with caution: " + ", ".join(
        f"'{r.label}' has only {int(r.nb_difficulte)} clients in difficulty" for _, r in small.iterrows())
        + ", too few for a reliable rate.")
st.caption("Group = the client's worst delay across all past instalments (Q7). "
           "This is an association, not proof that lateness causes difficulty.")

footer()