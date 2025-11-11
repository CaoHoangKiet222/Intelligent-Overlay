from typing import List, Optional


def build_answer_prompt(query: str, context_snippets: List[str], tool_result: Optional[str]) -> str:
	ctx = "\n---\n".join(context_snippets[:4])
	tool = f"\nKết quả từ hệ thống backend:\n{tool_result}\n" if tool_result else ""
	return f"""
Bạn là trợ lý CSKH. Trả lời ngắn gọn, có trích dẫn.
Câu hỏi: {query}
{tool}
Đoạn ngữ cảnh:
{ctx}

Yêu cầu:
- Trả lời chính xác theo dữ liệu.
- Cuối câu trả lời, ghi danh sách [#citation_i] tương ứng với các đoạn đã dùng.
"""


