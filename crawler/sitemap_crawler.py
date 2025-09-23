from loguru import logger
from scrapy.http import Response
from scrapy.crawler import CrawlerProcess
from definitions.custom_enums import ExitCode
from scrapy.spiders import SitemapSpider
from typing import Sequence
from scrapy.settings import BaseSettings
from crawler.html_processor import html_to_text_string
from datetime import datetime, UTC
from definitions.custom_types import PageItem
from definitions import constants
from config.settings import get_settings, AppSettings

custom_settings: AppSettings = get_settings()

class DocsSpider(SitemapSpider):

    name: str = "mcp_scraper"
    sitemap_urls: Sequence[str] = [str(url) for url in custom_settings.SCRAPELIST]

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        super().update_settings(settings)
        settings.set("AUTOTHROTTLE_ENABLED", custom_settings.SPIDER_AUTOTHROTTLE_ENABLED, priority=custom_settings.SPIDER_PRIORITY)
        settings.set("DOWNLOAD_DELAY", custom_settings.SPIDER_DOWNLOAD_DELAY, priority=custom_settings.SPIDER_PRIORITY)
        settings.set("CONCURRENT_REQUESTS", custom_settings.SPIDER_CONCURRENT_REQUESTS, priority=custom_settings.SPIDER_PRIORITY)
        settings.set("HTTPCACHE_ENABLED", custom_settings.SPIDER_HTTPCACHE_ENABLED, priority=custom_settings.SPIDER_PRIORITY)
        # User-Agent mit Kontakt
        settings.set("USER_AGENT", f"org-docs-crawler/1.0 (+{custom_settings.EMAIL})", priority=custom_settings.SPIDER_PRIORITY)
        # JSONL-Ausgabe
        now: datetime = datetime.now(UTC)
        ts: str = now.strftime("%Y%m%dT%H%M%SZ")
        feed_path =  f"{constants.FEED_PATH}/out_{ts}.jsonl"
        settings.set("FEEDS", {feed_path: {"format": "jsonlines", "encoding": "utf-8"}}, priority=custom_settings.SPIDER_PRIORITY)

    def parse(self, response: Response):
        text = html_to_text_string(response.text)
        title = (response.css("h1::text").get() or "").strip()
        if not title and text:
            title = text.split("\n", 1)[0].lstrip("# ").strip()
        yield PageItem(url=response.url, title=title, text=text)
    
    def crawl(self) -> ExitCode:
        try:
            process = CrawlerProcess(settings={"LOG_LEVEL": custom_settings.CRAWLER_LOG_LEVEL})
            process.crawl(DocsSpider)
            process.start()  # blockiert bis Crawl fertig ist
            return ExitCode.SUCCESS
        except Exception as e:
            logger.exception(e)
            return ExitCode.ERROR