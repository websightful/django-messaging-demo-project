"""
Playwright tests for DM (Direct Messaging) frontend functionality with WebSocket.

This is the WebSocket version of the DM tests that uses WebSocket transport.
For WSGI/polling tests, see test_dm_frontend_polling.py

Tests real-time messaging features between two users:
- Sender in normal Chromium window
- Receiver in incognito Chromium window viewing messages page

Tests cover:
- Sending and receiving messages in real-time via WebSocket
- Adding and removing reactions
- Editing messages
- Deleting messages
"""

import asyncio
import pytest
from playwright.async_api import async_playwright, expect
from django.contrib.auth import get_user_model
from channels.testing import ChannelsLiveServerTestCase
from django.urls import reverse

User = get_user_model()


@pytest.mark.frontend
@pytest.mark.slow
@pytest.mark.websocket
class DMFrontendWebSocketTestCase(ChannelsLiveServerTestCase):
    """Test DM functionality with Playwright using WebSocket transport"""

    serve_static = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sender = User.objects.create_user(
            username="sender_user_ws",
            password="testpass123",
            email="sender_ws@test.com",
            first_name="Sender",
            last_name="User",
        )
        cls.receiver = User.objects.create_user(
            username="receiver_user_ws",
            password="testpass123",
            email="receiver_ws@test.com",
            first_name="Receiver",
            last_name="User",
        )

    def test_dm_real_time_messaging(self):
        """Test complete DM workflow with real-time WebSocket updates"""
        asyncio.run(self._test_dm_real_time_messaging())

    async def _test_dm_real_time_messaging(self):
        """Async test for DM real-time messaging via WebSocket"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=500)

            sender_context = await browser.new_context()
            sender_page = await sender_context.new_page()

            receiver_context = await browser.new_context()
            receiver_page = await receiver_context.new_page()

            try:
                await self._login(sender_page, "sender_user_ws", "testpass123")
                await self._login(receiver_page, "receiver_user_ws", "testpass123")
                await asyncio.sleep(1)

                messages_url = reverse('django_messaging:messaging-view')
                await receiver_page.goto(f"{self.live_server_url}{messages_url}")
                await receiver_page.wait_for_load_state("networkidle")
                await asyncio.sleep(1)

                transport_check = await receiver_page.evaluate(
                    """
                    () => {
                        return {
                            hasPollingTransport: typeof PollingTransport !== 'undefined',
                            hasWebSocketTransport: typeof WebSocketTransport !== 'undefined',
                            transportType: window.chatApp?.wsTransport?.constructor?.name || 'unknown'
                        };
                    }
                """
                )
                print(f"🔍 Transport check: {transport_check}")
                if not transport_check["hasWebSocketTransport"]:
                    print("⚠️ WARNING: WebSocketTransport not loaded!")
                if transport_check["transportType"] != "WebSocketTransport":
                    print(
                        f"⚠️ WARNING: Using {transport_check['transportType']} instead of WebSocketTransport!"
                    )

                person_detail_url = reverse('people:person_detail', kwargs={'user_id': self.receiver.id})
                await sender_page.goto(
                    f"{self.live_server_url}{person_detail_url}"
                )
                await sender_page.wait_for_load_state("networkidle")
                await asyncio.sleep(1)

                chat_toggle_btn = sender_page.locator("#chat-toggle-btn")
                await expect(chat_toggle_btn).to_be_visible()
                await chat_toggle_btn.click()
                await asyncio.sleep(1)

                widget = sender_page.locator("#fixed-chat-widget")
                await expect(widget).to_be_visible()
                await asyncio.sleep(1)

                print("📤 Test 1: Sending message from sender via WebSocket...")
                await self._send_message_in_widget(sender_page, "Hello via WebSocket!")
                await asyncio.sleep(1.5)

                await expect(
                    sender_page.locator("#widget-message-list").get_by_text(
                        "Hello via WebSocket!"
                    )
                ).to_be_visible(timeout=5000)
                await asyncio.sleep(1)

                print(
                    "📥 Test 2: Receiver sees new chat via WebSocket and selects it..."
                )
                print("⏳ WebSocket should push the update instantly...")

                await asyncio.sleep(2)

                sender_name = self.sender.first_name
                chat_item = receiver_page.locator(".chat-item").filter(
                    has_text=sender_name
                )
                await expect(chat_item).to_be_visible(timeout=5000)
                print(f"✅ Chat with '{sender_name}' is visible")
                await asyncio.sleep(1.5)

                await chat_item.click()
                await asyncio.sleep(2)

                message_list = receiver_page.locator("#message-list")
                await expect(message_list).to_be_visible(timeout=5000)
                await asyncio.sleep(1)

                print("📥 Verifying receiver sees message via WebSocket...")
                await expect(
                    message_list.get_by_text("Hello via WebSocket!")
                ).to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)

                print("📤 Test 3: Receiver sends reply...")
                await self._send_message_in_messages_page(
                    receiver_page, "Hello from receiver!"
                )
                await asyncio.sleep(1.5)

                print("📥 Verifying sender receives reply via WebSocket...")
                await expect(
                    sender_page.locator("#widget-message-list").get_by_text(
                        "Hello from receiver!"
                    )
                ).to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)

                print("👍 Test 4: Sender adds reaction...")
                await self._add_reaction_in_widget(
                    sender_page, "Hello from receiver!", "👍"
                )
                await asyncio.sleep(1)

                print("📥 Test 5: Verifying receiver sees reaction via WebSocket...")
                receiver_message = receiver_page.locator(
                    "#message-list [data-message-id]"
                ).filter(has_text="Hello from receiver!")
                await expect(
                    receiver_message.locator(".reaction").filter(has_text="👍")
                ).to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)

                print("❤️ Test 6: Receiver adds reaction...")
                await self._add_reaction_in_messages_page(
                    receiver_page, "Hello via WebSocket!", "❤️"
                )
                await asyncio.sleep(1)

                print("📥 Test 7: Verifying sender sees reaction via WebSocket...")
                sender_message = sender_page.locator(
                    "#widget-message-list [data-message-id]"
                ).filter(has_text="Hello via WebSocket!")
                await expect(
                    sender_message.locator(".reaction").filter(has_text="❤️")
                ).to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)

                print("🗑️ Test 8: Sender removes reaction...")
                await self._remove_reaction_in_widget(
                    sender_page, "Hello from receiver!", "👍"
                )
                await asyncio.sleep(1)

                print(
                    "📥 Test 9: Verifying receiver sees reaction removed via WebSocket..."
                )
                receiver_message = receiver_page.locator(
                    "#message-list [data-message-id]"
                ).filter(has_text="Hello from receiver!")
                await expect(
                    receiver_message.locator(".reaction").filter(has_text="👍")
                ).not_to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)

                print("🗑️ Test 10: Receiver removes reaction...")
                await self._remove_reaction_in_messages_page(
                    receiver_page, "Hello via WebSocket!", "❤️"
                )
                await asyncio.sleep(1)

                print(
                    "📥 Test 11: Verifying sender sees reaction removed via WebSocket..."
                )
                sender_message = sender_page.locator(
                    "#widget-message-list [data-message-id]"
                ).filter(has_text="Hello via WebSocket!")
                await expect(
                    sender_message.locator(".reaction").filter(has_text="❤️")
                ).not_to_be_visible(timeout=5000)
                await asyncio.sleep(1.5)

                print("✏️ Test 12: Sender edits message...")
                await self._edit_message_in_widget(
                    sender_page, "Hello via WebSocket!", "Hello via WebSocket (edited)!"
                )
                await asyncio.sleep(1)

                print(
                    "📥 Test 13: Verifying receiver sees edited message via WebSocket..."
                )
                await expect(
                    receiver_page.locator("#message-list").get_by_text(
                        "Hello via WebSocket (edited)!"
                    )
                ).to_be_visible(timeout=5000)
                edited_message = receiver_page.locator(
                    "#message-list [data-message-id]"
                ).filter(has_text="Hello via WebSocket (edited)!")
                await edited_message.locator(".message-bubble").click()
                await asyncio.sleep(0.3)
                timestamp = edited_message.locator(".message-timestamp")
                await expect(timestamp).to_be_visible()
                await expect(timestamp).to_contain_text("Edited")
                await asyncio.sleep(1.5)

                print("✏️ Test 14: Receiver edits message...")
                await self._edit_message_in_messages_page(
                    receiver_page,
                    "Hello from receiver!",
                    "Hello from receiver (edited)!",
                )
                await asyncio.sleep(1)

                print(
                    "📥 Test 15: Verifying sender sees edited message via WebSocket..."
                )
                await expect(
                    sender_page.locator("#widget-message-list").get_by_text(
                        "Hello from receiver (edited)!"
                    )
                ).to_be_visible(timeout=5000)
                edited_message_widget = sender_page.locator(
                    "#widget-message-list [data-message-id]"
                ).filter(has_text="Hello from receiver (edited)!")
                await edited_message_widget.locator(".message-bubble").click()
                await asyncio.sleep(0.3)
                timestamp_widget = edited_message_widget.locator(".message-timestamp")
                await expect(timestamp_widget).to_be_visible()
                await expect(timestamp_widget).to_contain_text("Edited")
                await asyncio.sleep(1.5)

                print("🗑️ Test 16: Sender deletes message...")
                await self._delete_message_in_widget(
                    sender_page, "Hello via WebSocket (edited)!"
                )
                await asyncio.sleep(1)

                print(
                    "📥 Test 17: Verifying receiver sees deleted message via WebSocket..."
                )
                await asyncio.sleep(2.5)
                await expect(
                    receiver_page.locator(".deleted-indicator").first
                ).to_be_visible(timeout=10000)
                await asyncio.sleep(1.5)

                print("🗑️ Test 18: Receiver deletes message...")
                await self._delete_message_in_messages_page(
                    receiver_page, "Hello from receiver (edited)!"
                )
                await asyncio.sleep(1)

                print(
                    "📥 Test 19: Verifying sender sees deleted message via WebSocket..."
                )
                await asyncio.sleep(2.5)
                await expect(
                    sender_page.locator(".deleted-indicator").first
                ).to_be_visible(timeout=10000)
                await asyncio.sleep(1.5)

                print("✅ All DM WebSocket tests passed!")

            finally:
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
        message_input = page.locator("#message-input")
        await message_input.fill(message_text)
        await message_input.press("Enter")
        await asyncio.sleep(1)

    async def _add_reaction_in_widget(self, page, message_text, emoji):
        """Helper to add a reaction in the DM widget"""
        await page.evaluate(
            """(messageText) => {
            const messages = document.querySelectorAll('#widget-message-list [data-message-id]');
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

    async def _add_reaction_in_messages_page(self, page, message_text, emoji):
        """Helper to add a reaction in the messages page"""
        await page.evaluate(
            """(messageText) => {
            const messages = document.querySelectorAll('#message-list [data-message-id]');
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

    async def _remove_reaction_in_widget(self, page, message_text, emoji):
        """Helper to remove a reaction in the DM widget"""
        message = page.locator("#widget-message-list [data-message-id]").filter(
            has_text=message_text
        )
        reaction_button = message.locator(".reaction").filter(has_text=emoji)
        await reaction_button.click()
        await asyncio.sleep(1)

    async def _remove_reaction_in_messages_page(self, page, message_text, emoji):
        """Helper to remove a reaction in the messages page"""
        message = page.locator("#message-list [data-message-id]").filter(
            has_text=message_text
        )
        reaction_button = message.locator(".reaction").filter(has_text=emoji)
        await reaction_button.click()
        await asyncio.sleep(1)

    async def _edit_message_in_widget(self, page, original_text, new_text):
        """Helper to edit a message in the DM widget"""
        await page.evaluate(
            """(messageText) => {
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
        }""",
            original_text,
        )

        await asyncio.sleep(0.5)

        await page.evaluate(
            """() => {
            const editBtn = document.querySelector('#fixed-chat-widget .edit-btn');
            if (editBtn) {
                editBtn.click();
                return true;
            }
            return false;
        }"""
        )

        await asyncio.sleep(0.3)

        message_input = page.locator("#widget-message-input")
        await message_input.fill(new_text)
        save_btn = page.locator("#fixed-chat-widget .edit-save-btn")
        await save_btn.click()
        await asyncio.sleep(1)

    async def _edit_message_in_messages_page(self, page, original_text, new_text):
        """Helper to edit a message in the messages page"""
        result = await page.evaluate(
            """(messageText) => {
            const messages = document.querySelectorAll('#message-list [data-message-id]');
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
                        return {success: false, error: 'Context menu button not found or not visible'};
                    }

                    contextMenuBtn.click();

                    const contextMenu = contextMenuBtn.parentElement.querySelector('.context-menu');
                    if (!contextMenu) {
                        return {success: false, error: 'Context menu element not found'};
                    }

                    contextMenu.classList.remove('hidden');

                    const editBtn = contextMenu.querySelector('.edit-btn');
                    if (!editBtn) {
                        return {success: false, error: 'Edit button not found in context menu'};
                    }

                    editBtn.click();
                    return {success: true};
                }
            }
            return {success: false, error: 'Message not found'};
        }""",
            original_text,
        )

        if not result["success"]:
            raise Exception(
                f"Could not edit message: {result.get('error', 'Unknown error')}"
            )

        await asyncio.sleep(0.5)

        message_input = page.locator("#message-input")
        await message_input.fill(new_text)

        await asyncio.sleep(0.3)

        save_btn = page.locator(".edit-save-btn")
        await save_btn.click()
        await asyncio.sleep(1)

    async def _delete_message_in_widget(self, page, message_text):
        """Helper to delete a message in the DM widget"""
        result = await page.evaluate(
            """(messageText) => {
            const messages = document.querySelectorAll('#widget-message-list [data-message-id]');
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
                        return {success: false, error: 'Context menu button not found or not visible'};
                    }

                    contextMenuBtn.click();

                    const contextMenu = contextMenuBtn.parentElement.querySelector('.context-menu');
                    if (!contextMenu) {
                        return {success: false, error: 'Context menu element not found'};
                    }

                    contextMenu.classList.remove('hidden');

                    const deleteBtn = contextMenu.querySelector('.delete-btn');
                    if (!deleteBtn) {
                        return {success: false, error: 'Delete button not found in context menu'};
                    }

                    deleteBtn.click();
                    return {success: true};
                }
            }
            return {success: false, error: 'Message not found'};
        }""",
            message_text,
        )

        if not result["success"]:
            raise Exception(
                f"Could not delete message: {result.get('error', 'Unknown error')}"
            )

        await asyncio.sleep(1)

    async def _delete_message_in_messages_page(self, page, message_text):
        """Helper to delete a message in the messages page"""
        result = await page.evaluate(
            """(messageText) => {
            const messages = document.querySelectorAll('#message-list [data-message-id]');
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
                        return {success: false, error: 'Context menu button not found or not visible'};
                    }

                    contextMenuBtn.click();

                    const contextMenu = contextMenuBtn.parentElement.querySelector('.context-menu');
                    if (!contextMenu) {
                        return {success: false, error: 'Context menu element not found'};
                    }

                    contextMenu.classList.remove('hidden');

                    const deleteBtn = contextMenu.querySelector('.delete-btn');
                    if (!deleteBtn) {
                        return {success: false, error: 'Delete button not found in context menu'};
                    }

                    deleteBtn.click();
                    return {success: true};
                }
            }
            return {success: false, error: 'Message not found'};
        }""",
            message_text,
        )

        if not result["success"]:
            raise Exception(
                f"Could not delete message: {result.get('error', 'Unknown error')}"
            )

        await asyncio.sleep(1)
