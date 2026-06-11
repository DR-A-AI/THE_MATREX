const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

/**
 * Omni-Plan Phase 2: Chrome Crawler
 * Operator: Triple-X
 * Status: Production Ready
 */
(async () => {
    console.log("[SYSTEM] Connecting to the Matrix...");

    const url = process.argv[2];
    if (!url) {
        console.error("[ERROR] Destination coordinates missing. Provide a URL.");
        process.exit(1);
    }

    console.log(`[SYSTEM] Tracing path to ${url}...`);

    let browser;
    try {
        browser = await puppeteer.launch({
            headless: "new",
            args: ['--no-sandbox', '--disable-setuid-sandbox'] 
        });

        console.log("[SYSTEM] Jacked in. Browser instance initialized.");

        const page = await browser.newPage();
        await page.setViewport({ width: 1920, height: 1080 });

        console.log("[SYSTEM] Bypassing preliminary firewalls (navigating)...");
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

        const title = await page.title();
        console.log(`[DATA] Target Identity (Title): ${title}`);

        const screenshotDir = path.join(__dirname, '../output');
        if (!fs.existsSync(screenshotDir)) {
            fs.mkdirSync(screenshotDir, { recursive: true });
        }

        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const screenshotPath = path.join(screenshotDir, `snapshot_${timestamp}.png`);

        console.log("[SYSTEM] Capturing visual footprint...");
        await page.screenshot({ path: screenshotPath, fullPage: true });
        console.log(`[DATA] Visual footprint secured at: ${screenshotPath}`);

        console.log("[SYSTEM] Mission accomplished. Disconnecting from the Matrix...");
    } catch (error) {
        console.error(`[CRITICAL] Matrix glitch detected: ${error.message}`);
        process.exit(1);
    } finally {
        if (browser) {
            await browser.close();
            console.log("[SYSTEM] Connection severed.");
        }
    }
})();
