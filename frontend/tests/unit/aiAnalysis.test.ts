import { afterEach, expect, test, vi } from "vitest";
import { apiClient } from "../../src/api/client";
import { waitForAnalysis } from "../../src/api/aiAnalysisApi";
import { useAIAnalysisStore } from "../../src/stores/aiAnalysisStore";
import type { AIAnalysisData } from "../../src/types/aiAnalysis";

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
  useAIAnalysisStore.getState().reset();
});

test("polling returns completed results", async () => {
  vi.useFakeTimers();
  const complete = { analysisId: "a", status: "COMPLETED" } as AIAnalysisData;
  vi.spyOn(apiClient, "get").mockResolvedValue({ data: { data: complete } });
  const pending = waitForAnalysis({
    analysisId: "a",
    status: "ANALYZING",
  } as AIAnalysisData);
  await vi.advanceTimersByTimeAsync(1000);
  expect(await pending).toEqual(complete);
});

test("aborted polling never issues another request", async () => {
  const controller = new AbortController();
  controller.abort();
  const get = vi.spyOn(apiClient, "get");
  await expect(
    waitForAnalysis(
      { status: "ANALYZING" } as AIAnalysisData,
      controller.signal,
    ),
  ).rejects.toThrow();
  expect(get).not.toHaveBeenCalled();
});

test("empty selection is handled without calling a model", async () => {
  const post = vi.spyOn(apiClient, "post");
  await useAIAnalysisStore.getState().analyzeEndpoints("p", []);
  expect(useAIAnalysisStore.getState().error).toBeTruthy();
  expect(post).not.toHaveBeenCalled();
});

test("late analysis cannot overwrite state after a project switch", async () => {
  let finish!: (value: unknown) => void;
  vi.spyOn(apiClient, "post").mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const pending = useAIAnalysisStore
    .getState()
    .analyzeEndpoints("old-project", ["endpoint"]);
  useAIAnalysisStore.getState().reset();
  finish({ data: { data: { analysisId: "old", status: "COMPLETED" } } });
  await pending;
  expect(useAIAnalysisStore.getState().analysis).toBeNull();
});
