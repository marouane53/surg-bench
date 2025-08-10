from src.evalsys.prompting import pack_messages_for_question
from src.evalsys.dataset import QAItem

def test_pack_messages():
    it = QAItem(qid="Q1.1", chapter="General", page_start=1, page_end=2,
                question_text="Dx and next step?", sub_questions=[], images=[], answer_text="Antibiotics, drainage")
    msg = pack_messages_for_question(it)
    assert msg["messages"][0]["role"] == "system"
    assert msg["messages"][1]["role"] == "user"
