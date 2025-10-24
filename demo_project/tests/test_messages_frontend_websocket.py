"""
Playwright tests for Messages page frontend functionality with WebSocket.

This is the WebSocket version of the Messages page tests.
For WSGI/polling tests, see test_messages_frontend_polling.py

Tests messaging features between two users on the main messages page:
- User 1 in normal Chromium window
- User 2 in incognito Chromium window

Tests cover:
- Creating a new chat
- Searching for users and adding them to a chat
- Removing users from a chat
- Renaming a chat
- Receiving indicators for new messages on inactive chats
- Joining a room
- Leaving a room
- Leaving a chat and admin transfer
- Deleting a chat
"""

import asyncio
import pytest
from playwright.async_api import async_playwright, expect
from django.contrib.auth import get_user_model
from channels.testing import ChannelsLiveServerTestCase
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


@pytest.mark.frontend
@pytest.mark.slow
@pytest.mark.websocket
class MessagesFrontendWebSocketTestCase(ChannelsLiveServerTestCase):
    """Test Messages page functionality with Playwright using WebSocket transport"""

    serve_static = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        from demo_project.apps.videos.models import Video
        from django_messaging.models import ChatRoom, ChatMembership

        cls.user1 = User.objects.create_user(
            username="msg_user1_ws",
            password="testpass123",
            email="msguser1_ws@test.com",
            first_name="Message",
            last_name="UserOne",
        )
        cls.user2 = User.objects.create_user(
            username="msg_user2_ws",
            password="testpass123",
            email="msguser2_ws@test.com",
            first_name="Message",
            last_name="UserTwo",
        )
        cls.user3 = User.objects.create_user(
            username="msg_user3_ws",
            password="testpass123",
            email="msguser3_ws@test.com",
            first_name="Message",
            last_name="UserThree",
        )

        cls.video = Video.objects.create(
            title="Test Video for Messages WS",
            description="A test video with a chat room",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            embed_url="https://www.youtube.com/embed/dQw4w9WgXcQ",
            uploaded_by=cls.user1,
            is_public=True,
        )

        content_type = ContentType.objects.get_for_model(Video)
        cls.public_room = ChatRoom.objects.create(
            content_type=content_type,
            object_id=cls.video.pk,
            title="Public Test Room WS",
            is_room=True,
            is_group=True,
        )

    def test_messages_page_functionality(self):
        """Test complete messages page workflow with WebSocket"""
        asyncio.run(self._test_messages_page_functionality())

    async def _test_messages_page_functionality(self):
        """Async test for messages page functionality via WebSocket"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=500)

            user1_context = await browser.new_context()
            user1_page = await user1_context.new_page()

            user2_context = await browser.new_context()
            user2_page = await user2_context.new_page()

            try:
                print("🔐 Logging in users...")
                await self._login(user1_page, "msg_user1_ws", "testpass123")
                await self._login(user2_page, "msg_user2_ws", "testpass123")
                await asyncio.sleep(1)

                print("🌐 Navigating to messages page...")
                await user1_page.goto(f"{self.live_server_url}/messages/")
                await user1_page.wait_for_load_state("networkidle")
                await asyncio.sleep(1)

                await user2_page.goto(f"{self.live_server_url}/messages/")
                await user2_page.wait_for_load_state("networkidle")
                await asyncio.sleep(1)

                transport_check = await user1_page.evaluate(
                    """
                    () => {
                        return {
                            hasWebSocketTransport: typeof WebSocketTransport !== 'undefined',
                            transportType: window.chatApp?.wsTransport?.constructor?.name || 'unknown'
                        };
                    }
                """
                )
                print(f"🔍 Transport check: {transport_check}")
                if transport_check["transportType"] != "WebSocketTransport":
                    print(
                        f"⚠️ WARNING: Using {transport_check['transportType']} instead of WebSocketTransport!"
                    )

                print("➕ Test 1: Creating new chat...")
                await self._create_new_chat(user1_page)
                await asyncio.sleep(1)

                chat_list = user1_page.locator("#chat-list")
                await expect(chat_list.locator(".chat-item").first).to_be_visible(
                    timeout=5000
                )
                await asyncio.sleep(1)

                chat_title = user1_page.locator("#current-chat-name")
                await expect(chat_title).to_be_visible(timeout=5000)
                await asyncio.sleep(1)

                print("✏️ Test 2: Renaming chat...")
                await self._rename_chat(user1_page, "Test Group Chat WS")
                await asyncio.sleep(2)

                await expect(chat_title).to_have_text("Test Group Chat WS")
                await asyncio.sleep(1.5)

                print("👥 Test 3: Adding user2 to chat...")
                await self._open_members_dialog(user1_page)
                await self._search_and_add_user(user1_page, "msg_user2_ws")
                await asyncio.sleep(2)

                print("📥 Test 4: User2 sees new chat via WebSocket...")
                await asyncio.sleep(1.5)
                user2_chat_list = user2_page.locator("#chat-list")
                await expect(
                    user2_chat_list.get_by_text("Test Group Chat WS")
                ).to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)

                print("📤 Test 5: User1 sends message...")
                await self._send_message(user1_page, "Hello in the group!")
                await asyncio.sleep(1)

                print("📥 Test 6: User2 sees unread indicator via WebSocket...")
                await asyncio.sleep(1.5)
                user2_chat_item = user2_page.locator(".chat-item").filter(
                    has_text="Test Group Chat WS"
                )
                await expect(
                    user2_chat_item.locator(".unread-indicator")
                ).to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)

                print("👁️ Test 7: User2 selects chat and sees message...")
                await user2_chat_item.click()
                await asyncio.sleep(2)
                await expect(
                    user2_page.locator("#message-list").get_by_text(
                        "Hello in the group!"
                    )
                ).to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)

                print("👥 Test 8: Adding user3 to chat...")
                await self._open_members_dialog(user1_page)
                await self._search_and_add_user(user1_page, "msg_user3_ws")
                await asyncio.sleep(2)

                print("🗑️ Test 9: Removing user3 from chat...")
                await self._open_members_dialog(user1_page)
                await self._switch_to_manage_members_tab(user1_page)
                await asyncio.sleep(1)
                await self._remove_member(user1_page, "msg_user3_ws")
                await asyncio.sleep(2.5)

                print("🏠 Test 10: User2 browses and joins public room...")
                await self._browse_rooms(user2_page)
                await self._join_room_from_dialog(user2_page, "Public Test Room WS")
                await asyncio.sleep(2)

                await expect(
                    user2_page.locator("#chat-list").get_by_text("Public Test Room WS")
                ).to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)

                print("🚪 Test 11: User2 leaves room...")
                await self._select_chat_by_title(user2_page, "Public Test Room WS")
                await asyncio.sleep(1)
                await self._leave_chat(user2_page)
                await asyncio.sleep(2.5)

                print("🚪 Test 12: User1 leaves chat (admin transfer)...")
                await self._select_chat_by_title(user1_page, "Test Group Chat WS")
                await asyncio.sleep(1)

                await self._leave_chat(user1_page)
                await asyncio.sleep(2)

                print("👑 Verifying user2 is now admin...")
                await asyncio.sleep(2)
                await self._select_chat_by_title(user2_page, "Test Group Chat WS")
                await asyncio.sleep(2)
                members_btn = user2_page.locator("#members-btn")
                await expect(members_btn).to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)

                print("🗑️ Test 13: User2 deletes chat...")
                await self._delete_chat(user2_page)
                await asyncio.sleep(2)

                await expect(
                    user2_page.locator("#chat-list").get_by_text("Test Group Chat WS")
                ).not_to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)

                print("✅ All messages page WebSocket tests passed!")

            finally:
                await user1_context.close()
                await user2_context.close()
                await browser.close()

    async def _login(self, page, username, password):
        """Helper to login a user"""
        await page.goto(f"{self.live_server_url}/accounts/login/")
        await page.fill('input[name="username"]', username)
        await page.fill('input[name="password"]', password)
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")

    async def _create_new_chat(self, page):
        """Helper to create a new chat"""
        new_chat_btn = page.locator("#new-chat-btn")
        await new_chat_btn.click()
        await asyncio.sleep(2.5)

        close_btn = page.locator("#close-dialog-btn")
        await close_btn.click()
        await asyncio.sleep(1)

    async def _rename_chat(self, page, new_title):
        """Helper to rename a chat"""
        chat_title = page.locator("#current-chat-name")
        await chat_title.click()
        await asyncio.sleep(0.5)

        title_input = page.locator(".chat-title-input")
        await title_input.fill(new_title)

        save_btn = page.locator(".chat-title-save-btn")
        await save_btn.click()
        await asyncio.sleep(1)

    async def _open_members_dialog(self, page):
        """Helper to open the members dialog"""
        members_btn = page.locator("#members-btn")
        await members_btn.click()
        await asyncio.sleep(1)

    async def _search_and_add_user(self, page, username):
        """Helper to search for a user and add them"""
        search_input = page.locator("#user-search-input")
        await search_input.fill(username)

        search_btn = page.locator("#search-btn")
        await search_btn.click()
        await asyncio.sleep(1)

        add_btn = page.locator(".add-user-btn").first
        await add_btn.click()
        await asyncio.sleep(1)

        close_btn = page.locator("#close-dialog-btn")
        await close_btn.click()
        await asyncio.sleep(0.5)

    async def _switch_to_manage_members_tab(self, page):
        """Helper to switch to manage members tab"""
        manage_tab = page.locator("#manage-members-tab")
        await manage_tab.click()
        await asyncio.sleep(0.5)

    async def _remove_member(self, page, username):
        """Helper to remove a member from the chat"""
        member_item = page.locator(".member-item").filter(has_text=username)
        remove_btn = member_item.locator(".remove-member-btn")
        await remove_btn.click()
        await asyncio.sleep(0.5)

        confirm_btn = page.locator("#confirmation-confirm-btn")
        await confirm_btn.click()
        await asyncio.sleep(1)

        close_btn = page.locator("#close-dialog-btn")
        await close_btn.click()
        await asyncio.sleep(0.5)

    async def _send_message(self, page, message_text):
        """Helper to send a message"""
        message_input = page.locator("#message-input")
        await message_input.fill(message_text)
        await message_input.press("Enter")
        await asyncio.sleep(1)

    async def _browse_rooms(self, page):
        """Helper to open the browse rooms dialog"""
        browse_btn = page.locator("#browse-rooms-btn")
        await browse_btn.click()
        await asyncio.sleep(1)

    async def _join_room_from_dialog(self, page, room_title):
        """Helper to join a room from the rooms dialog"""
        room_item = page.locator(".room-item").filter(has_text=room_title)
        join_btn = room_item.locator(".join-room-btn")
        await join_btn.click()
        await asyncio.sleep(2)

    async def _select_chat_by_title(self, page, chat_title):
        """Helper to select a chat by its title"""
        chat_item = page.locator(".chat-item").filter(has_text=chat_title)
        await chat_item.click()
        await asyncio.sleep(1)

    async def _leave_chat(self, page):
        """Helper to leave the current chat"""
        leave_btn = page.locator("#leave-chat-btn")
        await leave_btn.click()
        await asyncio.sleep(0.5)

        confirm_btn = page.locator("#confirmation-confirm-btn")
        await confirm_btn.click()
        await asyncio.sleep(1)

    async def _delete_chat(self, page):
        """Helper to delete the current chat"""
        chat_menu_btn = page.locator("#chat-menu-btn")
        await chat_menu_btn.click()
        await asyncio.sleep(0.5)

        delete_btn = page.locator("#delete-chat-btn")
        await delete_btn.click()
        await asyncio.sleep(0.5)

        confirm_btn = page.locator("#confirmation-confirm-btn")
        await confirm_btn.click()
        await asyncio.sleep(1)
