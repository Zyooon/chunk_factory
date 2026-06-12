"""
chatbot_rag LangGraph 시각화 스크립트

Mermaid Ink API(온라인)를 우선 사용하고,
네트워크 오류 시 networkx + matplotlib 로 PNG를 로컬 렌더링한다.

저장 위치: data/graph/chatbot_rag_graph.png
"""

from __future__ import annotations

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path 에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / "data" / "graph"
OUTPUT_PATH = OUTPUT_DIR / "chatbot_rag_graph.png"


def _save_via_mermaid_api(compiled_graph) -> bool:
    """Mermaid Ink API 로 PNG 를 저장한다. 성공 시 True 반환."""
    try:
        from langchain_core.runnables.graph_mermaid import MermaidDrawMethod

        png_bytes: bytes = compiled_graph.get_graph().draw_mermaid_png(
            draw_method=MermaidDrawMethod.API,
        )
        OUTPUT_PATH.write_bytes(png_bytes)
        print(f"[Mermaid API] 저장 완료: {OUTPUT_PATH}")
        return True
    except Exception as exc:
        print(f"[Mermaid API] 실패: {exc}")
        return False


def _save_via_matplotlib(compiled_graph) -> bool:
    """networkx + matplotlib 로 PNG 를 로컬 렌더링한다. 성공 시 True 반환."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.patches as mpatches
        import matplotlib.pyplot as plt
        import networkx as nx
        from langchain_core.runnables.graph import Graph

        lc_graph: Graph = compiled_graph.get_graph()

        # ── 노드 / 엣지 수집 ──────────────────────────────────────────────
        node_ids = list(lc_graph.nodes.keys())
        edges_raw = [
            (e.source, e.target, bool(e.data), e.data)
            for e in lc_graph.edges
        ]

        G = nx.DiGraph()
        G.add_nodes_from(node_ids)
        for src, dst, is_cond, label in edges_raw:
            G.add_edge(src, dst, conditional=is_cond, label=label or "")

        # ── 레이아웃 ──────────────────────────────────────────────────────
        try:
            pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
        except Exception:
            pos = nx.spring_layout(G, seed=42, k=2.5)

        # ── 색상 분류 ─────────────────────────────────────────────────────
        START_COLOR = "#4CAF50"
        END_COLOR   = "#F44336"
        DEFAULT_COLOR = "#64B5F6"

        node_colors = []
        for n in G.nodes():
            if n == "__start__":
                node_colors.append(START_COLOR)
            elif n == "__end__":
                node_colors.append(END_COLOR)
            else:
                node_colors.append(DEFAULT_COLOR)

        # ── 엣지 분류 ─────────────────────────────────────────────────────
        solid_edges = [(s, t) for s, t, d in G.edges(data=True) if not d.get("conditional")]
        cond_edges  = [(s, t) for s, t, d in G.edges(data=True) if d.get("conditional")]
        edge_labels = {
            (s, t): d["label"]
            for s, t, d in G.edges(data=True)
            if d.get("label")
        }

        # ── 그리기 ────────────────────────────────────────────────────────
        fig, ax = plt.subplots(figsize=(16, 12))
        ax.set_facecolor("#F8F9FA")
        fig.patch.set_facecolor("#F8F9FA")

        # 라벨용 짧은 이름 매핑
        label_map = {n: n.replace("__start__", "START").replace("__end__", "END") for n in G.nodes()}

        nx.draw_networkx_nodes(
            G, pos, ax=ax,
            node_color=node_colors,
            node_size=3000,
            alpha=0.95,
        )
        nx.draw_networkx_labels(
            G, pos, ax=ax,
            labels=label_map,
            font_size=9,
            font_weight="bold",
            font_color="white",
        )
        nx.draw_networkx_edges(
            G, pos, ax=ax,
            edgelist=solid_edges,
            edge_color="#37474F",
            arrows=True,
            arrowsize=20,
            width=1.8,
            connectionstyle="arc3,rad=0.08",
        )
        nx.draw_networkx_edges(
            G, pos, ax=ax,
            edgelist=cond_edges,
            edge_color="#FF9800",
            arrows=True,
            arrowsize=20,
            width=1.8,
            style="dashed",
            connectionstyle="arc3,rad=0.08",
        )
        if edge_labels:
            nx.draw_networkx_edge_labels(
                G, pos, ax=ax,
                edge_labels=edge_labels,
                font_size=7,
                font_color="#BF360C",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7),
            )

        # ── 범례 & 제목 ───────────────────────────────────────────────────
        legend_items = [
            mpatches.Patch(color=START_COLOR,   label="START"),
            mpatches.Patch(color=END_COLOR,     label="END"),
            mpatches.Patch(color=DEFAULT_COLOR, label="Node"),
            mpatches.Patch(color="#37474F",     label="일반 엣지"),
            mpatches.Patch(color="#FF9800",     label="조건부 엣지"),
        ]
        ax.legend(handles=legend_items, loc="upper left", fontsize=9)
        ax.set_title("chatbot_rag LangGraph", fontsize=16, fontweight="bold", pad=15)
        ax.axis("off")

        plt.tight_layout()
        plt.savefig(OUTPUT_PATH, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"[matplotlib] 저장 완료: {OUTPUT_PATH}")
        return True

    except Exception as exc:
        print(f"[matplotlib] 실패: {exc}")
        return False


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("chatbot_rag 그래프를 빌드 중...")
    from apps.chatbot_rag.graph import build_chatbot_graph
    compiled = build_chatbot_graph()
    print("그래프 빌드 완료.")

    if _save_via_mermaid_api(compiled):
        return

    print("Mermaid API 실패 — matplotlib 로 fallback 렌더링 중...")
    if _save_via_matplotlib(compiled):
        return

    print("모든 렌더링 방법 실패. matplotlib 패키지가 설치되어 있는지 확인하세요.")
    sys.exit(1)


if __name__ == "__main__":
    main()
