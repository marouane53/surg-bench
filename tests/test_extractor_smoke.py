from pathlib import Path
from src.evalsys.pdf_extractor import extract

def test_extract_first_page_smoke():
    pdf = "data/surgical.pdf"
    if not Path(pdf).exists():
        return
    items = extract(pdf, out_dir="data/out_test", images_dir="data/out_test/images")
    assert len(items) > 0
    assert items[0].qid.startswith("Q")
