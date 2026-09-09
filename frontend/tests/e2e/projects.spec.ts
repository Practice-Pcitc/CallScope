import { expect, test } from "@playwright/test";

test("project list loads and import form validates required values", async ({
  page,
}) => {
  await page.route("**/api/v1/projects**", (route) =>
    route.fulfill({
      json: {
        data: { items: [], pagination: { page: 1, pageSize: 20, total: 0 } },
      },
    }),
  );
  await page.goto("/projects");
  await page
    .getByRole("button", { name: /导入本地项目/ })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "导入项目", exact: true })
    .click();
  await expect(page.getByText("请输入项目名称", { exact: true })).toBeVisible();
});
