# CampusNav Sentinel — Submission Checklist

## OpenCV AI Competition 2026 (Devpost)

### Core Requirements

- [x] **Uses OpenCV 5** — Verified `cv2.__version__ == '5.0.0'` at runtime
- [x] **Meaningful OpenCV usage** — CLAHE, Canny, MOG2, ROI masking, morphology, frame differencing, contour extraction (not just imread/imshow)
- [x] **Working application** — CLI and web interface both functional
- [x] **Reproducible** — `requirements.txt` with pinned OpenCV 5.0.0.93, test video generator included
- [x] **Tested** — 31/31 tests passing

### Agentic Vision Special Award

- [x] **Visual workload runs** — OpenCV 5 frame analysis + YOLOv8 detection
- [x] **Agent inspects visual outputs** — State machine reads detection counts, confidence, ROI position, motion score
- [x] **Outputs determine next action** — ANALYZE_FRAME → INSPECT_REGION → VERIFY_PERSISTENCE based on evidence
- [x] **Agent obtains new evidence** — Each action produces results that feed the next decision
- [x] **New evidence changes decisions** — Persistence confirmation vs. candidate drop; CLEAR vs. CONFIRMED_HAZARD
- [x] **Execution trace inspectable** — Full trace in JSON report with action, evidence, state transitions per step
- [x] **Not a single-pass detector + fixed response** — Multi-iteration loop with evidence-dependent branching

### AWS Integration

- [x] **AWS component designed** — ECS Fargate + S3 + CloudWatch architecture
- [x] **Deployment files prepared** — Dockerfile, docker-compose.yml, CloudFormation template
- [ ] **Live deployment** — Not deployed (AWS CLI not available on dev machine)
- [x] **Works without AWS** — Full local operation, AWS behind feature flag
- [x] **Deployment documentation** — AWS_DEPLOYMENT.md with instructions, costs, cleanup

### Documentation

- [x] **README.md** — Project overview and quick start
- [x] **TECHNICAL_REPORT.md** — Full technical details
- [x] **ARCHITECTURE.md** — System architecture with Mermaid diagrams
- [x] **EVALUATION.md** — Measured results and test analysis
- [x] **DEMO_SCRIPT.md** — 3-minute demo walkthrough
- [x] **KNOWN_LIMITATIONS.md** — Honest limitation disclosure
- [x] **ASSET_ATTRIBUTION.md** — License and attribution for dependencies
- [x] **JUDGE_SETUP.md** — Quick setup for evaluators
- [x] **AWS_DEPLOYMENT.md** — AWS deployment plan and status

### Code Quality

- [x] **Type hints** — Core interfaces use Python type annotations
- [x] **Configuration** — Environment variable overrides via Config dataclass
- [x] **Error handling** — Invalid inputs, corrupt frames, missing models, detector failures
- [x] **No hardcoded paths** — All paths relative or configurable
- [x] **No secrets committed** — .gitignore covers .env files
- [x] **No fabricated results** — All numbers from actual test runs

### Devpost Submission Items

- [ ] **Project title and description** — Ready in PROJECT_SUMMARY.md
- [ ] **Demo video** — Demo script ready; recording needed
- [ ] **Screenshots** — Take from running web dashboard
- [ ] **Repository link** — Push to GitHub
- [ ] **Devpost form** — Submit through official interface

### Remaining Manual Steps

1. Record demo video following DEMO_SCRIPT.md
2. Take screenshots of dashboard, CLI output, and annotated video
3. Push repository to GitHub
4. Complete Devpost submission form
5. (Optional) Deploy to AWS if credentials and CLI become available
