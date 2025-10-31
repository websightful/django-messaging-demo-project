"""
Playwright tests for Messages page frontend functionality.

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
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from .conftest import position_browser_windows_side_by_side

User = get_user_model()


@pytest.mark.frontend
@pytest.mark.slow
@pytest.mark.polling
@override_settings(
    DJANGO_MESSAGING={
        "BASE_TEMPLATE": "base.html",
        "TOP_NAVIGATION_HEIGHT": "72px",
        "TRANSPORT": "polling",
        "SHOW_DELETED_MESSAGE_INDICATORS": True,
    }
)
class MessagesFrontendTestCase(StaticLiveServerTestCase):
    """Test Messages page functionality with Playwright using two browser contexts"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Import models here to avoid import issues
        from demo_project.apps.videos.models import Video
        from django_messaging.models import ChatRoom, ChatMembership
        
        # Create test users
        cls.user1 = User.objects.create_user(
            username="msg_user1",
            password="testpass123",
            email="msguser1@test.com",
            first_name="Message",
            last_name="UserOne"
        )
        cls.user2 = User.objects.create_user(
            username="msg_user2",
            password="testpass123",
            email="msguser2@test.com",
            first_name="Message",
            last_name="UserTwo"
        )
        cls.user3 = User.objects.create_user(
            username="msg_user3",
            password="testpass123",
            email="msguser3@test.com",
            first_name="Message",
            last_name="UserThree"
        )
        
        # Create a test video for room testing
        cls.video = Video.objects.create(
            title="Test Video for Messages",
            description="A test video with a chat room",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            embed_url="https://www.youtube.com/embed/dQw4w9WgXcQ",
            uploaded_by=cls.user1,
            is_public=True
        )
        
        # Create a public chat room
        content_type = ContentType.objects.get_for_model(Video)
        cls.public_room = ChatRoom.objects.create(
            content_type=content_type,
            object_id=cls.video.pk,
            title="Public Test Room",
            is_room=True,
            is_group=True,
        )

    def test_messages_page_functionality(self):
        """Test complete messages page workflow"""
        asyncio.run(self._test_messages_page_functionality())

    async def _test_messages_page_functionality(self):
        """Async test for messages page functionality"""
        async with async_playwright() as p:
            # Launch browser in headed mode with slow motion for visibility
            browser = await p.chromium.launch(headless=False, slow_mo=500)

            # Create normal context for user1
            user1_context = await browser.new_context()
            user1_page = await user1_context.new_page()

            # Create incognito context for user2
            user2_context = await browser.new_context()
            user2_page = await user2_context.new_page()

            # Position windows side by side
            await position_browser_windows_side_by_side(user1_page, user2_page)

            try:
                # Login both users
                print("🔐 Logging in users...")
                await self._login(user1_page, "msg_user1", "testpass123")
                await self._login(user2_page, "msg_user2", "testpass123")

                # Navigate both users to messages page
                print("🌐 Navigating to messages page...")
                messages_url = reverse('django_messaging:messaging-view')
                await user1_page.goto(f"{self.live_server_url}{messages_url}")
                await user1_page.wait_for_load_state("networkidle")

                await user2_page.goto(f"{self.live_server_url}{messages_url}")
                await user2_page.wait_for_load_state("networkidle")

                # Test 1: Create a new chat (user1)
                print("➕ Test 1: Creating new chat...")
                await self._create_new_chat(user1_page)
                await asyncio.sleep(1)

                # Verify chat appears in chat list and is selected
                chat_list = user1_page.locator("#chat-list")
                await expect(chat_list.locator(".chat-item").first).to_be_visible(timeout=10000)

                # Wait for chat to be loaded (it's already selected by createNewChat)
                chat_title = user1_page.locator("#current-chat-name")
                await expect(chat_title).to_be_visible(timeout=10000)

                # Test 2: Rename the chat
                print("✏️ Test 2: Renaming chat...")
                await self._rename_chat(user1_page, "Test Group Chat")
                await asyncio.sleep(2)

                # Verify chat title updated
                await expect(chat_title).to_have_text("Test Group Chat")

                # Test 3: Search for user2 and add them to the chat
                print("👥 Test 3: Adding user2 to chat...")
                await self._open_members_dialog(user1_page)
                await self._search_and_add_user(user1_page, "msg_user2")
                await asyncio.sleep(2)

                # Test 4: User2 sees the new chat in real-time
                print("📥 Test 4: User2 sees new chat in real-time...")
                await asyncio.sleep(2)
                user2_chat_list = user2_page.locator("#chat-list")
                await expect(user2_chat_list.get_by_text("Test Group Chat")).to_be_visible(timeout=10000)

                # Test 5: User1 sends a message
                print("📤 Test 5: User1 sends message...")
                await self._send_message(user1_page, "Hello in the group!")

                # Test 6: User2 receives the message (chat is not selected)
                # Verify unread indicator appears on the chat
                print("📥 Test 6: User2 sees unread indicator...")
                await asyncio.sleep(2)
                user2_chat_item = user2_page.locator(".chat-item").filter(has_text="Test Group Chat")
                await expect(user2_chat_item.locator(".unread-indicator")).to_be_visible(timeout=10000)

                # Test 7: User2 selects the chat and sees the message
                print("👁️ Test 7: User2 selects chat and sees message...")
                await user2_chat_item.click()
                await asyncio.sleep(2)
                await expect(user2_page.locator("#message-list").get_by_text("Hello in the group!")).to_be_visible(timeout=10000)

                # Test 8: Search for user3 and add them to the chat
                print("👥 Test 8: Adding user3 to chat...")
                await self._open_members_dialog(user1_page)
                await self._search_and_add_user(user1_page, "msg_user3")
                await asyncio.sleep(2)

                # Test 9: Remove user3 from the chat
                print("🗑️ Test 9: Removing user3 from chat...")
                await self._open_members_dialog(user1_page)
                await self._switch_to_manage_members_tab(user1_page)
                await asyncio.sleep(1)
                await self._remove_member(user1_page, "msg_user3")
                await asyncio.sleep(2.5)

                # Test 10: Browse and join a public room (user2)
                print("🏠 Test 10: User2 browses and joins public room...")
                await self._browse_rooms(user2_page)
                await self._join_room_from_dialog(user2_page, "Public Test Room")
                await asyncio.sleep(2)

                # Verify room appears in chat list
                await expect(user2_page.locator("#chat-list").get_by_text("Public Test Room")).to_be_visible(timeout=10000)

                # Test 11: Leave the room (user2)
                print("🚪 Test 11: User2 leaves room...")
                await self._select_chat_by_title(user2_page, "Public Test Room")
                await asyncio.sleep(1)
                await self._leave_chat(user2_page)
                await asyncio.sleep(2.5)

                # Test 12: User1 leaves the group chat (admin transfer)
                print("🚪 Test 12: User1 leaves chat (admin transfer)...")
                # First, select the group chat
                await self._select_chat_by_title(user1_page, "Test Group Chat")
                await asyncio.sleep(1)

                # Leave the chat
                await self._leave_chat(user1_page)
                await asyncio.sleep(2)

                # Verify user2 is now admin (they should see the members button)
                print("👑 Verifying user2 is now admin...")
                await asyncio.sleep(2)
                # User2 needs to select the chat to see the members button
                await self._select_chat_by_title(user2_page, "Test Group Chat")
                await asyncio.sleep(1)
                members_btn = user2_page.locator("#members-btn")
                await expect(members_btn).to_be_visible(timeout=10000)

                # Test 13: User2 deletes the chat
                print("🗑️ Test 13: User2 deletes chat...")
                await self._delete_chat(user2_page)
                await asyncio.sleep(2)

                # Verify chat is removed from chat list
                await expect(user2_page.locator("#chat-list").get_by_text("Test Group Chat")).not_to_be_visible(timeout=10000)

                print("✅ All messages page frontend tests passed!")

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

    async def _create_new_chat(self, page):
        """Helper to create a new chat"""
        new_chat_btn = page.locator("#new-chat-btn")
        await new_chat_btn.click()
        await asyncio.sleep(2.5)  # Wait for chat to be created, selected, and members dialog to open

        # Close the members dialog that automatically opens
        close_btn = page.locator("#close-dialog-btn")
        await close_btn.click()
        await asyncio.sleep(1)  # Wait for dialog to close and chat to fully load

    async def _rename_chat(self, page, new_title):
        """Helper to rename a chat"""
        # Click on the chat title to edit
        chat_title = page.locator("#current-chat-name")
        await chat_title.click()
        await asyncio.sleep(0.5)

        # Fill in the new title
        title_input = page.locator(".chat-title-input")
        await title_input.fill(new_title)

        # Save the title
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
        # Enter search query
        search_input = page.locator("#user-search-input")
        await search_input.fill(username)
        
        # Click search button
        search_btn = page.locator("#search-btn")
        await search_btn.click()
        await asyncio.sleep(1)
        
        # Click add button for the user
        add_btn = page.locator(".add-user-btn").first
        await add_btn.click()
        await asyncio.sleep(1)
        
        # Close dialog
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
        # Find the member item and click remove
        member_item = page.locator(".member-item").filter(has_text=username)
        remove_btn = member_item.locator(".remove-member-btn")
        await remove_btn.click()
        await asyncio.sleep(0.5)

        # Confirm the removal in the confirmation dialog
        confirm_btn = page.locator("#confirmation-confirm-btn")
        await confirm_btn.click()
        await asyncio.sleep(1)

        # Close members dialog
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
        # Find the room and click join
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
        # Click the leave chat button
        leave_btn = page.locator("#leave-chat-btn")
        await leave_btn.click()
        await asyncio.sleep(0.5)

        # Confirm in the confirmation dialog
        confirm_btn = page.locator("#confirmation-confirm-btn")
        await confirm_btn.click()
        await asyncio.sleep(1)

    async def _delete_chat(self, page):
        """Helper to delete the current chat"""
        # Open chat menu
        chat_menu_btn = page.locator("#chat-menu-btn")
        await chat_menu_btn.click()
        await asyncio.sleep(0.5)

        # Click delete option
        delete_btn = page.locator("#delete-chat-btn")
        await delete_btn.click()
        await asyncio.sleep(0.5)

        # Confirm in the confirmation dialog
        confirm_btn = page.locator("#confirmation-confirm-btn")
        await confirm_btn.click()
        await asyncio.sleep(1)

