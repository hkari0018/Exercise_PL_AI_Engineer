"""
Command-line interface for the Portfolio Analytics Agent.
Usage:
    python main.py
    python main.py --question "How many portfolios do we have?"
    python main.py --debug
"""

import argparse
import json
import logging
import os
import sys

from dotenv import load_dotenv
from google import genai

from database import build_database
from agent import PortfolioAgent


def configure_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=level,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                os.path.join(os.path.dirname(__file__), "logs", "agent.log"),
                mode="a",
                encoding="utf-8",
            ),
        ],
    )


def print_result(result: dict) -> None:
    print()
    print("=" * 70)
    print(f"Question : {result['question']}")
    print(f"Tool used: {result['tool_used']}")

    if result.get("error"):
        print(f"Error    : {result['error']}")
    else:
        print()
        print("Answer:")
        print(result["answer"])

        # Show SQL if applicable
        tool_result = result.get("tool_result", {})
        if result["tool_used"] == "sql_query" and tool_result.get("sql"):
            print()
            print(f"SQL executed: {tool_result['sql']}")
            print(f"Rows returned: {tool_result.get('row_count', 0)}")

        # Show sector exposures if applicable
        if result["tool_used"] == "exposure_calculator":
            exposures = tool_result.get("sector_exposures", {})
            if exposures:
                print()
                print("Sector exposures (equity-only):")
                for sector, pct in exposures.items():
                    print(f"  {sector:<30} {pct:>6.2f}%")

    print("=" * 70)
    print()


def run_interactive(agent: PortfolioAgent) -> None:
    print()
    print("Portfolio Analytics Agent")
    print("Type your question and press Enter. Type 'exit' or 'quit' to stop.")
    print()

    while True:
        try:
            question = input("Question> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not question:
            continue
        if question.lower() in ("exit", "quit", "q"):
            print("Exiting.")
            break

        result = agent.answer_question(question)
        print_result(result)


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Portfolio Analytics Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py\n"
            "  python main.py --question 'How many portfolios do we have?'\n"
            "  python main.py --question 'What are sector exposures for Tech Innovation Fund?'\n"
            "  python main.py --debug\n"
        ),
    )
    parser.add_argument(
        "--question",
        type=str,
        default=None,
        help="Ask a single question and exit.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Enable debug logging.",
    )
    args = parser.parse_args()

    configure_logging(debug=args.debug)
    logger = logging.getLogger(__name__)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print(
            "Error: GEMINI_API_KEY environment variable is not set.\n"
            "Create a .env file with: GEMINI_API_KEY=your_key_here\n"
            "Get a key at: https://ai.google.dev/gemini-api/docs"
        )
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-pro")

    logger.info("Building in-memory database...")
    conn = build_database()

    agent = PortfolioAgent(conn, model)

    if args.question:
        result = agent.answer_question(args.question)
        print_result(result)
    else:
        run_interactive(agent)


if __name__ == "__main__":
    main()