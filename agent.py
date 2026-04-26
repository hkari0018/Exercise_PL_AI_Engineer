"""
Portfolio Agent.
Routes question → selects tool → executes → generates final answer.
"""

import json
import logging
import re
from typing import Any

from google import genai

from tools.sql_tool import SQLQueryTool
from tools.exposure_tool import ExposureCalculatorTool

logger = logging.getLogger(__name__)


TOOL_ROUTER_PROMPT = """You are a routing agent for a portfolio analytics system.
Given a user question, decide which tool to use.

Available tools:
1. sql_query - Use for database queries (counts, lists, aggregations, joins).
2. exposure_calculator - Use ONLY for sector exposure of a portfolio.

Respond ONLY with JSON:
{
  "tool": "sql_query" | "exposure_calculator",
  "reasoning": "<one sentence>",
  "portfolio_name": "<exact name if exposure_calculator else null>"
}
"""


ANSWER_GENERATION_PROMPT = """You are a portfolio analytics assistant.
Generate a clear, concise answer.

Question: {question}
Tool: {tool_name}
Tool Result:
{tool_result}

Answer:
"""


def _parse_router_response(raw: str) -> dict:
    text = raw.strip()
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")
    return json.loads(text.strip())


class PortfolioAgent:
    def __init__(self, conn, client: genai.Client):
        self.conn = conn
        self.client = client
        self.model_name = "gemini-2.5-flash"

        self.sql_tool = SQLQueryTool(conn, client, self.model_name)
        self.exposure_tool = ExposureCalculatorTool(conn)

    # Centralized LLM call (VERY IMPORTANT)
    def _generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        return response.text.strip() if response.text else ""

    def answer_question(self, question: str) -> dict[str, Any]:
        logger.info("Agent received question: %s", question)

        # --- Step 1: Route ---
        try:
            routing_prompt = f"{TOOL_ROUTER_PROMPT}\n\nQuestion: {question}"
            routing_raw = self._generate(routing_prompt)
            route = _parse_router_response(routing_raw)

        except Exception as exc:
            logger.error("Routing error: %s", exc)
            return self._build_response(
                question, "none", {}, error=f"Routing failed: {exc}"
            )

        tool_name = route.get("tool", "sql_query")

        logger.info(
            "Routing decision: tool=%s, reasoning=%s",
            tool_name,
            route.get("reasoning"),
        )

        # --- Step 2: Execute Tool ---
        try:
            if tool_name == "exposure_calculator":
                portfolio_name = route.get("portfolio_name") or self._extract_portfolio_name(question)
                tool_result = self.exposure_tool.run(portfolio_name)
            else:
                tool_result = self.sql_tool.run(question)

        except Exception as exc:
            logger.error("Tool execution error: %s", exc)
            return self._build_response(
                question, tool_name, {}, error=f"Tool execution failed: {exc}"
            )

        # --- Step 3: Generate Answer ---
        answer = self._generate_answer(question, tool_name, tool_result)

        return self._build_response(question, tool_name, tool_result, answer=answer)

    def _generate_answer(self, question: str, tool_name: str, tool_result: dict) -> str:
        if tool_result.get("error"):
            return f"Unable to answer: {tool_result['error']}"

        result_for_prompt = self._summarize_tool_result(tool_result)

        prompt = ANSWER_GENERATION_PROMPT.format(
            question=question,
            tool_name=tool_name,
            tool_result=json.dumps(result_for_prompt, indent=2),
        )

        try:
            return self._generate(prompt)
        except Exception as exc:
            logger.error("Answer generation error: %s", exc)
            return f"Answer generation failed: {exc}"

    def _summarize_tool_result(self, result: dict) -> dict:
        summarized = dict(result)

        if "rows" in summarized and len(summarized["rows"]) > 50:
            summarized["rows"] = summarized["rows"][:50]
            summarized["truncated"] = True

        if "holdings_detail" in summarized:
            del summarized["holdings_detail"]

        return summarized

    @staticmethod
    def _extract_portfolio_name(question: str) -> str:
        known = [
            "Growth Equity Fund",
            "Conservative Income Fund",
            "Tech Innovation Fund",
            "Balanced Portfolio",
            "ESG Sustainable Fund",
            "Small Cap Value Fund",
            "International Equity Fund",
            "Fixed Income Plus",
            "Dividend Aristocrats Fund",
            "Emerging Markets Fund",
            "Total Stock Market Index Fund",
            "Total Bond Market Index Fund",
            "Total International Index Fund",
        ]

        q_lower = question.lower()
        for name in known:
            if name.lower() in q_lower:
                return name

        return ""

    @staticmethod
    def _build_response(
        question: str,
        tool_used: str,
        tool_result: dict,
        answer: str = "",
        error: str = None,
    ) -> dict:
        return {
            "question": question,
            "tool_used": tool_used,
            "tool_result": tool_result,
            "answer": answer or "",
            "error": error,
        }