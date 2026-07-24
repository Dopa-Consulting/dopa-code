import dbase, { type Job, type Diff, type PendingAction } from "../db";

const API_BASE = "http://localhost:8000/api/v1";

export type { Job, Diff, PendingAction };

export async function syncJobs(): Promise<Job[]> {
  try {
    const res = await fetch(`${API_BASE}/jobs/`);
    if (!res.ok) return [];
    const data = await res.json();
    const jobs: Job[] = (data.jobs || []).map((j: Record<string, unknown>) => ({
      id: j.id as string,
      title: j.title as string || "",
      description: "",
      status: j.status as string || "unknown",
      priority: j.priority as string || "normal",
      branchName: j.branch_name as string || "",
      updatedAt: j.updated_at as string || new Date().toISOString(),
      lastSyncedAt: new Date().toISOString(),
      profile: j.profile as string || "pro_mix",
      autonomyLevel: j.autonomy_level as string || "human_gatekeeper",
    }));
    await dbase.jobs.bulkPut(jobs);
    return jobs;
  } catch {
    return [];
  }
}

export function getLocalJobs(): Promise<Job[]> {
  return dbase.jobs.orderBy("updatedAt").reverse().toArray();
}

export async function syncDiffs(jobId: string): Promise<Diff[]> {
  try {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/diffs`);
    if (!res.ok) return [];
    const data = await res.json();
    const diffs: Diff[] = (data.diffs || []).map((d: Record<string, unknown>) => ({
      id: d.id as string,
      jobId: jobId,
      summary: d.summary as string || "",
      status: d.status as string || "unknown",
      filesChanged: (d.files_changed as string[]) || [],
      updatedAt: d.created_at as string || new Date().toISOString(),
      lastSyncedAt: new Date().toISOString(),
    }));
    await dbase.diffs.bulkPut(diffs);
    return diffs;
  } catch {
    return [];
  }
}

export function getLocalDiffs(jobId: string): Promise<Diff[]> {
  return dbase.diffs.where("jobId").equals(jobId).toArray();
}

export async function approveJob(jobId: string, deviceId = "pwa"): Promise<boolean> {
  const action: PendingAction = {
    id: crypto.randomUUID(),
    jobId,
    actionType: "approve_diff",
    payload: { deviceId },
    createdAt: new Date().toISOString(),
    status: "pending",
  };

  const online = navigator.onLine;
  if (online) {
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/approve?device_id=${deviceId}`, {
        method: "POST",
      });
      if (res.ok) {
        action.status = "synced";
        await dbase.pendingActions.put(action);
        return true;
      }
    } catch {
      // fall through to queue
    }
  }

  await dbase.pendingActions.put(action);
  return false;
}

export async function rejectJob(jobId: string, deviceId = "pwa"): Promise<boolean> {
  const action: PendingAction = {
    id: crypto.randomUUID(),
    jobId,
    actionType: "reject_diff",
    payload: { deviceId },
    createdAt: new Date().toISOString(),
    status: "pending",
  };

  const online = navigator.onLine;
  if (online) {
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/reject?device_id=${deviceId}`, {
        method: "POST",
      });
      if (res.ok) {
        action.status = "synced";
        await dbase.pendingActions.put(action);
        return true;
      }
    } catch {
      // fall through to queue
    }
  }

  await dbase.pendingActions.put(action);
  return false;
}

export async function flushPendingActions(): Promise<number> {
  const pending = await dbase.pendingActions.where("status").equals("pending").toArray();
  let synced = 0;

  for (const action of pending) {
    try {
      const endpoint = action.actionType === "approve_diff"
        ? `${API_BASE}/jobs/${action.jobId}/approve`
        : `${API_BASE}/jobs/${action.jobId}/reject`;

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_id: action.payload?.deviceId || "pwa" }),
      });

      if (res.ok) {
        await dbase.pendingActions.update(action.id, { status: "synced" });
        synced++;
      }
    } catch {
      // retry on next flush
    }
  }

  return synced;
}
