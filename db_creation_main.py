from vector_database.create_chromadb import ingest_chunks_to_chroma
from loguru import logger
from definitions.custom_enums import ExitCode

def main() -> ExitCode:
    """If a database already exists it will be replaced"""
    logger.add("vector_database_creation.log")
    try:
        ingest_chunks_to_chroma()
    except Exception as e:
        logger.exception(e)
        return ExitCode.ERROR
    return ExitCode.SUCCESS

if __name__ == "__main__":
    result: ExitCode = main()
    if result == ExitCode.SUCCESS:
        logger.info("Successfully created vector database")
    elif result == ExitCode.ERROR:
        logger.info("Failed to create vector database")