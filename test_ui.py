import asyncio
import logging

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


def _write_chat_history(messages: list) -> None:
    with open("output.txt", "w", encoding="utf-8") as f:
        f.write("=== Chat History ===\n")
        f.writelines(f"{i + 1}: {msg.strip()}\n" for i, msg in enumerate(messages))


def _append_statuses(statuses: list) -> None:
    with open("output.txt", "a", encoding="utf-8") as f:
        f.write("=== Active Statuses ===\n")
        f.writelines(f"Status: {status.strip()}\n" for status in statuses)


def _append_error(text: str) -> None:
    with open("output.txt", "a", encoding="utf-8") as f:
        f.write(f"Error during interaction: {text}\n")


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("Setting localStorage...")
        await page.goto("http://localhost:5173/login")
        await page.evaluate("localStorage.setItem('commander_email', 'dr-anas-hilal')")

        print("Navigating to chat page...")
        await page.goto("http://localhost:5173/")

        print("Waiting for chat page to load...")
        await page.wait_for_selector("text=Comm Channels")

        # Send a message to Neo
        print("Sending message to Neo...")
        await page.get_by_placeholder("Transmit command...").fill("مرحبا نيو، اختبر النظام.")
        # Click the send button by finding the Send icon (which has lucide-send class) or just press Enter
        await page.get_by_placeholder("Transmit command...").press("Enter")

        print("Waiting for Neo's response...")
        # Wait for either status update or new message
        try:
            # Wait for 10 seconds to see all updates
            await page.wait_for_timeout(10000)

            # Print all messages in chat history
            messages = await page.locator(".p-3.rounded-lg").all_text_contents()
            await asyncio.to_thread(_write_chat_history, messages)

            # Check for status after a few seconds
            await asyncio.sleep(5)
            statuses = await page.locator(".animate-pulse").all_text_contents()
            if statuses:
                await asyncio.to_thread(_append_statuses, statuses)
        except Exception as e:
            logger.exception("Error during UI interaction")
            await asyncio.to_thread(_append_error, str(e))

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
