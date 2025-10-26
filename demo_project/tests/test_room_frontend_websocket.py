"""
Playwright tests for Chat Room frontend functionality with WebSocket.

This is the WebSocket version of the Chat Room tests.
For WSGI/polling tests, see test_room_frontend_polling.py

Tests real-time chat room features between two users:
- User 1 in normal Chromium window
- User 2 in incognito Chromium window

Tests cover:
- Joining a chat room
- Leaving a chat room
- Member count changes
- Sending and receiving messages in real-time
- Adding and removing reactions
- Editing messages
- Deleting messages
"""

import asyncio
import pytest
from playwright.async_api import async_playwright, expect
from django.contrib.auth import get_user_model
from channels.testing import ChannelsLiveServerTestCase
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

User = get_user_model()


@pytest.mark.frontend
@pytest.mark.slow
@pytest.mark.websocket
class ChatRoomFrontendWebSocketTestCase(ChannelsLiveServerTestCase):
    """Test Chat Room functionality with Playwright using WebSocket transport"""

    serve_static = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        from demo_project.apps.videos.models import Video
        from django_messaging.models import ChatRoom, ChatMembership

        cls.user1 = User.objects.create_user(
            username="room_user1_ws",
            password="testpass123",
            email="user1_ws@test.com",
            first_name="User",
            last_name="One",
        )
        cls.user2 = User.objects.create_user(
            username="room_user2_ws",
            password="testpass123",
            email="user2_ws@test.com",
            first_name="User",
            last_name="Two",
        )
        cls.user3 = User.objects.create_user(
            username="room_user3_ws",
            password="testpass123",
            email="user3_ws@test.com",
            first_name="User",
            last_name="Three",
        )

        cls.video = Video.objects.create(
            title="Test Video for Chat Room WS",
            description="A test video with a chat room",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            embed_url="https://www.youtube.com/embed/dQw4w9WgXcQ",
            uploaded_by=cls.user1,
            is_public=True,
        )

        content_type = ContentType.objects.get_for_model(Video)
        cls.room = ChatRoom.objects.create(
            content_type=content_type,
            object_id=cls.video.pk,
            title=f"Discussion: {cls.video.title}",
            is_room=True,
            is_group=True,
        )

        ChatMembership.objects.create(
            chat=cls.room, user=cls.user3, role=ChatMembership.Role.MEMBER
        )

    def test_room_real_time_messaging(self):
        """Test complete chat room workflow with real-time WebSocket updates"""
        asyncio.run(self._test_room_real_time_messaging())

    async def _test_room_real_time_messaging(self):
        """Async test for chat room real-time messaging via WebSocket"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=500)

            user1_context = await browser.new_context()
            user1_page = await user1_context.new_page()

            user2_context = await browser.new_context()
            user2_page = await user2_context.new_page()

            try:
                print("🔐 Logging in users...")
                await self._login(user1_page, "room_user1_ws", "testpass123")
                await self._login(user2_page, "room_user2_ws", "testpass123")
                await asyncio.sleep(1)

                print("🌐 Navigating to video page with chat room...")
                video_detail_url = reverse('videos:detail', kwargs={'pk': self.video.pk})
                await user1_page.goto(f"{self.live_server_url}{video_detail_url}")
                await user1_page.wait_for_load_state("networkidle")
                await asyncio.sleep(1)

                await user2_page.goto(f"{self.live_server_url}{video_detail_url}")
                await user2_page.wait_for_load_state("networkidle")
                await asyncio.sleep(1)

                print("👥 Test 1: Verifying initial member count...")
                await asyncio.sleep(2)
                user1_member_count = await user1_page.locator(
                    ".member-count"
                ).text_content()
                self.assertEqual(user1_member_count.strip(), "1 member")
                await asyncio.sleep(1)

                print("➕ Test 2: User1 joining room...")
                join_btn = user1_page.locator(".join-room-btn")
                await expect(join_btn).to_be_visible()
                await join_btn.click()
                await asyncio.sleep(2)

                print("👥 Test 3: Verifying member count increased to 2...")
                await asyncio.sleep(1)
                user1_member_count = await user1_page.locator(
                    ".member-count"
                ).text_content()
                self.assertEqual(user1_member_count.strip(), "2 members")
                await asyncio.sleep(1.5)

                print("📥 Test 4: User2 sees member count update via WebSocket...")
                await asyncio.sleep(2)
                user2_member_count = await user2_page.locator(
                    ".member-count"
                ).text_content()
                self.assertEqual(user2_member_count.strip(), "2 members")
                await asyncio.sleep(1.5)

                print("➕ Test 5: User2 joining room...")
                join_btn2 = user2_page.locator(".join-room-btn")
                await expect(join_btn2).to_be_visible()
                await join_btn2.click()
                await asyncio.sleep(2)

                print("👥 Test 6: Verifying member count increased to 3...")
                await asyncio.sleep(1)
                user2_member_count = await user2_page.locator(
                    ".member-count"
                ).text_content()
                self.assertEqual(user2_member_count.strip(), "3 members")
                await asyncio.sleep(1.5)

                print("📥 Test 7: User1 sees member count update via WebSocket...")
                await asyncio.sleep(1.5)
                user1_member_count = await user1_page.locator(
                    ".member-count"
                ).text_content()
                self.assertEqual(user1_member_count.strip(), "3 members")
                await asyncio.sleep(1.5)

                print("📤 Test 8: User1 sends message...")
                await self._send_message_in_room(user1_page, "Hello from User 1!")
                await asyncio.sleep(1)

                await expect(
                    user1_page.locator(".room-message-list").get_by_text(
                        "Hello from User 1!"
                    )
                ).to_be_visible(timeout=5000)
                await asyncio.sleep(1)

                print("📥 Test 9: User2 receives message via WebSocket...")
                await expect(
                    user2_page.locator(".room-message-list").get_by_text(
                        "Hello from User 1!"
                    )
                ).to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)

                print("📤 Test 10: User2 sends reply...")
                await self._send_message_in_room(user2_page, "Hello from User 2!")
                await asyncio.sleep(1)

                print("📥 Test 11: User1 receives reply via WebSocket...")
                await expect(
                    user1_page.locator(".room-message-list").get_by_text(
                        "Hello from User 2!"
                    )
                ).to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)

                print("👍 Test 12: User1 adds reaction...")
                await self._add_reaction_in_room(user1_page, "Hello from User 2!", "👍")
                await asyncio.sleep(1)

                print("📥 Test 13: User2 sees reaction via WebSocket...")
                await asyncio.sleep(1.5)
                user2_message = user2_page.locator(".message-item").filter(
                    has_text="Hello from User 2!"
                )
                await expect(
                    user2_message.locator(".reaction-emoji").filter(has_text="👍")
                ).to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)

                print("❤️ Test 14: User2 adds reaction...")
                await self._add_reaction_in_room(user2_page, "Hello from User 1!", "❤️")
                await asyncio.sleep(1)

                print("📥 Test 15: User1 sees reaction via WebSocket...")
                await asyncio.sleep(1.5)
                user1_message = user1_page.locator(".message-item").filter(
                    has_text="Hello from User 1!"
                )
                await expect(
                    user1_message.locator(".reaction-emoji").filter(has_text="❤️")
                ).to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)

                print("🗑️ Test 16: User1 removes reaction...")
                await self._remove_reaction_in_room(
                    user1_page, "Hello from User 2!", "👍"
                )
                await asyncio.sleep(1)

                print("📥 Test 17: User2 sees reaction removed via WebSocket...")
                await asyncio.sleep(1.5)
                user2_message = user2_page.locator(".message-item").filter(
                    has_text="Hello from User 2!"
                )
                await expect(
                    user2_message.locator(".reaction-emoji").filter(has_text="👍")
                ).not_to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)

                print("✏️ Test 18: User1 edits message...")
                await self._edit_message_in_room(
                    user1_page, "Hello from User 1!", "Hello from User 1 (edited)!"
                )
                await asyncio.sleep(1)

                print("📥 Test 19: User2 sees edited message via WebSocket...")
                await expect(
                    user2_page.locator(".room-message-list").get_by_text(
                        "Hello from User 1 (edited)!"
                    )
                ).to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)

                print("🗑️ Test 20: User1 deletes message...")
                await self._delete_message_in_room(
                    user1_page, "Hello from User 1 (edited)!"
                )
                await asyncio.sleep(1)

                print(
                    "📥 Test 21: User2 sees deleted message indicator via WebSocket..."
                )
                await asyncio.sleep(2.5)
                await expect(
                    user2_page.locator(".deleted-indicator").first
                ).to_be_visible(timeout=10000)
                await asyncio.sleep(1.5)

                print("🚪 Test 22: User1 leaves room...")
                leave_btn = user1_page.locator(".leave-room-btn-header")
                await expect(leave_btn).to_be_visible()
                await leave_btn.click()
                await asyncio.sleep(2)

                print("👥 Test 23: Verifying member count decreased to 2...")
                await asyncio.sleep(1)
                user2_member_count = await user2_page.locator(
                    ".member-count"
                ).text_content()
                self.assertEqual(user2_member_count.strip(), "2 members")
                await asyncio.sleep(1.5)

                print("🚪 Test 24: User2 leaves room...")
                leave_btn2 = user2_page.locator(".leave-room-btn-header")
                await expect(leave_btn2).to_be_visible()
                await leave_btn2.click()
                await asyncio.sleep(2)

                print("✅ Test 25: Verifying join button reappears...")
                join_btn2 = user2_page.locator(".join-room-btn")
                await expect(join_btn2).to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)

                print("✅ All chat room WebSocket tests passed!")

            finally:
                await user1_context.close()
                await user2_context.close()
                await browser.close()

    async def _login(self, page, username, password):
        """Helper to login a user"""
        login_url = reverse('login')
        await page.goto(f"{self.live_server_url}{login_url}")
        await page.fill('input[name="username"]', username)
        await page.fill('input[name="password"]', password)
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")

    async def _send_message_in_room(self, page, message_text):
        """Helper to send a message in the chat room"""
        message_input = page.locator(".room-message-input")
        await message_input.fill(message_text)
        await message_input.press("Enter")
        await asyncio.sleep(1)

    async def _add_reaction_in_room(self, page, message_text, emoji):
        """Helper to add a reaction in the chat room"""
        await page.evaluate(
            """(messageText) => {
            const messages = document.querySelectorAll('.message-item');
            for (const msg of messages) {
                if (msg.textContent.includes(messageText)) {
                    const emojiBtns = msg.querySelectorAll('.emoji-btn');
                    for (const btn of emojiBtns) {
                        if (btn.offsetParent !== null) {
                            btn.click();
                            return true;
                        }
                    }
                }
            }
            return false;
        }""",
            message_text,
        )

        await asyncio.sleep(1)
        emoji_picker = page.locator("emoji-picker")
        await expect(emoji_picker).to_be_visible(timeout=5000)
        emoji_option = emoji_picker.get_by_text(emoji).first
        await emoji_option.click()
        await asyncio.sleep(1)

    async def _remove_reaction_in_room(self, page, message_text, emoji):
        """Helper to remove a reaction in the chat room"""
        message = page.locator(".message-item").filter(has_text=message_text)
        reaction = message.locator(".reaction-emoji").filter(has_text=emoji)
        await reaction.click()
        await asyncio.sleep(1)

    async def _edit_message_in_room(self, page, original_text, new_text):
        """Helper to edit a message in the chat room"""
        result = await page.evaluate(
            """(messageText) => {
            const messages = document.querySelectorAll('.message-item');
            for (const msg of messages) {
                if (msg.textContent.includes(messageText)) {
                    const contextMenuBtns = msg.querySelectorAll('.context-menu-btn');
                    let contextMenuBtn = null;
                    for (const btn of contextMenuBtns) {
                        if (btn.offsetParent !== null) {
                            contextMenuBtn = btn;
                            break;
                        }
                    }

                    if (!contextMenuBtn) {
                        return {success: false, error: 'Context menu button not found'};
                    }

                    contextMenuBtn.click();

                    const contextMenu = contextMenuBtn.parentElement.querySelector('.context-menu');
                    if (!contextMenu) {
                        return {success: false, error: 'Context menu element not found'};
                    }

                    contextMenu.classList.remove('hidden');

                    const editBtn = contextMenu.querySelector('.edit-btn');
                    if (!editBtn) {
                        return {success: false, error: 'Edit button not found'};
                    }

                    editBtn.click();
                    return {success: true};
                }
            }
            return {success: false, error: 'Message not found'};
        }""",
            original_text,
        )

        await asyncio.sleep(0.5)

        message_input = page.locator(".room-message-input")
        await message_input.fill(new_text)

        save_btn = page.locator(".edit-save-btn")
        await save_btn.click()
        await asyncio.sleep(1)

    async def _delete_message_in_room(self, page, message_text):
        """Helper to delete a message in the chat room"""
        result = await page.evaluate(
            """(messageText) => {
            const messages = document.querySelectorAll('.message-item');
            for (const msg of messages) {
                if (msg.textContent.includes(messageText)) {
                    const contextMenuBtns = msg.querySelectorAll('.context-menu-btn');
                    let contextMenuBtn = null;
                    for (const btn of contextMenuBtns) {
                        if (btn.offsetParent !== null) {
                            contextMenuBtn = btn;
                            break;
                        }
                    }

                    if (!contextMenuBtn) {
                        return {success: false, error: 'Context menu button not found'};
                    }

                    contextMenuBtn.click();

                    const contextMenu = contextMenuBtn.parentElement.querySelector('.context-menu');
                    if (!contextMenu) {
                        return {success: false, error: 'Context menu element not found'};
                    }

                    contextMenu.classList.remove('hidden');

                    const deleteBtn = contextMenu.querySelector('.delete-btn');
                    if (!deleteBtn) {
                        return {success: false, error: 'Delete button not found'};
                    }

                    deleteBtn.click();
                    return {success: true};
                }
            }
            return {success: false, error: 'Message not found'};
        }""",
            message_text,
        )

        await asyncio.sleep(1)
