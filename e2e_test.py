import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Navigating to dashboard...")
        
        # Retry loop for Vite server startup
        for i in range(10):
            try:
                await page.goto("http://localhost:5173", timeout=5000)
                break
            except Exception as e:
                print(f"Vite not ready yet, retrying... ({i+1}/10)")
                await asyncio.sleep(2)
                
        await page.screenshot(path="screenshot_1_loaded.png")
        print("Captured screenshot_1_loaded.png")

        # Check if we are on the login page by looking for the email input
        email_input = page.locator("input[type='email']")
        if await email_input.count() > 0:
            print("Login page detected. Authenticating...")
            await email_input.fill("commander@matrix.ai")
            await page.locator("input[type='password']").fill("password123")
            await page.locator("button[type='submit']").click()
            
            # Wait for login to complete (it has a ~6s fake delay + reload)
            print("Waiting for handshake...")
            await asyncio.sleep(8)
            await page.wait_for_selector("input[placeholder='Transmit command...']", timeout=15000)
            
        # Wait for connection to establish
        await asyncio.sleep(2)
        
        # Fill the textarea
        print("Typing message for Neo...")
        # Locate the text input
        chat_input = page.locator("input[placeholder='Transmit command...']")
        await chat_input.fill("neo: قم بإنشاء ملف نصي في الجذور باسم test_by_neo.txt واكتب فيه 'Hello from Matrix' ثم اقرأ محتوياته وأخبرني بالنتيجة.")
        
        # Press Enter
        print("Sending message...")
        await chat_input.press("Enter")
            
        print("Message sent. Waiting for status box to appear...")
        # The status box has classes like 'bg-cyan-900/20 text-cyan-400 text-xs'
        await asyncio.sleep(3)
        await page.screenshot(path="screenshot_2_status.png")
        print("Captured screenshot_2_status.png (Checking if status box is there)")
        
        # Wait for the final reply
        print("Waiting for Neo's final response...")
        await asyncio.sleep(90)
        await page.screenshot(path="screenshot_3_final.png")
        print("Captured screenshot_3_final.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
