import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("Setting localStorage...")
        await page.goto('http://localhost:5173/login')
        await page.evaluate("localStorage.setItem('commander_email', 'dr-anas-hilal')")
        
        print("Navigating to chat page...")
        await page.goto('http://localhost:5173/')
        
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
            messages = await page.locator('.p-3.rounded-lg').all_text_contents()
            with open('output.txt', 'w', encoding='utf-8') as f:
                f.write("=== Chat History ===\n")
                for i, msg in enumerate(messages):
                    f.write(f"{i+1}: {msg.strip()}\n")
                
            # Check for status after a few seconds
            import asyncio
            await asyncio.sleep(5)
            statuses = await page.locator('.animate-pulse').all_text_contents()
            if statuses:
                with open('output.txt', 'a', encoding='utf-8') as f:
                    f.write("=== Active Statuses ===\n")
                    for status in statuses:
                        f.write(f"Status: {status.strip()}\n")
        except Exception as e:
            with open('output.txt', 'a', encoding='utf-8') as f:
                f.write(f"Error during interaction: {e}\n")
            
        await browser.close()

if __name__ == '__main__':
    asyncio.run(run())
