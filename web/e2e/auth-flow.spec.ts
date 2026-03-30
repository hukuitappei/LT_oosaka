import { expect, test } from "@playwright/test"

test("authenticated users can navigate core pages and manage GitHub connections", async ({ page }) => {
  await page.goto("/login", { waitUntil: "domcontentloaded" })
  await expect(page.getByTestId("login-submit")).toBeVisible()

  await page.evaluate(() => {
    document.cookie = "token=e2e-token; path=/; SameSite=Lax"
    document.cookie = "workspace_id=1; path=/; SameSite=Lax"
    localStorage.setItem("auth_token", "e2e-token")
    localStorage.setItem("workspace_id", "1")
    localStorage.setItem("auth_email", "e2e@example.com")
  })

  await page.goto("/learning-items", { waitUntil: "domcontentloaded" })
  await expect(page).toHaveURL(/\/learning-items$/)
  await expect(page.getByText("acme/review-hub")).toBeVisible()

  await page.goto("/weekly-digests", { waitUntil: "domcontentloaded" })
  await expect(page).toHaveURL(/\/weekly-digests$/)
  await expect(page.getByText("Validation and API boundary handling improved.")).toBeVisible()

  await page.goto("/github-connections", { waitUntil: "domcontentloaded" })
  await expect(page).toHaveURL(/\/github-connections$/)
  await expect(page.getByTestId("github-connections-ready")).toHaveAttribute("data-hydrated", "true")
  await expect(page.getByRole("heading", { name: "GitHub 接続", exact: true })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Personal token", exact: true })).toHaveCount(2)
  await expect(page.getByRole("heading", { name: "GitHub App", exact: true })).toHaveCount(2)
  await expect(page.getByRole("heading", { name: "接続一覧", exact: true })).toBeVisible()
  await expect(page.getByText("octocat")).toHaveCount(2)
  await expect(page.getByText("2 件")).toBeVisible()

  await page.getByTestId("github-token-access-token").fill("ghp-added-for-e2e")
  await page.getByTestId("github-token-login").fill("review-bot")
  await page.getByTestId("github-token-label").fill("E2E token")
  await page.getByTestId("github-token-submit").click()
  await expect(page.getByRole("heading", { name: "E2E token", exact: true })).toBeVisible()
  await expect(page.getByText("3 件")).toBeVisible()

  await page.getByTestId("github-app-installation-id").fill("987654")
  await page.getByTestId("github-app-login").fill("review-bot")
  await page.getByTestId("github-app-label").fill("E2E app")
  await page.getByTestId("github-app-submit").click()
  await expect(page.getByRole("heading", { name: "E2E app", exact: true })).toBeVisible()
  await expect(page.getByText("4 件")).toBeVisible()

  page.once("dialog", (dialog) => dialog.accept())
  await page.getByTestId("github-connection-delete-3").click()
  await expect(page.getByRole("heading", { name: "E2E token", exact: true })).toHaveCount(0)
  await expect(page.getByText("3 件")).toBeVisible()

  await page.getByTestId("logout-button").click()
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByTestId("login-submit")).toBeVisible()
})
