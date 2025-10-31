"""
Playwright tests for DM (Direct Messaging) frontend functionality.

Tests real-time messaging features between two users:
- Sender in normal Chromium window
- Receiver in incognito Chromium window viewing messages page

Tests cover:
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
class DMFrontendTestCase(StaticLiveServerTestCase):
    """Test DM functionality with Playwright using two browser contexts"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test users
        cls.sender = User.objects.create_user(
            username="sender_user",
            password="testpass123",
            email="sender@test.com",
            first_name="Sender",
            last_name="User"
        )
        cls.receiver = User.objects.create_user(
            username="receiver_user",
            password="testpass123",
            email="receiver@test.com",
            first_name="Receiver",
            last_name="User"
        )

    def test_dm_real_time_messaging(self):
        """Test complete DM workflow with real-time updates"""
        asyncio.run(self._test_dm_real_time_messaging())

    async def _test_dm_real_time_messaging(self):
        """Async test for DM real-time messaging"""
        async with async_playwright() as p:
            # Launch browser in headed mode with slow motion for visibility
            browser = await p.chromium.launch(headless=False, slow_mo=500)

            # Create normal context for sender
            sender_context = await browser.new_context()
            sender_page = await sender_context.new_page()

            # Create incognito context for receiver
            receiver_context = await browser.new_context()
            receiver_page = await receiver_context.new_page()

            # Add console message listeners for debugging
            receiver_page.on("console", lambda msg: print(f"[RECEIVER CONSOLE] {msg.type}: {msg.text}"))
            sender_page.on("console", lambda msg: print(f"[SENDER CONSOLE] {msg.type}: {msg.text}"))

            # Position windows side by side
            await position_browser_windows_side_by_side(sender_page, receiver_page)

            try:
                # Login sender
                await self._login(sender_page, "sender_user", "testpass123")

                # Login receiver
                await self._login(receiver_page, "receiver_user", "testpass123")

                # Navigate receiver to messages page
                messages_url = reverse('django_messaging:messaging-view')
                await receiver_page.goto(f"{self.live_server_url}{messages_url}")
                await receiver_page.wait_for_load_state("networkidle")

                # Verify polling transport is loaded
                transport_check = await receiver_page.evaluate("""
                    () => {
                        return {
                            hasPollingTransport: typeof PollingTransport !== 'undefined',
                            hasWebSocketTransport: typeof WebSocketTransport !== 'undefined',
                            transportType: window.chatApp?.wsTransport?.constructor?.name || 'unknown'
                        };
                    }
                """)
                print(f"🔍 Transport check: {transport_check}")
                if not transport_check['hasPollingTransport']:
                    print("⚠️ WARNING: PollingTransport not loaded!")
                if transport_check['transportType'] != 'PollingTransport':
                    print(f"⚠️ WARNING: Using {transport_check['transportType']} instead of PollingTransport!")

                # Navigate sender to receiver's profile page
                person_detail_url = reverse('people:person_detail', kwargs={'user_id': self.receiver.id})
                await sender_page.goto(f"{self.live_server_url}{person_detail_url}")
                await sender_page.wait_for_load_state("networkidle")
                await asyncio.sleep(1)

                # Open DM widget on sender's page
                chat_toggle_btn = sender_page.locator("#chat-toggle-btn")
                await expect(chat_toggle_btn).to_be_visible()
                await chat_toggle_btn.click()

                # Wait for widget to be visible
                widget = sender_page.locator("#fixed-chat-widget")
                await expect(widget).to_be_visible()

                # Test 1: Send a message from sender
                print("📤 Test 1: Sending message from sender...")
                await self._send_message_in_widget(sender_page, "Hello from sender!")
                await asyncio.sleep(2)  # Wait for message to be sent and saved

                # Verify message appears in sender's widget
                await expect(
                    sender_page.locator("#widget-message-list").get_by_text("Hello from sender!")
                ).to_be_visible(timeout=10000)

                # Test 2: Receiver sees new chat appear and selects it
                print("📥 Test 2: Receiver sees new chat and selects it...")
                print("⏳ Waiting for polling to fetch new chat (polling interval is 3s)...")

                # Wait for at least one polling cycle (3 seconds) plus some buffer
                await asyncio.sleep(4)

                # Wait for chat to appear in chat list
                # Use just first name since that's what appears in the chat item
                sender_name = self.sender.first_name
                chat_item = receiver_page.locator(".chat-item").filter(has_text=sender_name)

                # Try to find the chat, if not found, wait for next polling cycle
                try:
                    await expect(chat_item).to_be_visible(timeout=8000)  # Wait up to 8 more seconds
                except Exception as e:
                    print(f"⚠️ Chat not visible yet, waiting for next polling cycle...")
                    await asyncio.sleep(3)  # Wait for another polling cycle
                    await expect(chat_item).to_be_visible(timeout=10000)

                # Click on the chat to open it
                await chat_item.click()
                await asyncio.sleep(2)  # Wait for chat to load

                # Wait for message list to be visible (use ID selector)
                message_list = receiver_page.locator("#message-list")
                await expect(message_list).to_be_visible(timeout=10000)

                # Verify receiver sees the message
                print("📥 Verifying receiver sees message...")
                await expect(
                    message_list.get_by_text("Hello from sender!")
                ).to_be_visible(timeout=10000)

                # Test 3: Receiver sends a reply
                print("📤 Test 3: Receiver sends reply...")
                await self._send_message_in_messages_page(receiver_page, "Hello from receiver!")

                # Verify sender receives the reply in real-time
                print("📥 Verifying sender receives reply in real-time...")
                await expect(
                    sender_page.locator("#widget-message-list").get_by_text("Hello from receiver!")
                ).to_be_visible(timeout=10000)

                # Test 4: Sender adds a reaction to receiver's message
                print("👍 Test 4: Sender adds reaction...")
                await self._add_reaction_in_widget(sender_page, "Hello from receiver!", "👍")

                # Test 5: Verify receiver sees the reaction in real-time
                print("📥 Test 5: Verifying receiver sees reaction in real-time...")
                receiver_message = receiver_page.locator("#message-list [data-message-id]").filter(has_text="Hello from receiver!")
                await expect(receiver_message.locator(".reaction").filter(has_text="👍")).to_be_visible(timeout=15000)

                # Test 6: Receiver adds a reaction to sender's message
                print("❤️ Test 6: Receiver adds reaction...")
                await self._add_reaction_in_messages_page(receiver_page, "Hello from sender!", "❤️")

                # Test 7: Verify sender sees the reaction in real-time
                print("📥 Test 7: Verifying sender sees reaction in real-time...")
                sender_message = sender_page.locator("#widget-message-list [data-message-id]").filter(has_text="Hello from sender!")
                await expect(sender_message.locator(".reaction").filter(has_text="❤️")).to_be_visible(timeout=15000)

                # Test 8: Sender removes their reaction
                print("🗑️ Test 8: Sender removes reaction...")
                await self._remove_reaction_in_widget(sender_page, "Hello from receiver!", "👍")

                # Test 9: Verify receiver sees reaction removed in real-time
                print("📥 Test 9: Verifying receiver sees reaction removed...")
                receiver_message = receiver_page.locator("#message-list [data-message-id]").filter(has_text="Hello from receiver!")
                await expect(receiver_message.locator(".reaction").filter(has_text="👍")).not_to_be_visible(timeout=15000)

                # Test 10: Receiver removes their reaction
                print("🗑️ Test 10: Receiver removes reaction...")
                await self._remove_reaction_in_messages_page(receiver_page, "Hello from sender!", "❤️")

                # Test 11: Verify sender sees reaction removed in real-time
                print("📥 Test 11: Verifying sender sees reaction removed...")
                sender_message = sender_page.locator("#widget-message-list [data-message-id]").filter(has_text="Hello from sender!")
                await expect(sender_message.locator(".reaction").filter(has_text="❤️")).not_to_be_visible(timeout=15000)

                # Test 12: Sender edits their message
                print("✏️ Test 12: Sender edits message...")
                await self._edit_message_in_widget(sender_page, "Hello from sender!", "Hello from sender (edited)!")

                # Test 13: Verify receiver sees the edited message in real-time
                print("📥 Test 13: Verifying receiver sees edited message...")
                await expect(
                    receiver_page.locator("#message-list").get_by_text("Hello from sender (edited)!")
                ).to_be_visible(timeout=10000)
                # Click message bubble to show timestamp with edited indicator
                edited_message = receiver_page.locator("#message-list [data-message-id]").filter(has_text="Hello from sender (edited)!")
                await edited_message.locator(".message-bubble").click()
                await asyncio.sleep(0.3)  # Wait for timestamp to appear
                timestamp = edited_message.locator(".message-timestamp")
                await expect(timestamp).to_be_visible()
                await expect(timestamp).to_contain_text("Edited")

                # Test 14: Receiver edits their message
                print("✏️ Test 14: Receiver edits message...")
                await self._edit_message_in_messages_page(receiver_page, "Hello from receiver!", "Hello from receiver (edited)!")

                # Test 15: Verify sender sees the edited message in real-time
                print("📥 Test 15: Verifying sender sees edited message...")
                await expect(
                    sender_page.locator("#widget-message-list").get_by_text("Hello from receiver (edited)!")
                ).to_be_visible(timeout=10000)
                # Click message bubble to show timestamp with edited indicator
                edited_message_widget = sender_page.locator("#widget-message-list [data-message-id]").filter(has_text="Hello from receiver (edited)!")
                await edited_message_widget.locator(".message-bubble").click()
                await asyncio.sleep(0.3)  # Wait for timestamp to appear
                timestamp_widget = edited_message_widget.locator(".message-timestamp")
                await expect(timestamp_widget).to_be_visible()
                await expect(timestamp_widget).to_contain_text("Edited")

                # Test 16: Sender deletes their message
                print("🗑️ Test 16: Sender deletes message...")
                await self._delete_message_in_widget(sender_page, "Hello from sender (edited)!")

                # Test 17: Verify receiver sees the deleted message in real-time
                print("📥 Test 17: Verifying receiver sees deleted message...")
                await asyncio.sleep(4)  # Wait for polling to detect the deletion
                await expect(
                    receiver_page.locator(".deleted-indicator").first
                ).to_be_visible(timeout=10000)

                # Test 18: Receiver deletes their message
                print("🗑️ Test 18: Receiver deletes message...")
                await self._delete_message_in_messages_page(receiver_page, "Hello from receiver (edited)!")

                # Test 19: Verify sender sees the deleted message in real-time
                print("📥 Test 19: Verifying sender sees deleted message...")
                await asyncio.sleep(4)  # Wait for polling to detect the deletion
                await expect(
                    sender_page.locator(".deleted-indicator").first
                ).to_be_visible(timeout=10000)

                print("✅ All DM frontend tests passed!")

            finally:
                # Cleanup
                await sender_context.close()
                await receiver_context.close()
                await browser.close()

    async def _login(self, page, username, password):
        """Helper to login a user"""
        login_url = reverse('login')
        await page.goto(f"{self.live_server_url}{login_url}")
        await page.fill('input[name="username"]', username)
        await page.fill('input[name="password"]', password)
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")

    async def _send_message_in_widget(self, page, message_text):
        """Helper to send a message in the DM widget"""
        message_input = page.locator("#widget-message-input")
        await message_input.fill(message_text)
        await message_input.press("Enter")
        await asyncio.sleep(1)

    async def _send_message_in_messages_page(self, page, message_text):
        """Helper to send a message in the messages page"""
        # Find the active chat and send message
        message_input = page.locator("#message-input")
        await message_input.fill(message_text)
        await message_input.press("Enter")
        await asyncio.sleep(1)

    async def _add_reaction_in_widget(self, page, message_text, emoji):
        """Helper to add a reaction in the DM widget"""
        # Messages in widget have data-message-id attribute, not message-item class
        message = page.locator("#widget-message-list [data-message-id]").filter(has_text=message_text)

        # Find the visible emoji button (one container has display:none, the other has display:flex)
        # Use JavaScript to click the visible emoji button
        await page.evaluate("""(messageText) => {
            const messages = document.querySelectorAll('#widget-message-list [data-message-id]');
            for (const msg of messages) {
                if (msg.textContent.includes(messageText)) {
                    // Find all emoji buttons in this message
                    const emojiBtns = msg.querySelectorAll('.emoji-btn');
                    for (const btn of emojiBtns) {
                        // Check if button is in a visible container (offsetParent !== null means it's rendered)
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
        # Wait for emoji picker to be visible
        emoji_picker = page.locator("emoji-picker")
        await expect(emoji_picker).to_be_visible(timeout=10000)
        # Click the emoji in the picker
        emoji_option = emoji_picker.get_by_text(emoji).first
        await emoji_option.click()
        await asyncio.sleep(1)

    async def _add_reaction_in_messages_page(self, page, message_text, emoji):
        """Helper to add a reaction in the messages page"""
        # Messages have data-message-id attribute, not message-item class
        message = page.locator("#message-list [data-message-id]").filter(has_text=message_text)

        # Find the visible emoji button (one container has display:none, the other has display:flex)
        # Use JavaScript to click the visible emoji button
        await page.evaluate("""(messageText) => {
            const messages = document.querySelectorAll('#message-list [data-message-id]');
            for (const msg of messages) {
                if (msg.textContent.includes(messageText)) {
                    // Find all emoji buttons in this message
                    const emojiBtns = msg.querySelectorAll('.emoji-btn');
                    for (const btn of emojiBtns) {
                        // Check if button is in a visible container (offsetParent !== null means it's rendered)
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
        # Wait for emoji picker to be visible
        emoji_picker = page.locator("emoji-picker")
        await expect(emoji_picker).to_be_visible(timeout=10000)
        # Click the emoji in the picker
        emoji_option = emoji_picker.get_by_text(emoji).first
        await emoji_option.click()
        await asyncio.sleep(1)

    async def _remove_reaction_in_widget(self, page, message_text, emoji):
        """Helper to remove a reaction in the DM widget"""
        message = page.locator("#widget-message-list [data-message-id]").filter(has_text=message_text)
        # Click the reaction button (not the emoji span which has pointer-events-none)
        reaction_button = message.locator(".reaction").filter(has_text=emoji)
        await reaction_button.click()
        await asyncio.sleep(1)

    async def _remove_reaction_in_messages_page(self, page, message_text, emoji):
        """Helper to remove a reaction in the messages page"""
        message = page.locator("#message-list [data-message-id]").filter(has_text=message_text)
        # Click the reaction button (not the emoji span which has pointer-events-none)
        reaction_button = message.locator(".reaction").filter(has_text=emoji)
        await reaction_button.click()
        await asyncio.sleep(1)

    async def _edit_message_in_widget(self, page, original_text, new_text):
        """Helper to edit a message in the DM widget"""
        # Use JavaScript to click the visible context menu button and edit button
        await page.evaluate("""(messageText) => {
            const messages = document.querySelectorAll('#widget-message-list [data-message-id]');
            for (const msg of messages) {
                if (msg.textContent.includes(messageText)) {
                    const contextMenuBtns = msg.querySelectorAll('.context-menu-btn');
                    for (const btn of contextMenuBtns) {
                        if (btn.offsetParent !== null) {
                            btn.click();
                            return true;
                        }
                    }
                }
            }
            return false;
        }""", original_text)

        await asyncio.sleep(0.5)

        # Use JavaScript to click the edit button
        await page.evaluate("""() => {
            const editBtn = document.querySelector('#fixed-chat-widget .edit-btn');
            if (editBtn) {
                editBtn.click();
                return true;
            }
            return false;
        }""")

        await asyncio.sleep(0.3)

        # Edit the message in the main message input field
        message_input = page.locator("#widget-message-input")
        await message_input.fill(new_text)
        # Save the edit
        save_btn = page.locator("#fixed-chat-widget .edit-save-btn")
        await save_btn.click()
        await asyncio.sleep(1)

    async def _edit_message_in_messages_page(self, page, original_text, new_text):
        """Helper to edit a message in the messages page"""
        # Use JavaScript to find the message, open context menu, and click edit - all in one call
        result = await page.evaluate("""(messageText) => {
            const messages = document.querySelectorAll('#message-list [data-message-id]');
            for (const msg of messages) {
                if (msg.textContent.includes(messageText)) {
                    // Find and click the visible context menu button
                    const contextMenuBtns = msg.querySelectorAll('.context-menu-btn');
                    let contextMenuBtn = null;
                    for (const btn of contextMenuBtns) {
                        if (btn.offsetParent !== null) {
                            contextMenuBtn = btn;
                            break;
                        }
                    }

                    if (!contextMenuBtn) {
                        return {success: false, error: 'Context menu button not found or not visible'};
                    }

                    // Click to open context menu
                    contextMenuBtn.click();

                    // Find the context menu (it's a sibling of the button)
                    const contextMenu = contextMenuBtn.parentElement.querySelector('.context-menu');
                    if (!contextMenu) {
                        return {success: false, error: 'Context menu element not found'};
                    }

                    // Remove hidden class to show menu
                    contextMenu.classList.remove('hidden');

                    // Find and click the edit button
                    const editBtn = contextMenu.querySelector('.edit-btn');
                    if (!editBtn) {
                        return {success: false, error: 'Edit button not found in context menu'};
                    }

                    editBtn.click();
                    return {success: true};
                }
            }
            return {success: false, error: 'Message not found'};
        }""", original_text)

        if not result['success']:
            raise Exception(f"Could not edit message: {result.get('error', 'Unknown error')}")

        await asyncio.sleep(0.5)

        # Edit the message in the main message input field
        message_input = page.locator("#message-input")
        await message_input.fill(new_text)

        await asyncio.sleep(0.3)

        # Save the edit - edit buttons are added to the form, not scoped to messages-container
        save_btn = page.locator(".edit-save-btn")
        await save_btn.click()
        await asyncio.sleep(1)

    async def _delete_message_in_widget(self, page, message_text):
        """Helper to delete a message in the DM widget"""
        # Use JavaScript to find the message, open context menu, and click delete - all in one call
        result = await page.evaluate("""(messageText) => {
            const messages = document.querySelectorAll('#widget-message-list [data-message-id]');
            for (const msg of messages) {
                if (msg.textContent.includes(messageText)) {
                    // Find and click the visible context menu button
                    const contextMenuBtns = msg.querySelectorAll('.context-menu-btn');
                    let contextMenuBtn = null;
                    for (const btn of contextMenuBtns) {
                        if (btn.offsetParent !== null) {
                            contextMenuBtn = btn;
                            break;
                        }
                    }

                    if (!contextMenuBtn) {
                        return {success: false, error: 'Context menu button not found or not visible'};
                    }

                    // Click to open context menu
                    contextMenuBtn.click();

                    // Find the context menu (it's a sibling of the button)
                    const contextMenu = contextMenuBtn.parentElement.querySelector('.context-menu');
                    if (!contextMenu) {
                        return {success: false, error: 'Context menu element not found'};
                    }

                    // Remove hidden class to show menu
                    contextMenu.classList.remove('hidden');

                    // Find and click the delete button
                    const deleteBtn = contextMenu.querySelector('.delete-btn');
                    if (!deleteBtn) {
                        return {success: false, error: 'Delete button not found in context menu'};
                    }

                    deleteBtn.click();
                    return {success: true};
                }
            }
            return {success: false, error: 'Message not found'};
        }""", message_text)

        if not result['success']:
            raise Exception(f"Could not delete message: {result.get('error', 'Unknown error')}")

        await asyncio.sleep(1)

    async def _delete_message_in_messages_page(self, page, message_text):
        """Helper to delete a message in the messages page"""
        # Use JavaScript to find the message, open context menu, and click delete - all in one call
        result = await page.evaluate("""(messageText) => {
            const messages = document.querySelectorAll('#message-list [data-message-id]');
            for (const msg of messages) {
                if (msg.textContent.includes(messageText)) {
                    // Find and click the visible context menu button
                    const contextMenuBtns = msg.querySelectorAll('.context-menu-btn');
                    let contextMenuBtn = null;
                    for (const btn of contextMenuBtns) {
                        if (btn.offsetParent !== null) {
                            contextMenuBtn = btn;
                            break;
                        }
                    }

                    if (!contextMenuBtn) {
                        return {success: false, error: 'Context menu button not found or not visible'};
                    }

                    // Click to open context menu
                    contextMenuBtn.click();

                    // Find the context menu (it's a sibling of the button)
                    const contextMenu = contextMenuBtn.parentElement.querySelector('.context-menu');
                    if (!contextMenu) {
                        return {success: false, error: 'Context menu element not found'};
                    }

                    // Remove hidden class to show menu
                    contextMenu.classList.remove('hidden');

                    // Find and click the delete button
                    const deleteBtn = contextMenu.querySelector('.delete-btn');
                    if (!deleteBtn) {
                        return {success: false, error: 'Delete button not found in context menu'};
                    }

                    deleteBtn.click();
                    return {success: true};
                }
            }
            return {success: false, error: 'Message not found'};
        }""", message_text)

        if not result['success']:
            raise Exception(f"Could not delete message: {result.get('error', 'Unknown error')}")

        await asyncio.sleep(1)

