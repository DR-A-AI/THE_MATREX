const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

(async () => {
    console.log("[MATRIX] Initializing Clerk Auto-Extractor...");
    const url = "https://dashboard.clerk.com/apps/app_3Ey9xHngR8HylzTvX9h5FyeNE8x/instances/ins_3Ey9xCNeMZ6xpqsXX1cunebcntz/api-keys";
    
    // We must use the user's real Chrome profile to bypass login.
    const userDataDir = "C:\\Users\\ai\\AppData\\Local\\Google\\Chrome\\User Data";
    const executablePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

    let browser;
    try {
        console.log("[MATRIX] Hijacking Chrome Session...");
        browser = await puppeteer.launch({
            headless: "new",
            executablePath: executablePath,
            userDataDir: userDataDir,
            args: ['--no-sandbox', '--disable-setuid-sandbox', '--profile-directory=Default']
        });

        const page = await browser.newPage();
        await page.setViewport({ width: 1920, height: 1080 });
        
        console.log(`[MATRIX] Infiltrating Clerk Dashboard: ${url}`);
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
        
        // Wait for the keys to load in the DOM
        console.log("[MATRIX] Scanning DOM for cryptographic keys...");
        await page.waitForFunction(() => {
            return document.body.innerText.includes('pk_test_') || document.body.innerText.includes('pk_live_');
        }, { timeout: 15000 });

        const bodyText = await page.evaluate(() => document.body.innerText);
        
        const pkMatch = bodyText.match(/(pk_(test|live)_[a-zA-Z0-9A-Za-z]+)/);
        const skMatch = bodyText.match(/(sk_(test|live)_[a-zA-Z0-9A-Za-z]+)/);

        if (pkMatch) {
            const pk = pkMatch[0];
            console.log(`[SUCCESS] Publishable Key extracted: ${pk.substring(0, 15)}...`);
            
            const envPath = path.join('J:', 'THE_MATRIX', 'dashboard', '.env');
            let envContent = fs.readFileSync(envPath, 'utf8');
            
            // Replace mock key with real key
            if (envContent.includes('VITE_CLERK_PUBLISHABLE_KEY=')) {
                envContent = envContent.replace(/VITE_CLERK_PUBLISHABLE_KEY=.*/g, `VITE_CLERK_PUBLISHABLE_KEY=${pk}`);
            } else {
                envContent += `\nVITE_CLERK_PUBLISHABLE_KEY=${pk}`;
            }
            fs.writeFileSync(envPath, envContent);
            console.log("[MATRIX] Key injected into .env file.");
            
        } else {
            console.log("[ERROR] Could not find the Publishable Key in the DOM.");
        }

    } catch (err) {
        console.error("[CRITICAL ERROR]", err.message);
    } finally {
        if (browser) {
            await browser.close();
            console.log("[MATRIX] Disconnecting...");
        }
    }
})();
