import { expect, test } from "@playwright/test"

test("redirects anonymous users and renders authenticated navigation", async ({ page }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" })
  await expect(page).toHaveURL(/\/login$/)

  await page.goto("/login", { waitUntil: "domcontentloaded" })
  await page.evaluate(() => {
    document.cookie = "token=e2e-token; path=/; SameSite=Lax"
    document.cookie = "workspace_id=1; path=/; SameSite=Lax"
    localStorage.setItem("auth_token", "e2e-token")
    localStorage.setItem("workspace_id", "1")
    localStorage.setItem("auth_email", "e2e@example.com")
  })

  await page.goto("/", { waitUntil: "domcontentloaded" })
  await expect(page).toHaveURL("/")
  await expect(page.locator('nav a[href="/learning-items"]')).toBeVisible()
  await expect(page.locator('nav a[href="/weekly-digests"]')).toBeVisible()
  await expect(page.locator('nav a[href="/github-connections"]')).toBeVisible()

  await page.getByRole("link", { name: "Learning Items" }).first().click()
  await expect(page).toHaveURL(/\/learning-items$/)
  await expect(page.getByText("acme/review-hub")).toBeVisible()

  await page.goto("/weekly-digests", { waitUntil: "domcontentloaded" })
  await expect(page).toHaveURL(/\/weekly-digests$/)
  await expect(page.getByText("Validation and API boundary handling improved.")).toBeVisible()
  await expect(page.getByText("Repeated after reuse 1")).toBeVisible()

  await page.getByRole("link", { name: "PR Knowledge Hub" }).click()
  await expect(page).toHaveURL("/")
})
