import math
import numpy as np
from sentence_transformers import CrossEncoder
from app.core.config import BGE_RERANKER, NLI

class Evaluator:
    def __init__(self, sts_model, nli_model):
        # 语义覆盖率打分模型
        self.sts_model = sts_model

        # 逻辑诊断模型 (NLI)
        self.nli_model = nli_model

    def _parse_nli_logits(self, logits: np.ndarray) -> dict:
        """
        处理 NLI 模型的原始输出 (Logits)，转化为概率分布
        """
        # Softmax 归一化 (减去最大值防止指数爆炸溢出)
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / np.sum(exp_logits)

        # ：此处的 Index 映射必须严格对齐 MoritzLaurer/mDeBERTa 模型的 config.json
        # 0: entailment (蕴含/一致), 1: neutral (中立/无关), 2: contradiction (矛盾/对立)
        return {
            "Entailment": float(probs[0]),
            "Neutral": float(probs[1]),
            "Contradiction": float(probs[2])
        }

    def evaluate_mastery(self, user_answer: str, standard_answer: str) -> dict:
        """
        综合评估候选人的知识掌握度
        """
        # 防御性编程：处理用户沉默或极短回答
        if not user_answer or len(user_answer.strip()) < 2:
            return {
                "mastery_score": 0.0,
                "coverage_raw": 0.0,
                "logic_status": "Neutral",
                "nli_probs": {"Entailment": 0.0, "Neutral": 1.0, "Contradiction": 0.0}
            }

        # --------------------------------------------------
        # Step 1: 测算知识点覆盖率 (STS)
        # --------------------------------------------------
        sts_logits = self.sts_model.predict([[standard_answer, user_answer]])[0]
        # BGE 模型的输出是未归一化的 logit，使用 Sigmoid 映射到 0.0 ~ 1.0
        coverage = 1 / (1 + math.exp(-sts_logits))

        # --------------------------------------------------
        # Step 2: 逻辑诊断 (NLI)
        # --------------------------------------------------
        nli_logits = self.nli_model.predict([[user_answer, standard_answer]])[0]
        nli_probs = self._parse_nli_logits(nli_logits)

        Pe = nli_probs["Entailment"]
        Pn = nli_probs["Neutral"]
        Pc = nli_probs["Contradiction"]

        # 提取占据主导地位的逻辑状态
        logic_status = max(nli_probs, key=nli_probs.get)

        # --------------------------------------------------
        # Step 3: 融合计算真实掌握度 (True Mastery Score)
        # --------------------------------------------------
        # 【融合公式设计原则】：
        # 1. 逻辑一致 (Pe)：完美继承覆盖率
        # 2. 逻辑中立/废话 (Pn)：对覆盖率打折 (0.8)，防止瞎猫碰死耗子
        # 3. 逻辑矛盾 (Pc)：实施断崖式惩罚 (扣除 1.5 倍权重)
        logic_multiplier = (Pe * 1.0) + (Pn * 0.8) - (Pc * 1.5)

        # 计算基础得分并裁剪到 0~1 范围
        m_score = coverage * logic_multiplier
        m_score = max(0.0, min(1.0, m_score))

        return {
            "mastery_score": round(m_score * 100, 2),  # 综合掌握度 (0~100)
            "coverage_raw": round(coverage * 100, 2),  # 原始覆盖率 (0~100)
            "logic_status": logic_status,  # 主导逻辑状态
            "nli_probs": nli_probs  # 全量概率分布，供外层精细控制
        }


from typing import Tuple


class PruningStrategy:
    """
    图谱剪枝配额策略引擎
    职责：根据底层诊断的掌握度 (m_score) 和逻辑状态 (l_status)，
    动态分配下一次图谱查询中 [深挖(Forward), 平移(Sibling), 降级(Backward)] 的节点名额限制。
    """

    @staticmethod
    def calculate_quota(mastery_score: float, logic_status: str) -> Tuple[int, int, int]:
        """
        返回格式: (limit_fwd, limit_sib, limit_bwd)
        """
        # ==========================================
        # 优先级 1：一票否决（逻辑刺客 / 严重反常识）
        # ==========================================
        if logic_status == "Contradiction":
            # 表现：不仅不会，还在胡编乱造。
            # 策略：绝对禁止深挖 (0)，给一个平移机会试探 (1)，重点给出降级回溯节点 (3)
            return 0, 1, 3

        # ==========================================
        # 优先级 2：分数硬切分（根据真实掌握度）
        # ==========================================
        if mastery_score >= 80:
            # 碾压局 (学霸模式)
            # 表现：核心词汇全中，逻辑顺畅。
            # 策略：重点给进阶深挖题 (3)，少量平移侧写 (1)，绝对不给降级基础题 (0)
            return 3, 1, 0

        elif mastery_score < 40:
            # 崩溃局 (逃兵/基础极差)
            # 表现：没踩中任何得分点。
            # 策略：停止深挖 (0)，给平移台阶 (1)，重点降级回溯 (3)
            return 0, 1, 3

        else:
            # 僵持局 (半懂不懂 / 挤牙膏区)
            # 表现：40 ~ 79 分。说对了一部分，或者说了一堆正确的废话。
            # 策略：各给一点选择。重点放在平移侧探 (2)，轻微保留深挖 (1) 和降级 (1) 的可能性。
            # 此时大模型 (LLM) 拿到的菜单最丰富，它将结合对话历史自主决定该上还是该下。
            return 1, 2, 1



if __name__ == "__main__":
    # 测试时可以设为 cpu，有 NVIDIA 显卡请改为 cuda 以获得极致速度
    evaluator = Evaluator(device="cpu")

    std_ans = "HashMap 是线程不安全的。在多线程环境下，建议使用 ConcurrentHashMap 来保证线程安全。"

    # 模拟场景 1：学霸 (完美命中)
    ans_1 = "HashMap 不能在多线程里用，不安全，得换成 ConcurrentHashMap。"

    # 模拟场景 2：废话流 (覆盖率低)
    ans_2 = "HashMap 底层是数组和链表，我平时经常用它来存键值对。"

    # 模拟场景 3：逻辑刺客 (因果倒置，命中关键词但逻辑全错)
    ans_3 = "HashMap 绝对是线程安全的，它里面加了锁，多线程随便用。"

    print("--- 测试场景 1 (学霸) ---")
    print(evaluator.evaluate_mastery(ans_1, std_ans))

    print("\n--- 测试场景 2 (废话/没答到点子上) ---")
    print(evaluator.evaluate_mastery(ans_2, std_ans))

    print("\n--- 测试场景 3 (逻辑刺客) ---")
    print(evaluator.evaluate_mastery(ans_3, std_ans))

    user_ans = "A一定要B"
    stand_ans = "A不一定要B"
    print(evaluator.evaluate_mastery(stand_ans,user_ans))