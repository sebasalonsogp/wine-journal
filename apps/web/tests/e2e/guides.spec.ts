import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("guest guides are readable, sourced and linked to catalog searches", async ({
  page,
}, testInfo) => {
  const journalWrites: string[] = [];
  page.on("request", (request) => {
    if (
      request.url().includes("/api/v1/") &&
      !["GET", "HEAD", "OPTIONS"].includes(request.method())
    ) {
      journalWrites.push(request.method());
    }
  });
  await page.goto("/guides");
  const guides = page.getByRole("list", { name: "Beginner wine guides" });
  await expect(guides.getByRole("link")).toHaveCount(4);
  await expect(page.getByRole("link", { name: "Sign in", exact: true })).toBeVisible();
  const links = await guides.getByRole("link").evaluateAll((items) =>
    items.map((item) => ({
      href: (item as HTMLAnchorElement).getAttribute("href")!,
      title: item.querySelector("h2")!.textContent!,
    })),
  );
  for (const width of [320, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.screenshot({
      path: testInfo.outputPath(`guides-index-${width}.png`),
      fullPage: true,
    });
  }
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  for (const link of links) {
    const trigger = guides
      .getByRole("link")
      .filter({ has: page.getByRole("heading", { name: link.title, exact: true }) });
    await trigger.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(link.title);
    await expect(page.getByRole("link", { name: "Guides", exact: true })).toHaveAttribute(
      "aria-current",
      "page",
    );
    await expect(page.locator("article time")).toHaveAttribute("datetime", "2026-10-23");
    await expect(
      page.getByRole("region", { name: "Sources and review" }).getByRole("link").first(),
    ).toHaveAttribute("href", /^https:\/\//);
    await expect(
      page
        .getByRole("navigation", { name: "Explore wines from this guide" })
        .getByRole("link")
        .first(),
    ).toHaveAttribute("href", /^\/browse\?q=/);
    await page.reload();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(link.title);
    await page.getByRole("link", { name: "All wine guides", exact: true }).click();
    await expect(guides).toBeVisible();
  }
  await page.goto(links[0].href);
  for (const width of [320, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.screenshot({
      path: testInfo.outputPath(`guide-article-${width}.png`),
      fullPage: true,
    });
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  }
  await page.getByRole("link", { name: "Find Cabernet Sauvignon", exact: true }).click();
  await expect(page.getByLabel("Search the wine library")).toHaveValue("Cabernet Sauvignon");
  await expect(page.locator(".catalog-wine").first()).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(links[0].title);
  expect(journalWrites).toEqual([]);
});

test("guide searches recover from no results and unknown guides return 404", async ({ page }) => {
  await page.goto("/guides/wine-styles");
  await page.getByRole("link", { name: "Find Riesling", exact: true }).click();
  await expect(page.getByRole("heading", { name: "No matching wines yet." })).toBeVisible();
  await page.getByRole("link", { name: "Clear search", exact: true }).click();
  await expect(page.locator(".catalog-wine").first()).toBeVisible();
  const response = await page.goto("/guides/not-a-guide");
  expect(response?.status()).toBe(404);
  await expect(page.getByRole("heading", { name: "Guide not found", exact: true })).toBeVisible();
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex");
  await page.getByRole("link", { name: "All wine guides", exact: true }).click();
  await expect(
    page.getByRole("list", { name: "Beginner wine guides" }).getByRole("link"),
  ).toHaveCount(4);
});
