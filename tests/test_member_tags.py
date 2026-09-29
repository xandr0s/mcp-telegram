"""Unit tests for Telegram member tags."""

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, call

from telethon import types, utils
from telethon.tl import functions

from mcp_telegram.telegram import Telegram


class TestTelegramMemberTags(IsolatedAsyncioTestCase):
    """Test member tag validation and Telegram RPC construction."""

    async def asyncSetUp(self) -> None:
        self.telegram = object.__new__(Telegram)
        self.client = AsyncMock()
        self.telegram._client = self.client

        self.chat = types.Chat(
            id=42,
            title="Group",
            photo=types.ChatPhotoEmpty(),
            participants_count=2,
            date=None,
            version=1,
        )
        self.channel = types.Channel(
            id=43,
            title="Megagroup",
            photo=types.ChatPhotoEmpty(),
            date=None,
            megagroup=True,
            access_hash=4300,
        )
        self.broadcast = types.Channel(
            id=44,
            title="Broadcast",
            photo=types.ChatPhotoEmpty(),
            date=None,
            broadcast=True,
            access_hash=4400,
        )
        self.user = types.User(id=7, access_hash=700, first_name="Member")
        self.other_user = types.User(id=8, access_hash=800, first_name="Other")
        self.input_chat = types.InputPeerChat(self.chat.id)
        self.input_channel = types.InputPeerChannel(
            self.channel.id, self.channel.access_hash
        )
        self.input_user = types.InputPeerUser(self.user.id, self.user.access_hash)

    def set_resolution(self, entity: object, member: object) -> None:
        """Configure entity and member resolution without making network calls."""

        async def resolve(value: object) -> object:
            if value == "chat":
                return entity
            if value == "member":
                return member
            raise LookupError(value)

        async def input_entity(value: object) -> object:
            if value is self.chat:
                return self.input_chat
            if value is self.channel:
                return self.input_channel
            if value is self.user:
                return self.input_user
            raise LookupError(value)

        self.client.get_entity.side_effect = resolve
        self.client.get_input_entity.side_effect = input_entity

    async def test_dry_run_resolves_identities_without_mutating(self) -> None:
        """Dry-run returns the resolved tag and never sends the mutation RPC."""

        self.set_resolution(self.chat, self.user)

        result = await self.telegram.set_member_tag("chat", "member", "moderator")

        self.assertEqual(result.chat_id, utils.get_peer_id(self.chat))
        self.assertEqual(result.user_id, self.user.id)
        self.assertEqual(result.tag, "moderator")
        self.assertFalse(result.applied)
        self.client.assert_not_awaited()
        self.client.get_entity.assert_has_awaits([call("chat"), call("member")])
        self.client.get_input_entity.assert_has_awaits(
            [call(self.chat), call(self.user)]
        )

    async def test_apply_builds_raw_rank_request_for_chat(self) -> None:
        """Applying a tag sends the expected raw request with resolved peers."""

        self.set_resolution(self.chat, self.user)

        result = await self.telegram.set_member_tag(
            "chat", "member", "moderator", dry_run=False
        )

        self.assertTrue(result.applied)
        self.assertEqual(result.chat_id, utils.get_peer_id(self.chat))
        self.assertEqual(result.user_id, self.user.id)
        request = self.client.await_args.args[0]
        self.assertIsInstance(
            request, functions.messages.EditChatParticipantRankRequest
        )
        self.assertEqual(request.peer, self.input_chat)
        self.assertEqual(request.participant, self.input_user)
        self.assertEqual(request.rank, "moderator")

    async def test_apply_builds_raw_rank_request_for_megagroup(self) -> None:
        """Megagroup channels are accepted and use their input channel peer."""

        self.set_resolution(self.channel, self.user)

        await self.telegram.set_member_tag("chat", "member", "", dry_run=False)

        request = self.client.await_args.args[0]
        self.assertEqual(request.peer, self.input_channel)
        self.assertEqual(request.participant, self.input_user)
        self.assertEqual(request.rank, "")

    async def test_empty_tag_is_allowed_and_removed(self) -> None:
        """An empty rank is a valid request that removes the existing tag."""

        self.set_resolution(self.chat, self.user)

        result = await self.telegram.set_member_tag("chat", "member", "", dry_run=False)

        self.assertEqual(result.tag, "")
        self.assertTrue(result.applied)
        self.assertEqual(self.client.await_args.args[0].rank, "")

    async def test_sixteen_character_tag_is_allowed(self) -> None:
        """The maximum supported tag length is inclusive."""

        self.set_resolution(self.chat, self.user)

        await self.telegram.set_member_tag("chat", "member", "x" * 16)

        self.client.get_entity.assert_any_await("chat")

    async def test_seventeen_character_tag_is_rejected_before_resolution(self) -> None:
        """An overlong tag is rejected before any entity lookup."""

        with self.assertRaises(ValueError):
            await self.telegram.set_member_tag("chat", "member", "x" * 17)

        self.client.get_entity.assert_not_awaited()
        self.client.get_input_entity.assert_not_awaited()
        self.client.assert_not_awaited()

    async def test_personal_chat_is_rejected(self) -> None:
        """A personal user dialog cannot contain member tags."""

        self.set_resolution(self.user, self.other_user)

        with self.assertRaises(ValueError):
            await self.telegram.set_member_tag("chat", "member", "tag")

        self.client.get_input_entity.assert_not_awaited()
        self.client.assert_not_awaited()

    async def test_broadcast_channel_is_rejected(self) -> None:
        """Broadcast channels are not valid member-tag targets."""

        self.set_resolution(self.broadcast, self.user)

        with self.assertRaises(ValueError):
            await self.telegram.set_member_tag("chat", "member", "tag")

        self.client.get_input_entity.assert_not_awaited()
        self.client.assert_not_awaited()

    async def test_non_user_member_is_rejected(self) -> None:
        """Only a User can be tagged as a member."""

        self.set_resolution(self.chat, self.channel)

        with self.assertRaises(ValueError):
            await self.telegram.set_member_tag("chat", "member", "tag")

        self.client.get_input_entity.assert_not_awaited()
        self.client.assert_not_awaited()

    async def test_resolution_errors_are_propagated(self) -> None:
        """Entity lookup failures are not converted into a success result."""

        error = LookupError("unknown entity")
        self.client.get_entity.side_effect = error

        with self.assertRaisesRegex(LookupError, "unknown entity"):
            await self.telegram.set_member_tag("chat", "member", "tag")

        self.client.assert_not_awaited()

    async def test_rpc_errors_are_propagated(self) -> None:
        """RPC failures are returned to the caller unchanged."""

        self.set_resolution(self.chat, self.user)
        error = RuntimeError("rpc failed")
        self.client.side_effect = error

        with self.assertRaisesRegex(RuntimeError, "rpc failed"):
            await self.telegram.set_member_tag("chat", "member", "tag", dry_run=False)
