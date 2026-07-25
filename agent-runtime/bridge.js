import { spawn } from "child_process";
import http from "http";
import path from "path";
import fs from "fs";

const PORT = 4097;
const BRIDGE_TOKEN = process.env.DOPA_BRIDGE_TOKEN || "dopa-bridge-local-dev";

function runOpencode(directory, prompt, agent = "build") {
  return new Promise((resolve, reject) => {
    const child = spawn("opencode", ["run", prompt], {
      cwd: directory,
      env: { ...process.env, OPENCODE_AGENT: agent },
      stdio: ["pipe", "pipe", "pipe"],
      timeout: 120000,
    });

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (data) => { stdout += data.toString(); });
    child.stderr.on("data", (data) => { stderr += data.toString(); });

    child.on("close", (code) => {
      resolve({ exit_code: code, stdout: stdout.slice(-5000), stderr: stderr.slice(-2000) });
    });

    child.on("error", (err) => {
      reject(err);
    });
  });
}

function getGitDiff(directory) {
  return new Promise((resolve, reject) => {
    const child = spawn("git", ["diff", "--stat"], {
      cwd: directory,
      timeout: 10000,
    });

    let stdout = "";
    child.stdout.on("data", (data) => { stdout += data.toString(); });
    child.on("close", () => { resolve({ diff_summary: stdout.trim() || "no changes" }); });
    child.on("error", reject);
  });
}

function getFullDiff(directory) {
  return new Promise((resolve, reject) => {
    const child = spawn("git", ["diff"], {
      cwd: directory,
      timeout: 10000,
    });

    let stdout = "";
    child.stdout.on("data", (data) => { stdout += data.toString(); });
    child.on("close", () => {
      resolve({ diff_text: stdout.slice(-50000) || "", files_changed: parseFilesChanged(stdout) });
    });
    child.on("error", reject);
  });
}

function parseFilesChanged(diff) {
  const files = [];
  const regex = /^diff --git a\/(.+?) b\/(.+?)$/gm;
  let match;
  while ((match = regex.exec(diff)) !== null) {
    files.push(match[1]);
  }
  return [...new Set(files)];
}

async function main() {
  // Activar co-autoria de Inti en este workspace
  try {
    const hookDir = require("path").join(require("child_process").execSync("git rev-parse --git-dir", { encoding: "utf8" }).trim(), "hooks");
    const intiCoAuthor = `

Co-authored-by: Inti <inti@dopa.solutions>
`;
    const hookPath = require("path").join(hookDir, "prepare-commit-msg");
    if (!require("fs").existsSync(hookPath)) {
      require("fs").writeFileSync(hookPath,
        `#!/bin/sh
if ! grep -q "Co-authored-by: Inti" "$1"; then
  printf "${intiCoAuthor}" >> "$1"
fi
`);
      require("fs").chmodSync(hookPath, "755");
      console.log("[bridge] Inti co-author hook installed");
    }
  } catch (e) {
    // non-git directory, skip
  }

  const server = http.createServer(async (req, res) => {
    res.setHeader("Content-Type", "application/json");
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type, x-bridge-token");

    if (req.method === "OPTIONS") {
      res.writeHead(204);
      res.end();
      return;
    }

    const token = req.headers["x-bridge-token"];
    if (token !== BRIDGE_TOKEN) {
      res.writeHead(401);
      res.end(JSON.stringify({ error: "unauthorized" }));
      return;
    }

    const url = new URL(req.url, `http://localhost:${PORT}`);
    const p = url.pathname;

    try {
      if (p === "/health") {
        res.writeHead(200);
        res.end(JSON.stringify({ status: "ok", bridge: "dopa-code", mode: "cli" }));

      } else if (p === "/plan" && req.method === "POST") {
        const body = await readBody(req);
        const dir = body.directory || process.cwd();
        const prompt = `You are an Architect LLM. Analyze the following task and create a structured plan:\n\n${body.prompt}\n\nRespond with a JSON plan: {"title": "...", "steps": [...], "estimated_files": N}.`;
        const result = await runOpencode(dir, prompt, "plan");
        res.writeHead(200);
        res.end(JSON.stringify(result));

      } else if (p === "/execute" && req.method === "POST") {
        const body = await readBody(req);
        const dir = body.directory || process.cwd();
        const result = await runOpencode(dir, body.prompt, body.agent || "build");
        res.writeHead(200);
        res.end(JSON.stringify(result));

      } else if (p === "/diff-stat" && req.method === "GET") {
        const dir = url.searchParams.get("directory") || process.cwd();
        const result = await getGitDiff(dir);
        res.writeHead(200);
        res.end(JSON.stringify(result));

      } else if (p === "/diff" && req.method === "GET") {
        const dir = url.searchParams.get("directory") || process.cwd();
        const result = await getFullDiff(dir);
        res.writeHead(200);
        res.end(JSON.stringify(result));

      } else if (p === "/close") {
        res.writeHead(200);
        res.end(JSON.stringify({ status: "closed" }));
        server.close();
        process.exit(0);

      } else {
        res.writeHead(404);
        res.end(JSON.stringify({ error: "not found", path: p }));
      }
    } catch (err) {
      console.error("[bridge] Error:", err.message);
      res.writeHead(500);
      res.end(JSON.stringify({ error: err.message }));
    }
  });

  server.listen(PORT, () => {
    console.log(`[bridge] Dopa Code bridge listening on http://localhost:${PORT}`);
  });

  process.on("SIGINT", () => { server.close(); process.exit(0); });
  process.on("SIGTERM", () => { server.close(); process.exit(0); });
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", (chunk) => (data += chunk));
    req.on("end", () => {
      try { resolve(JSON.parse(data)); } catch (e) { reject(e); }
    });
    req.on("error", reject);
  });
}

main().catch((err) => { console.error("[bridge] Fatal:", err.message); process.exit(1); });
