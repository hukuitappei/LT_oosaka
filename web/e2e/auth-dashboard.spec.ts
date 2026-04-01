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
  await expect(page.getByRole("navigation").getByRole("link", { name: "Learning Items" })).toBeVisible()
  await expect(page.getByRole("navigation").getByRole("link", { name: "Weekly Digests" })).toBeVisible()

  await page.getByRole("navigation").getByRole("link", { name: "Learning Items" }).click()
  await expect(page).toHaveURL(/\/learning-items$/)
  const firstCard = page.getByRole("article").first()
  await expect(firstCard.getByText("acme/review-hub")).toBeVisible()
  await expect(firstCard.getByText("PR #42")).toBeVisible()
  const appliedButton = firstCard.getByRole("button", { name: "Applied" })
  await appliedButton.click()
  await expect(appliedButton).toBeDisabled()
  await firstCard.getByRole("link", { name: "Review insights" }).click()
  await expect(page).toHaveURL(/\/pull-requests\/42$/)
  await expect(page.getByText("Before You Repeat This")).toBeVisible()
  await expect(page.getByText("Validate before persistence").first()).toBeVisible()

  await page.getByRole("navigation").getByRole("link", { name: "Weekly Digests" }).click()
  await expect(page).toHaveURL(/\/weekly-digests$/)
  await expect(page.getByText("Validation and API boundary handling improved.")).toBeVisible()

  await page.getByRole("link", { name: "PR Knowledge Hub" }).click()
  await expect(page).toHaveURL("/")
  await expect(page.getByText("Applied")).toBeVisible()
})
