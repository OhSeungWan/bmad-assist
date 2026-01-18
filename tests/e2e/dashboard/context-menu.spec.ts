/**
 * Story 16.7: Context Menu System - ATDD Failing Tests (RED Phase)
 *
 * These tests define the expected behavior of the context menu system.
 * All tests should FAIL initially (RED phase) and guide implementation.
 *
 * Test Levels:
 * - Primary: E2E (user interaction with UI)
 * - No API tests (frontend-only story)
 * - No component tests (Alpine.js not unit-testable in isolation)
 *
 * Prerequisites:
 * - Playwright must be installed: npm install @playwright/test
 * - Dashboard server must be running: bmad-assist serve --port 9600
 *
 * Run tests:
 * - npx playwright test tests/e2e/dashboard/context-menu.spec.ts --headed
 * - npx playwright test tests/e2e/dashboard/context-menu.spec.ts --debug
 */

import { test, expect, Page } from '@playwright/test';

// =============================================================================
// Test Fixtures and Helpers
// =============================================================================

const BASE_URL = process.env.DASHBOARD_URL || 'http://localhost:9600';

/**
 * Factory: Create mock story data for testing
 */
function createMockStory(overrides: Partial<Story> = {}): Story {
  return {
    id: 7,
    title: 'Context Menu System',
    status: 'ready-for-dev',
    phases: [
      { name: 'create-story', status: 'completed' },
      { name: 'validate', status: 'completed' },
      { name: 'dev-story', status: 'pending' },
      { name: 'code-review', status: 'pending' },
    ],
    ...overrides,
  };
}

interface Story {
  id: number;
  title: string;
  status: 'backlog' | 'ready-for-dev' | 'in-progress' | 'review' | 'done';
  phases: { name: string; status: string }[];
}

/**
 * Helper: Wait for context menu to appear
 */
async function waitForContextMenu(page: Page): Promise<void> {
  await expect(page.locator('[data-testid="context-menu"]')).toBeVisible({ timeout: 100 });
}

/**
 * Helper: Get context menu position
 */
async function getContextMenuPosition(page: Page): Promise<{ x: number; y: number }> {
  const menu = page.locator('[data-testid="context-menu"]');
  const box = await menu.boundingBox();
  if (!box) throw new Error('Context menu not found');
  return { x: box.x, y: box.y };
}

// =============================================================================
// AC 1: Right-click shows context menu at cursor position within 100ms
// =============================================================================

test.describe('AC 1: Right-click Context Menu Positioning', () => {
  test('should show context menu at cursor position when right-clicking tree item', async ({
    page,
  }) => {
    // GIVEN: Dashboard is loaded with tree view
    await page.goto(BASE_URL);
    await expect(page.locator('[data-testid="tree-view"]')).toBeVisible();

    // Expand an epic to see stories
    const epicNode = page.locator('[data-testid="epic-node"]').first();
    await epicNode.click();

    // WHEN: Right-click on a story item
    const storyNode = page.locator('[data-testid="story-node"]').first();
    const storyBox = await storyNode.boundingBox();
    if (!storyBox) throw new Error('Story node not found');

    const clickX = storyBox.x + storyBox.width / 2;
    const clickY = storyBox.y + storyBox.height / 2;

    await storyNode.click({ button: 'right' });

    // THEN: Context menu appears at cursor position
    await waitForContextMenu(page);

    const menuPos = await getContextMenuPosition(page);

    // Menu should appear near the click position (within reasonable tolerance)
    expect(Math.abs(menuPos.x - clickX)).toBeLessThan(50);
    expect(Math.abs(menuPos.y - clickY)).toBeLessThan(50);
  });

  test('should reposition menu if it would render off-screen (right edge)', async ({ page }) => {
    // GIVEN: Dashboard loaded with tree near right edge
    await page.goto(BASE_URL);
    await page.setViewportSize({ width: 400, height: 600 });

    // WHEN: Right-click near right edge of viewport
    const treeItem = page.locator('[data-testid="story-node"]').first();
    await treeItem.click({ button: 'right', position: { x: 350, y: 100 } });

    // THEN: Menu is fully visible (repositioned to stay in viewport)
    await waitForContextMenu(page);
    const menu = page.locator('[data-testid="context-menu"]');
    const menuBox = await menu.boundingBox();

    expect(menuBox).not.toBeNull();
    if (menuBox) {
      expect(menuBox.x + menuBox.width).toBeLessThanOrEqual(400);
    }
  });

  test('should reposition menu if it would render off-screen (bottom edge)', async ({ page }) => {
    // GIVEN: Dashboard with small viewport
    await page.goto(BASE_URL);
    await page.setViewportSize({ width: 800, height: 300 });

    // WHEN: Right-click near bottom of viewport
    await page.mouse.click(200, 280, { button: 'right' });

    // THEN: Menu is repositioned to stay within viewport
    await waitForContextMenu(page);
    const menu = page.locator('[data-testid="context-menu"]');
    const menuBox = await menu.boundingBox();

    expect(menuBox).not.toBeNull();
    if (menuBox) {
      expect(menuBox.y + menuBox.height).toBeLessThanOrEqual(300);
    }
  });

  test('should appear within 100ms of right-click (NFR-D2)', async ({ page }) => {
    // GIVEN: Dashboard loaded
    await page.goto(BASE_URL);

    // WHEN: Right-click with timing measurement
    const startTime = performance.now();
    await page.locator('[data-testid="story-node"]').first().click({ button: 'right' });
    await waitForContextMenu(page);
    const endTime = performance.now();

    // THEN: Menu appears within 100ms
    expect(endTime - startTime).toBeLessThan(100);
  });
});

// =============================================================================
// AC 2: Kebab icon click shows menu below the icon
// =============================================================================

test.describe('AC 2: Kebab Icon Context Menu', () => {
  test('should show context menu 4px below kebab icon when clicked', async ({ page }) => {
    // GIVEN: Dashboard loaded with visible kebab icons
    await page.goto(BASE_URL);

    // Hover to reveal kebab icon
    const storyNode = page.locator('[data-testid="story-node"]').first();
    await storyNode.hover();

    // WHEN: Click the kebab icon
    const kebabButton = storyNode.locator('[data-testid="kebab-button"]');
    const kebabBox = await kebabButton.boundingBox();
    if (!kebabBox) throw new Error('Kebab button not found');

    await kebabButton.click();

    // THEN: Menu appears 4px below the kebab button
    await waitForContextMenu(page);
    const menuPos = await getContextMenuPosition(page);

    // Menu should be positioned 4px below kebab button
    const expectedY = kebabBox.y + kebabBox.height + 4;
    expect(Math.abs(menuPos.y - expectedY)).toBeLessThan(2);
  });

  test('should not overlap the clicked kebab icon', async ({ page }) => {
    // GIVEN: Dashboard loaded
    await page.goto(BASE_URL);

    const storyNode = page.locator('[data-testid="story-node"]').first();
    await storyNode.hover();

    // WHEN: Click kebab icon
    const kebabButton = storyNode.locator('[data-testid="kebab-button"]');
    const kebabBox = await kebabButton.boundingBox();
    await kebabButton.click();

    // THEN: Menu does not overlap kebab button
    await waitForContextMenu(page);
    const menu = page.locator('[data-testid="context-menu"]');
    const menuBox = await menu.boundingBox();

    expect(menuBox).not.toBeNull();
    if (menuBox && kebabBox) {
      // Menu top should be at or below kebab bottom
      expect(menuBox.y).toBeGreaterThanOrEqual(kebabBox.y + kebabBox.height);
    }
  });
});

// =============================================================================
// AC 3: Ready-for-dev story shows primary action
// =============================================================================

test.describe('AC 3: Ready-for-dev Story Actions', () => {
  test('should show Run dev-story, View prompt, Open story file for ready-for-dev story', async ({
    page,
  }) => {
    // GIVEN: Dashboard with a ready-for-dev story
    await page.goto(BASE_URL);

    // Find and right-click a ready-for-dev story
    const readyStory = page.locator('[data-testid="story-node"][data-status="ready-for-dev"]');
    await readyStory.first().click({ button: 'right' });

    // THEN: Menu shows expected actions
    await waitForContextMenu(page);

    await expect(page.locator('[data-testid="action-run-dev-story"]')).toBeVisible();
    await expect(page.locator('[data-testid="action-view-prompt"]')).toBeVisible();
    await expect(page.locator('[data-testid="action-open-file"]')).toBeVisible();
  });

  test('should visually emphasize Run dev-story as primary action', async ({ page }) => {
    // GIVEN: Context menu for ready-for-dev story
    await page.goto(BASE_URL);
    const readyStory = page.locator('[data-testid="story-node"][data-status="ready-for-dev"]');
    await readyStory.first().click({ button: 'right' });
    await waitForContextMenu(page);

    // THEN: Run dev-story has primary styling (bg-bp-accent/20 text-bp-accent)
    const runAction = page.locator('[data-testid="action-run-dev-story"]');
    await expect(runAction).toHaveClass(/bg-bp-accent/);
    await expect(runAction).toHaveClass(/text-bp-accent/);
  });
});

// =============================================================================
// AC 4: Done story shows view actions and Re-run with warning
// =============================================================================

test.describe('AC 4: Done Story Actions', () => {
  test('should show View prompt, View review, Re-run for done story', async ({ page }) => {
    // GIVEN: Dashboard with a done story
    await page.goto(BASE_URL);

    const doneStory = page.locator('[data-testid="story-node"][data-status="done"]');
    await doneStory.first().click({ button: 'right' });

    // THEN: Menu shows expected actions
    await waitForContextMenu(page);

    await expect(page.locator('[data-testid="action-view-prompt"]')).toBeVisible();
    await expect(page.locator('[data-testid="action-view-review"]')).toBeVisible();
    await expect(page.locator('[data-testid="action-re-run"]')).toBeVisible();
  });

  test('should show Re-run with danger/warning styling', async ({ page }) => {
    // GIVEN: Context menu for done story
    await page.goto(BASE_URL);
    const doneStory = page.locator('[data-testid="story-node"][data-status="done"]');
    await doneStory.first().click({ button: 'right' });
    await waitForContextMenu(page);

    // THEN: Re-run has danger styling (text-bp-error)
    const reRunAction = page.locator('[data-testid="action-re-run"]');
    await expect(reRunAction).toHaveClass(/text-bp-error/);
  });
});

// =============================================================================
// AC 5: Phase-specific actions per wireframe 3b/3c
// =============================================================================

test.describe('AC 5: Phase-Specific Actions', () => {
  test('should show phase actions for create-story phase', async ({ page }) => {
    // GIVEN: Expanded story with phases visible
    await page.goto(BASE_URL);

    // Navigate to phase
    const phase = page.locator('[data-testid="phase-node"][data-phase="create-story"]');
    await phase.first().click({ button: 'right' });

    // THEN: Shows create-story specific actions
    await waitForContextMenu(page);
    await expect(page.locator('[data-testid="action-view-prompt"]')).toBeVisible();
    await expect(page.locator('[data-testid="action-view-story-file"]')).toBeVisible();
  });

  test('should show validation reports for validate phase', async ({ page }) => {
    // GIVEN: Validate phase selected
    await page.goto(BASE_URL);

    const phase = page.locator('[data-testid="phase-node"][data-phase="validate"]');
    await phase.first().click({ button: 'right' });

    // THEN: Shows validation-specific actions
    await waitForContextMenu(page);
    await expect(page.locator('[data-testid="action-view-prompt"]')).toBeVisible();
    await expect(page.locator('[data-testid="action-view-validation-reports"]')).toBeVisible();
    await expect(page.locator('[data-testid="action-view-synthesis"]')).toBeVisible();
  });

  test('should show Re-run and Skip actions for all phases', async ({ page }) => {
    // GIVEN: Any phase selected
    await page.goto(BASE_URL);

    const phase = page.locator('[data-testid="phase-node"]').first();
    await phase.click({ button: 'right' });

    // THEN: Common actions present
    await waitForContextMenu(page);
    await expect(page.locator('[data-testid="action-re-run-phase"]')).toBeVisible();
    await expect(page.locator('[data-testid="action-skip-phase"]')).toBeVisible();
  });

  test('should style Skip to next phase as destructive', async ({ page }) => {
    // GIVEN: Phase context menu open
    await page.goto(BASE_URL);
    const phase = page.locator('[data-testid="phase-node"]').first();
    await phase.click({ button: 'right' });
    await waitForContextMenu(page);

    // THEN: Skip action has danger styling
    const skipAction = page.locator('[data-testid="action-skip-phase"]');
    await expect(skipAction).toHaveClass(/text-bp-error/);
  });
});

// =============================================================================
// AC 6: Review status story actions
// =============================================================================

test.describe('AC 6: Review Status Story Actions', () => {
  test('should show view actions but no run actions for review status', async ({ page }) => {
    // GIVEN: Story in review status
    await page.goto(BASE_URL);

    const reviewStory = page.locator('[data-testid="story-node"][data-status="review"]');
    await reviewStory.first().click({ button: 'right' });

    // THEN: Shows view actions only
    await waitForContextMenu(page);
    await expect(page.locator('[data-testid="action-view-prompt"]')).toBeVisible();
    await expect(page.locator('[data-testid="action-open-file"]')).toBeVisible();
    await expect(page.locator('[data-testid="action-view-review"]')).toBeVisible();

    // No run actions
    await expect(page.locator('[data-testid="action-run-dev-story"]')).not.toBeVisible();
  });
});

// =============================================================================
// AC 7: Menu closes on blur or Escape
// =============================================================================

test.describe('AC 7: Menu Close Behavior', () => {
  test('should close menu when clicking outside', async ({ page }) => {
    // GIVEN: Context menu is open
    await page.goto(BASE_URL);
    const storyNode = page.locator('[data-testid="story-node"]').first();
    await storyNode.click({ button: 'right' });
    await waitForContextMenu(page);

    // WHEN: Click outside the menu
    await page.mouse.click(10, 10);

    // THEN: Menu is closed
    await expect(page.locator('[data-testid="context-menu"]')).not.toBeVisible();
  });

  test('should close menu when pressing Escape', async ({ page }) => {
    // GIVEN: Context menu is open
    await page.goto(BASE_URL);
    const storyNode = page.locator('[data-testid="story-node"]').first();
    await storyNode.click({ button: 'right' });
    await waitForContextMenu(page);

    // WHEN: Press Escape key
    await page.keyboard.press('Escape');

    // THEN: Menu is closed
    await expect(page.locator('[data-testid="context-menu"]')).not.toBeVisible();
  });

  test('should not trigger any action when closing', async ({ page }) => {
    // GIVEN: Context menu is open
    await page.goto(BASE_URL);
    await page.locator('[data-testid="story-node"]').first().click({ button: 'right' });
    await waitForContextMenu(page);

    // Watch for network requests (no API calls should happen)
    const requests: string[] = [];
    page.on('request', (req) => requests.push(req.url()));

    // WHEN: Close with Escape
    await page.keyboard.press('Escape');

    // THEN: No action triggered (no new API requests)
    expect(requests.filter((r) => r.includes('/api/'))).toHaveLength(0);
  });
});

// =============================================================================
// Visual and Styling Tests
// =============================================================================

test.describe('Visual Styling', () => {
  test('should show separator line before destructive actions', async ({ page }) => {
    // GIVEN: Context menu for done story (has Re-run destructive action)
    await page.goto(BASE_URL);
    const doneStory = page.locator('[data-testid="story-node"][data-status="done"]');
    await doneStory.first().click({ button: 'right' });
    await waitForContextMenu(page);

    // THEN: Separator exists before Re-run
    const separator = page.locator('[data-testid="context-menu-separator"]');
    await expect(separator).toBeVisible();
  });

  test('should not show visual flicker when menu appears near edges', async ({ page }) => {
    // GIVEN: Small viewport (forces edge repositioning)
    await page.goto(BASE_URL);
    await page.setViewportSize({ width: 400, height: 400 });

    // WHEN: Open context menu near edge
    await page.mouse.click(350, 350, { button: 'right' });

    // THEN: Menu should appear smoothly (opacity transition)
    // Note: This is more of a visual check, but we verify the menu exists
    await waitForContextMenu(page);
    const menu = page.locator('[data-testid="context-menu"]');

    // Verify menu is in final position and visible
    await expect(menu).toHaveCSS('opacity', '1');
  });
});
