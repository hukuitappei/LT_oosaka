import { expect, test } from "@playwright/test"

test("authenticated users can navigate core pages and log out", async ({ page }) => {
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
  await expect(page.getByText("Validate before persistence")).toBeVisible()

  await page.goto("/weekly-digests", { waitUntil: "domcontentloaded" })
  await expect(page).toHaveURL(/\/weekly-digests$/)
  await expect(page.getByText("Validation and API boundary handling improved.")).toBeVisible()

  await page.getByTestId("logout-button").click()
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByTestId("login-submit")).toBeVisible()
})
