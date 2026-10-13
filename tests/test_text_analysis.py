"""Transcript parsing on small synthetic transcripts in the two layouts seen in practice."""
import pandas as pd

from src import text_analysis as ta

COLON_LAYOUT = """Cover letter to the exchange
Stock Code: 500696
Moderator: Good day and welcome. I now hand the conference over to Ms. Priya Nair. Over to you.
Priya Nair: Thank you. Growth was strong this quarter.
Corporate Office: Sun House, Mumbai
We expect margins to improve.
Moderator: Thank you. The first question is from the line of Abneesh Roy from Nuvama. Please go ahead.
Abneesh Roy: What drove volume growth?
Priya Nair: Rural demand recovered.
Moderator: The next question is from the line of Percy Panthaki from IIFL. Please go ahead.
Percy Panthaki: Can you comment on pricing?
Priya Nair: Pricing was stable.
"""

NAME_LINE_LAYOUT = """CORPORATE PARTICIPANTS
Salil Parekh
Chief Executive Officer
ANALYSTS
Ankur Rudra
JP Morgan
Moderator
Welcome to the call. I now hand the conference over to Mr. Salil Parekh.
Salil Parekh
Revenue grew in constant currency terms.
Moderator
The first question is from the line of Ankur Rudra from JP Morgan.
Ankur Rudra
How is deal flow?
Salil Parekh
Deal flow is healthy.
"""


def test_colon_layout_roles_and_page_headers():
    t = ta.speaker_turns(COLON_LAYOUT)
    roles = dict(zip(t["speaker"], t["role"]))
    assert roles["Priya Nair"] == "management"
    assert roles["Abneesh Roy"] == "analyst" and roles["Percy Panthaki"] == "analyst"
    assert "Stock Code" not in roles                      # cover letter skipped
    assert "Corporate Office" not in roles               # page header skipped
    first = t[t["speaker"] == "Priya Nair"].iloc[0]["text"]
    assert "margins to improve" in first                 # text after the header stays with the speaker
    assert ta.usable(t)


def test_name_line_layout():
    t = ta.speaker_turns(NAME_LINE_LAYOUT)
    roles = dict(zip(t["speaker"], t["role"]))
    assert roles == {"Moderator": "moderator", "Salil Parekh": "management", "Ankur Rudra": "analyst"}


def test_unusable_without_analysts():
    t = ta.speaker_turns("Modarcdor: garbled\nRohlUcawa: text\nRohlUcawa: more")
    assert not ta.usable(t)


def test_majority_vote_fixes_a_one_off_mistake():
    good = pd.DataFrame({"speaker": ["CFO", "Analyst"], "role": ["management", "analyst"], "text": ["a", "b"]})
    bad = pd.DataFrame({"speaker": ["CFO", "Analyst"], "role": ["analyst", "analyst"], "text": ["a", "b"]})
    fixed = ta.harmonise_roles([good, good, bad])
    assert fixed[2].set_index("speaker").loc["CFO", "role"] == "management"


def test_sentences_and_hedging():
    s = ta.sentences("We may see some volatility. Ok. Demand could recover next year if rates fall.")
    assert s == ["Demand could recover next year if rates fall."]   # short fragments dropped
    assert ta.hedge_share("We may see volatility") == 0.5
