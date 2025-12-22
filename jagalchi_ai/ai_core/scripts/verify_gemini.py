import os

from jagalchi_ai.ai_core.clients.gemini_client import GeminiClient


def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY 환경 변수가 필요합니다.")

    client = GeminiClient(api_key=api_key, model="gemini-2.5-flash")
    response = client.generate_text("Explain how AI works in a few words")
    print(response)


if __name__ == "__main__":
    main()
