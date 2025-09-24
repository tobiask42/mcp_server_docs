# crawler/sitemap_crawler.py
from __future__ import annotations
from loguru import logger
from scrapy.http import Response
from scrapy.crawler import CrawlerProcess
from scrapy.spiders import SitemapSpider
from scrapy.settings import BaseSettings
from typing import Sequence
from datetime import datetime, UTC
from pathlib import Path

from definitions.custom_enums import ExitCode
from definitions.custom_types import PageItem
from definitions import constants
from config.settings import get_settings, AppSettings
from crawler.html_processor import html_to_text_string

custom_settings: AppSettings = get_settings()

class DocsSpider(SitemapSpider):
    name: str = "mcp_scraper"
    sitemap_urls: Sequence[str] = [str(url) for url in custom_settings.SCRAPELIST]

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        super().update_settings(settings)
        prio = custom_settings.SPIDER_PRIORITY

        settings.set("AUTOTHROTTLE_ENABLED", custom_settings.SPIDER_AUTOTHROTTLE_ENABLED, priority=prio)
        settings.set("DOWNLOAD_DELAY", custom_settings.SPIDER_DOWNLOAD_DELAY, priority=prio)
        settings.set("CONCURRENT_REQUESTS", custom_settings.SPIDER_CONCURRENT_REQUESTS, priority=prio)
        settings.set("HTTPCACHE_ENABLED", custom_settings.SPIDER_HTTPCACHE_ENABLED, priority=prio)
        settings.set("USER_AGENT", f"org-docs-crawler/1.0 (+{custom_settings.EMAIL})", priority=prio)

        # FEEDS sicher setzen
        now = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        feed_dir: Path = constants.FEED_PATH
        feed_dir.mkdir(parents=True, exist_ok=True)
        feed_path = (feed_dir / f"out_{now}.jsonl").as_posix()
        settings.set("FEEDS", {feed_path: {"format": "jsonlines", "encoding": "utf-8"}}, priority=prio)

    def parse(self, response: Response):
        text = html_to_text_string(response.text)
        title = (response.css("h1::text").get() or "").strip()
        if not title and text:
            title = text.split("\n", 1)[0].lstrip("# ").strip()
        yield PageItem(url=response.url, title=title, text=text)

    def crawl(self) -> ExitCode:
        try:
            # Achtung: Dieser Weg ist nur ok, wenn im Main-Thread!
            process = CrawlerProcess(settings={"LOG_LEVEL": custom_settings.CRAWLER_LOG_LEVEL})
            process.crawl(DocsSpider)
            process.start()  # blockiert
            return ExitCode.SUCCESS
        except Exception as e:
            logger.exception(e)
            return ExitCode.ERROR
