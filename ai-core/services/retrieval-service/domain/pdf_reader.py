from typing import List
import fitz


def extract_pdf_text(pdf_bytes: bytes) -> str:
	doc = fitz.open(stream=pdf_bytes, filetype="pdf")
	texts: List[str] = []
	for page in doc:
		texts.append(page.get_text("text"))
	return "\n".join(texts)


