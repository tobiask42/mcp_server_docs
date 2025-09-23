from definitions.custom_enums import ExitCode
from crawler.sitemap_crawler import DocsSpider
from loguru import logger

def main() -> ExitCode:
    logger.add("scraper.log")
    try:
        web_crawler = DocsSpider()
        result: ExitCode = web_crawler.crawl()
    except Exception as e:
        logger.exception(e)
        return ExitCode.ERROR
    return result



if __name__ == "__main__":
    result: ExitCode = main()
    if result == ExitCode.SUCCESS:
        logger.info("Successfully scraped websites")
    elif result == ExitCode.ERROR:
        logger.info("Failed scraping")