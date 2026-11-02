import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def call_server():
    # Start the real server as a subprocess and talk to it like any MCP client would.
    server = StdioServerParameters(command=sys.executable, args=["mcp_server.py"])

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool(
                "calculate_roi_metrics",
                {"property_price": 1_000_000, "monthly_rent": 10_000},
            )

    return tools, result


def test_mcp_client_can_list_and_call_tool():
    tools, result = asyncio.run(call_server())
    metrics = json.loads(result.content[0].text)

    assert [tool.name for tool in tools.tools] == ["calculate_roi_metrics"]
    assert metrics["cap_rate_pct"] == 7.98
