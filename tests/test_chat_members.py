"""Read-only participant pagination tests."""

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from telethon import types
from telethon.tl import functions

from mcp_telegram.telegram import Telegram


class TestChatMembers(IsolatedAsyncioTestCase):
    """Validate pages and visibility without a live Telegram session."""

    async def test_page_preserves_counts_and_identities(self):
        tg = object.__new__(Telegram)
        tg._client = AsyncMock()
        tg._client.get_entity.return_value = types.Channel(
            id=12,
            title="Group",
            photo=types.ChatPhotoEmpty(),
            date=None,
            megagroup=True,
        )
        user = types.User(id=34, first_name="Test", username="test", bot=True)
        user.usernames = [types.Username(username="alias", active=True)]
        full = SimpleNamespace(
            full_chat=SimpleNamespace(
                participants_count=250,
                participants_hidden=True,
                can_view_participants=True,
            )
        )
        page = SimpleNamespace(
            count=250,
            users=[user],
            participants=[SimpleNamespace(user_id=34, rank="Флант")],
        )
        tg._client.side_effect = [full, page]
        result = await tg.list_chat_members(-1000000000012, offset=200, limit=50)
        self.assertEqual(result["returned_count"], 1)
        self.assertEqual(result["total"], 250)
        self.assertEqual(result["members"][0]["usernames"], ["alias"])
        self.assertEqual(result["members"][0]["tag"], "Флант")
        self.assertTrue(result["participants_hidden"])
        calls = tg._client.await_args_list
        self.assertIsInstance(
            calls[0].args[0], functions.channels.GetFullChannelRequest
        )
        request = calls[1].args[0]
        self.assertIsInstance(request, functions.channels.GetParticipantsRequest)
        self.assertEqual((request.offset, request.limit, request.hash), (200, 50, 0))

    async def test_bad_pagination_never_contacts_telegram(self):
        tg = object.__new__(Telegram)
        tg._client = AsyncMock()
        for offset, limit in [(-1, 20), (0, 0), (0, 201)]:
            with self.assertRaises(ValueError):
                await tg.list_chat_members("group", offset, limit)
        tg._client.get_entity.assert_not_awaited()
        tg._client.assert_not_awaited()

    async def test_errors_are_not_returned_as_empty_roster(self):
        tg = object.__new__(Telegram)
        tg._client = AsyncMock()
        tg._client.get_entity.side_effect = RuntimeError("CHAT_ADMIN_REQUIRED")
        with self.assertRaisesRegex(RuntimeError, "CHAT_ADMIN_REQUIRED"):
            await tg.list_chat_members("group")
