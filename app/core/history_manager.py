#局部工作记忆 (Local Probing History)：当前题目的拉扯记录（原文，极短）。作用：找茬、给 Hint。
#全局动态摘要 (Global Fact-Sheet)：这是真正的“全局历史”。它不是原文，而是经过后台小模型提纯出的事实标签。 在评分时输出

#import tiktoken
from typing import List
from app.models.schemas import AgentState, ChatMessage

class HistoryManager:
    def __init__(self, max_token_num : int = 1500):
        #self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.max_token_num = max_token_num


    # 对chat_history: List[ChatMessage]的处理 添加历史记录
    @staticmethod
    def add_messages(state : AgentState, content : str, role : str, concept : str):
        num_len = len(content)
        msg = ChatMessage(role = role, content = content, concept = concept, num_token = num_len)
        state.chat_history.append(msg)

    # 对recent_messages的管理 最近几期的回答(如果concept相同，则一定提取，若concept更换，则只提取1000tokens）在更换当前concept前执行
    def add_track_memory(self, state : AgentState):
        recent_messages = []
        current_concept = state.current_concept
        current_num_token = 0

        for msg in reversed(state.chat_history):

            if msg.concept == current_concept:
                recent_messages.insert(0,msg)
                current_num_token += len(msg.content)
                continue

            else :
                if current_num_token >= self.max_token_num:
                    break

                recent_messages.insert(0,msg)
                current_num_token += len(msg.content)

        state.recent_messages = self._format_messages(recent_messages)

    def _format_messages(self, messages: List[ChatMessage]) -> str :
        if not messages:
            return "无历史记录"

        return "\n".join([f"[{m.role}]: {m.content}" for m in messages])

    # 添加问题id
    def q_id_add(self, state : AgentState, q_id : str, question_brief):
        state.q_id_list.append([q_id,question_brief])

    def q_id_get(self, state : AgentState):
        if not state.q_id_list:
            raise ValueError("q_id_list is empty")

        last_item = state.q_id_list[-1]
        if not isinstance(last_item, list) or len(last_item) < 2:
            raise ValueError(f"Invalid q_id_list item format: {last_item}")

        q_id = last_item[0]
        q_brief = last_item[1]
        return q_id, q_brief

