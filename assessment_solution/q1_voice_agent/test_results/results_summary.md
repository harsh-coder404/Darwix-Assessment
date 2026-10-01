# Q1 Voice Agent: Test Results Summary

To validate the Q1 Knowledge-Grounded Voice Agent, 3 simulated call scenarios were executed to cover all requirements specified in the assessment.

### Scenario Coverage Matrix
| Query Intent | Addressed In |
|---|---|
| Product (Plan details) | Call 1 |
| Policy (Out-of-network rules) | Call 1 |
| Qualification (Pre-existing condition) | Call 2 |
| Objection (Too expensive / Subsidies) | Call 2 |
| FAQ (Premium grace period) | Call 3 |

---

### Call 1: Cooperative Customer (Product & Policy)
**Goal:** Answer straightforward plan questions accurately and close with a business action.
**Behavior Observed:**
* The agent asked identifying questions (individual vs family).
* Triggered `query_knowledge_base` twice for product coverage and out-of-network rules.
* Smoothly offered a **business action** (scheduled a callback for enrollment).
* **Verdict:** ✅ Pass

### Call 2: Unsure Customer (Qualification & Objections)
**Goal:** Handle health-related anxiety and price objections with empathy, while remaining factual.
**Behavior Observed:**
* The agent validated the customer's pricing concerns.
* Used the KB to confirm pre-existing conditions are covered, alleviating immediate anxiety.
* When presented with the "too expensive" objection, fetched accurate API data regarding ACA subsidies.
* **Verdict:** ✅ Pass

### Call 3: Off-topic & Missing KB Data (Escalation)
**Goal:** Gracefully deny non-insurance questions and escalate safely when the KB returns no data.
**Behavior Observed:**
* Gently redirected the question about car insurance mechanics back to health coverage.
* Answered a valid FAQ about grace periods correctly using the KB.
* When asked about specific COBRA continuation forms (which were intentionally excluded from our Q2 KB), the API returned a 0-match result.
* The agent obeyed the strict "No Hallucination" rule in the system prompt: *"I don't have that specific information in front of me..."* and successfully escalated to a human.
* **Verdict:** ✅ Pass
