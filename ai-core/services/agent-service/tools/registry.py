from typing import Dict, Any, Callable, Awaitable
from .http_tools import get_order_status, get_refund_policy

ToolFn = Callable[..., Awaitable[Dict[str, Any]]]

REGISTRY: Dict[str, ToolFn] = {
	"get_order_status": get_order_status,
	"get_refund_policy": get_refund_policy,
}


