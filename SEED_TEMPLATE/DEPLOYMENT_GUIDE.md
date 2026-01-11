# LOOP WORKFLOW SYSTEM - DEPLOYMENT GUIDE

VERSION: 1.0
DATE: 2026-01-10

---

## OVERVIEW

This guide explains how to deploy the loop-based workflow system to a new project. The system provides a deterministic, amnesia-based workflow that enables long-running AI-assisted projects to remain reliable over time.

---

## WHAT YOU GET

**Core Architecture:**
- Deterministic loop-based workflow with forced memory resets
- Pointer-only core documents (no inline content drift)
- Automatic validation and guardrails
- Flask-based cockpit for lifecycle management
- Report-first development methodology

**Key Components:**
- 12 Universal Laws enforcing workflow discipline
- State authority in `current.json`
- Entry validation via `_LOOP_GATE.md`
- Task management (NEU.md for active, Alt.md for closed)
- Immutable loop archives for history tracking

---

## PREREQUISITES

**Required:**
- Python 3.8 or higher
- pip (Python package manager)
- Text editor or IDE
- AI assistant with file access (e.g., GitHub Copilot, Claude)

**Recommended:**
- Git for version control
- Virtual environment (venv or virtualenv)

---

## INSTALLATION METHODS

### Method 1: Automated Setup (Recommended)

1. **Extract the SEED_TEMPLATE to your project directory**
   ```bash
   # Windows
   xcopy /E /I SEED_TEMPLATE C:\path\to\your\project
   
   # Unix/Mac
   cp -r SEED_TEMPLATE /path/to/your/project
   cd /path/to/your/project
   ```

2. **Run the initialization script**
   ```bash
   python init_project.py
   ```
   
3. **Follow the interactive prompts**
   - Enter your project name, description, and goals
   - Specify your tech stack details
   - Confirm the configuration
   - The script will create all necessary files with your customizations

4. **Install dependencies**
   ```bash
   pip install -r requirements_cockpit.txt
   ```

5. **Start the cockpit**
   ```bash
   # Windows
   START_COCKPIT.bat
   
   # Unix/Mac
   chmod +x START_COCKPIT.sh
   ./START_COCKPIT.sh
   ```

6. **Initialize the first loop**
   - Open browser to http://localhost:5000
   - Click "Reset Loop" button to create `_BOOTSTRAP.md`

7. **Begin working**
   - Start a fresh AI chat session
   - Say: "Read _BOOTSTRAP.md and work autonomously until all tasks are done and all rules are satisfied."

### Method 2: Manual Setup

If you prefer to customize the installation manually:

1. **Create directory structure**
   ```
   your-project/
   ├── archive/
   ├── tasks/
   ├── reports/
   ├── docs/
   └── templates/
   ```

2. **Copy core files**
   - PROJECT_TECH_BASELINE.md
   - NEURAL_CORTEX.md
   - NEU.md
   - Alt.md
   - current.json
   - knownissues.json
   - milestone_01.json
   - _LOOP_GATE.md (initial version)

3. **Edit placeholders**
   Replace all `{{PLACEHOLDER}}` tokens with your project details:
   - `{{PROJECT_NAME}}` - Your project name
   - `{{PROJECT_DESCRIPTION}}` - Brief description
   - `{{PROJECT_GOAL}}` - Ultimate objective
   - `{{LANGUAGES}}` - Programming languages
   - `{{FRAMEWORKS}}` - Frameworks used
   - `{{RUNTIME}}` - Runtime environment
   - `{{DATABASE}}` - Database system
   - `{{INFRASTRUCTURE}}` - Infrastructure type
   - `{{DEPLOYMENT}}` - Deployment method
   - `{{API_STYLE}}` - API architecture
   - `{{AUTH_MODEL}}` - Authentication approach
   - `{{DATA_FORMATS}}` - Data serialization formats
   - `{{VERSIONING}}` - Versioning scheme
   - `{{INIT_TIMESTAMP}}` - Current UTC timestamp (ISO 8601)
   - `{{INIT_DATE}}` - Current date (YYYY-MM-DD)
   - `{{MILESTONE_NAME}}` - First milestone name
   - `{{GOAL_1_DESCRIPTION}}` - First goal description

4. **Copy automation files**
   - loop_guardrails.py
   - loop_cockpit.py
   - requirements_cockpit.txt
   - START_COCKPIT.bat / START_COCKPIT.sh
   - templates/cockpit.html

5. **Copy documentation**
   - docs/OPS_PROTOCOLS.md
   - docs/ARCHITECTURE.md

6. **Create initial task**
   - tasks/task_TASK_0001.md (bootstrap validation task)

7. **Follow steps 4-7 from Method 1**

---

## CONFIGURATION

### Customizing the Tech Stack

Edit [PROJECT_TECH_BASELINE.md](PROJECT_TECH_BASELINE.md):

```markdown
## TECH STACK (IMMUTABLE)
Languages: Python, TypeScript
Frameworks: Flask, React
Runtime: Python 3.11, Node.js 20
Database: PostgreSQL
Infrastructure: Web application
Deployment: Docker + AWS
```

### Setting Project Goals

Edit [milestone_01.json](milestone_01.json):

```json
{
  "MILESTONE": {
    "id": "01",
    "name": "MVP Launch",
    "version": 1,
    "created": "2026-01-10",
    "status": "PENDING"
  },
  "GOALS": [
    {
      "id": "G001",
      "description": "Build user authentication system",
      "status": "PENDING"
    },
    {
      "id": "G002",
      "description": "Create core API endpoints",
      "status": "PENDING"
    }
  ]
}
```

### Adjusting Cockpit Settings

The cockpit runs on port 5000 by default. To change:

Edit [loop_cockpit.py](loop_cockpit.py) at the bottom:

```python
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
```

---

## WORKFLOW OVERVIEW

### The Loop Lifecycle

1. **READY_FOR_RESET** - Reset prepares new loop, creates `_BOOTSTRAP.md`
2. **ACTIVE** - AI deletes `_BOOTSTRAP.md`, begins work on tasks
3. **FINALIZED** - All tasks complete, archive created
4. **Back to step 1** - Human clicks "Reset Loop" in cockpit

### Working with the AI

**Starting a loop:**
```
"Read _BOOTSTRAP.md and work autonomously until all tasks are done and all rules are satisfied."
```

**The AI will:**
1. Validate the loop gate
2. Load project state
3. Identify active tasks
4. Work through tasks following REPORT-FIRST LAW
5. Auto-finalize when all tasks complete
6. Create immutable archive

**Key principle:** The AI operates autonomously within the framework. Fresh chat sessions provide "amnesia" that prevents context drift over time.

---

## COCKPIT FEATURES

Access at http://localhost:5000 after starting the cockpit.

**Main Functions:**
- **Status Dashboard** - Current loop state, active task, gate status
- **Reset Loop** - Finalize current loop and prepare next one
- **Regenerate Gate** - Update validation gate with current state
- **Generate Session Pack** - Create session context summary
- **Lint Metadata** - Validate reference format compliance
- **Generate History Index** - Create searchable archive index
- **Query/Search Engine** - Structured search across tasks, reports, and archives
- **Generate Query Index** - Build metadata index for fast semantic search

**API Endpoints:**
- `GET /api/status` - Current state JSON
- `POST /api/reset-loop` - Trigger loop reset
- `POST /api/regenerate-loop-gate` - Update gate
- `POST /api/generate-session-pack` - Create session context
- `GET /api/lint` - Run metadata validation
- `POST /api/generate-history-index` - Build archive index
- `POST /api/query` - Execute structured queries on metadata
- `GET /api/search` - Text search across workspace files

---

## FILE STRUCTURE REFERENCE

```
project/
├── PROJECT_TECH_BASELINE.md  # Immutable laws and tech stack
├── NEURAL_CORTEX.md          # Pointer-only navigation map
├── NEU.md                    # Active task queue (pointer-only)
├── Alt.md                    # Closed/blocked tasks (pointer-only)
├── current.json              # State authority (loop ID, status, etc.)
├── knownissues.json          # Blocker registry
├── milestone_01.json         # Goal tracking
├── _LOOP_GATE.md             # Entry validator (generated)
├── _BOOTSTRAP.md             # Fresh session entry (ephemeral)
├── _SESSION.md               # Session context pack (optional)
├── loop_guardrails.py        # Validation and generation logic
├── loop_cockpit.py           # Flask server for lifecycle management
├── requirements_cockpit.txt  # Python dependencies
├── START_COCKPIT.bat         # Windows start script
├── START_COCKPIT.sh          # Unix start script
├── archive/                  # Immutable loop archives
│   ├── ARCHIV_0001.md
│   └── ARCHIV_0002.md
├── tasks/                    # Task specifications
│   ├── task_TASK_0001.md
│   └── task_TASK_0002.md
├── reports/                  # Task execution reports
│   ├── report_TASK_0001_L01_v01.md
│   └── report_TASK_0002_L02_v01.md
├── docs/                     # Documentation
│   ├── ARCHITECTURE.md
│   ├── OPS_PROTOCOLS.md
│   ├── HISTORY_INDEX.md      # Generated archive index
│   └── QUERY_INDEX.json      # Generated search metadata
└── templates/                # Cockpit UI
    └── cockpit.html
```

---

## UNIVERSAL LAWS (CRITICAL)

The system enforces 12 Universal Laws that must never be violated:

1. **REPORT-FIRST LAW** - No work without a report file
2. **NO INLINE CONTEXT** - Core docs are pointer-only
3. **REFERENCE FORMAT LAW** - Standard ref format required
4. **LOOP FINALITY** - One loop = one archive
5. **ARCHIVE IMMUTABILITY** - Archives never edited
6. **AMNESIA IS A FEATURE** - Fresh sessions are mandatory
7. **LOCATION LAW** - Right document for right action
8. **POINTER-ONLY CORE** - CORTEX, NEU, ALT are pointers only
9. **DETERMINISTIC NAMING** - Canonical zero-padded names
10. **VIOLATION = INVALID OUTPUT** - No exceptions
11. **GATE VALIDATION LAW** - Check gate before any work
12. **STATE AUTHORITY LAW** - current.json is single source of truth

See [PROJECT_TECH_BASELINE.md](PROJECT_TECH_BASELINE.md) for full details.

---

## TROUBLESHOOTING

### Cockpit won't start

**Problem:** Import errors or missing dependencies

**Solution:**
```bash
pip install --upgrade -r requirements_cockpit.txt
```

### AI doesn't follow the loop workflow

**Problem:** AI unfamiliar with the system

**Solution:**
- Always start with: "Read _BOOTSTRAP.md and work autonomously..."
- Ensure _BOOTSTRAP.md exists (click "Reset Loop" if needed)
- Use fresh chat session for each loop (amnesia is intentional)

### Loop gate shows BLOCKED

**Problem:** Validation issues detected

**Solution:**
- Check gate output for specific violations
- Fix issues (e.g., move orphaned ARCHIV files to archive/)
- Regenerate gate via cockpit

### Files have placeholder tokens

**Problem:** init_project.py wasn't run or manual setup incomplete

**Solution:**
- Re-run init_project.py, or
- Manually replace all {{PLACEHOLDERS}} with real values

---

## BEST PRACTICES

### Task Creation

1. Create task spec in `tasks/task_TASK_XXXX.md`
2. Add reference to NEU.md (top of queue for high priority)
3. Keep task specs focused and actionable
4. Include clear acceptance criteria

### Report Writing

1. Create report BEFORE significant work (REPORT-FIRST LAW)
2. Use naming: `report_TASK_XXXX_LYY_vNN.md`
   - XXXX = task ID
   - YY = loop number
   - NN = version (if task spans multiple loops)
3. Document decisions, challenges, outcomes
4. Update report as work progresses

### Loop Finalization

1. Complete all active tasks
2. Move task refs from NEU.md to Alt.md
3. Let AI auto-finalize (creates archive)
4. Human clicks "Reset Loop" in cockpit
5. Start fresh chat for next loop

### Version Control

**Commit strategy:**
- Commit after each loop finalization
- Include archive file in commit
- Tag releases by milestone

**Ignore patterns (.gitignore):**
```
__pycache__/
venv/
*.pyc
_BOOTSTRAP.md
_SESSION.md
```

---

## SEARCH AND QUERY SYSTEM

The system includes a structured query engine that enables fast semantic search across loops without relying on external dependencies.

### Query Index Generation

Generate the metadata index to enable structured queries:

**Via Cockpit:**
1. Open cockpit at http://localhost:5000
2. Use the search panel to query archives/reports/tasks

**Via CLI:**
```bash
python loop_cockpit.py --generate-query-index
```

This creates `docs/QUERY_INDEX.json` containing:
- Task metadata (objectives, acceptance criteria, status)
- Report metadata (goals, validation results, files changed)
- Archive references (loop numbers, embedded tasks, completion dates)
- Cross-references between documents

### Using the Search System

**In the Cockpit UI:**
1. Navigate to the Search panel
2. Enter query terms (e.g., "validation", "UI design", "dark mode")
3. Filter by document type (tasks, reports, archives)
4. Click results to view details

**Via API:**
```bash
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "validation", "types": ["reports"]}'
```

**Response structure:**
```json
{
  "results": [
    {
      "id": "report_TASK_0048_L31_v01",
      "type": "report",
      "taskId": "TASK_0048",
      "loopNum": 31,
      "relevance": 0.95,
      "excerpt": "...validation logic implemented..."
    }
  ],
  "total": 1
}
```

### Benefits

- **Fast Context Retrieval:** Find relevant past work in seconds
- **Cross-Loop Learning:** AI can quickly access lessons from previous loops
- **Pattern Discovery:** Identify recurring issues or successful approaches
- **Onboarding:** New team members can rapidly understand project history

### Maintenance

Regenerate the query index after significant work:
- After loop finalization (recommended)
- After creating multiple new tasks/reports
- When search results seem outdated

The index generation is deterministic and can be run safely at any time.

---

## GETTING HELP

### Resources

- **Architecture Overview:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Operational Protocols:** [docs/OPS_PROTOCOLS.md](docs/OPS_PROTOCOLS.md)
- **Archive History:** [docs/HISTORY_INDEX.md](docs/HISTORY_INDEX.md) (generated)

### Support Channels

- Review archive files for past decisions and patterns
- Check knownissues.json for documented blockers
- Consult PROJECT_TECH_BASELINE.md for immutable rules

---

## ADVANCED TOPICS

### Extending the Cockpit

The cockpit is built with Flask. To add new features:

1. Edit [loop_cockpit.py](loop_cockpit.py)
2. Add new routes as needed
3. Update [templates/cockpit.html](templates/cockpit.html) for UI
4. Follow existing patterns for consistency

### Custom Guardrails

To add new validation rules:

1. Edit [loop_guardrails.py](loop_guardrails.py)
2. Add new validation functions
3. Update lint() function to call them
4. Test with: `python loop_cockpit.py --lint`

### Integration with CI/CD

Example GitHub Actions workflow:

```yaml
name: Loop Validation

on: [push]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements_cockpit.txt
      - name: Run lint
        run: python loop_cockpit.py --lint
```

---

## EVOLUTION ROADMAP

### For AI Assistants: Scaling This System

Once you've mastered the core loop workflow, here's how to evolve the system for larger projects and teams:

**📖 Complete Evolution Guide:** [ref:docs/PROJECT_EVOLUTION_ROADMAP.md|v:1|tags:evolution,roadmap,scaling|src:doc]

### Immediate Evolution Priorities (1-2 Loops)

**1. Multi-User Collaboration**
- Add user session management for team work
- Implement session-scoped workspaces to prevent conflicts
- Enable collaborative gate validation

**2. Plugin Architecture** 
- Create extension points for custom tools
- Add built-in plugins for testing, code quality, deployment
- Establish plugin marketplace for community extensions

**3. Performance Analytics**
- Track loop completion times and quality metrics
- Add predictive analytics for project health
- Implement visual analytics dashboard

### When to Evolve

- **Multi-user needs:** Implement session management (Phase 1)
- **Performance issues:** Add analytics and monitoring (Phase 4)
- **Scale problems:** Migrate to database backend (Phase 6)
- **Integration needs:** Connect external tools (Phase 8)

### Evolution Guidelines

- **Maintain Core Principles:** Keep amnesia, report-first methodology, pointer-only navigation
- **Incremental Changes:** Test each evolution with real work before full adoption
- **Backward Compatibility:** Don't break existing workflows
- **Document Everything:** Follow REPORT-FIRST LAW for all evolution work

### Example Evolution Path

**Loop 1-5:** Master core workflow, implement basic search
**Loop 6-10:** Add multi-user support, performance tracking  
**Loop 11-20:** Implement plugin system, advanced visualization
**Loop 21+:** Database migration, external integrations, AI autonomy

---

## CHANGELOG

### Version 1.0 (2026-01-10)
- Initial deployment guide
- Automated init_project.py script
- Complete seed template package
- Documentation for manual and automated setup

---

## LICENSE

[Specify your license here]

---

END OF DOCUMENT
