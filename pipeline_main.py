from loguru import logger
from definitions.custom_enums import ExitCode
from crawler.sitemap_crawler import DocsSpider
from content_processor.chunker import build_chunks
from vector_database.create_chromadb import ingest_chunks_to_chroma

def main() -> ExitCode:
    logger.add("pipeline.log")
    try:
        web_crawler = DocsSpider()
        web_crawler.crawl()
    except Exception as e:
        logger.error("Failed to crawl websites")
        logger.exception(e)
        return ExitCode.ERROR
    logger.info("Starting to build chunks")
    try:
        build_chunks()
    except Exception as e:
        logger.error("Failed to build chunks")
        logger.exception(e)
        return ExitCode.ERROR
    try:
        ingest_chunks_to_chroma()
    except Exception as e:
        logger.error("Failed to create vector database")
        logger.exception(e)
        return ExitCode.ERROR
    return ExitCode.SUCCESS




if __name__ == "__main__":
    result: ExitCode = main()
    if result == ExitCode.SUCCESS:
        logger.info("Successfully finished scraping, chunking, and creating vector database")
    elif result == ExitCode.ERROR:
        logger.info("Pipeline failed")