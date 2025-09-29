import asyncio
from loguru import logger

# zentrale Config (lädt .env/ENV und validiert Pflichtfelder wie EMAIL)
from config.settings import get_settings, AppSettings

# der FastMCP-Server mit den @mcp.tool()-Funktionen (crawl, chunk, build_vector_db)
from server.mcp_server import mcp


async def _run() -> None:
    # Frühe Sichtprüfung der Settings, damit Fehlkonfig direkt auffällt
    custom_settings:AppSettings = get_settings()
    logger.info(f"Loaded settings: EMAIL={custom_settings.EMAIL}, SCRAPELIST={len(custom_settings.SCRAPELIST)} URL(s)")
    # MCP-Server über stdio starten (der Dev-Client/Inspector spricht ihn dann an)
    mcp.run()

if __name__ == "__main__":
    asyncio.run(_run())
