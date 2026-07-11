"""Label Lens: a chat UI over the additive-intelligence agent.

Runs in a phone or laptop browser. Ask about an additive or a product; the agent
routes to the Store (legal status), RAG (evidence), or a live government API and
answers with citations. The sidebar holds the user's memory: a diet/allergy
profile and a log of products, which the agent reads to personalise and to answer
cumulative questions.

Entry point for Streamlit Community Cloud (auto-detected at the repo root).
"""
from __future__ import annotations

import hmac
import os
import sys
import uuid
from pathlib import Path

# src/ layout: on Streamlit Community Cloud the app is run from the repo root and
# our package is not pip-installed (requirements.txt has only third-party deps),
# so make `import label_lens` resolve by putting src/ on the path.
_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st

# On Streamlit Community Cloud the secret lives in st.secrets, not .env.local.
# Bridge it into the environment the agent reads before importing the agent.
# Accessing st.secrets with no secrets file raises, so guard it (local dev).
try:
    for _k in ("OPENROUTER_API_KEY", "OPENROUTER_MODEL", "LANGSMITH_API_KEY"):
        if _k in st.secrets and not os.getenv(_k):
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass

from label_lens.agent import memory  # noqa: E402
from label_lens.agent.graph import answer  # noqa: E402
from label_lens.agent.tools import _con  # noqa: E402
from label_lens.rag.index import ensure_index  # noqa: E402

st.set_page_config(page_title="Label Lens", page_icon="🔎", layout="centered")


@st.cache_resource(show_spinner="Building the brief index (first load only)...")
def _warm() -> bool:
    """Build the Chroma index once per host if it is missing (deployed clones)."""
    ensure_index()
    return True

# A pool of starter questions across the three lanes. Four are shown at a time;
# using one rotates in the next unused one, so the suggestions stay fresh.
EXAMPLE_POOL = [
    "Is E171 (titanium dioxide) banned in the EU?",
    "Why did the EU ban titanium dioxide, and does that mean it's dangerous?",
    "Is Red 40 sketchy?",
    "Has the FDA taken any recent action on erythrosine (Red 3)?",
    "Is aspartame a carcinogen?",
    "Is Red 3 banned in California?",
    "Why is sodium nitrite in cured meat controversial?",
    "Is potassium bromate allowed in US food?",
    "What does the EU require for FD&C Yellow 6?",
    "Are there any recent recalls involving food dyes?",
]
CHIPS_SHOWN = 4


@st.cache_resource
def _products() -> list[dict]:
    """Every product with additives: name, barcode, image URL, additive tags."""
    rows = _con().execute(
        """SELECT name, barcode, image_url, additives_tags FROM product
           WHERE name IS NOT NULL AND additives_tags <> ''
           ORDER BY name""").fetchall()
    return [{"name": n, "barcode": b, "image": img, "additives": tags}
            for n, b, img, tags in rows]


def _codes(additives_tags: str) -> str:
    """'en:e171,en:e102' -> 'E171, E102' for display."""
    return ", ".join(t.split(":")[-1].upper() for t in (additives_tags or "").split(",") if t)


def _pantry_barcodes(con, uid: str) -> set[str]:
    return {r["barcode"] for r in memory.get_log_with_additives(con, uid)}


def _user_id() -> str:
    if "user_id" not in st.session_state:
        st.session_state.user_id = f"web-{uuid.uuid4().hex[:8]}"
    return st.session_state.user_id


def _password_ok() -> bool:
    """Shared-password gate so a public visitor can't spend the OpenRouter key.

    The expected password comes from st.secrets["APP_PASSWORD"]. If none is set
    (e.g. local dev), the app is open. Nothing downstream runs until this returns
    True, so no model call happens for an unauthenticated visitor.
    """
    try:
        expected = st.secrets.get("APP_PASSWORD")
    except Exception:
        expected = None
    if not expected:
        return True
    if st.session_state.get("auth_ok"):
        return True

    st.caption("This demo is password-protected. Enter the password from the submission.")
    with st.form("login"):
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("Enter"):
            if hmac.compare_digest(pw, str(expected)):
                st.session_state.auth_ok = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    return False


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

        pantry = memory.get_log_with_additives(con, uid)
        st.header(f"Pantry ({len(pantry)})")
        st.caption("Build your pantry in the **Pantry** tab, then ask cumulative questions in **Chat**.")
        for r in pantry:
            st.markdown(f"**{r['name']}** — {_codes(r['additives']) or 'additives not on file'}")


def main() -> None:
    st.title("🔎 Label Lens")
    st.caption(
        "Ask about a food additive or a product. Answers are cited from regulators "
        "(EU, US FDA, California, IARC), separate legal status from hazard from harm, "
        "and never give medical advice."
    )
    if not _password_ok():
        return
    _warm()
    sidebar()

    view = st.segmented_control(
        "view", ["💬 Chat", "🧺 Pantry"], default="💬 Chat",
        key="view", label_visibility="collapsed")
    if view == "🧺 Pantry":
        render_pantry()
    else:
        render_chat()


def render_chat() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Resolve the prompt (a pending chip-click, else freshly typed input).
    # chat_input is always rendered; it pins to the bottom and never drops a click.
    typed = st.chat_input("Ask about an additive or product...")
    prompt = st.session_state.pop("pending", None) or typed

    for m in st.session_state.messages:
        st.chat_message(m["role"]).markdown(m["content"])

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

    _suggestion_chips()


def render_pantry() -> None:
    con, uid = _con(), _user_id()
    products = _products()
    in_pantry = _pantry_barcodes(con, uid)

    st.subheader(f"🧺 Your pantry ({len(in_pantry)})")
    mine = [p for p in products if p["barcode"] in in_pantry]
    if mine:
        _product_grid(mine, in_pantry, key_prefix="pantry")
        st.caption("Then switch to **Chat** and ask: *Across the candy I've logged, is anything banned or restricted anywhere?*")
    else:
        st.caption("Your pantry is empty. Add candies from the catalogue below.")

    st.divider()
    st.subheader("Browse products")
    query = st.text_input("Search", placeholder="Search by name…", label_visibility="collapsed")
    shown = [p for p in products if query.lower() in p["name"].lower()] if query else products
    st.caption(f"{len(shown)} product{'s' if len(shown) != 1 else ''}")
    _product_grid(shown, in_pantry, key_prefix="browse")


def _product_grid(items: list[dict], in_pantry: set[str], *, key_prefix: str,
                  cols: int = 4) -> None:
    con, uid = _con(), _user_id()
    columns = st.columns(cols)
    for i, p in enumerate(items):
        with columns[i % cols], st.container(border=True):
            if p["image"]:
                st.image(p["image"], use_container_width=True)
            else:
                st.markdown(
                    "<div style='height:110px;display:flex;align-items:center;"
                    "justify-content:center;font-size:3rem'>🍬</div>",
                    unsafe_allow_html=True)
            st.markdown(f"**{p['name'][:42]}**")
            st.caption(_codes(p["additives"]) or "additives not on file")
            bc = p["barcode"]
            if bc in in_pantry:
                if st.button("✓ In pantry — remove", key=f"{key_prefix}_rm_{bc}",
                             use_container_width=True):
                    memory.remove_product(con, uid, bc)
                    st.rerun()
            elif st.button("＋ Add to pantry", key=f"{key_prefix}_add_{bc}",
                           use_container_width=True):
                memory.log_product(con, uid, barcode=bc, name=p["name"])
                st.rerun()


def _suggestion_chips() -> None:
    """Show a few starter questions, always. Using one rotates in a fresh one.

    Rendered on every run (never conditional), so a visible chip is always
    instantiated on the run its click is processed: no dropped clicks. Below the
    conversation and above the input, so it reads as a suggestion row.
    """
    used = st.session_state.setdefault("used_examples", [])
    show = [q for q in EXAMPLE_POOL if q not in used][:CHIPS_SHOWN]
    if not show:
        return
    st.caption("Try one of these:")
    cols = st.columns(2)
    for i, ex in enumerate(show):
        if cols[i % 2].button(ex, key=f"ex{i}"):
            used.append(ex)
            st.session_state.pending = ex
            st.rerun()


if __name__ == "__main__":
    main()
