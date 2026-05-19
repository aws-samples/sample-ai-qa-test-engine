# Requirements Clarification Questions — AgentCore Deployment

You noted that I missed questions about AgentCore deployment. Here are the follow-up questions for that area.

---

## Question 17
For AgentCore deployment architecture — should it follow the same 2-agent pattern (Orchestrator + Test Runner)?

A) Yes — same pattern: Orchestrator fans out scenarios to parallel Test Runner agents
B) Single agent that handles both orchestration and execution (simpler but no parallelism)
C) 3-agent pattern: Orchestrator + Translator + Test Runner (separate translation agent)
D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 18
For AgentCore browser usage — should the engine support both AgentCore browser AND local browser when deployed to AgentCore?

A) AgentCore browser only when deployed (simpler, no browser packaging needed)
B) Both — AgentCore browser by default, but option to package a browser in the container
C) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 19
For the S3 input structure when deployed — should it match the existing deploy_test_translator pattern?

```
s3://bucket/prefix/
├── features/*.feature
├── tag-url-mapping.json
└── custom-functions/
    └── custom_functions.py (+ any user-supplied files)
```

A) Yes — same structure as existing deploy_test_translator
B) Extend it — add support for Excel data files, common steps, trajectory cache in S3
C) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 20
For the AgentCore deployment — should translation (Gherkin → JSON) happen in the orchestrator, test runner, or be pre-translated?

A) Orchestrator translates (like current deploy_test_translator — orchestrator calls test runner's translate action)
B) Pre-translated: user uploads JSON directly, no runtime translation
C) Both — support pre-translated JSON OR runtime translation (cache in S3)
D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 21
For parallelism when deployed — what's the expected concurrency model?

A) Fan-out per scenario (each scenario = 1 Test Runner invocation, like current)
B) Fan-out per feature (each feature = 1 Test Runner invocation that runs all its scenarios sequentially)
C) Configurable — user chooses per-scenario or per-feature parallelism
D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 22
For the "develop one feature at a time" approach — when should AgentCore deployment be built?

A) After core local execution is working (feature 2 or 3)
B) After most local features are done (near the end)
C) Build the deployment infrastructure early, then add features to both local and deployed simultaneously
D) Other (please describe after [Answer]: tag below)

[Answer]: D - after most are done except mobile, guage

---
