import { test, expect } from '@playwright/test';

test.describe('RichMan E2E Tests', () => {

  test('1. Dashboard - 市场总览', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // Sidebar menu items
    await expect(page.locator('.ant-menu-item').filter({ hasText: '市场总览' })).toBeVisible({ timeout: 10000 });
    // Index cards
    await expect(page.locator('.ant-card').filter({ hasText: '上证指数' }).first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('.ant-card').filter({ hasText: '深证成指' }).first()).toBeVisible();
    await expect(page.locator('.ant-card').filter({ hasText: '创业板指' }).first()).toBeVisible();
    await expect(page.locator('.ant-card').filter({ hasText: '科创50' }).first()).toBeVisible();
    // 涨跌家数统计
    await expect(page.locator('text=涨跌家数统计')).toBeVisible();
    // 市场情绪
    await expect(page.locator('text=市场情绪')).toBeVisible();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'screenshots/01-dashboard.png', fullPage: true });
  });

  test('2. Market Center - 行情中心', async ({ page }) => {
    await page.goto('/market');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.ant-menu-item').filter({ hasText: '行情中心' })).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(2000);
    // Tab navigation
    await expect(page.locator('.ant-tabs-tab').filter({ hasText: '涨跌排行' })).toBeVisible({ timeout: 10000 });
    // Table should exist
    await expect(page.locator('.ant-table').first()).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: 'screenshots/02-market-ranking.png', fullPage: true });

    // Switch to sector heatmap tab
    const sectorTab = page.locator('.ant-tabs-tab').filter({ hasText: '板块热力图' });
    if (await sectorTab.isVisible()) {
      await sectorTab.click();
      await page.waitForTimeout(2000);
      await page.screenshot({ path: 'screenshots/02-market-sectors.png', fullPage: true });
    }
  });

  test('3. Stock Analysis - 个股分析', async ({ page }) => {
    await page.goto('/stock/000001');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(5000);
    // Should have a chart canvas
    const canvas = page.locator('canvas').first();
    await expect(canvas).toBeVisible({ timeout: 20000 });
    // Stock code in header
    await expect(page.locator('text=000001').first()).toBeVisible({ timeout: 15000 });
    await page.screenshot({ path: 'screenshots/03-stock-analysis.png', fullPage: true });
  });

  test('4. Trend Analysis - 趋势分析', async ({ page }) => {
    await page.goto('/trend');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.ant-menu-item').filter({ hasText: '趋势分析' })).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(3000);
    // Should have tabs or tables
    await expect(page.locator('.ant-tabs, .ant-table, .ant-card').first()).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: 'screenshots/04-trend-signals.png', fullPage: true });
  });

  test('5. Quant Strategy - 量化策略', async ({ page }) => {
    await page.goto('/quant');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.ant-menu-item').filter({ hasText: '量化策略' })).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(2000);
    // Should have strategy form or cards
    await expect(page.locator('.ant-form, .ant-card, .ant-select').first()).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: 'screenshots/05-quant-strategy.png', fullPage: true });
  });

  test('6. News Center - 资讯中心', async ({ page }) => {
    await page.goto('/news');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.ant-menu-item').filter({ hasText: '资讯中心' })).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(2000);
    // Should have cards or list items for news
    await expect(page.locator('.ant-card, .ant-list-item, .ant-spin').first()).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: 'screenshots/06-news-center.png', fullPage: true });
  });

});
