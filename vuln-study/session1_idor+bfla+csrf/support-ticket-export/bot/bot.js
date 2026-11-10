import express from 'express';
import { chromium } from 'playwright';


const app = express();
app.use(express.json());

const APP_BASE = process.env.APP_BASE ?? 'http://gateway:8080';
const ALLOWED_FILE_ORIGIN = process.env.ALLOWED_FILE_ORIGIN ?? 'http://gateway:8080';
const ADMIN_BOT_TOKEN = process.env.ADMIN_BOT_TOKEN ?? 'local-admin-bot-token';

let visiting = false;


app.get('/health', (_request, response) => {
  response.json({ status: 'ok' });
});


app.post('/visit', async (request, response) => {
  if (visiting) {
    return response.status(429).json({ error: 'Administrator bot is busy' });
  }

  let target;
  try {
    target = new URL(request.body.url);
  } catch {
    return response.status(400).json({ error: 'Invalid URL' });
  }

  if (target.origin !== ALLOWED_FILE_ORIGIN || !target.pathname.startsWith('/files/')) {
    return response.status(400).json({ error: 'Only uploaded attachment URLs are allowed' });
  }

  visiting = true;
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();

    // 내부 토큰으로 관리자 세션을 만든 뒤 공격자가 제출한 페이지를 방문합니다.
    await page.goto(`${APP_BASE}/bot-login?token=${encodeURIComponent(ADMIN_BOT_TOKEN)}`, {
      waitUntil: 'networkidle',
      timeout: 8000,
    });
    await page.goto(target.toString(), { waitUntil: 'domcontentloaded', timeout: 8000 });
    await page.waitForTimeout(2500);

    return response.json({ status: 'visited' });
  } catch (error) {
    console.error(error);
    return response.status(500).json({ error: 'Bot visit failed' });
  } finally {
    visiting = false;
    if (browser) await browser.close();
  }
});


app.listen(3000, '0.0.0.0', () => {
  console.log('관리자 봇이 3000번 포트에서 실행 중입니다.');
});

