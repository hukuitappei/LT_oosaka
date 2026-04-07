import { expect, test, type Page } from "@playwright/test"

async function setAuthenticatedState(page: Page, token: string) {
  await page.goto("/login", { waitUntil: "domcontentloaded" })
  await page.evaluate(
    ({ token: currentToken }) => {
      document.cookie = `token=${currentToken}; path=/; SameSite=Lax`
      document.cookie = "workspace_id=1; path=/; SameSite=Lax"
      localStorage.setItem("auth_token", currentToken)
      localStorage.setItem("workspace_id", "1")
      localStorage.setItem("auth_email", "e2e@example.com")
    },
    { token },
  )
}

test("redirects anonymous users from protected pages", async ({ page }) => {
  await page.goto("/weekly-digests/1", { waitUntil: "domcontentloaded" })
  await expect(page).toHaveURL(/\/login$/)

  await page.goto("/login", { waitUntil: "domcontentloaded" })
  await expect(page.getByTestId("login-submit")).toBeVisible()
})

test("renders weekly digest detail for authenticated users", async ({ page }) => {
  await setAuthenticatedState(page, "e2e-token")

  await page.goto("/weekly-digests/1", { waitUntil: "domcontentloaded" })

  await expect(page).toHaveURL(/\/weekly-digests\/1$/)
  await expect(page.getByTestId("weekly-digest-detail")).toBeVisible()
  await expect(page.getByTestId("weekly-digest-back-link")).toBeVisible()
  await expect(page.getByTestId("weekly-digest-summary")).toContainText(
    "Validation and API boundary handling improved.",
  )
  await expect(page.getByTestId("weekly-digest-repeated-issues")).toContainText(
    "Validation checks were missing at the request boundary.",
  )
  await expect(page.getByTestId("weekly-digest-next-time-notes")).toContainText("Keep boundary validation early.")
})

test("shows an empty state for learning items", async ({ page }) => {
  await setAuthenticatedState(page, "e2e-empty")

  await page.goto("/learning-items", { waitUntil: "domcontentloaded" })

  await expect(page).toHaveURL(/\/learning-items$/)
  await expect(page.getByTestId("learning-items-empty-state")).toBeVisible()
})

test("authenticated users can navigate core pages and manage GitHub connections", async ({ page }) => {
  await setAuthenticatedState(page, "e2e-token")

  await page.goto("/learning-items", { waitUntil: "domcontentloaded" })
  await expect(page).toHaveURL(/\/learning-items$/)
  await expect(page.getByText("acme/review-hub")).toBeVisible()

  await page.goto("/weekly-digests", { waitUntil: "domcontentloaded" })
  await expect(page).toHaveURL(/\/weekly-digests$/)
  await expect(page.getByText("Validation and API boundary handling improved.")).toBeVisible()

  await page.goto("/github-connections", { waitUntil: "domcontentloaded" })
  await expect(page).toHaveURL(/\/github-connections$/)
  await expect(page.getByTestId("github-connections-ready")).toHaveAttribute("data-hydrated", "true")
  await expect(page.getByTestId("github-connections-title")).toHaveText("GitHub connections")
  await expect(page.getByTestId("github-token-form")).toBeVisible()
  await expect(page.getByTestId("github-app-form")).toBeVisible()
  await expect(page.getByRole("heading", { name: "Connection list", exact: true })).toBeVisible()
  await expect(page.getByTestId("github-connections-count")).toHaveText("2 items")
  await expect(page.getByTestId("github-connection-card-1")).toBeVisible()
  await expect(page.getByTestId("github-connection-card-2")).toBeVisible()

  await page.getByTestId("github-token-access-token").fill("ghp-added-for-e2e")
  await page.getByTestId("github-token-login").fill("review-bot")
  await page.getByTestId("github-token-label").fill("E2E token")
  await page.getByTestId("github-token-submit").click()
  await expect(page.getByTestId("github-connection-card-3")).toBeVisible()
  await expect(page.getByTestId("github-connections-count")).toHaveText("3 items")
  await expect(page.getByTestId("github-token-access-token")).toHaveValue("")
  await expect(page.getByTestId("github-token-login")).toHaveValue("")
  await expect(page.getByTestId("github-token-label")).toHaveValue("")

  await page.getByTestId("github-app-installation-id").fill("987654")
  await page.getByTestId("github-app-login").fill("review-bot")
  await page.getByTestId("github-app-label").fill("E2E app")
  await page.getByTestId("github-app-submit").click()
  await expect(page.getByTestId("github-connection-card-4")).toBeVisible()
  await expect(page.getByTestId("github-connections-count")).toHaveText("4 items")

  page.once("dialog", (dialog) => dialog.accept())
  await page.getByTestId("github-connection-delete-3").click()
  await expect(page.getByTestId("github-connection-card-3")).toHaveCount(0)
  await expect(page.getByTestId("github-connections-count")).toHaveText("3 items")

  await page.getByTestId("logout-button").click()
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByTestId("login-submit")).toBeVisible()
})
