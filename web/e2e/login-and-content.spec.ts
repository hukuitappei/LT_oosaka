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

async function waitForLoginFormReady(page: Page) {
  await page.waitForLoadState("networkidle")
  await expect(page.getByTestId("login-submit")).toBeEnabled()
}

test("shows error on login failure", async ({ page }) => {
  await page.goto("/login", { waitUntil: "domcontentloaded" })
  await waitForLoginFormReady(page)

  await page.getByTestId("login-email").fill("fail@example.com")
  await page.getByTestId("login-password").fill("validpass123")
  await page.getByTestId("login-submit").click()

  await expect(page.getByTestId("login-error")).toBeVisible()
  await expect(page.getByTestId("login-error")).toContainText("Invalid credentials")
})

test("register mode switches UI and creates account", async ({ page }) => {
  await page.goto("/login", { waitUntil: "domcontentloaded" })
  await waitForLoginFormReady(page)

  await expect(page.getByTestId("login-submit")).toContainText("Log In")
  await page.getByRole("button", { name: "Register" }).click()
  await expect(page.getByTestId("login-submit")).toContainText("Create Account")

  await page.getByTestId("login-email").fill("newuser@example.com")
  await page.getByTestId("login-password").fill("securepass123")
  await page.getByTestId("login-submit").click()

  await expect(page).toHaveURL("/")
})

test("shows empty state when no weekly digests exist", async ({ page }) => {
  await setAuthenticatedState(page, "e2e-empty")

  await page.goto("/weekly-digests", { waitUntil: "domcontentloaded" })
  await expect(page).toHaveURL(/\/weekly-digests$/)
  await expect(page.getByTestId("weekly-digests-empty-state")).toBeVisible()
  await expect(page.getByTestId("weekly-digests-empty-state")).toContainText("週次ダイジェスト")
})

test("dashboard displays stat cards and learning item content", async ({ page }) => {
  await setAuthenticatedState(page, "e2e-token")

  await page.goto("/", { waitUntil: "domcontentloaded" })
  await expect(page).toHaveURL("/")
  await expect(page.getByText("Validate before persistence")).toBeVisible()
  await expect(page.getByText("acme/review-hub").first()).toBeVisible()
  await expect(page.getByText("Validation and API boundary handling improved.").first()).toBeVisible()
  await expect(page.getByText("Top Categories")).toBeVisible()
})

test("learning items page shows card with full detail", async ({ page }) => {
  await setAuthenticatedState(page, "e2e-token")

  await page.goto("/learning-items", { waitUntil: "domcontentloaded" })
  await expect(page).toHaveURL(/\/learning-items$/)
  await expect(page.getByText("Validate before persistence")).toBeVisible()
  await expect(page.getByText("acme/review-hub")).toBeVisible()
  await expect(page.getByText("Reject malformed payloads before saving them.")).toBeVisible()
  await expect(page.getByText("The review pointed out missing validation.")).toBeVisible()
  await expect(page.getByText("Add boundary validation in the request layer.")).toBeVisible()
})
