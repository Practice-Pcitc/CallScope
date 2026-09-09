import { useEffect } from "react";

import { useEndpointStore } from "../stores/endpointStore";
import { useProjectStore } from "../stores/projectStore";

const ACTIVE_STATUSES = new Set(["PENDING", "RUNNING"]);

export function useScanPolling(projectId: string | undefined) {
  const activeScanId = useProjectStore((state) => state.activeScan?.id);
  const refreshScan = useProjectStore((state) => state.refreshScan);
  const fetchProject = useProjectStore((state) => state.fetchProject);
  const fetchEndpoints = useEndpointStore((state) => state.fetchEndpoints);

  useEffect(() => {
    if (!projectId) {
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
          if (task.status === "SUCCEEDED") {
            await fetchEndpoints(projectId);
          }
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
  }, [activeScanId, fetchEndpoints, fetchProject, projectId, refreshScan]);
}
