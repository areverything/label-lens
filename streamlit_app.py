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
    for _k in ("OPENROUTER_API_KEY", "OPENROUTER_MODEL", "LANGSMITH_API_KEY",
               "SHOW_ACTIVITY_LOG"):
        if _k in st.secrets and not os.getenv(_k):
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass

from label_lens.agent import memory  # noqa: E402
from label_lens.agent.graph import answer_with_trace  # noqa: E402
from label_lens.agent.trace import agent_info as graph_agent_info  # noqa: E402
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
/* Make the logo's paragraph its own full-height flex box so the name+icon are
   centred on the bar's centre line, not left sitting on the text baseline (the
   emoji's ascent/descent otherwise drags the whole logo below the tabs). */
.st-key-ll_header .stMarkdown p {
  margin: 0; line-height: 1;
  height: 100%; display: flex; align-items: center;
}

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

/* Phones: the header's columns stack, and a fixed, fixed-height bar can't hold
   the stacked logo + tab rows, so the tabs spilled over and painted on top of
   the chat. On narrow screens let the header flow with the page (static, natural
   height): the logo sits on one row, the tabs centre on the next, and nothing
   overlaps. The desktop rules above still apply on wider screens. */
@media (max-width: 640px) {
  /* Keep the bar pinned, but let it grow to two rows (logo, then tabs) instead of
     forcing everything onto one 3.75rem line that the columns overflowed. */
  .st-key-ll_header {
    height: auto !important;
    min-height: 5.75rem;
    display: block !important;
    padding: 0.35rem 1rem 0.55rem !important;
  }
  /* Undo the full-height flex-centering chain so the two rows size to content. */
  .st-key-ll_header > div,
  .st-key-ll_header [data-testid="stHorizontalBlock"],
  .st-key-ll_header [data-testid="stColumn"],
  .st-key-ll_header [data-testid="stElementContainer"],
  .st-key-ll_header [data-testid="stButtonGroup"],
  .st-key-ll_header [data-testid="stMarkdown"],
  .st-key-ll_header [data-testid="stMarkdown"] > div,
  .st-key-ll_header [data-testid="stMarkdownContainer"] { height: auto !important; }
  .st-key-ll_header .stMarkdown p { height: auto !important; }
  /* Drop the desktop right-hand spacer column (it reserved room for Streamlit's
     Share button, which collapses to a compact menu on phones) and centre the
     tab row under the logo. */
  .st-key-ll_header [data-testid="stColumn"]:last-child { display: none !important; }
  .st-key-ll_header [data-testid="stButtonGroup"] { justify-content: center !important; }
  /* Match the content offset and sidebar to the taller two-row bar. */
  [data-testid="stMainBlockContainer"], .block-container { padding-top: 6.5rem !important; }
  [data-testid="stSidebar"] { margin-top: 5.75rem; }
  /* Park the collapsed-sidebar chevron in the header's tab row (dark bar, left of
     the centred tabs) so it stops floating over the caption text below. */
  [data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] {
    top: 3.4rem !important; left: 0.6rem !important;
  }
}
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

    # Streamlit's chat container auto-scrolls to the bottom to keep the newest
    # message in view. On the empty initial screen that just tucks the top of the
    # page (the intro caption) under the fixed header, especially on mobile. While
    # there are no messages, hold the scroll at the top; once a conversation
    # exists we leave it alone so new replies stay visible.
    if not st.session_state.messages:
        _pin_scroll_top()

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


def _pin_scroll_top() -> None:
    """Hold the chat container at the top for ~1.2s, beating Streamlit's
    auto-scroll-to-bottom on the empty initial view. A one-shot reset loses that
    race, so this listens for the scroll and forces it back to 0, then detaches so
    it never fights the user's own scrolling."""
    from streamlit.components.v1 import html
    html(
        '<script>(function(){const d=window.parent.document;'
        'const sel="[data-testid=\\"stAppScrollToBottomContainer\\"]";'
        'const pin=()=>{const c=d.querySelector(sel);if(c)c.scrollTop=0;'
        'window.parent.scrollTo(0,0);};'
        'const c=d.querySelector(sel);if(!c)return;'
        'c.addEventListener("scroll",pin);pin();'
        'setTimeout(()=>c.removeEventListener("scroll",pin),1200);})();</script>',
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


# One text size for every sans line in the log; only code (the function call and
# the exact query) uses monospace, set off by a subtle background chip. Colours
# inherit the theme's text colour and use opacity for muting, so the log reads in
# both light and dark themes (the viewer chooses).
_TXT = "font-size:0.9rem;line-height:1.5"
_MONO = ("font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:0.82rem;"
         "background:rgba(128,128,128,0.15);border-radius:3px;padding:0 4px")


def _agent_header() -> str:
    """One-time reviewer banner naming the agent framework and the model."""
    info = graph_agent_info()
    return (
        f'<div style="{_TXT};margin:2px 0 10px;padding:8px 11px;'
        'border-left:2px solid rgba(128,128,128,0.5);background:rgba(128,128,128,0.08);'
        'border-radius:4px">'
        f'<strong>Agent:</strong> {html.escape(info["framework"])} · '
        f'<strong>Model:</strong> <code style="{_MONO}">'
        f'{html.escape(info["model"])}</code>'
        f'<br><span style="opacity:0.75">{html.escape(info["note"])}</span></div>'
    )


def _val(text: str) -> str:
    """One value line under a subsection label (inherits the theme text colour)."""
    return f'<div style="{_TXT};padding-left:0.9rem">{html.escape(text)}</div>'


def _labeled(label: str, value_html: str) -> str:
    """A subsection: a muted bold label with its value(s) beneath."""
    return (f'<div style="margin-top:7px">'
            f'<div style="{_TXT};font-weight:600;opacity:0.6">{label}</div>'
            f'{value_html}</div>')


def _tech_value_html(step: dict) -> str:
    """Value for the "Tool and technique used" subsection: the tool call and the
    technique on one line, the exact call (monospace) beneath."""
    t = step.get("tech") or {}
    technique, call = t.get("technique", ""), t.get("call", "")
    tool, query = step.get("tool"), step.get("query")
    if tool:
        label = f'{tool}("{query}")' if query else tool
        head = f'<code style="{_MONO}">{html.escape(label)}</code>'
        if technique:
            head += f' <span style="opacity:0.8">· {html.escape(technique)}</span>'
    else:
        head = f'<span style="opacity:0.8">{html.escape(technique)}</span>'
    out = f'<div style="{_TXT};padding-left:0.9rem">{head}'
    if call:
        out += (f'<div style="{_MONO};word-break:break-word;line-height:1.7;'
                f'display:inline-block;margin-top:3px">↳ {html.escape(call)}</div>')
    return out + '</div>'


def _steps_html(trace: list[dict]) -> str:
    """Render each step as labelled subsections: What it did / What it found /
    Why it matters / Tool and technique used. No emojis; one consistent font;
    colours inherit the theme so it reads in light and dark."""
    parts, n = [], 0
    for s in trace:
        if s.get("final"):
            marker = "Answer"
            found: list[str] = []
            why = s.get("lines") or []          # the closing cited/safety lines
        else:
            n += 1
            marker = f"Step {n}"
            found = s.get("lines") or []
            why = [s["note"]] if s.get("note") else []
        seg = [f'<div style="{_TXT};font-weight:700;opacity:0.8">{marker}</div>']
        seg.append(_labeled("What it did", _val(s["title"])))
        if found:
            seg.append(_labeled("What it found", "".join(_val(x) for x in found)))
        if why:
            seg.append(_labeled("Why it matters", "".join(_val(x) for x in why)))
        if s.get("tool") or (s.get("tech") or {}).get("technique"):
            seg.append(_labeled("Tool and technique used", _tech_value_html(s)))
        parts.append(f'<div style="margin:1rem 0 0.3rem">{"".join(seg)}</div>')
    return "".join(parts)


def _trace_expander(trace: list[dict] | None) -> None:
    """Collapsible "How it found this answer" panel under one assistant reply."""
    if not trace:
        return
    n = sum(1 for s in trace if not s.get("final"))
    label = f"How it found this answer · {n} step{'s' if n != 1 else ''}"
    with st.expander(label, expanded=False):
        st.markdown(_agent_header(), unsafe_allow_html=True)
        st.markdown(_steps_html(trace), unsafe_allow_html=True)


def _record_activity(question: str, trace: list[dict]) -> None:
    """Append this question's run to the session-wide activity log."""
    st.session_state.setdefault("activity_log", []).append(
        {"time": time.strftime("%H:%M:%S"), "question": question, "trace": trace})


def _activity_log_enabled() -> bool:
    """The chat-wide activity log renders only when SHOW_ACTIVITY_LOG is truthy.

    It is a reviewer / debugging aid, not part of the shopper UI, so it stays off
    by default. Set SHOW_ACTIVITY_LOG=1 (env var locally, or a Streamlit secret in
    the cloud). The per-answer "How it found this answer" panel is unaffected.
    """
    return os.getenv("SHOW_ACTIVITY_LOG", "").strip().lower() in {"1", "true", "yes", "on"}


def _footer_log() -> None:
    """The app-wide activity log, at the foot of every tab.

    Shows, newest first, what the app did behind the scenes for each question:
    the sources it checked, what it found, and why each step matters. Same trace
    the per-answer panel shows, accumulated across the session. Gated behind
    SHOW_ACTIVITY_LOG so it does not show for shoppers by default.
    """
    if not _activity_log_enabled():
        return
    log = st.session_state.get("activity_log", [])
    st.divider()
    title = f"Activity log · {len(log)} question{'s' if len(log) != 1 else ''} this session"
    with st.expander(title, expanded=False):
        if not log:
            st.caption("Nothing yet. Ask a question in the **Chat** tab and it'll "
                       "show up here.")
            return
        st.markdown(_agent_header(), unsafe_allow_html=True)
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
