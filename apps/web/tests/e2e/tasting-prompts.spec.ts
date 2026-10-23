import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { finishSignIn } from "./journal-auth";

test("tasting help preserves guest notes through sign-in and later editing", async ({
  page,
  request,
}, testInfo) => {
  await page.goto("/capture");
  await page.getByLabel("Wine name", { exact: true }).fill("A memorable Cabernet");
  await page.getByLabel("Date tried").fill("2026-10-20");
  const notes = page.getByLabel("Quick notes");
  const help = page.getByText("Help me describe it", { exact: true });
  await expect(page.getByText("What did it remind you of?", { exact: true })).toBeHidden();
  await help.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("What did it remind you of?", { exact: true })).toBeVisible();
  await expect(notes).toHaveValue("");
  await notes.fill("Reminded me of the cherry tree at home.");
  await help.focus();
  await page.keyboard.press("Space");
  await expect(page.getByText("What did it remind you of?", { exact: true })).toBeHidden();
  await expect(notes).toHaveValue("Reminded me of the cherry tree at home.");
  await help.click();
  await page.getByText("Body, acidity and tannin", { exact: true }).click();
  for (const width of [320, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await notes.scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath(`tasting-help-${width}.png`) });
  }
  const audit = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(audit.violations.map((issue) => issue.id)).toEqual([]);
  await page.getByRole("button", { name: "Sign in to save", exact: true }).click();
  await finishSignIn(page, request);
  await expect(notes).toHaveValue("Reminded me of the cherry tree at home.");
  await page.getByRole("button", { name: "Save entry", exact: true }).click();
  await expect(page.getByTestId("drinking-entry")).toHaveCount(1);
  await expect(page.getByTestId("current-rating")).toHaveText("Not rated yet");
  await page.getByLabel("Your score", { exact: true }).selectOption("4");
  await page.getByRole("button", { name: "Save rating", exact: true }).click();
  await expect(page.getByTestId("current-rating")).toHaveText("4 / 5");
  await page.getByRole("button", { name: "Edit entry", exact: true }).click();
  const editor = page.getByRole("form", { name: "Edit drinking entry" });
  const savedNotes = editor.getByLabel("Notes", { exact: true });
  await editor.getByText("Help me describe it", { exact: true }).click();
  await expect(savedNotes).toHaveValue("Reminded me of the cherry tree at home.");
  await savedNotes.fill("Cherry and a gentle drying feeling. Lovely with dinner.");
  await editor.getByText("Help me describe it", { exact: true }).click();
  await editor.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("Entry updated.", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByTestId("drinking-entry").locator(".entry-notes")).toHaveText(
    "Cherry and a gentle drying feeling. Lovely with dinner.",
  );
  await expect(page.getByTestId("current-rating")).toHaveText("4 / 5");
  await page.getByRole("button", { name: "View rating history" }).click();
  await expect(page.locator(".rating-revisions li")).toHaveCount(1);
});

test("opening help still allows a wine-and-date-only save", async ({ page, request }) => {
  await page.goto("/auth/sign-in?next=%2Fcapture");
  await finishSignIn(page, request);
  await page.getByLabel("Wine name", { exact: true }).fill("A quick glass");
  await page.getByLabel("Date tried").fill("2026-10-21");
  await page.getByText("Help me describe it", { exact: true }).click();
  await page.getByText("Body, acidity and tannin", { exact: true }).click();
  await page.getByRole("button", { name: "Save entry", exact: true }).click();
  await expect(page.getByTestId("drinking-entry")).toHaveCount(1);
  await page.getByRole("button", { name: "Edit entry", exact: true }).click();
  await expect(
    page.getByRole("form", { name: "Edit drinking entry" }).getByLabel("Notes", { exact: true }),
  ).toHaveValue("");
  await expect(page.getByTestId("current-rating")).toHaveText("Not rated yet");
});
