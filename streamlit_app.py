"""Label Lens: a chat UI over the additive-intelligence agent.

Runs in a phone or laptop browser. Ask about an additive or a product; the agent
routes to the Store (legal status), RAG (evidence), or a live government API and
answers with citations. Three tabs in the header: Chat, Pantry (browse products
and build a pantry), and Profile (diet/allergies). The sidebar shows a read-only
summary of the profile and pantry.

Entry point for Streamlit Community Cloud (auto-detected at the repo root).
"""
from __future__ import annotations

import hmac
import html
import os
import sys
import time
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
from label_lens.agent.graph import answer_with_trace  # noqa: E402
from label_lens.agent.tools import _con  # noqa: E402
from label_lens.config import DATA  # noqa: E402
from label_lens.rag.index import ensure_index  # noqa: E402

st.set_page_config(page_title="Label Lens", page_icon="🔎", layout="centered")

# A real top header (logo + tabs pinned to the top of the viewport, aligned with
# Streamlit's own toolbar so Share/menu stay on the right), bigger base text, and
# red "Remove from Pantry" buttons (their widget keys contain "_rm_", which
# Streamlit exposes as an st-key- class). The developer chrome (Clear cache etc.)
# is handled by toolbarMode in .streamlit/config.toml, not here.
st.markdown("""
<style>
html { font-size: 18px; }
[data-testid="stCaptionContainer"] p { font-size: 0.92rem; }
.stMarkdown p, [data-testid="stChatMessageContent"] p { font-size: 1.03rem; line-height: 1.55; }
div[class*="_rm_"] button { background-color:#e05656 !important; border-color:#e05656 !important; color:#fff !important; }
div[class*="_rm_"] button:hover { background-color:#c94444 !important; border-color:#c94444 !important; }

/* Real fixed header bar across the top of the screen.
   Streamlit stacks the sidebar (z 999991) and its own header (z 999990) above
   normal content with opaque backgrounds, so a plain fixed bar gets painted
   over. Lift our bar above the sidebar (999992). Keep Streamlit's header above
   ours (999993) but make it transparent so its background stops hiding our bar.
   The bar height matches the native header (3.75rem) with no vertical padding,
   so the logo, tabs and Share buttons all sit on the same centre line. */
.st-key-ll_header {
  position: fixed; top: 0; left: 0; right: 0; z-index: 999992;
  background: #0e1117; border-bottom: 1px solid rgba(128,128,128,0.28);
  height: 3.75rem; padding: 0 1.25rem;
  display: flex; align-items: center;
}
/* Full-height flex-centering down the whole nesting so the logo, tabs and the
   Share buttons all land on the same vertical centre line. */
.st-key-ll_header > div,
.st-key-ll_header [data-testid="stHorizontalBlock"],
.st-key-ll_header [data-testid="stColumn"],
.st-key-ll_header [data-testid="stElementContainer"],
.st-key-ll_header [data-testid="stButtonGroup"],
.st-key-ll_header [data-testid="stMarkdown"],
.st-key-ll_header [data-testid="stMarkdown"] > div,
.st-key-ll_header [data-testid="stMarkdownContainer"] {
  height: 100%; display: flex; align-items: center; width: 100%;
}
.st-key-ll_header .stMarkdown p { margin: 0; line-height: 1; }

/* Tabs = plain clickable text: strip the segmented-control button borders/pills
   and show selection by colour only (bright+bold = selected, muted = not). */
.st-key-ll_header [data-testid="stButtonGroup"] button {
  border: none !important; background: transparent !important; box-shadow: none !important;
  padding: 0.25rem 0.7rem !important;
}
.st-key-ll_header button[aria-checked="false"] { color: #9aa0aa !important; }
.st-key-ll_header button[aria-checked="false"]:hover { color: #d7dae0 !important; }
.st-key-ll_header button[aria-checked="true"] { color: #ffffff !important; font-weight: 700 !important; }

/* Streamlit's toolbar spans the whole header width and is transparent but
   click-catching, which swallowed clicks meant for the tabs. Let clicks pass
   through the header/toolbar and re-enable only the real toolbar controls. */
[data-testid="stHeader"] { background: transparent !important; z-index: 999993 !important; }
[data-testid="stHeader"], [data-testid="stToolbar"] { pointer-events: none; }
[data-testid="stToolbar"] button, [data-testid="stToolbar"] a,
[data-testid="stToolbar"] summary, [data-testid="stToolbar"] [role="button"] { pointer-events: auto; }

/* Push the page down, and push the whole sidebar below the bar so its collapse
   arrow (which lives at the very top of the sidebar) clears the bar and stays
   clickable. */
[data-testid="stMainBlockContainer"], .block-container { padding-top: 5rem !important; }
[data-testid="stSidebar"] { margin-top: 3.75rem; }
/* Sidebar collapse arrow: always visible (no hover needed) and, thanks to the
   margin above, it sits below the bar so it stays clickable. */
[data-testid="stSidebarCollapseButton"] { opacity: 1 !important; visibility: visible !important; }
/* When the sidebar is collapsed the expand button appears top-left, under the
   bar and over the logo. Pin it below the bar (fixed) so it's clear and clickable. */
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] {
  position: fixed !important; top: 4.5rem !important; left: 0.5rem !important;
  z-index: 999994 !important;
}

/* Keep the product-card action buttons on one line. */
div[class*="_add_"] button, div[class*="_rm_"] button { white-space: nowrap !important; }
</style>
""", unsafe_allow_html=True)


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
def _product_images() -> dict[str, str]:
    """barcode -> front-image URL, from a committed JSON sidecar (deploys cleanly)."""
    import json
    path = DATA / "product_images.json"
    return json.loads(path.read_text()) if path.exists() else {}


@st.cache_resource
def _products() -> list[dict]:
    """Every product with additives, with the fields the card and detail view need."""
    images = _product_images()
    rows = _con().execute(
        """SELECT name, barcode, additives_tags, brands, categories,
                  ingredients_text, off_url
           FROM product
           WHERE name IS NOT NULL AND additives_tags <> ''
           ORDER BY name""").fetchall()
    return [{"name": n, "barcode": b, "additives": tags, "brands": br,
             "categories": cat, "ingredients": ing, "off_url": url,
             "image": images.get(b)}
            for n, b, tags, br, cat, ing, url in rows]


@st.cache_resource
def _additive_names() -> dict[str, str]:
    """E-number -> chemical name, for the product detail view."""
    return {e: n for e, n in _con().execute(
        "SELECT e_number, name FROM additives").fetchall()}


def _products_by_barcode() -> dict[str, dict]:
    return {p["barcode"]: p for p in _products()}


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

    st.markdown("## 🔎 Label Lens")
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


def sidebar_summary() -> None:
    """Read-only summary of the profile and pantry. Editing lives in the tabs."""
    con, uid = _con(), _user_id()
    with st.sidebar:
        st.subheader("Your profile")
        prof = memory.get_profile(con, uid) or {"diet": "", "allergies": ""}
        if prof["diet"] or prof["allergies"]:
            st.caption(f"**Diet:** {prof['diet'] or '—'}  \n**Allergies:** {prof['allergies'] or '—'}")
        else:
            st.caption("Not set yet. Add it in the **Profile** tab.")

        pantry = memory.get_log_with_additives(con, uid)
        st.subheader(f"Your pantry ({len(pantry)})")
        if not pantry:
            st.caption("Empty. Add candies in the **Pantry** tab.")
            return
        by_bc = _products_by_barcode()
        for r in pantry:
            p = by_bc.get(r["barcode"], {})
            img = _product_images().get(r["barcode"], "")
            tip = html.escape(
                f"Additives: {_codes(r['additives']) or 'none on file'}\n"
                f"Ingredients: {(p.get('ingredients') or 'not on file')[:300]}")
            thumb = (f'<img src="{img}" style="width:34px;height:34px;object-fit:cover;'
                     'border-radius:6px;flex:0 0 auto">' if img
                     else '<span style="font-size:1.6rem">🍬</span>')
            st.markdown(
                f'<div title="{tip}" style="display:flex;align-items:center;gap:8px;margin:5px 0">'
                f'{thumb}<span style="font-size:0.85rem">{html.escape(r["name"][:26])}</span></div>',
                unsafe_allow_html=True)


def main() -> None:
    if not _password_ok():
        return
    _warm()
    sidebar_summary()
    view = _header()
    if view == "🧺 Pantry":
        render_pantry()
    elif view == "👤 Profile":
        render_profile()
    else:
        render_chat()
    _footer_log()


def _header() -> str:
    """A real header bar pinned to the top of the screen: name+icon on the left,
    the tabs in the middle. The right column is a spacer that keeps the tabs clear
    of Streamlit's own Share button and menu, which the toolbar pins top-right.

    The `key="ll_header"` gives the container an `st-key-ll_header` class that the
    CSS above uses to fix it to the top of the viewport."""
    with st.container(key="ll_header"):
        left, mid, _right = st.columns([3, 4, 2], vertical_alignment="center")
        with left:
            st.markdown(
                "<span style='display:inline-flex;align-items:center;gap:0.4rem;"
                "font-size:1.4rem;font-weight:700;line-height:1;white-space:nowrap;"
                "color:#eaecf2'><span style='font-size:1.2rem;line-height:1'>🔎</span>"
                "Label Lens</span>", unsafe_allow_html=True)
        with mid:
            view = st.segmented_control(
                "view", ["💬 Chat", "🧺 Pantry", "👤 Profile"], default="💬 Chat",
                key="view", label_visibility="collapsed")
    return view or "💬 Chat"


def render_profile() -> None:
    _scroll_to_top()
    con, uid = _con(), _user_id()
    st.subheader("👤 Your profile")
    st.caption("The agent reads this to personalise answers. It still cites every fact.")
    profile = memory.get_profile(con, uid) or {"diet": "", "allergies": ""}
    with st.form("profile"):
        diet = st.text_input("Diet", value=profile["diet"], placeholder="e.g. vegetarian")
        allergies = st.text_input("Allergies", value=profile["allergies"], placeholder="e.g. peanuts")
        if st.form_submit_button("Save profile"):
            memory.set_profile(con, uid, diet=diet, allergies=allergies)
            st.success("Saved.")


def render_chat() -> None:
    st.caption(
        "Ask about a food additive or a product. Answers are cited from regulators "
        "(EU, US FDA, California, IARC), keep legal status, hazard and harm separate, "
        "and never give medical advice."
    )
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Resolve the prompt (a pending chip-click, else freshly typed input).
    # chat_input is always rendered; it pins to the bottom and never drops a click.
    typed = st.chat_input("Ask about an additive or product...")
    prompt = st.session_state.pop("pending", None) or typed

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m["role"] == "assistant":
                _trace_expander(m.get("trace"))

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)
        with st.chat_message("assistant"), st.spinner("Checking the regulators..."):
            try:
                reply, trace = answer_with_trace(prompt, user_id=_user_id())
            except Exception as e:
                reply, trace = f"Something went wrong: {e}", []
            st.markdown(reply)
            _trace_expander(trace)
        st.session_state.messages.append(
            {"role": "assistant", "content": reply, "trace": trace})
        _record_activity(prompt, trace)

    _suggestion_chips()


@st.dialog("Product details", width="large")
def _show_details(p: dict) -> None:
    top = st.columns([1, 2])
    with top[0]:
        if p["image"]:
            st.image(p["image"], use_container_width=True)
        else:
            st.markdown("<div style='font-size:4rem;text-align:center'>🍬</div>",
                        unsafe_allow_html=True)
    with top[1]:
        st.subheader(p["name"])
        if p["brands"]:
            st.caption(f"Brand: {p['brands']}")
        if p["categories"]:
            st.caption(p["categories"].replace("en:", "").replace(",", ", "))

    st.markdown("**Additives**")
    names = _additive_names()
    for t in (p["additives"] or "").split(","):
        e = t.split(":")[-1].upper()
        if e:
            nm = names.get(e)
            st.markdown(f"- **{e}**" + (f" — {nm}" if nm else " — (not in our slice)"))

    if p["ingredients"]:
        st.markdown("**Ingredients**")
        st.write(p["ingredients"])
    if p["off_url"]:
        st.markdown(f"[View on Open Food Facts ↗]({p['off_url']})")


def _scroll_to_top() -> None:
    """Pin the page to the top for a moment after switching tabs. The chat view
    uses a container that briefly scrolls to the bottom during the transition,
    which reads as a jarring jump; this overrides it for ~0.3s."""
    from streamlit.components.v1 import html
    html(
        '<script>const w=window.parent;let n=0;(function f(){'
        '["section[data-testid=\\"stMain\\"]","[data-testid=\\"stAppScrollToBottomContainer\\"]"]'
        '.forEach(s=>{const c=w.document.querySelector(s);if(c)c.scrollTop=0;});'
        'w.scrollTo(0,0);if(++n<18)requestAnimationFrame(f);})();</script>',
        height=0,
    )


def render_pantry() -> None:
    _scroll_to_top()
    con, uid = _con(), _user_id()
    products = _products()
    in_pantry = _pantry_barcodes(con, uid)

    st.subheader(f"🧺 Your pantry ({len(in_pantry)})")
    mine = [p for p in products if p["barcode"] in in_pantry]
    if mine:
        _product_grid(mine, in_pantry, key_prefix="pantry")
        st.caption("Then open **Chat** and ask: *Across the candy I've logged, is anything banned or restricted anywhere?*")
    else:
        st.caption("Your pantry is empty. Add candies from the catalogue below.")

    st.divider()
    st.subheader("Browse products")
    query = st.text_input("Search", placeholder="Search by name…", label_visibility="collapsed")
    shown = [p for p in products if query.lower() in p["name"].lower()] if query else products
    st.caption(f"{len(shown)} product{'s' if len(shown) != 1 else ''} · click a name for details")
    _product_grid(shown, in_pantry, key_prefix="browse")


def _product_grid(items: list[dict], in_pantry: set[str], *, key_prefix: str,
                  cols: int = 4) -> None:
    con, uid = _con(), _user_id()
    columns = st.columns(cols)
    for i, p in enumerate(items):
        bc = p["barcode"]
        with columns[i % cols], st.container(border=True):
            if p["image"]:
                st.image(p["image"], use_container_width=True)
            else:
                st.markdown(
                    "<div style='height:110px;display:flex;align-items:center;"
                    "justify-content:center;font-size:3rem'>🍬</div>",
                    unsafe_allow_html=True)
            # The product name is a link-style button that opens the detail overlay.
            if st.button(p["name"][:42], key=f"{key_prefix}_info_{bc}",
                         type="tertiary", use_container_width=True):
                _show_details(p)
            if bc in in_pantry:
                if st.button("✕ Remove", key=f"{key_prefix}_rm_{bc}",
                             use_container_width=True):
                    memory.remove_product(con, uid, bc)
                    st.rerun()
            elif st.button("＋ Add", key=f"{key_prefix}_add_{bc}",
                           type="primary", use_container_width=True):
                memory.log_product(con, uid, barcode=bc, name=p["name"])
                st.rerun()


# --- Background activity log ------------------------------------------------
# The agent answers by checking official sources one step at a time. We show the
# real steps it took, in plain English, in two places: a "How it found this
# answer" panel under each reply, and a session-wide log at the foot of the app.
# Both read the same trace, so they show what actually ran.


def _tool_html(step: dict) -> str:
    """The muted "how it was retrieved" line: the tool called and the method.

    Names the exact tool so the tool use is visible, then a plain description of
    the retrieval method (database lookup, RAG search, live API, or none)."""
    how = step.get("how") or ""
    tool, query = step.get("tool"), step.get("query")
    if tool:
        call = f'{tool}("{query}")' if query else tool
        mech = (f'<code style="font-size:0.78rem;color:#c9a86a">{html.escape(call)}'
                f'</code> · {html.escape(how)}')
    elif how:
        mech = html.escape(how)
    else:
        return ""
    return (f'<div style="color:#8a8f98;font-size:0.79rem;line-height:1.4;'
            f'padding-left:1.9rem;margin-top:2px">🔧 {mech}</div>')


def _steps_html(trace: list[dict]) -> str:
    """Render the ordered steps: numbered actions, how it was retrieved (tool),
    plain results, and a why-it-matters note."""
    parts, n = [], 0
    for s in trace:
        if s.get("final"):
            marker = s["icon"]
        else:
            n += 1
            marker = f'<span style="color:#8a8f98">{n}.</span> {s["icon"]}'
        body = "".join(
            f'<div style="color:#c9ccd1;font-size:0.88rem;line-height:1.45;'
            f'padding-left:1.9rem;margin-top:2px">{html.escape(line)}</div>'
            for line in s.get("lines") or [])
        note = ""
        if s.get("note"):
            note = (f'<div style="color:#8a8f98;font-size:0.8rem;font-style:italic;'
                    f'padding-left:1.9rem;margin-top:3px">Why it matters: '
                    f'{html.escape(s["note"])}</div>')
        parts.append(
            f'<div style="margin:0.7rem 0">'
            f'<div style="font-weight:600;font-size:0.94rem">{marker} '
            f'{html.escape(s["title"])}</div>{_tool_html(s)}{body}{note}</div>')
    return "".join(parts)


def _trace_expander(trace: list[dict] | None) -> None:
    """Collapsible "How it found this answer" panel under one assistant reply."""
    if not trace:
        return
    n = sum(1 for s in trace if not s.get("final"))
    label = f"🔍 How it found this answer · {n} step{'s' if n != 1 else ''}"
    with st.expander(label, expanded=False):
        st.caption("Label Lens answers by checking official sources one step at a "
                   "time. Each step below shows what it did, the 🔧 tool it used "
                   "and how it retrieved the information, and what it found:")
        st.markdown(_steps_html(trace), unsafe_allow_html=True)


def _record_activity(question: str, trace: list[dict]) -> None:
    """Append this question's run to the session-wide activity log."""
    st.session_state.setdefault("activity_log", []).append(
        {"time": time.strftime("%H:%M:%S"), "question": question, "trace": trace})


def _footer_log() -> None:
    """The app-wide activity log, at the foot of every tab.

    Shows, newest first, what the app did behind the scenes for each question:
    the sources it checked, what it found, and why each step matters. Same trace
    the per-answer panel shows, accumulated across the session.
    """
    log = st.session_state.get("activity_log", [])
    st.divider()
    title = f"📋 Activity log · {len(log)} question{'s' if len(log) != 1 else ''} this session"
    with st.expander(title, expanded=False):
        st.caption("A plain-language record of what the app did behind the scenes "
                   "for each question you asked.")
        if not log:
            st.caption("Nothing yet. Ask a question in the **Chat** tab and it'll "
                       "show up here.")
            return
        for entry in reversed(log):
            st.markdown(
                f'<div style="margin-top:0.9rem;font-size:0.92rem">'
                f'<span style="color:#8a8f98">{entry["time"]}</span> · '
                f'<strong>{html.escape(entry["question"])}</strong></div>',
                unsafe_allow_html=True)
            st.markdown(_steps_html(entry["trace"]), unsafe_allow_html=True)


def _suggestion_chips() -> None:
    """Show a few starter questions, always. Using one rotates in a fresh one.

    Rendered on every run (never conditional), so a visible chip is always
    instantiated on the run its click is processed: no dropped clicks.
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
