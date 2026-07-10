"""Label Lens: a chat UI over the additive-intelligence agent.

Runs in a phone or laptop browser. Ask about an additive or a product; the agent
routes to the Store (legal status), RAG (evidence), or a live government API and
answers with citations. The sidebar holds the user's memory: a diet/allergy
profile and a log of products, which the agent reads to personalise and to answer
cumulative questions.

Entry point for Streamlit Community Cloud (auto-detected at the repo root).
"""
from __future__ import annotations

import uuid

import streamlit as st

from label_lens.agent import memory
from label_lens.agent.graph import answer
from label_lens.agent.tools import _con

st.set_page_config(page_title="Label Lens", page_icon="🔎", layout="centered")

EXAMPLES = [
    "Is E171 (titanium dioxide) banned in the EU?",
    "Why did the EU ban titanium dioxide, and does that mean it's dangerous?",
    "Is Red 40 sketchy?",
    "Has the FDA taken any recent action on erythrosine (Red 3)?",
]


@st.cache_resource
def _products() -> list[tuple[str, str]]:
    """(name, barcode) for every product with additives, for the log picker."""
    rows = _con().execute(
        """SELECT name, barcode FROM product
           WHERE name IS NOT NULL AND additives_tags <> ''
           ORDER BY name""").fetchall()
    return [(n, b) for n, b in rows]


def _user_id() -> str:
    if "user_id" not in st.session_state:
        st.session_state.user_id = f"web-{uuid.uuid4().hex[:8]}"
    return st.session_state.user_id


def sidebar() -> None:
    uid = _user_id()
    con = _con()
    with st.sidebar:
        st.header("Your profile")
        st.caption("The agent reads this to personalise answers. It still cites every fact.")
        profile = memory.get_profile(con, uid) or {"diet": "", "allergies": ""}
        with st.form("profile"):
            diet = st.text_input("Diet", value=profile["diet"], placeholder="e.g. vegetarian")
            allergies = st.text_input("Allergies", value=profile["allergies"], placeholder="e.g. peanuts")
            if st.form_submit_button("Save profile"):
                memory.set_profile(con, uid, diet=diet, allergies=allergies)
                st.success("Saved.")

        st.header("Log a product")
        st.caption("Log candies you eat; then ask cumulative questions about their additives.")
        products = _products()
        label = st.selectbox("Product", options=[p[0] for p in products], index=None,
                             placeholder="Search products...")
        if st.button("Log product", disabled=label is None):
            barcode = dict(products)[label]
            memory.log_product(con, uid, barcode=barcode, name=label)
            st.success(f"Logged {label}.")

        logged = memory.get_log_with_additives(con, uid)
        if logged:
            st.subheader("Logged so far")
            for r in logged:
                codes = ", ".join(t.split(":")[-1].upper()
                                  for t in r["additives"].split(",") if t)
                st.markdown(f"**{r['name']}** — {codes or 'additives not on file'}")


def main() -> None:
    st.title("🔎 Label Lens")
    st.caption(
        "Ask about a food additive or a product. Answers are cited from regulators "
        "(EU, US FDA, California, IARC), separate legal status from hazard from harm, "
        "and never give medical advice."
    )
    sidebar()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if not st.session_state.messages:
        st.write("**Try one of these:**")
        cols = st.columns(2)
        for i, ex in enumerate(EXAMPLES):
            if cols[i % 2].button(ex, key=f"ex{i}"):
                st.session_state.pending = ex
                st.rerun()

    for m in st.session_state.messages:
        st.chat_message(m["role"]).markdown(m["content"])

    prompt = st.chat_input("Ask about an additive or product...")
    prompt = prompt or st.session_state.pop("pending", None)
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)
        with st.chat_message("assistant"), st.spinner("Checking the regulators..."):
            try:
                reply = answer(prompt, user_id=_user_id())
            except Exception as e:
                reply = f"Something went wrong: {e}"
            st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()
