import { expect, type Page, type APIRequestContext } from "@playwright/test";

export async function finishSignIn(page: Page, request: APIRequestContext) {
  const email = `journal-${crypto.randomUUID()}@example.test`;
  await page.getByLabel("Email address").fill(email);
  await page.getByRole("button", { name: "Send me a code", exact: true }).click();
  let code = "";
  await expect
    .poll(
      async () => {
        const inbox = await (await request.get("http://127.0.0.1:54324/api/v1/messages")).json();
        const message = inbox.messages.find((item: { To: { Address: string }[] }) =>
          item.To.some((recipient) => recipient.Address === email),
        );
        if (!message) return false;
        const content = await (
          await request.get(`http://127.0.0.1:54324/api/v1/message/${message.ID}`)
        ).json();
        code = (content.Text || content.HTML).match(/\b\d{6}\b/)?.[0] ?? "";
        return code.length === 6;
      },
      { timeout: 15000, message: "Synthetic local email code received (contents withheld)" },
    )
    .toBe(true);
  try {
    await page.getByLabel("Verification code").fill(code);
  } catch {
    throw new Error("Could not enter code; value withheld.");
  }
  await page.getByRole("button", { name: "Open my journal" }).click();
}
