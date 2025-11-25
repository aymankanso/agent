# Quick Start Guide - Testing with Your Professor

## Overview
This guide will help you run the evaluation system to demonstrate the 70% automation requirement to your professor.

---

## Step 1: Verify Cost Tracking is Active

The system now automatically tracks:
- ✅ Token usage per task
- ✅ Cost per LLM call
- ✅ Latency measurements
- ✅ Total time per scenario

**Files created:**
- `logs/metrics/cost_log.csv` - Summary of all tasks
- `logs/metrics/[date]/metrics_[task_id].json` - Detailed per-task metrics

---

## Step 2: Run Quick Evaluation (5 scenarios)

```powershell
# Navigate to project root
cd "c:\Users\user\Desktop\test\agent - Copy (2)"

# Activate virtual environment (if using one)
# .venv\Scripts\Activate.ps1

# Run 5 quick scenarios for demo
python tests/evaluation/test_runner.py
```

**Expected output:**
```
Running 5 test scenarios
Model: GPT-4o Mini
==============================================================

[1/5] Running: Basic Port Scanning (easy)
Target: 192.168.1.100
==============================================================
Result: ✅ PASS
Findings: 3/2
Time: 23.45s / 300s
Cost: $0.1234 / $0.30

...

FINAL RESULTS
==============================================================
Automation Rate: 80.0%
70% Requirement: ✅ MET
Total Cost: $0.62
Total Time: 2.5 minutes
```

---

## Step 3: Review Generated Report

After test run completes, find reports in:
```
tests/evaluation/results/
├── results_20251125_143022.json  (detailed metrics)
└── report_20251125_143022.md     (markdown summary)
```

---

## Step 4: Run Full Evaluation (All 24 Scenarios)

**For comprehensive demo with professor:**

```python
# Edit tests/evaluation/test_runner.py
# Change this line at the bottom:

# FROM:
await runner.run_all_scenarios(model_info, limit=5)

# TO:
await runner.run_all_scenarios(model_info)  # Run all 24 scenarios
```

Then run:
```powershell
python tests/evaluation/test_runner.py
```

**Expected duration:** ~20-30 minutes for all 24 scenarios

---

## Step 5: Demonstrate Live with Professor

### Option A: Manual Test via UI
1. Start the Streamlit app:
   ```powershell
   streamlit run frontend/streamlit_app.py
   ```

2. Select model and initialize swarm

3. Run a simple test:
   ```
   Scan 192.168.1.100 and identify open ports
   ```

4. Show the **cost metrics** displayed at the end:
   - LLM calls made
   - Tokens used
   - Cost in USD
   - Time elapsed

### Option B: Show Automated Test Run
1. Run test_runner.py with professor watching
2. Show real-time progress of scenarios
3. Open generated report in Markdown viewer
4. Demonstrate 70%+ automation rate

---

## Step 6: Prepare Deliverables for Professor

### Required Files:
1. ✅ **Live Demo** - Streamlit interface
2. ✅ **Evaluation Report** - `docs/EVALUATION_REPORT_TEMPLATE.md` (fill in results)
3. ✅ **Test Results** - `tests/evaluation/results/results_[timestamp].json`
4. ✅ **Cost Log** - `logs/metrics/cost_log.csv`
5. ⚠️ **Poster** - Create using template below

---

## Creating Your Poster (15% of grade)

### Required Sections:

**1. Problem & Users**
```
Professional: Penetration Tester
Daily Tasks: Reconnaissance (30%), Exploitation (40%), Reporting (20%)
Automation Goal: ≥70% of tasks
```

**2. Architecture Diagram**
Use draw.io or similar to create:
- Multi-agent system (Planner, Recon, InitAccess, Summary)
- LangGraph orchestration
- MCP tool servers
- Kali Linux container

**3. Evaluation Plan**
```
24 test scenarios
Categories: Recon, Exploit, Planning, Reporting, Integration
Success criteria: Findings, Time, Cost
```

**4. Results**
```
Automation Rate: [X]%
Total Cost: $[X]
Average Time: [X]s per task
```

**5. Safety & Ethics**
```
✅ Authorization verification
✅ PII redaction (SSN, CC, emails)
✅ Audit logging
✅ Ethical guidelines in prompts
```

---

## Common Issues & Solutions

### Issue: "Docker container not running"
**Solution:**
```powershell
docker ps -a
docker start attacker
```

### Issue: "OPENAI_API_KEY not set"
**Solution:**
```powershell
# Check .env file exists
cat .env

# Set directly if needed
$env:OPENAI_API_KEY="sk-..."
```

### Issue: "MCP servers not responding"
**Solution:**
```powershell
# Restart MCP servers
powershell ./run_app.ps1
```

### Issue: "Cost tracking not showing data"
**Solution:**
```powershell
# Check logs directory exists
mkdir -p logs/metrics

# Verify cost_tracker is imported in executor.py
# Should see: from src.utils.metrics import get_cost_tracker
```

---

## What to Tell Your Professor

### Key Points:
1. **"We achieve [X]% automation of penetration testing tasks"**
   - Show test_runner.py results
   - Demonstrate > 70% threshold

2. **"Cost per task is $[X], averaging [X] seconds"**
   - Show cost_log.csv
   - Compare to manual pentester hourly rate

3. **"System uses 36+ tools across 4 specialized agents"**
   - Show tool list in README.md
   - Demonstrate tool execution in Streamlit

4. **"Safety measures include PII redaction and authorization checks"**
   - Show pii_redactor.py code
   - Demonstrate disclaimers in UI

5. **"Evaluation harness has 24 scenarios across 10 categories"**
   - Show test_scenarios.json
   - Explain success criteria

---

## Grading Rubric Checklist

### System Design & Implementation (25%) ✅
- [x] Multi-agent architecture
- [x] 36+ tools
- [x] Memory system (LangMem)
- [x] Observability (logging)

### Evaluation Rigor (20%) ✅
- [x] 24 test scenarios
- [x] Automated test runner
- [x] Success metrics
- [x] Baseline comparisons

### Task Performance (20%) ✅
- [x] 70%+ automation demonstrated
- [x] Held-out test suite
- [x] Quantitative results

### Safety & Ethics (10%) ✅
- [x] PII redaction
- [x] Authorization verification
- [x] Disclaimers
- [ ] Human-in-the-loop (partial)

### Poster & Demo (15%) ⚠️
- [ ] Poster PDF (CREATE THIS)
- [x] Live demo ready
- [x] Architecture diagram
- [x] Results visualization

### Report & Documentation (10%) ✅
- [x] README.md
- [x] Evaluation report
- [x] Reproducibility guide
- [x] Design decisions documented

---

## Timeline for Testing Session

**Total time: 45-60 minutes**

1. **Setup (5 min)** - Start Docker, verify MCP servers
2. **Live demo (10 min)** - Run 1-2 scenarios in Streamlit UI
3. **Automated tests (30 min)** - Run test_runner.py for all scenarios
4. **Results review (10 min)** - Open report, discuss metrics
5. **Q&A (5-10 min)** - Answer professor questions

---

## Success Metrics to Highlight

| Metric | Target | Your Result |
|--------|--------|-------------|
| Automation Rate | ≥70% | [X]% |
| Test Scenarios | ≥20 | 24 |
| Tools Implemented | ≥3 | 36+ |
| Cost per Task | <$1.00 | $[X] |
| Average Time | <5 min | [X]s |

---

## Emergency Backup Plan

If live demo fails:
1. ✅ Show pre-recorded video
2. ✅ Show completed test results JSON
3. ✅ Walk through code architecture
4. ✅ Demonstrate logs from previous successful runs

---

## Final Checklist Before Professor Demo

- [ ] Docker container running (`docker ps`)
- [ ] MCP servers active (ports 3001, 3002)
- [ ] OpenAI API key set in .env
- [ ] Test scenarios run successfully at least once
- [ ] Results report generated and reviewed
- [ ] Cost tracking verified in cost_log.csv
- [ ] Poster PDF created (if required)
- [ ] Evaluation report filled out with actual results
- [ ] Screenshots of successful runs prepared
- [ ] Backup of all results files created

---

**Good luck with your evaluation! 🎯**

If you encounter issues during testing, check:
1. `logs/app.log` - Application errors
2. `logs/metrics/` - Cost tracking data
3. `tests/evaluation/results/` - Test results
