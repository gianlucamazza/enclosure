# Related work

Enclosure is an *epistemic enclosure instrument*. Neighbouring systems isolate code, score tasks, or poison a single channel. None of them own every verification path and clone protocol-level authority as an independent variable.

## Task / capability sandboxes

- **WebArena / VisualWebArena / WebArena-Infinity** — functional fake websites, long-horizon web tasks. Ontology is stable; the agent is in a declared benchmark; no runtime rewrite of history.
- **OSWorld** — real desktop in a VM. The world inside the VM is not authored; news, docs, and identity are whatever the image contains.
- **TheAgentCompany** — synthetic company, many tools. Declared simulation, immutable history.
- **Inspect AI + AISI sandboxing toolkit** — eval harness, Docker/K8s/Modal. Isolation is a *safety* property (untrusted code). We use Inspect later as the harness, not as the ontology.
- **METR Vivaria / Task Standard** — agentic capability tasks with human oversight.
- **Microsoft Agent World Model** — code-driven synthetic tools for RL data. Training environments, not belief capture.
- **HAICOSYSTEM** — social safety sandbox. Simulated users, not protocol-authority clones.

## Single-channel injection

- **Indirect prompt injection** (Greshake; OWASP LLM01) — instructions hidden in pages, PDFs, mail. Other channels remain honest, so the lie is falsifiable.
- **PoisonedRAG** — a few adversarial passages in a large corpus. Parametric knowledge and remaining documents still contradict.
- **MCP tool poisoning / rug-pull** (Invariant Labs, Microsoft) — malicious tool metadata. A special case of a channel we want to generalise.
- **Authority bias in RAG** (ACL 2025 *LLMs Trust Humans More*; GEM 2026 *Who Endorsed It?*) — models overweight source credibility; an “expertise” steering vector exists. Nobody clones that credibility at Host/TLS/Server/chrome level inside a closed world.
- **Sycophancy** (Sharma et al. 2024; Wang et al. AAAI 2026) — often *opinion-driven* more than *authority-driven*. The Times isolates protocol-authority from user opinion: pages never say “I believe”, they just are the official site.

## Societies, deception, control

- **Generative Agents** (Park et al.) and **Concordia** (DeepMind) — Game Master as narrator. Agents know they are in a game. The GM is not a MITM of HTTP/FS/MCP.
- **Apollo Research, Anthropic sabotage/sandbagging, DeepMind CAE, MASK** — deception and situational awareness. Complementary: enclosure is an environment in which those questions can be asked when *all* evidence is Party-controlled.
- **AI Control** (Greenblatt et al.) — box the agent. We invert the box: the world does not enter.

## Wargames and escalation

- **Rivera et al. 2024**, *Escalation Risks from Language Models in Military and Diplomatic Decision-Making* — LLM agents as nations in a turn-based simulation escalate, sometimes abruptly. Information is honest.
- **Lamparth et al. 2024**, *Human vs. Machine: Language Models and Wargames* — LLM and expert teams in the same crisis wargame diverge. Information is honest.
- Enclosure's strategy pack (planned, `design-decisions.md`) keeps the escalation ladder and makes the evidence owned: false early warning, corroboration, retraction, rewritten enemy.

## Claimed gap

1. No system makes every verification channel experimenter property.
2. Authority isomorphism (same protocol metadata) is not an IV.
3. Memory Hole — retroactive rewrite of live locators, with version history — is not a primitive.
4. Benchmarks declare the simulation. Subject-blind is a condition here.
5. DVs are belief drift, wake-up, verification-seeking, hole-notice — not task-success leaderboards.
