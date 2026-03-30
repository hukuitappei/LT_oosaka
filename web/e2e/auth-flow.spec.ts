import { expect, test } from "@playwright/test"

test("authenticated users can navigate core pages and inspect GitHub connections", async ({ page }) => {
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
  await expect(page.getByRole("heading", { name: "GitHub Connections", exact: true })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Personal token", exact: true })).toHaveCount(2)
  await expect(page.getByRole("heading", { name: "GitHub App", exact: true })).toHaveCount(2)
  await expect(page.getByRole("heading", { name: "Visible connections", exact: true })).toBeVisible()
  await expect(page.getByText("octocat")).toHaveCount(2)
  await expect(page.getByText("2 total")).toBeVisible()

  await page.getByTestId("logout-button").click()
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByTestId("login-submit")).toBeVisible()
})
