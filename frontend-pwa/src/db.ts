import Dexie, { type EntityTable } from "dexie";

interface Job {
  id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  branchName: string;
  updatedAt: string;
  lastSyncedAt: string;
}

interface Diff {
  id: string;
  jobId: string;
  summary: string;
  status: string;
  filesChanged: string[];
  updatedAt: string;
  lastSyncedAt: string;
}

interface PendingAction {
  id: string;
  jobId: string;
  actionType: "approve_diff" | "reject_diff" | "comment" | "change_priority";
  payload: Record<string, unknown>;
  createdAt: string;
  status: "pending" | "syncing" | "synced" | "failed";
}

const db = new Dexie("dopaCode") as Dexie & {
  jobs: EntityTable<Job, "id">;
  diffs: EntityTable<Diff, "id">;
  pendingActions: EntityTable<PendingAction, "id">;
};

db.version(1).stores({
  jobs: "id, status, updatedAt",
  diffs: "id, jobId, status, updatedAt",
  pendingActions: "id, jobId, status",
});

export type { Job, Diff, PendingAction };
export default db;
