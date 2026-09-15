import assert from "node:assert/strict";
import { test } from "node:test";
import {
  AuthFailure,
  checkOrigin,
  emailAddress,
  enabledProviders,
  readForm,
  returnPath,
  verificationCode,
} from "../../src/features/auth/validation";

test("return destinations never accept external URLs, encoded redirects or arbitrary paths", () => {
  for (const input of [
    "https://evil.test",
    "//evil.test",
    "/\\evil.test",
    "/%2f%2fevil.test",
    "/auth/sign-out",
    null,
    "/browse?next=https://evil.test",
  ]) {
    assert.equal(returnPath(input), "/my-wines");
  }
  assert.equal(returnPath("/occasions"), "/occasions");
  assert.deepEqual(enabledProviders("apple,unknown, google,google"), ["google", "apple"]);
});

test("cookie-backed requests require the exact configured Origin", () => {
  for (const origin of ["https://evil.test", "http://localhost:3000.evil.test", "null", ""]) {
    assert.throws(
      () =>
        checkOrigin(
          new Request("http://localhost:3000/auth/session", { headers: { origin } }),
          "http://localhost:3000",
        ),
      AuthFailure,
    );
  }
  checkOrigin(
    new Request("http://localhost:3000/auth/session", {
      headers: { origin: "http://localhost:3000" },
    }),
    "http://localhost:3000",
  );
});

test("form parsing rejects malformed and oversized bodies without exposing submitted values", async () => {
  const headers = { origin: "http://localhost:3000", "content-type": "application/json" };
  for (const body of ["invalid", "[]", "null", JSON.stringify({ email: "a".repeat(5000) })]) {
    await assert.rejects(
      readForm(
        new Request("http://localhost:3000/auth/otp", { method: "POST", headers, body }),
        headers.origin,
      ),
      AuthFailure,
    );
  }
  assert.equal(emailAddress(" person@example.test "), "person@example.test");
  assert.throws(() => emailAddress("bad"), AuthFailure);
  assert.equal(verificationCode("012345"), "012345");
  assert.throws(() => verificationCode("12ab56"), AuthFailure);
});
