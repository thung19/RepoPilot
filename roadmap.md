RepoPilot: Agent Harness Project Roadmap
Project objective
Build an agent that investigates unfamiliar GitHub repositories and produces an evidence-backed developer onboarding guide covering architecture, entry points, dependencies, data flow, and setup instructions.

The learning objective is to understand agent harnesses, orchestration, tool execution, state management, verification, and evaluation by implementing progressively more capable versions of the same system.
Version overview
Version	Architecture	Primary learning goal
V0	Deterministic pipeline	Baselines and ordinary workflows
V1	LLM-assisted pipeline	Prompting and structured outputs
V2	Single tool-using agent	Agent loops, tools, and state
V3	Multi-agent orchestrator	Delegation and coordination
V4	Verification and evaluation	Feedback loops and benchmarking


V0: Deterministic repository analyzer
Goal: Produce a basic repository report without an LLM.

Workflow: Repository → Inspect → Extract metadata → Generate report
- [ ] Accept a local repository path through a CLI.
- [ ] List directories and relevant source files.
- [ ] Read the README and locate dependency/configuration files.
- [ ] Identify candidate entry points using explicit rules.
- [ ] Generate a Markdown report.
- [ ] Test the filesystem and search functions.
Completion criterion: A single command produces a reproducible report for an unfamiliar repository.

Learn: Deterministic pipelines, reusable tools, and baseline construction.
V1: LLM-assisted analyzer
Goal: Use an LLM to interpret repository evidence collected by a fixed pipeline.

Workflow: Repository → Deterministic inspection → LLM → Structured report
- [ ] Integrate an LLM API directly.
- [ ] Provide the collected repository evidence as context.
- [ ] Define a structured output schema for architecture, dependencies, entry points, and setup.
- [ ] Require file references for factual claims and explicit unknowns for missing evidence.
- [ ] Validate the returned structure.
Completion criterion: The LLM produces a structured architecture summary from the V0 evidence, without dynamically choosing tools.

Learn: Model APIs, prompts, context, structured outputs, and schema validation.
V2: Autonomous tool-using agent
Goal: Build a basic agent harness from scratch that lets an LLM decide how to investigate a repository.

Workflow: Objective → LLM → Tool request → Execute → Observe → Repeat → Report
- [ ] Expose tools such as list_directory, read_file, find_files, search_code, and inspect_imports.
- [ ] Define tool descriptions and argument schemas.
- [ ] Implement a tool registry and dispatcher.
- [ ] Implement the agent execution loop and message history.
- [ ] Feed tool results back to the model.
- [ ] Handle invalid arguments, unknown tools, and execution errors.
- [ ] Add step limits and explicit termination conditions.
- [ ] Record tool calls, results, token usage, and execution time in JSONL traces.
Completion criterion: Given only a repository and an objective, the agent selects its own sequence of tools and produces an evidence-backed report within a bounded execution budget.

Learn: Tool calling, agent runtimes, state management, context, termination, and tracing.

Priority: This is the most important version to implement yourself before adopting an agent framework.
V3: Multi-agent orchestrator
Goal: Explore whether specialized agents improve repository investigation.

Workflow: Objective → Lead orchestrator → Specialized agents → Consolidated report
- [ ] Reuse the V2 runtime for specialized agents.
- [ ] Create an architecture agent to investigate components and data flow.
- [ ] Create a dependency agent to investigate packages, configuration, and setup.
- [ ] Create a quality agent to investigate tests and potential issues.
- [ ] Implement an orchestrator that delegates subtasks and collects structured findings.
- [ ] Define how agents exchange evidence and maintain separate contexts.
- [ ] Consolidate results while preserving evidence references and unresolved disagreements.
- [ ] Enforce an overall execution budget across workers.
Completion criterion: The orchestrator delegates investigation to specialized agents and combines their findings into one report.

Learn: Task decomposition, delegation, agent communication, shared versus private state, and orchestration.

Research question: Does multi-agent orchestration improve report quality enough to justify additional cost and complexity?
V4: Verification and evaluation
Goal: Verify agent outputs, enable bounded refinement, and compare architectures objectively.

Workflow: Generate report → Verify claims → Revise if necessary → Score and log
- [ ] Validate cited file paths and function/class references.
- [ ] Check cited evidence against the original source files.
- [ ] Flag unsupported claims and unresolved assumptions.
- [ ] Feed verification failures back to the agent for bounded revision.
- [ ] Create benchmark cases using at least three familiar repositories.
- [ ] Manually establish reference facts for each benchmark case.
- [ ] Run V0 through V3 on the same repositories and compare applicable metrics.
- [ ] Record accuracy, coverage, unsupported claims, tool calls, tokens, and wall-clock time.
- [ ] Document trade-offs and failure cases.
Completion criterion: One benchmark command produces comparable results and execution traces for each architecture.

Learn: Evaluator-optimizer loops, deterministic verification, scoring, experimental design, and reproducibility.

Limitation: Checking that a file or symbol exists does not prove that a semantic architecture claim is correct. Use manually reviewed reference facts for semantic evaluation. Setup instructions must be marked unverified unless actually tested in an appropriate isolated environment.
Implementation guidelines
- Start with Python, a direct LLM SDK, pathlib, ast, Pydantic, pytest, and JSONL.
- Keep the MVP CLI-based and read-only; restrict file access to the selected repository and treat repository content as untrusted data.
- Do not execute arbitrary repository code or expose secrets to the LLM.
- Reuse tools and evaluation cases across versions to make comparisons meaningful.
- Avoid agent frameworks, MCP, databases, and a frontend initially.
- Complete V0–V2 before expanding to V3–V4. The latter are stretch goals, not MVP blockers.
Connection to Agentic Transfer Bench
RepoPilot	Agentic Transfer Bench
Repository inspection	Dataset profiling
Codebase requirements	Model input contracts
Tool selection	Statistical and ML tool selection
Evidence-backed report	Adaptation strategy
Claim verification	Model compatibility and scientific validation
Architecture benchmarking	Agent-vs-rule evaluation


The reusable deliverable is the harness infrastructure, not just the repository analysis tool.