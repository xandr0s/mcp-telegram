"""Tests of the public MCP tagging interface without a Telegram connection."""

import json

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from mcp.server.fastmcp.exceptions import ToolError

from mcp_telegram import server
from mcp_telegram.types import MemberTagResult


class TestMemberTagTool(IsolatedAsyncioTestCase):
    """Exercise the registered MCP tool, defaults and error handling."""

    async def test_preview_default_and_numeric_ids(self):
        """MCP invocation converts IDs and defaults to preview."""
        expected = MemberTagResult(
            chat_id=-100123, user_id=456, tag="Флант", applied=False
        )
        with patch.object(server.tg, "set_member_tag", new_callable=AsyncMock) as tag:
            tag.return_value = expected
            result = await server.mcp.call_tool(
                "set_member_tag",
                {"entity": "-100123", "member": "456", "tag": "Флант"},
            )
            tag.assert_awaited_once_with(-100123, 456, "Флант", dry_run=True)
        content = result[0] if isinstance(result, tuple) else result
        self.assertEqual(json.loads(content[0].text), expected.model_dump())

    async def test_apply_empty_tag(self):
        """Explicit application and an empty tag reach the client unchanged."""
        expected = MemberTagResult(chat_id=-100123, user_id=456, tag="", applied=True)
        with patch.object(server.tg, "set_member_tag", new_callable=AsyncMock) as tag:
            tag.return_value = expected
            await server.mcp.call_tool(
                "set_member_tag",
                {"entity": "@group", "member": "@user", "tag": "", "dry_run": False},
            )
            tag.assert_awaited_once_with("@group", "@user", "", dry_run=False)

    async def test_failure_is_mcp_error(self):
        """A failed write must not produce a successful MCP result."""
        with patch.object(server.tg, "set_member_tag", new_callable=AsyncMock) as tag:
            tag.side_effect = ValueError("CHAT_ADMIN_REQUIRED")
            with self.assertRaisesRegex(ToolError, "CHAT_ADMIN_REQUIRED"):
                await server.mcp.call_tool(
                    "set_member_tag",
                    {
                        "entity": "@group",
                        "member": "@user",
                        "tag": "Флант",
                        "dry_run": False,
                    },
                )

    async def test_schema_exposes_preview_default(self):
        """Clients can discover the tool and its non-writing default."""
        tool = next(
            t for t in await server.mcp.list_tools() if t.name == "set_member_tag"
        )
        self.assertTrue(tool.inputSchema["properties"]["dry_run"]["default"])
        self.assertEqual(set(tool.inputSchema["required"]), {"entity", "member", "tag"})
