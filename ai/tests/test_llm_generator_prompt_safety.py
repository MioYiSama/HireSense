import asyncio

from app.services.llm_generator import Clarify, LLMGenerator, TacticalDecision


def test_decide_tactics_and_generate_allows_braces_in_dynamic_text():
    llm_gen = LLMGenerator(llm=object(), fast_llm=object())

    async def fake_retry(prompt_template, input_data, model_class, llm, max_retries=3):
        prompt_value = await prompt_template.ainvoke(input_data)
        rendered = prompt_value.to_string()

        assert "{dangerous: true}" in rendered
        assert "history { payload }" in rendered
        assert "fact {sheet}" in rendered

        return TacticalDecision(
            reasoning="ok",
            action="PROBE",
            selected_node=None,
            reply_speech="继续说说",
            q_id_and_brief=None,
        )

    llm_gen._retry_structured_generation = fake_retry

    result = asyncio.run(
        llm_gen.decide_tactics_and_generate(
            current_topic="Python",
            question_brief="解释字典实现",
            std_answer="哈希表",
            cumulative_answer="我会先看 {dangerous: true}",
            mastery_score=42.0,
            completed_rounds=1,
            current_turn=1,
            max_turn=3,
            menu=[],
            history="history { payload }",
            candidate_fact_sheet=["fact {sheet}"],
            resume_star="做过编译器项目",
        )
    )

    assert result.action == "PROBE"
    assert result.reply_speech == "继续说说"


def test_clarify_question_allows_braces_in_user_text():
    llm_gen = LLMGenerator(llm=object(), fast_llm=object())

    async def fake_retry(prompt_template, input_data, model_class, llm, max_retries=3):
        prompt_value = await prompt_template.ainvoke(input_data)
        rendered = prompt_value.to_string()

        assert "最近历史 { clarifying }" in rendered
        assert "用户输入里有 {" in rendered

        return Clarify(reply_speech="我换个说法解释一下")

    llm_gen._retry_structured_generation = fake_retry

    result = asyncio.run(
        llm_gen.clarify_question(
            user_text="用户输入里有 {，想确认题目边界",
            current_topic="Redis",
            question_brief="解释持久化机制",
            std_answer="RDB 和 AOF",
            history="最近历史 { clarifying }",
        )
    )

    assert result.reply_speech == "我换个说法解释一下"
