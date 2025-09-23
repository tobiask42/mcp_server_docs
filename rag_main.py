from loguru import logger
from definitions.custom_enums import ExitCode, CtxKeys
from rag.qa import answer_question
from textwrap import shorten

def main() -> ExitCode:
    logger.add("rag.log")
    try:
        question: str = input("How can I help you?\n")
        ans, used = answer_question(question=question)
        print("\n=== ANSWER ===\n")
        print(ans)
        print("\n=== SOURCES USED ===")
        for i, it in enumerate(used, 1):
            print(f"[{i}] {shorten(it[CtxKeys.URL.value], width=120)}  (distance={it[CtxKeys.DISTANCE.value]:.3f}, overlap={it[CtxKeys.OVERLAP.value]})")
    except Exception as e:
        logger.exception(e)
        return ExitCode.ERROR
    return ExitCode.SUCCESS



if __name__ == "__main__":
    result: ExitCode = main()
    if result == ExitCode.SUCCESS:
        logger.info("Successfully answered prompt")
    elif result == ExitCode.ERROR:
        logger.info("Failed to answer prompt")