import Dexie, { type EntityTable } from "dexie";

export interface Job {
  id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  branchName: string;
  updatedAt: string;
  lastSyncedAt: string;
  profile: string;
  autonomyLevel: string;
}

export interface Diff {
  id: string;
  jobId: string;
  summary: string;
  status: string;
  filesChanged: string[];
  diffText?: string;
  updatedAt: string;
  lastSyncedAt: string;
}

export interface PendingAction {
  id: string;
  jobId: string;
  actionType: "approve_diff" | "reject_diff" | "comment" | "change_priority";
  payload: Record<string, unknown>;
  createdAt: string;
  status: "pending" | "syncing" | "synced" | "failed";
}

export interface ChatMessage {
  id: string;
  sessionId: string;
  role: string;
  content: string;
  timestamp: string;
}

const dbase = new Dexie("dopaCode") as Dexie & {
  jobs: EntityTable<Job, "id">;
  diffs: EntityTable<Diff, "id">;
  pendingActions: EntityTable<PendingAction, "id">;
  messages: EntityTable<ChatMessage, "id">;
  syncMeta: EntityTable<{ id: string; value: string }, "id">;
};

dbase.version(2).stores({
  jobs: "id, status, updatedAt",
  diffs: "id, jobId, status, updatedAt",
  pendingActions: "id, jobId, status",
  messages: "id, sessionId, timestamp",
  syncMeta: "id",
});

export default dbase;
