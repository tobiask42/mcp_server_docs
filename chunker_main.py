from content_processor.chunker import build_chunks
from definitions.custom_enums import ExitCode
from loguru import logger

def main() -> ExitCode:
    logger.add("chunker.log")
    logger.info("Starting to build chunks")
    try:
        build_chunks()
    except Exception as e:
        logger.exception(e)
        return ExitCode.ERROR
    return ExitCode.SUCCESS


if __name__ == "__main__":
    result: ExitCode = main()
    if result == ExitCode.SUCCESS:
        logger.info("Successfully chunked data")
    elif result == ExitCode.ERROR:
        logger.info("Failed to chunk data")