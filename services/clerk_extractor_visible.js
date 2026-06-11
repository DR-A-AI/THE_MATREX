const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

(async () => {
    console.log("[MATRIX] Initializing Clerk Auto-Extractor (Visible Mode)...");
    const url = "https://dashboard.clerk.com/apps/app_3Ey9xHngR8HylzTvX9h5FyeNE8x/instances/ins_3Ey9xCNeMZ6xpqsXX1cunebcntz/api-keys";
    
    const userDataDir = "J:\\THE_MATRIX\\chrome_temp";
    const executablePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

    let browser;
    try {
        browser = await puppeteer.launch({
            headless: false,
            defaultViewport: null,
            executablePath: executablePath,
            userDataDir: userDataDir,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });

        const page = await browser.newPage();
        
        console.log(`[MATRIX] Infiltrating Clerk Dashboard: ${url}`);
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });
        
        console.log("[MATRIX] Waiting 10 seconds for Cloudflare/Login to settle...");
        await new Promise(r => setTimeout(r, 10000));

        await page.screenshot({ path: "J:\\THE_MATRIX\\scratch\\clerk_vision.png", fullPage: true });
        console.log("[MATRIX] Screenshot saved. Scanning DOM...");

        const bodyText = await page.evaluate(() => document.body.innerText);
        
        const pkMatch = bodyText.match(/(pk_(test|live)_[a-zA-Z0-9A-Za-z_]+)/);
        const skMatch = bodyText.match(/(sk_(test|live)_[a-zA-Z0-9A-Za-z_]+)/);

        if (pkMatch) {
            const pk = pkMatch[0];
            console.log(`[SUCCESS] Publishable Key extracted: ${pk.substring(0, 15)}...`);
            
            const envPath = path.join('J:', 'THE_MATRIX', 'dashboard', '.env');
            let envContent = fs.readFileSync(envPath, 'utf8');
            
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
        }
    }
})();
