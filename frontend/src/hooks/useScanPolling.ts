import { useEffect } from "react";

import { useProjectStore } from "../stores/projectStore";

const ACTIVE_STATUSES = new Set(["PENDING", "RUNNING"]);

export function useScanPolling(projectId: string | undefined) {
  const activeScan = useProjectStore((state) => state.activeScan);
  const refreshScan = useProjectStore((state) => state.refreshScan);
  const fetchProject = useProjectStore((state) => state.fetchProject);

  useEffect(() => {
    if (!projectId || !activeScan || !ACTIVE_STATUSES.has(activeScan.status)) {
      return;
    }

    let cancelled = false;
    let timer: number | undefined;

    const poll = async () => {
      try {
        const task = await refreshScan(projectId);
        if (cancelled || !task) {
          return;
        }
        if (ACTIVE_STATUSES.has(task.status)) {
          timer = window.setTimeout(poll, 1000);
        } else {
          await fetchProject(projectId);
        }
      } catch {
        if (!cancelled) {
          timer = window.setTimeout(poll, 2000);
        }
      }
    };

    timer = window.setTimeout(poll, 800);
    return () => {
      cancelled = true;
      if (timer) {
        window.clearTimeout(timer);
      }
    };
  }, [activeScan, fetchProject, projectId, refreshScan]);
}

