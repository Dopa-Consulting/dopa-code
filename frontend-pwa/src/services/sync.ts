import dbase, { type Job, type Diff, type PendingAction } from "../db";

const API_BASE = `${location.protocol}//${location.host}/api/v1`;

export type { Job, Diff, PendingAction };

// ── Sync Meta ──

async function getLastSyncTs(): Promise<string | null> {
  try {
    const meta = await dbase.syncMeta.get("lastSyncTs");
    return meta?.value || null;
  } catch {
    return null;
  }
}

async function setLastSyncTs(ts: string) {
  await dbase.syncMeta.put({ id: "lastSyncTs", value: ts });
}

// ── Incremental Sync ──

export async function syncJobs(): Promise<Job[]> {
  try {
    const lastTs = await getLastSyncTs();
    const url = lastTs
      ? `${API_BASE}/jobs/?since=${encodeURIComponent(lastTs)}`
      : `${API_BASE}/jobs/`;
    const res = await fetch(url);
    if (!res.ok) return getLocalJobs();
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
    if (jobs.length > 0) {
      await dbase.jobs.bulkPut(jobs);
      await setLastSyncTs(jobs[0].updatedAt);
    }
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
    const lastTs = await getLastSyncTs();
    const url = lastTs
      ? `${API_BASE}/jobs/${jobId}/diffs?since=${encodeURIComponent(lastTs)}`
      : `${API_BASE}/jobs/${jobId}/diffs`;
    const res = await fetch(url);
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

// ── Actions (approve/reject) ──

async function registerBgSync() {
  try {
    if ("serviceWorker" in navigator && navigator.serviceWorker.ready) {
      const reg = await navigator.serviceWorker.ready;
      if ("sync" in reg) {
        await (reg as ServiceWorkerRegistration & { sync: { register(tag: string): Promise<void> } }).sync.register("flush-pending");
      }
    }
  } catch { /* SW not available */ }
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
      const res = await fetch(`${API_BASE}/jobs/${jobId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_id: deviceId }),
      });
      if (res.ok) {
        action.status = "synced";
        await dbase.pendingActions.put(action);
        return true;
      }
    } catch {
      // queue below
    }
  }

  action.status = "pending";
  await dbase.pendingActions.put(action);
  await registerBgSync();
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
      const res = await fetch(`${API_BASE}/jobs/${jobId}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_id: deviceId }),
      });
      if (res.ok) {
        action.status = "synced";
        await dbase.pendingActions.put(action);
        return true;
      }
    } catch {
      // queue below
    }
  }

  action.status = "pending";
  await dbase.pendingActions.put(action);
  await registerBgSync();
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

// ── Chat Messages Sync ──

export async function saveMessage(sessionId: string, role: string, content: string): Promise<string> {
  const id = crypto.randomUUID();
  await dbase.messages.put({
    id,
    sessionId,
    role,
    content,
    timestamp: new Date().toISOString(),
  });
  return id;
}

export async function getMessages(sessionId: string, limit = 100) {
  return dbase.messages
    .where("sessionId").equals(sessionId)
    .reverse()
    .sortBy("timestamp")
    .then(msgs => msgs.slice(-limit));
}
