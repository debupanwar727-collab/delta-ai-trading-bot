import asyncio

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = "https://delta-ai-trading-bot-zt5d.onrender.com/mcp"

async def main():

    async with streamablehttp_client(URL) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            tools = await session.list_tools()

            print("CONNECTED SUCCESSFULLY")

            for tool in tools.tools:
                print(tool.name)

            result = await session.call_tool(
                "get_market_data", {}
            )

            print(result)

asyncio.run(main())
