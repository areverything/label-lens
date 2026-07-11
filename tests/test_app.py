"""Drive the Streamlit UI headlessly with AppTest: profile, product log, chat.

The agent's answer() is stubbed so these tests exercise the UI wiring (widgets,
memory writes, chat rendering) without a live LLM call.
"""
from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

import label_lens.agent.graph as graph

APP = "streamlit_app.py"
CANNED = "E171 is banned in the EU [Reg (EU) 2022/63]."


@pytest.fixture(autouse=True)
def _stub_answer(monkeypatch):
    # streamlit_app does `from ...graph import answer`; AppTest re-runs that import
    # each run, so patching the source binds the stub into the app namespace.
    monkeypatch.setattr(graph, "answer", lambda q, **kw: CANNED)


def test_app_renders_title_and_examples():
    at = AppTest.from_file(APP).run(timeout=30)
    assert not at.exception
    assert any("Label Lens" in t.value for t in at.title)
    assert len(at.button) >= 4  # the example-question buttons


def test_saving_profile_persists_to_memory():
    at = AppTest.from_file(APP).run(timeout=30)
    # Fill the profile form and submit (form-submit buttons live in at.button).
    at.text_input[0].set_value("vegetarian")
    at.text_input[1].set_value("peanuts")
    save = next(b for b in at.button if b.label == "Save profile")
    save.click().run(timeout=30)
    assert not at.exception

    # The same session id should now read back the saved profile.
    from label_lens.agent import memory
    from label_lens.agent.tools import _con
    uid = at.session_state["user_id"]
    profile = memory.get_profile(_con(), uid)
    assert profile["diet"] == "vegetarian"
    assert profile["allergies"] == "peanuts"


def test_chat_input_produces_a_cited_answer():
    at = AppTest.from_file(APP).run(timeout=30)
    at.chat_input[0].set_value("Is E171 banned in the EU?").run(timeout=30)
    assert not at.exception
    replies = [m.value for m in at.chat_message if CANNED in getattr(m, "value", "")]
    # The assistant markdown should carry the (stubbed) cited answer.
    assert any(CANNED in md.value for md in at.markdown)


EX0 = "Is E171 (titanium dioxide) banned in the EU?"


def test_clicking_an_example_chip_answers_that_question():
    at = AppTest.from_file(APP).run(timeout=30)
    assert EX0 in [b.label for b in at.button]  # chip shown on the empty state
    at.button(key="ex0").click().run(timeout=30)
    assert not at.exception
    assert at.session_state["messages"][0] == {"role": "user", "content": EX0}
    assert any(CANNED in md.value for md in at.markdown)


def test_password_gate_blocks_until_correct():
    at = AppTest.from_file(APP)
    at.secrets["APP_PASSWORD"] = "s3cret"
    at.run(timeout=30)
    assert not at.exception
    # Gated: the chat input is not rendered, so nothing can call the model.
    assert len(at.chat_input) == 0

    # Wrong password stays gated.
    at.text_input[0].set_value("nope")
    next(b for b in at.button if b.label == "Enter").click().run(timeout=30)
    assert len(at.chat_input) == 0

    # Correct password unlocks the app.
    at.text_input[0].set_value("s3cret")
    next(b for b in at.button if b.label == "Enter").click().run(timeout=30)
    assert len(at.chat_input) == 1


def test_no_password_secret_leaves_app_open():
    at = AppTest.from_file(APP).run(timeout=30)  # no APP_PASSWORD set
    assert not at.exception
    assert len(at.chat_input) == 1  # open, chat available


def test_pantry_add_and_remove_a_product():
    from label_lens.agent import memory
    from label_lens.agent.tools import _con
    SKITTLES = "0072392328307"  # a real product with additives + image

    at = AppTest.from_file(APP)
    at.session_state["view"] = "🧺 Pantry"
    at.run(timeout=60)
    assert not at.exception
    uid = at.session_state["user_id"]
    con = _con()

    at.button(key=f"browse_add_{SKITTLES}").click().run(timeout=60)
    assert SKITTLES in {r["barcode"] for r in memory.get_log(con, uid)}

    at.button(key=f"browse_rm_{SKITTLES}").click().run(timeout=60)
    assert SKITTLES not in {r["barcode"] for r in memory.get_log(con, uid)}


def _chips(at):
    """The suggestion-chip labels (excluding the sidebar and login buttons)."""
    other = {"Save profile", "Log product", "Enter"}
    return [b.label for b in at.button if b.label not in other]


def test_example_chips_persist_and_rotate_after_use():
    """Chips stay visible after answering, and a used one is replaced by a fresh
    one (the click is never dropped because the chip block always renders)."""
    at = AppTest.from_file(APP).run(timeout=30)
    before = _chips(at)
    assert EX0 in before
    n = len(before)

    at.button(key="ex0").click().run(timeout=30)
    assert not at.exception
    after = _chips(at)
    assert len(after) == n          # row stays full: a fresh chip rotated in
    assert EX0 not in after         # the used chip is gone
    assert set(after) - set(before) # at least one new question appeared
