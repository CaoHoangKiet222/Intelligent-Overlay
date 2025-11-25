from typing import List


def build_planner_prompt(query: str, context_snippets: List[str], allow_external: bool = True) -> str:
	ctx = "\n---\n".join(context_snippets[:3])
	tool_section = """
- Nếu cần gọi tool:
  - Trạng thái đơn hàng: {"intent":"tool","tool":"get_order_status","args":{"order_id":"..."}}
  - Chính sách hoàn tiền: {"intent":"tool","tool":"get_refund_policy","args":{}}
""" if allow_external else "\n- Không được đề xuất gọi tool; chỉ trả lời dạng {\"intent\":\"qa_only\"}."
	return f"""
Bạn là planner cho bot CSKH. Người dùng hỏi: `{query}`.
Ngữ cảnh liên quan:
{ctx}

Hãy trả lời dưới dạng JSON duy nhất, không thêm chữ:
- Nếu chỉ cần trả lời Q&A từ ngữ cảnh: {{"intent":"qa_only"}}
{tool_section}
"""


