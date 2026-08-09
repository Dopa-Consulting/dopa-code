/**
 * Loop Cost — Token & cost tracking for Inti bridge.
 * 
 * Wraps each opencode run with cost tracking.
 * Exposes GET /cost/:jobId endpoint.
 */

let costStore = {};

function startCost({ jobId, model, skill }) {
  const costId = `${jobId}-${Date.now()}`;
  costStore[costId] = {
    jobId,
    model,
    skill,
    startedAt: new Date().toISOString(),
    promptTokens: 0,
    completionTokens: 0,
  };
  return costId;
}

function endCost(costId, { tokensUsed = 0, exitCode = 0 } = {}) {
  const cost = costStore[costId];
  if (!cost) return null;
  cost.totalTokens = tokensUsed;
  cost.exitCode = exitCode;
  cost.endedAt = new Date().toISOString();
  // Estimate cost (simplified pricing)
  const pricing = {
    "deepseek/deepseek-chat": 0.0002,  // per 1K tokens
    "deepseek-v4-pro": 0.0008,
    "claude-sonnet-5": 0.015,
    default: 0.005,
  };
  const rate = pricing[cost.model] || pricing.default;
  cost.costUsd = Math.round((tokensUsed / 1000) * rate * 10000) / 10000;
  return cost;
}

function getCost(jobId) {
  return Object.values(costStore)
    .filter(c => c.jobId === jobId)
    .reduce((acc, c) => ({
      jobId,
      totalTokens: (acc.totalTokens || 0) + (c.totalTokens || 0),
      totalCostUsd: ((acc.totalCostUsd || 0) + (c.costUsd || 0)).toFixed(4),
      runs: (acc.runs || 0) + 1,
    }), { jobId, totalTokens: 0, totalCostUsd: "0.0000", runs: 0 });
}

// Export for bridge.js
export { startCost, endCost, getCost, costStore };
