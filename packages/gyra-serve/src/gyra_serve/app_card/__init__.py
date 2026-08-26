"""AppCard serve — agent-generated interactive sub-apps (应用卡片).

A sub-app is a frozen, agent-generated artifact (self-contained HTML/JS) plus a
named "query" data contract. At runtime the card renders in a sandboxed iframe
inside the space homepage and fetches data through a single unified `invoke`
protocol (`op`-based capability dispatch), never re-invoking the agent.
"""
