from typing import List, Optional


def build_answer_prompt(query: str, context_snippets: List[str], tool_result: Optional[str], allow_external: bool = True) -> str:
	ctx = "\n---\n".join(context_snippets[:4])
	tool = f"\nKết quả từ hệ thống backend:\n{tool_result}\n" if tool_result else ""
	instructions = [
		"Trả lời chính xác và súc tích.",
		"Luôn kèm theo [#citation_i] ứng với đoạn đã dùng.",
	]
	if not allow_external:
		instructions.append("Chỉ sử dụng thông tin trong ngữ cảnh trên; nếu không đủ dữ liệu hãy trả lời 'Xin lỗi, tôi không đủ thông tin trong ngữ cảnh hiện có.'")
	else:
		instructions.append("Nếu cần thiết có thể sử dụng dữ liệu bổ sung từ công cụ đã gọi.")
	return f"""
Bạn là trợ lý CSKH.
Câu hỏi: {query}
{tool}
Đoạn ngữ cảnh:
{ctx}

Yêu cầu:
- {' '.join(instructions)}
"""


