import { expect, test } from "@playwright/test"

test("redirects anonymous users and renders authenticated pages with seeded auth state", async ({ page, context }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" })
  await expect(page).toHaveURL(/\/login$/)

  await context.addCookies([
    {
      name: "token",
      value: "e2e-token",
      url: "http://127.0.0.1:3100",
    },
    {
      name: "workspace_id",
      value: "1",
      url: "http://127.0.0.1:3100",
    },
  ])
  await page.addInitScript(() => {
    localStorage.setItem("auth_token", "e2e-token")
    localStorage.setItem("workspace_id", "1")
    localStorage.setItem("auth_email", "e2e@example.com")
  })

  await page.goto("/", { waitUntil: "domcontentloaded" })
  await expect(page).toHaveURL("/")
  await expect(page.getByRole("link", { name: "Learning Items" })).toBeVisible()
  await expect(page.getByRole("link", { name: "Weekly Digests" })).toBeVisible()

  await page.getByRole("link", { name: "Learning Items" }).click()
  await expect(page).toHaveURL(/\/learning-items$/)
  await expect(page.getByText("acme/review-hub")).toBeVisible()
  await expect(page.getByText("PR #42")).toBeVisible()

  await page.getByRole("link", { name: "Weekly Digests" }).click()
  await expect(page).toHaveURL(/\/weekly-digests$/)
  await expect(page.getByText("Validation and API boundary handling improved.")).toBeVisible()
})
