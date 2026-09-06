"""查询参数校验与默认值准备节点。"""

from processor.query_processor.base import NodeBase
from processor.query_processor.state import QueryGraphState


class NodePrepareQuery(NodeBase):
    """校验问题和知识库，并关闭高成本检索增强的默认开关。"""

    name = "node_prepare_query"

    def process(self, state: QueryGraphState) -> QueryGraphState:
        query = str(state.get("original_query") or "").strip()
        library_id = state.get("library_id")
        if not query:
            state["answer"] = "请输入要查询的问题。"
        elif not isinstance(library_id, int) or library_id <= 0:
            state["answer"] = "请选择有效的知识库后再进行查询。"
        state["rewritten_query"] = query
        state["item_names"] = list(state.get("item_names") or [])
        state["history"] = list(state.get("history") or [])
        state["session_id"] = str(state.get("session_id") or "query-session")
        state["is_stream"] = bool(state.get("is_stream", False))
        state["use_hyde"] = bool(state.get("use_hyde", False))
        state["use_web_search"] = bool(state.get("use_web_search", False))
        state["retrieval_top_k"] = int(state.get("retrieval_top_k") or 20)
        state["top_k"] = int(state.get("top_k") or 5)
        return state
