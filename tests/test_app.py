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


def test_example_chips_do_not_linger_after_answering():
    """Regression: chips rendered before the answer was appended lingered one
    render, then swallowed the next click and re-showed the old Q&A."""
    at = AppTest.from_file(APP).run(timeout=30)
    at.button(key="ex0").click().run(timeout=30)
    assert not at.exception
    # Once a question is answered, the starter chips must be gone, so a later
    # click cannot land on a stale button whose handler no longer runs.
    assert EX0 not in [b.label for b in at.button]
