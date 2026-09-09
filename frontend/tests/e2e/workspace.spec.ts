import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
const fixture = JSON.parse(
  readFileSync(new URL("../fixtures/workspace.json", import.meta.url), "utf8"),
);

test("sample import, scan, graph and AI analysis flow", async ({ page }) => {
  const unexpected: string[] = [];
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const prefix = `/api/v1/projects/${fixture.project.data.id}`;
    let json: unknown;
    if (path === "/api/v1/projects") {
      json =
        route.request().method() === "POST"
          ? fixture.project
          : {
              data: {
                items: [],
                pagination: { page: 1, pageSize: 20, total: 0 },
              },
            };
    } else if (path === prefix) json = fixture.project;
    else if (path.endsWith("/scans") || path.endsWith("/scans/latest"))
      json = fixture.scan;
    else if (path.endsWith("/endpoints")) json = fixture.endpoints;
    else if (path.endsWith("/graphs") || path.endsWith("/graphs/combined"))
      json = fixture.graph;
    else if (path.endsWith("/ai-analyses")) json = fixture.analysis;
    else if (path.includes("/nodes/")) {
      const nodeId = path.split("/nodes/")[1].split("/")[0];
      json =
        fixture.nodes[nodeId][path.endsWith("/source") ? "source" : "detail"];
    } else {
      unexpected.push(path);
      await route.fulfill({ status: 404, json: {} });
      return;
    }
    await route.fulfill({ json });
  });
  await page.setViewportSize({ width: 1600, height: 1000 });
  await page.goto("/projects");
  await page.getByRole("button", { name: /导入本地项目/ }).click();
  await page.getByLabel("项目名称").fill("FastAPI 示例项目");
  await page.getByLabel("项目绝对路径").fill("D:/samples/fastapi-sample");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "导入项目", exact: true })
    .click();
  await expect(page).toHaveURL(new RegExp(fixture.project.data.id));
  const endpoint = page.locator(".endpoint-item").first();
  await expect(endpoint).toBeVisible();
  await endpoint.click();
  await expect(page.getByRole("img", { name: "接口调用拓扑图" })).toBeVisible();
  await page.getByRole("button", { name: /分析接口业务/ }).click();
  await page.getByRole("tab", { name: "业务概览", exact: true }).click();
  await expect(
    page
      .locator(".ant-alert-description")
      .filter({ hasText: fixture.analysis.data.result.businessSummary }),
  ).toBeVisible();
  expect(unexpected).toEqual([]);
  if (process.env.CALLSCOPE_CAPTURE_DEMO === "1") {
    await expect(
      page.getByText("项目已导入，正在自动扫描", { exact: true }),
    ).toBeHidden();
    await page.screenshot({
      path: "../docs/screenshots/workspace.png",
      fullPage: true,
    });
  }
});
