import { test, expect, type APIRequestContext, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir } from "node:fs/promises";

const origin = "http://localhost:3000";

async function mailCode(request: APIRequestContext, email: string): Promise<string> {
  let code = "";
  await expect
    .poll(
      async () => {
        const response = await request.get("http://127.0.0.1:54324/api/v1/messages");
        const inbox = await response.json();
        const message = inbox.messages.find((item: { To: { Address: string }[] }) =>
          item.To.some((recipient) => recipient.Address === email),
        );
        if (!message) return false;
        const result = await request.get(`http://127.0.0.1:54324/api/v1/message/${message.ID}`);
        const content = await result.json();
        code = (content.Text || content.HTML).match(/\b\d{6}\b/)?.[0] ?? "";
        return code.length === 6;
      },
      { timeout: 15000, message: "Local Mailpit should receive a test code (contents withheld)" },
    )
    .toBe(true);
  return code;
}

async function signIn(page: Page, request: APIRequestContext) {
  const email = `wine-e2e-${crypto.randomUUID()}@example.test`;
  await page.goto("/auth/sign-in");
  await page.getByLabel("Email address").fill(email);
  await page.getByRole("button", { name: "Send me a code", exact: true }).click();
  await expect(page.getByLabel("Verification code")).toBeVisible();
  const code = await mailCode(request, email);
  // Do not attach the code, page DOM, session cookies or request traffic to reports.
  try {
    await page.getByLabel("Verification code").fill(code);
  } catch {
    throw new Error("Could not enter the local test code; value withheld.");
  }
  await page.getByRole("button", { name: "Open my journal" }).click();
  await expect(page.getByRole("heading", { name: "My wines", exact: true })).toBeVisible();
}

test("guests can browse; auth requests enforce Origin, methods, input limits and safe callbacks", async ({
  page,
  request,
}) => {
  await page.goto("/browse");
  await expect(page.getByRole("heading", { name: "Browse wines" })).toBeVisible();
  await expect(page.getByRole("navigation").getByRole("link").first()).toHaveText("Browse wines");
  await page.goto("/my-wines");
  await expect(page).toHaveURL(/\/auth\/sign-in/);
  expect((await request.get("http://127.0.0.1:8000/api/v1/me")).status()).toBe(401);
  for (const path of ["session", "sign-out", "otp/request", "otp/verify", "oauth"]) {
    const response = await request.post(`/auth/${path}`, {
      data: {},
      headers: { Origin: "https://untrusted.test" },
    });
    expect(response.status()).toBe(403);
    expect(response.headers()["cache-control"]).toContain("no-store");
  }
  expect((await request.get("/auth/sign-out")).status()).toBe(405);
  expect(
    (
      await request.post("/auth/otp/request", {
        data: { email: "x".repeat(5000) },
        headers: { Origin: origin },
      })
    ).status(),
  ).toBe(413);
  expect(
    (
      await request.post("/auth/oauth", {
        data: { provider: "google" },
        headers: { Origin: origin },
      })
    ).status(),
  ).toBe(400);
  const callback = await request.get("/auth/callback?code=invalid&next=https://untrusted.test", {
    maxRedirects: 0,
  });
  expect(callback.status()).toBe(303);
  expect(callback.headers().location).toBe(
    origin + "/auth/sign-in?error=callback&next=%2Fmy-wines",
  );
  await page.goto("/auth/sign-in?error=callback");
  await expect(page.locator("#auth-error")).toContainText("Sign-in wasn't completed");
});

test("real email sign-in, current account, refresh, two-account switch, cross-tab sign-out and back navigation", async ({
  page,
  request,
  context,
}) => {
  await signIn(page, request);
  const cookies = await context.cookies();
  expect(cookies.some((cookie) => cookie.name.startsWith("wine-journal-session"))).toBe(true);
  expect(
    cookies
      .filter((cookie) => cookie.name.startsWith("wine-journal-session"))
      .every((cookie) => cookie.httpOnly && cookie.sameSite === "Lax"),
  ).toBe(true);
  expect(await page.evaluate(() => document.cookie.includes("wine-journal-session"))).toBe(false);
  expect(await page.evaluate(() => localStorage.length === 0 && sessionStorage.length === 0)).toBe(
    true,
  );
  await page.getByRole("link", { name: "My account", exact: true }).click();
  const first = await page.getByTestId("account-email").innerText();
  await page.reload();
  await expect(page.getByTestId("account-email")).toHaveText(first);

  // Force one API expiry response; the client must perform one real Supabase refresh.
  let rejected = false;
  let refreshes = 0;
  await page.route("http://127.0.0.1:8000/api/v1/me", async (route) => {
    if (!rejected) {
      rejected = true;
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "UNAUTHENTICATED" } }),
      });
    } else await route.continue();
  });
  page.on("request", (request) => {
    if (request.url().endsWith("/auth/session") && request.postDataJSON()?.refresh === true)
      refreshes++;
  });
  await page.reload();
  await expect(page.getByTestId("account-email")).toHaveText(first);
  expect(refreshes).toBe(1);
  await page.unroute("http://127.0.0.1:8000/api/v1/me");

  const secondTab = await context.newPage();
  await secondTab.goto("/profile");
  await expect(secondTab.getByTestId("account-email")).toHaveText(first);
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/\/browse$/);
  await expect(secondTab).toHaveURL(/\/auth\/sign-in/);
  await page.goBack();
  await expect(page).toHaveURL(/\/auth\/sign-in/);
  await expect(page.getByTestId("account-email")).toHaveCount(0);
  await signIn(page, request);
  await page.getByRole("link", { name: "My account", exact: true }).click();
  const second = await page.getByTestId("account-email").innerText();
  expect(second !== first).toBe(true);

  // End the provider session behind this page; a stale private view must recover once.
  const staleCookies = await context.cookies();
  const ended = await context.request.post("/auth/sign-out", {
    data: {},
    headers: { Origin: origin },
  });
  expect(ended.status()).toBe(200);
  await context.addCookies(staleCookies);
  const failedRefresh = await context.request.post("/auth/session", {
    data: { refresh: true },
    headers: { Origin: origin },
  });
  expect(failedRefresh.status()).toBe(401);
  await page.reload();
  await expect(page).toHaveURL(/\/auth\/sign-in/);
  expect(
    await context
      .cookies()
      .then((values) => values.some((value) => value.name.startsWith("wine-journal-session"))),
  ).toBe(false);
  await secondTab.close();
});

test("invalid code keeps recovery usable; desktop and mobile UI are accessible and fit", async ({
  page,
  request,
}, testInfo) => {
  await mkdir(testInfo.outputPath("visuals"), { recursive: true });
  for (const width of [320, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/auth/sign-in");
    await expect(page.getByLabel("Email address")).toBeVisible();
    await page.getByLabel("Email address").focus();
    await page.keyboard.press("Tab");
    await expect(page.getByRole("button", { name: "Send me a code", exact: true })).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.screenshot({
      path: testInfo.outputPath(`visuals/sign-in-${width}.png`),
      fullPage: true,
    });
  }
  const audit = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(audit.violations.map((issue) => issue.id)).toEqual([]);
  await page.getByLabel("Email address").fill(`wine-invalid-${crypto.randomUUID()}@example.test`);
  await page.getByRole("button", { name: "Send me a code", exact: true }).click();
  await page.getByLabel("Verification code").fill("000000");
  await page.getByRole("button", { name: "Open my journal" }).click();
  await expect(page.locator("#auth-error")).toContainText("invalid or has expired");
  await page.getByRole("button", { name: "Use a different email" }).click();
  await expect(page.getByLabel("Email address")).toBeVisible();
  await signIn(page, request);
  for (const width of [320, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.screenshot({
      path: testInfo.outputPath(`visuals/journal-${width}.png`),
      fullPage: true,
    });
  }
  const privateAudit = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(privateAudit.violations.map((issue) => issue.id)).toEqual([]);
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/\/browse$/);
});
