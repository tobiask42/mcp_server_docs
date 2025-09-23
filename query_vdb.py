from definitions.custom_enums import ExitCode
from vector_database.query_chroma import query_db
from loguru import logger
from pprint import pprint

def main() -> ExitCode:
    logger.add("db_query.log")
    logger.info("Running demo query…")
    q = "How do I define my first FastAPI endpoint with @app.get?"

    try:
       res = query_db(q)
       pprint(res)
    except Exception as e:
        logger.exception(e)
        return ExitCode.ERROR
    return ExitCode.SUCCESS



if __name__ == "__main__":
    result: ExitCode = main()
    if result == ExitCode.SUCCESS:
        logger.info("Successfully queried database")
    elif result == ExitCode.ERROR:
        logger.info("Failed to query")