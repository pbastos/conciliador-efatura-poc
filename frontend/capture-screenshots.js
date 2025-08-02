const puppeteer = require('puppeteer');
const path = require('path');

async function captureScreenshots() {
  console.log('Starting screenshot capture...');
  
  const browser = await puppeteer.launch({
    headless: 'new',
    defaultViewport: {
      width: 1280,
      height: 800
    }
  });

  try {
    const page = await browser.newPage();
    
    // Wait for the app to be available
    console.log('Navigating to application...');
    await page.goto('http://localhost:3002', { waitUntil: 'networkidle2' });
    
    // 1. Dashboard screenshot
    console.log('Capturing Dashboard...');
    await page.waitForSelector('.dashboard-container', { timeout: 10000 });
    await page.screenshot({
      path: path.join(__dirname, '../screenshots/dashboard.png'),
      fullPage: true
    });
    
    // 2. File Upload page
    console.log('Capturing File Upload page...');
    await page.click('button[class*="sidebar-item"]:nth-child(2)');
    await page.waitForSelector('.file-upload-container', { timeout: 5000 });
    await page.screenshot({
      path: path.join(__dirname, '../screenshots/file-upload.png'),
      fullPage: true
    });
    
    // 3. Settings page
    console.log('Capturing Settings page...');
    await page.click('button[class*="sidebar-item"]:nth-child(3)');
    await page.waitForSelector('.settings-container', { timeout: 5000 });
    await page.screenshot({
      path: path.join(__dirname, '../screenshots/settings.png'),
      fullPage: true
    });
    
    // 4. Dashboard with data (if available)
    console.log('Checking for dashboard with data...');
    await page.click('button[class*="sidebar-item"]:nth-child(1)');
    await page.waitForSelector('.dashboard-container', { timeout: 5000 });
    
    // Check if there's data in the reconciliation table
    const hasData = await page.$('.reconciliation-table');
    if (hasData) {
      console.log('Capturing Dashboard with data...');
      await page.screenshot({
        path: path.join(__dirname, '../screenshots/dashboard-with-data.png'),
        fullPage: true
      });
    }
    
    console.log('Screenshots captured successfully!');
    
  } catch (error) {
    console.error('Error capturing screenshots:', error);
  } finally {
    await browser.close();
  }
}

// Run the script
captureScreenshots().catch(console.error);