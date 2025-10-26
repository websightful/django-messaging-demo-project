"""
Playwright tests for Chat Room frontend functionality.

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
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

User = get_user_model()


@pytest.mark.frontend
@pytest.mark.slow
@pytest.mark.polling
class ChatRoomFrontendTestCase(StaticLiveServerTestCase):
    """Test Chat Room functionality with Playwright using two browser contexts"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Import models here to avoid import issues
        from demo_project.apps.videos.models import Video
        from django_messaging.models import ChatRoom, ChatMembership
        
        # Create test users
        cls.user1 = User.objects.create_user(
            username="room_user1",
            password="testpass123",
            email="user1@test.com",
            first_name="User",
            last_name="One"
        )
        cls.user2 = User.objects.create_user(
            username="room_user2",
            password="testpass123",
            email="user2@test.com",
            first_name="User",
            last_name="Two"
        )
        cls.user3 = User.objects.create_user(
            username="room_user3",
            password="testpass123",
            email="user3@test.com",
            first_name="User",
            last_name="Three"
        )
        
        # Create a test video
        cls.video = Video.objects.create(
            title="Test Video for Chat Room",
            description="A test video with a chat room",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            embed_url="https://www.youtube.com/embed/dQw4w9WgXcQ",
            uploaded_by=cls.user1,
            is_public=True
        )
        
        # Create a chat room for the video
        content_type = ContentType.objects.get_for_model(Video)
        cls.room = ChatRoom.objects.create(
            content_type=content_type,
            object_id=cls.video.pk,
            title=f"Discussion: {cls.video.title}",
            is_room=True,
            is_group=True,
        )
        
        # Add user3 as an initial member
        ChatMembership.objects.create(
            chat=cls.room,
            user=cls.user3,
            role=ChatMembership.Role.MEMBER
        )

    def test_room_real_time_messaging(self):
        """Test complete chat room workflow with real-time updates"""
        asyncio.run(self._test_room_real_time_messaging())

    async def _test_room_real_time_messaging(self):
        """Async test for chat room real-time messaging"""
        async with async_playwright() as p:
            # Launch browser in headed mode with slow motion for visibility
            browser = await p.chromium.launch(headless=False, slow_mo=500)

            # Create normal context for user1
            user1_context = await browser.new_context()
            user1_page = await user1_context.new_page()

            # Create incognito context for user2
            user2_context = await browser.new_context()
            user2_page = await user2_context.new_page()

            try:
                # Login both users
                print("🔐 Logging in users...")
                await self._login(user1_page, "room_user1", "testpass123")
                await self._login(user2_page, "room_user2", "testpass123")
                await asyncio.sleep(1)  # Visual pause

                # Navigate both users to the video page with chat room
                print("🌐 Navigating to video page with chat room...")
                video_detail_url = reverse('videos:detail', kwargs={'pk': self.video.pk})
                await user1_page.goto(f"{self.live_server_url}{video_detail_url}")
                await user1_page.wait_for_load_state("networkidle")
                await asyncio.sleep(1)  # Visual pause

                await user2_page.goto(f"{self.live_server_url}{video_detail_url}")
                await user2_page.wait_for_load_state("networkidle")
                await asyncio.sleep(1)  # Visual pause

                # Test 1: Verify initial member count (only user3 is a member)
                print("👥 Test 1: Verifying initial member count...")
                await asyncio.sleep(2)  # Wait for room widget to initialize
                user1_member_count = await user1_page.locator(".member-count").text_content()
                self.assertEqual(user1_member_count.strip(), "1 member")
                await asyncio.sleep(1)  # Visual pause

                # Test 2: User1 joins the room
                print("➕ Test 2: User1 joining room...")
                join_btn = user1_page.locator(".join-room-btn")
                await expect(join_btn).to_be_visible()
                await join_btn.click()
                await asyncio.sleep(2)  # Wait for join to complete

                # Test 3: Verify member count increased to 2
                print("👥 Test 3: Verifying member count increased to 2...")
                await asyncio.sleep(1)
                user1_member_count = await user1_page.locator(".member-count").text_content()
                self.assertEqual(user1_member_count.strip(), "2 members")
                await asyncio.sleep(1.5)  # Visual pause

                # Test 4: User2 sees the updated member count in real-time
                print("📥 Test 4: User2 sees member count update in real-time...")
                await asyncio.sleep(4)
                user2_member_count = await user2_page.locator(".member-count").text_content()
                self.assertEqual(user2_member_count.strip(), "2 members")
                await asyncio.sleep(1.5)  # Visual pause

                # Test 5: User2 joins the room
                print("➕ Test 5: User2 joining room...")
                join_btn2 = user2_page.locator(".join-room-btn")
                await expect(join_btn2).to_be_visible()
                await join_btn2.click()
                await asyncio.sleep(2)  # Wait for join to complete

                # Test 6: Verify member count increased to 3
                print("👥 Test 6: Verifying member count increased to 3...")
                await asyncio.sleep(1)
                user2_member_count = await user2_page.locator(".member-count").text_content()
                self.assertEqual(user2_member_count.strip(), "3 members")
                await asyncio.sleep(1.5)  # Visual pause

                # Test 7: User1 sees the updated member count in real-time
                print("📥 Test 7: User1 sees member count update in real-time...")
                await asyncio.sleep(2)
                user1_member_count = await user1_page.locator(".member-count").text_content()
                self.assertEqual(user1_member_count.strip(), "3 members")
                await asyncio.sleep(1.5)  # Visual pause

                # Test 8: User1 sends a message
                print("📤 Test 8: User1 sends message...")
                await self._send_message_in_room(user1_page, "Hello from User 1!")
                await asyncio.sleep(1)  # Visual pause

                # Verify message appears in user1's room
                await expect(
                    user1_page.locator(".room-message-list").get_by_text("Hello from User 1!")
                ).to_be_visible(timeout=5000)
                await asyncio.sleep(1)  # Visual pause

                # Test 9: User2 receives the message in real-time
                print("📥 Test 9: User2 receives message in real-time...")
                await expect(
                    user2_page.locator(".room-message-list").get_by_text("Hello from User 1!")
                ).to_be_visible(timeout=10000)
                await asyncio.sleep(1.5)  # Visual pause

                # Test 10: User2 sends a reply
                print("📤 Test 10: User2 sends reply...")
                await self._send_message_in_room(user2_page, "Hello from User 2!")
                await asyncio.sleep(1)  # Visual pause

                # Test 11: User1 receives the reply in real-time
                print("📥 Test 11: User1 receives reply in real-time...")
                await expect(
                    user1_page.locator(".room-message-list").get_by_text("Hello from User 2!")
                ).to_be_visible(timeout=10000)
                await asyncio.sleep(1.5)  # Visual pause

                # Test 12: User1 adds a reaction to user2's message
                print("👍 Test 12: User1 adds reaction...")
                await self._add_reaction_in_room(user1_page, "Hello from User 2!", "👍")
                await asyncio.sleep(1)  # Visual pause

                # Test 13: User2 sees the reaction in real-time
                print("📥 Test 13: User2 sees reaction in real-time...")
                await asyncio.sleep(2)
                user2_message = user2_page.locator(".message-item").filter(has_text="Hello from User 2!")
                await expect(user2_message.locator(".reaction-emoji").filter(has_text="👍")).to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)  # Visual pause

                # Test 14: User2 adds a reaction to user1's message
                print("❤️ Test 14: User2 adds reaction...")
                await self._add_reaction_in_room(user2_page, "Hello from User 1!", "❤️")
                await asyncio.sleep(1)  # Visual pause

                # Test 15: User1 sees the reaction in real-time
                print("📥 Test 15: User1 sees reaction in real-time...")
                await asyncio.sleep(2)
                user1_message = user1_page.locator(".message-item").filter(has_text="Hello from User 1!")
                await expect(user1_message.locator(".reaction-emoji").filter(has_text="❤️")).to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)  # Visual pause

                # Test 16: User1 removes their reaction
                print("🗑️ Test 16: User1 removes reaction...")
                await self._remove_reaction_in_room(user1_page, "Hello from User 2!", "👍")
                await asyncio.sleep(1)  # Visual pause

                # Test 17: User2 sees reaction removed in real-time
                print("📥 Test 17: User2 sees reaction removed...")
                await asyncio.sleep(2)
                user2_message = user2_page.locator(".message-item").filter(has_text="Hello from User 2!")
                await expect(user2_message.locator(".reaction-emoji").filter(has_text="👍")).not_to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)  # Visual pause

                # Test 18: User1 edits their message
                print("✏️ Test 18: User1 edits message...")
                await self._edit_message_in_room(user1_page, "Hello from User 1!", "Hello from User 1 (edited)!")
                await asyncio.sleep(1)  # Visual pause

                # Test 19: User2 sees the edited message in real-time
                print("📥 Test 19: User2 sees edited message...")
                await expect(
                    user2_page.locator(".room-message-list").get_by_text("Hello from User 1 (edited)!")
                ).to_be_visible(timeout=10000)
                await asyncio.sleep(1.5)  # Visual pause

                # Test 20: User1 deletes their message
                print("🗑️ Test 20: User1 deletes message...")
                await self._delete_message_in_room(user1_page, "Hello from User 1 (edited)!")
                await asyncio.sleep(1)  # Visual pause

                # Test 21: User2 sees the deleted message indicator in real-time
                print("📥 Test 21: User2 sees deleted message indicator...")
                await asyncio.sleep(4)
                await expect(
                    user2_page.locator(".deleted-indicator").first
                ).to_be_visible(timeout=10000)
                await asyncio.sleep(1.5)  # Visual pause

                # Test 22: User1 leaves the room
                print("🚪 Test 22: User1 leaves room...")
                leave_btn = user1_page.locator(".leave-room-btn-header")
                await expect(leave_btn).to_be_visible()
                await leave_btn.click()
                await asyncio.sleep(2)  # Wait for leave to complete

                # Test 23: Verify member count decreased to 2
                print("👥 Test 23: Verifying member count decreased to 2...")
                await asyncio.sleep(1)
                user2_member_count = await user2_page.locator(".member-count").text_content()
                self.assertEqual(user2_member_count.strip(), "2 members")
                await asyncio.sleep(1.5)  # Visual pause

                # Test 24: User2 leaves the room
                print("🚪 Test 24: User2 leaves room...")
                leave_btn2 = user2_page.locator(".leave-room-btn-header")
                await expect(leave_btn2).to_be_visible()
                await leave_btn2.click()
                await asyncio.sleep(2)  # Wait for leave to complete

                # Test 25: Verify join button is visible again for user2
                print("✅ Test 25: Verifying join button reappears...")
                join_btn2 = user2_page.locator(".join-room-btn")
                await expect(join_btn2).to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)  # Visual pause

                print("✅ All chat room frontend tests passed!")

            finally:
                # Cleanup
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
        await asyncio.sleep(1)  # Wait for message to be sent

    async def _add_reaction_in_room(self, page, message_text, emoji):
        """Helper to add a reaction in the chat room"""
        await page.evaluate("""(messageText) => {
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
        }""", message_text)

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
        await asyncio.sleep(1)  # Wait for reaction to be removed

    async def _edit_message_in_room(self, page, original_text, new_text):
        """Helper to edit a message in the chat room"""
        result = await page.evaluate("""(messageText) => {
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
        }""", original_text)

        await asyncio.sleep(0.5)

        message_input = page.locator(".room-message-input")
        await message_input.fill(new_text)

        save_btn = page.locator(".edit-save-btn")
        await save_btn.click()
        await asyncio.sleep(1)

    async def _delete_message_in_room(self, page, message_text):
        """Helper to delete a message in the chat room"""
        result = await page.evaluate("""(messageText) => {
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
        }""", message_text)

        await asyncio.sleep(1)

