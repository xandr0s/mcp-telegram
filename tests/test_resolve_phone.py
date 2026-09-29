"""Read-only contacts.resolvePhone tests."""

import asyncio

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from telethon import types
from telethon.errors import FloodWaitError, PhoneNotOccupiedError
from telethon.tl import functions

from mcp_telegram.telegram import Telegram


class TestResolvePhone(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.telegram = object.__new__(Telegram)
        self.telegram._client = AsyncMock()
        self.telegram._phone_lookup_lock = asyncio.Lock()

    async def test_found_uses_exact_request_and_returns_active_aliases(self) -> None:
        user = types.User(id=42, first_name="A", last_name="B", username="alpha")
        user.usernames = [
            types.Username(username="old", active=False),
            types.Username(username="active", active=True),
        ]
        self.telegram._client.return_value = SimpleNamespace(
            peer=SimpleNamespace(user_id=42), users=[user]
        )
        with patch(
            "mcp_telegram.telegram.asyncio.sleep", new_callable=AsyncMock
        ) as sleep:
            result = await self.telegram.resolve_phone("+79001234567")
        request = self.telegram._client.await_args.args[0]
        self.assertIsInstance(request, functions.contacts.ResolvePhoneRequest)
        self.assertEqual(request.phone, "+79001234567")
        self.assertEqual(
            self.telegram._client.await_args.kwargs, {"flood_sleep_threshold": 0}
        )
        self.assertEqual(result["status"], "found")
        self.assertEqual(result["usernames"], ["active"])
        sleep.assert_awaited_once_with(3)

    async def test_invalid_phone_is_rejected_before_rpc(self) -> None:
        for phone in ("79001234567", "+123", "+1234567890123456", "+79 001234567"):
            with self.subTest(phone=phone):
                with self.assertRaises(ValueError):
                    await self.telegram.resolve_phone(phone)
        self.telegram._client.assert_not_awaited()

    async def test_not_found_and_rate_limited_statuses_and_finally_sleep(self) -> None:
        with patch(
            "mcp_telegram.telegram.asyncio.sleep", new_callable=AsyncMock
        ) as sleep:
            self.telegram._client.side_effect = PhoneNotOccupiedError(request=None)
            self.assertEqual(
                await self.telegram.resolve_phone("+79001234567"),
                {"status": "not_found"},
            )
            error = FloodWaitError(request=None, capture=7)
            self.telegram._client.side_effect = error
            self.assertEqual(
                await self.telegram.resolve_phone("+79001234568"),
                {"status": "rate_limited", "retry_after": 7},
            )
        self.assertEqual(sleep.await_count, 2)
