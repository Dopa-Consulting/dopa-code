"""
Prototipo LangGraph FSM para Inti.

Muestra como el pipeline secuencial actual:
    Planner → Executor → QA → Human → Deploy

Se convierte en un grafo con agentes paralelos:
    Planner → Executor → [QA_Security || QA_UX || QA_Perf] → Aggregator → Human → Deploy

Diferencias clave vs FSM actual (policies.py + agent_runtime.py):
1. Agentes en paralelo en vez de secuenciales
2. Ruteo condicional (si QA_Security falla → directo a Human sin esperar UX/Perf)
3. Estado tipado con TypedDict en vez de dicts sueltos
4. Checkpointing automatico (resume desde donde fallo)
5. Streaming nativo de estado del grafo a la PWA

NO requiere instalar langgraph. Es un prototipo auto-contenido que muestra
el patron de StateGraph, nodos, edges condicionales, y ejecucion paralela.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TypedDict, Literal, Callable, Awaitable

logger = logging.getLogger("inti.langgraph")


# ---------------------------------------------------------------------------
# Estado tipado del grafo (equivalente a Job + JobSteps en la FSM actual)
# ---------------------------------------------------------------------------

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class GraphState(TypedDict, total=False):
    """Estado completo que fluye por el grafo. Tipado fuerte vs dicts sueltos."""
    job_id: str
    title: str
    description: str
    profile: str
    autonomy_level: str
    branch_name: str

    # Resultados de cada nodo
    plan: dict | None
    execution_result: dict | None

    # QA paralelo → cada agente corre en simultaneo
    qa_security: dict | None
    qa_performance: dict | None
    qa_ux: dict | None
    qa_aggregated: dict | None

    # Decisiones
    requires_human: bool
    human_decision: str | None

    deploy_result: dict | None

    # Metadata del grafo
    current_step: str
    errors: list[str]
    audit_trail: list[dict]


# ---------------------------------------------------------------------------
# Nodos del grafo (cada uno es una funcion async que toma state → state)
# ---------------------------------------------------------------------------

NodeFn = Callable[[GraphState], Awaitable[GraphState]]


async def node_planner(state: GraphState) -> GraphState:
    """Architect LLM: analiza la tarea y genera un plan estructurado."""
    state["current_step"] = "planner"
    state["audit_trail"].append({"step": "planner", "status": StepStatus.RUNNING})

    # === FSM actual: agent_runtime.plan_change() ===
    # Aqui llamaria al LLM Architect (Opus/Sonnet)
    state["plan"] = {
        "title": state["title"],
        "steps": ["analizar", "modificar", "testear"],
        "estimated_files": 3,
    }
    state["audit_trail"].append({"step": "planner", "status": StepStatus.PASSED})
    return state


async def node_executor(state: GraphState) -> GraphState:
    """Executor LLM: aplica cambios en rama aislada via OpenCode."""
    state["current_step"] = "executor"
    state["audit_trail"].append({"step": "executor", "status": StepStatus.RUNNING})

    # === FSM actual: agent_runtime.apply_change() ===
    state["execution_result"] = {
        "success": True,
        "branch": state.get("branch_name", "feature/intl"),
        "files_modified": ["src/components/Header.tsx", "src/styles/theme.css"],
    }
    state["audit_trail"].append({"step": "executor", "status": StepStatus.PASSED})
    return state


# ---------------------------------------------------------------------------
# QA PARALELO — LA GRAN DIFERENCIA CON LA FSM ACTUAL
# En la FSM actual: QA secuencial (un solo agente revisa todo)
# En LangGraph: 3 agentes corren en simultaneo, cada uno especializado
# ---------------------------------------------------------------------------

async def node_qa_security(state: GraphState) -> GraphState:
    """QA especializado en seguridad: revisa vulnerabilidades, secrets, guardrails."""
    state["current_step"] = "qa_security"
    # En produccion: llama al LLM QA con prompt de seguridad
    state["qa_security"] = {
        "passed": True,
        "score": 0.95,
        "issues": [],
        "agent": "security",
    }
    return state


async def node_qa_performance(state: GraphState) -> GraphState:
    """QA especializado en performance: bundle size, lazy loading, render time."""
    state["current_step"] = "qa_performance"
    state["qa_performance"] = {
        "passed": True,
        "score": 0.88,
        "issues": ["Bundle size +15KB en Header.tsx"],
        "agent": "performance",
    }
    return state


async def node_qa_ux(state: GraphState) -> GraphState:
    """QA especializado en UX: accesibilidad, responsive, consistencia visual."""
    state["current_step"] = "qa_ux"
    state["qa_ux"] = {
        "passed": True,
        "score": 0.92,
        "issues": [],
        "agent": "ux",
    }
    return state


async def node_qa_aggregator(state: GraphState) -> GraphState:
    """Consolida resultados de los 3 QA agents en paralelo."""
    results = [
        state.get("qa_security", {}),
        state.get("qa_performance", {}),
        state.get("qa_ux", {}),
    ]
    all_passed = all(r.get("passed", False) for r in results if r)
    scores = [r.get("score", 0) for r in results if r]
    avg_score = sum(scores) / len(scores) if scores else 0
    all_issues = []
    for r in results:
        all_issues.extend(r.get("issues", []))

    state["qa_aggregated"] = {
        "passed": all_passed,
        "average_score": round(avg_score, 2),
        "total_issues": len(all_issues),
        "issues": all_issues,
        "agents_used": [r.get("agent") for r in results if r],
    }
    state["requires_human"] = not all_passed or avg_score < 0.85
    return state


async def node_human_approval(state: GraphState) -> GraphState:
    """Espera aprobacion humana via PWA."""
    state["current_step"] = "human_approval"
    state["human_decision"] = "approve" if state.get("qa_aggregated", {}).get("passed", False) else "reject"
    state["audit_trail"].append({
        "step": "human_approval",
        "status": StepStatus.PASSED if state["human_decision"] == "approve" else StepStatus.FAILED,
        "decision": state["human_decision"],
    })
    return state


async def node_deploy(state: GraphState) -> GraphState:
    """Deploy a Easypanel."""
    state["current_step"] = "deploy"
    state["deploy_result"] = {"status": "deployed", "environment": "staging"}
    state["audit_trail"].append({"step": "deploy", "status": StepStatus.PASSED})
    return state


async def node_notify_failure(state: GraphState) -> GraphState:
    """Notifica fallo a la PWA y registra en audit_log."""
    state["errors"].append(f"Pipeline failed at step: {state['current_step']}")
    state["audit_trail"].append({"step": "notify_failure", "status": StepStatus.FAILED})
    return state


# ---------------------------------------------------------------------------
# Funciones de ruteo (edges condicionales)
# ---------------------------------------------------------------------------

def route_after_qa(state: GraphState) -> Literal["human_approval", "notify_failure"]:
    """Si QA paso → human_approval. Si no → notify_failure."""
    if state.get("qa_aggregated", {}).get("passed", False):
        return "human_approval"
    return "notify_failure"


def route_after_human(state: GraphState) -> Literal["deploy", "notify_failure"]:
    """Si humano aprobo → deploy. Si no → notify_failure."""
    if state.get("human_decision") == "approve":
        return "deploy"
    return "notify_failure"


# ---------------------------------------------------------------------------
# El grafo (StateGraph) — equivalente al FSM actual
# ---------------------------------------------------------------------------

@dataclass
class GraphEdge:
    source: str
    target: str
    condition: Callable[[GraphState], str] | None = None  # conditional edge
    parallel: bool = False  # nodos paralelos


@dataclass
class StateGraph:
    """Representacion simplificada de un StateGraph de LangGraph.

    En LangGraph real seria:
        from langgraph.graph import StateGraph, END
        graph = StateGraph(GraphState)
        graph.add_node("planner", node_planner)
        graph.add_edge("planner", "executor")
        graph.add_node("executor", node_executor)
        graph.add_edge("executor", "qa_security")
        graph.add_edge("executor", "qa_performance")  # paralelo!
        graph.add_edge("executor", "qa_ux")            # paralelo!
        ...
        graph.add_conditional_edges("qa_aggregator", route_after_qa, {
            "human_approval": "human_approval",
            "notify_failure": "notify_failure",
        })
        app = graph.compile()
        result = await app.ainvoke(initial_state)
    """

    nodes: dict[str, NodeFn] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)

    def add_node(self, name: str, fn: NodeFn):
        self.nodes[name] = fn

    def add_edge(self, source: str, target: str):
        self.edges.append(GraphEdge(source=source, target=target))

    def add_conditional_edges(self, source: str, condition: Callable, routes: dict):
        self.edges.append(GraphEdge(source=source, target="", condition=condition))

    def add_parallel_nodes(self, source: str, targets: list[str]):
        for t in targets:
            self.edges.append(GraphEdge(source=source, target=t, parallel=True))

    async def invoke(self, state: GraphState) -> GraphState:
        """Ejecuta el grafo secuencialmente (demo; LangGraph real lo haria en paralelo)."""
        execution_order = [
            "planner", "executor",
            "qa_security", "qa_performance", "qa_ux",  # paralelo en LG real
            "qa_aggregator",
        ]

        # Nodos secuenciales
        for node_name in execution_order:
            if node_name in self.nodes:
                state = await self.nodes[node_name](state)

        # Ruteo condicional
        next_step = route_after_qa(state)
        if next_step in self.nodes:
            state = await self.nodes[next_step](state)

        if next_step == "human_approval":
            next_step2 = route_after_human(state)
            if next_step2 in self.nodes:
                state = await self.nodes[next_step2](state)

        return state


# ---------------------------------------------------------------------------
# Factory: construye el grafo completo
# ---------------------------------------------------------------------------

def build_dopa_code_graph() -> StateGraph:
    """Construye el StateGraph de Dopa Code con agentes paralelos."""
    graph = StateGraph()

    # Nodos secuenciales
    graph.add_node("planner", node_planner)
    graph.add_node("executor", node_executor)

    # Nodos paralelos (QA especializado)
    graph.add_node("qa_security", node_qa_security)
    graph.add_node("qa_performance", node_qa_performance)
    graph.add_node("qa_ux", node_qa_ux)
    graph.add_node("qa_aggregator", node_qa_aggregator)

    # Nodos de decision
    graph.add_node("human_approval", node_human_approval)
    graph.add_node("deploy", node_deploy)
    graph.add_node("notify_failure", node_notify_failure)

    # Edges
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "qa_aggregator")  # en LG real: parallel

    return graph


# ---------------------------------------------------------------------------
# Demo: ejecutar el grafo
# ---------------------------------------------------------------------------

async def run_graph_demo():
    """Demo: ejecuta el grafo completo y muestra el resultado."""
    graph = build_dopa_code_graph()

    initial_state: GraphState = {
        "job_id": "demo-001",
        "title": "Refactorizar checkout DopaWeb",
        "description": "Mejorar UX del checkout sin romper integracion ERP",
        "profile": "dopaweb_theme",
        "autonomy_level": "plan_and_pr_only",
        "branch_name": "intl/refactor-checkout",
        "plan": None,
        "execution_result": None,
        "qa_security": None,
        "qa_performance": None,
        "qa_ux": None,
        "qa_aggregated": None,
        "requires_human": False,
        "human_decision": None,
        "deploy_result": None,
        "current_step": "init",
        "errors": [],
        "audit_trail": [],
    }

    result = await graph.invoke(initial_state)

    print("=" * 60)
    print("  LangGraph FSM — Demo de ejecucion")
    print("=" * 60)
    print(f"  Job: {result['title']}")
    print(f"  Profile: {result['profile']}")
    print(f"  Plan steps: {len(result.get('plan', {}).get('steps', []))}")
    print(f"  Execution: {result.get('execution_result', {}).get('success')}")

    qa = result.get("qa_aggregated", {})
    print(f"  QA Aggregated: passed={qa.get('passed')}, score={qa.get('average_score')}")
    print(f"  QA Agents used: {qa.get('agents_used')}")
    print(f"  QA Issues: {qa.get('total_issues')}")
    print(f"  Requires human: {result.get('requires_human')}")
    print(f"  Human decision: {result.get('human_decision')}")
    print(f"  Deploy: {result.get('deploy_result', {}).get('status')}")

    print(f"\n  Audit trail ({len(result['audit_trail'])} steps):")
    for entry in result["audit_trail"]:
        print(f"    [{entry['status']}] {entry.get('step', '?')} {entry.get('decision', '')}")

    print("=" * 60)

    # Comparativa
    print("\n  [FSM ACTUAL] policies.py + agent_runtime.py:")
    print("     Planner -> Executor -> QA (1 agente) -> Human -> Deploy")
    print("     Tiempo estimado: secuencial, ~2-3 min por job")

    print("\n  [LANGGRAPH] este prototipo:")
    print("     Planner -> Executor -> [QA_Sec||QA_Perf||QA_UX] -> Agg -> Human -> Deploy")
    print("     Tiempo estimado: paralelo, ~1-2 min por job (3 QA agents simultaneos)")

    print("\n  [DIFERENCIAS CLAVE]:")
    print("     1. QA paralelo: 3 agentes especializados corren al mismo tiempo")
    print("     2. Ruteo condicional: si security falla -> directo a human sin esperar perf/ux")
    print("     3. Checkpointing: si el grafo falla en deploy, resume desde ahi")
    print("     4. Streaming nativo: cada nodo emite eventos a la PWA en tiempo real")
    print("     5. Estado tipado: GraphState TypedDict vs dicts sueltos en FSM actual")
    print("=" * 60)

    return result


if __name__ == "__main__":
    asyncio.run(run_graph_demo())


# ---------------------------------------------------------------------------
# COSTO DE IMPLEMENTACION ESTIMADO
# ---------------------------------------------------------------------------
#
# Que hay que cambiar si migramos a LangGraph:
#
#   Archivo actual          →  Que cambia
#   ─────────────────────────────────────────────────────
#   agent_runtime.py        →  Se reemplaza por nodos del grafo
#   policies.py             →  Se mantiene (perfiles, reglas), los nodos lo leen
#   events.py               →  Se mantiene, el grafo emite eventos nativamente
#   audit.py                →  Se mantiene, el grafo registra en audit_trail
#   api/jobs.py             →  Cambia: POST /jobs/{id}/start → graph.ainvoke()
#   memory.py               →  Se mantiene, se llama desde nodos
#   guardrails.py           →  Se mantiene, se llama desde qa_security
#   models/*                →  Se mantienen igual
#   main.py                 →  +1 linea: from inti.langgraph_fsm import graph
#
#   Archivos NUEVOS:
#   inti/langgraph_fsm.py   →  Grafo completo + nodos
#   inti/nodes/planner.py   →  Nodo planner (antes en agent_runtime)
#   inti/nodes/executor.py  →  Nodo executor
#   inti/nodes/qa_*.py      →  3 nodos QA especializados
#   inti/nodes/deploy.py    →  Nodo deploy
#
#   Tiempo estimado: 2-3 sprints (2-3 semanas con ayuda de agentes)
#   Riesgo: reescribir ~40% del backend (agent_runtime + jobs API)
#   Beneficio: QA paralelo, ruteo dinamico, checkpointing, streaming nativo
#
#   Recomendacion de Perplexity:
#   "Mantener FSM propia por ahora. LangGraph mas adelante para subagentes
#    paralelos. La FSM esta en buen punto."
#
#   Mi recomendacion:
#   Implementar LangGraph como feature flag (DOPA_USE_LANGGRAPH=1).
#   Ambos pipelines conviven. Se migra gradualmente sin romper lo existente.
# ---------------------------------------------------------------------------