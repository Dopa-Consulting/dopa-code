import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000/api/v1";

export default function useDeploy(jobId: string) {
  const [ciStatus, setCiStatus] = useState<string>("unknown");
  const [easyPanelToken, setEasyPanelToken] = useState<string>("");

  const fetchCiStatus = useCallback(async () => {
    if (!jobId) return;
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/ci-status`);
      if (!res.ok) return;
      const data = await res.json();
      const latest = data.ci_runs?.[0];
      if (latest) setCiStatus(latest.status);
    } catch {
      // ignore offline
    }
  }, [jobId]);

  useEffect(() => {
    fetchCiStatus();
    const interval = setInterval(fetchCiStatus, 10000);
    return () => clearInterval(interval);
  }, [fetchCiStatus]);

  const deploy = useCallback(async (environment = "production") => {
    if (!jobId) return { error: "No job ID" };
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/deploy`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ environment, triggered_by: "human" }),
      });
      return await res.json();
    } catch {
      return { error: "Deploy failed" };
    }
  }, [jobId]);

  const merge = useCallback(async (method = "merge") => {
    if (!jobId) return { error: "No job ID" };
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/merge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ merge_method: method, device_id: "pwa" }),
      });
      return await res.json();
    } catch {
      return { error: "Merge failed" };
    }
  }, [jobId]);

  const saveToken = useCallback(async (projectId: string, token: string, endpoint?: string) => {
    try {
      const res = await fetch(`${API_BASE}/jobs/deploy-token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId, token, endpoint }),
      });
      return await res.json();
    } catch {
      return { error: "Save failed" };
    }
  }, []);

  return { ciStatus, deploy, merge, easyPanelToken, setEasyPanelToken, saveToken };
}
