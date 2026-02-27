from typing import List
from datetime import datetime

def build_scope_prompt(rfp_text: str, kb_chunks: List[str], project=None, questions_context: str | None = None, rate_card_roles: List[str] | None = None, tokenizer=None, max_total_tokens: int = 124000) -> str:
    used_tokens = 0

    rfp_tokens = tokenizer.encode(rfp_text or "")
    if len(rfp_tokens) > 8000:
        rfp_tokens = rfp_tokens[:8000]
    rfp_text = tokenizer.decode(rfp_tokens)
    used_tokens += len(rfp_tokens)

    safe_kb_chunks = []
    for ch in kb_chunks or []:
        tokens = tokenizer.encode(ch)
        if used_tokens + len(tokens) > max_total_tokens:
            break
        safe_kb_chunks.append(ch)
        used_tokens += len(tokens)

    kb_context = "\\n\\n".join(safe_kb_chunks) if safe_kb_chunks else "(no KB context found)"

    name = (getattr(project, "name", "") or "").strip()
    domain = (getattr(project, "domain", "") or "").strip()
    complexity = (getattr(project, "complexity", "") or "").strip()
    tech_stack = (getattr(project, "tech_stack", "") or "").strip()
    use_cases = (getattr(project, "use_cases", "") or "").strip()
    compliance = (getattr(project, "compliance", "") or "").strip()
    duration = str(getattr(project, "duration", "") or "").strip()

    user_context = (
        "Some overview fields have been provided by the user.\\n"
        "Treat these user-provided values as the source of truth.\\n"
        "Only fill in fields that are blank — do NOT overwrite the given values.\\n\\n"
        f"Project Name: {name or '(infer if missing)'}\\n"
        f"Domain: {domain or '(infer if missing)'}\\n"
        f"Complexity: {complexity or '(infer if missing)'}\\n"
        f"Tech Stack: {tech_stack or '(MUST infer from RFP - see inference rules below)'}\\n"
        f"Use Cases: {use_cases or '(MUST infer from RFP - see inference rules below)'}\\n"
        f"Compliance: {compliance or '(MUST infer from RFP - see inference rules below)'}\\n"
        f"Duration (months): {duration or '(infer if missing)'}\\n\\n"
        "**CRITICAL: Inference Rules for Missing Fields**\\n"
        "When Tech Stack, Use Cases, or Compliance are missing, you MUST infer them from the RFP context.\\n"
        "NEVER output 'Not specified in RFP' or 'Not mentioned' - this is UNACCEPTABLE.\\n"
        "ALWAYS make reasonable inferences based on the RFP content.\\n\\n"
        "**Tech Stack Inference:**\\n"
        "- Look for explicit technology mentions (Python, Java, React, AWS, Azure, etc.)\\n"
        "- Infer from project type: Web app → React/Node.js, Data Analytics → Python/Spark/SQL, AI/ML → Python/TensorFlow\\n"
        "- Look for database needs → PostgreSQL/MongoDB/MySQL\\n"
        "- Look for cloud/infrastructure mentions → AWS/Azure/GCP\\n"
        "- Look for integration requirements → REST APIs, GraphQL, Kafka, etc.\\n"
        "- Example: If RFP mentions 'data analytics platform' and 'real-time processing', infer 'Python, Apache Spark, Kafka, PostgreSQL, AWS'\\n\\n"
        "**Use Cases Inference:**\\n"
        "- Extract main business objectives and user scenarios from RFP\\n"
        "- Look for phrases like 'users should be able to...', 'system will enable...', 'stakeholders can...'\\n"
        "- Identify key features and their purpose\\n"
        "- Example: If RFP describes data ingestion, analytics, and visualization, infer 'Data ingestion from multiple sources, Real-time analytics and reporting, Interactive dashboards for stakeholders'\\n\\n"
        "**Compliance Inference:**\\n"
        "- Look for mentions of regulations (GDPR, HIPAA, SOC2, ISO 27001, PCI-DSS)\\n"
        "- Look for data protection, privacy, or security requirements\\n"
        "- Infer from industry: Healthcare → HIPAA, Finance → PCI-DSS, EU customers → GDPR\\n"
        "- Look for audit trails, encryption, access controls\\n"
        "- Example: If RFP mentions 'personal data' and 'EU customers', infer 'GDPR compliance, Data encryption at rest and in transit, Role-based access control'\\n\\n"
    )

    today_str = datetime.today().date().isoformat()

    return (
        "CRITICAL INSTRUCTION: You MUST output ONLY valid JSON. Do NOT include any explanations, commentary, thinking process, or markdown.\\n"
        "Do NOT start with 'Okay' or 'Here is' or any prose. Your ENTIRE response must be valid JSON and nothing else.\\n\\n"
        "You are an expert AI project planner.\\n"
        "Use the RFP/project text as the **primary source** \\n"
        "Use questions and answers to clarify ambiguities.\\n"
        "but enrich missing fields with the Knowledge Base context (if relevant).\\n\\n"
        "MANDATORY REQUIREMENT: You MUST generate a complete 'activities' array with at least 8-15 activities.\\n"
        "DO NOT generate empty activities array - this is UNACCEPTABLE.\\n"
        "DO NOT return ONLY metadata without activities - this is a CRITICAL ERROR.\\n"
        "The 'activities' array is THE MOST IMPORTANT part of your response.\\n\\n"
        "Output schema (YOUR ENTIRE RESPONSE MUST MATCH THIS EXACT FORMAT):\\n"
        "{\\n"
        '  "overview": {\\n'
        '    "Project Name": string,\\n'
        '    "Domain": string,\\n'
        '    "Complexity": string,\\n'
        '    "Tech Stack": string,\\n'
        '    "Use Cases": string,\\n'
        '    "Compliance": string,\\n'
        '    "Duration": number\\n'
        "  },\\n"
        '  "activities": [\\n'
        '    {\\n'
        '      "ID": int,\\n'
        '      "Activities": string,\\n'
        '      "Owner": string | null,\\n'
        '      "Resources": string | null,\\n'
        '      "Start Date": "yyyy-mm-dd",\\n'
        '      "End Date": "yyyy-mm-dd",\\n'
        '      "Effort Months": number\\n'
        "    }\\n"
        "  ],\\n"
        '  "resourcing_plan": [],\\n'
        '  "project_summary": {\\n'
        '    "executive_summary": string,\\n'
        '    "key_deliverables": [string],\\n'
        '    "success_criteria": [string],\\n'
        '    "risks_and_mitigation": [{risk: string, mitigation: string}]\\n'
        "  }\\n"
        "}\\n\\n"
        " CRITICAL: The 'activities' array MUST contain at least 8-15 detailed activities covering ALL project phases:\\n"
        "   - Requirements gathering, analysis, and planning activities\\n"
        "   - Design and architecture activities\\n"
        "   - Development activities (broken down by feature/module)\\n"
        "   - Testing activities (unit, integration, UAT)\\n"
        "   - Deployment and go-live activities\\n"
        "   - Post-deployment support activities\\n\\n"
        "**CRITICAL: Activity Naming Rules:**\\n"
        "- Activity names MUST describe WHAT is being built (functionality), NOT WHO builds it (seniority)\\n"
        "- NEVER include seniority levels in activity names: [BAD] '(Junior)', '(Senior)', '(Mid-level)'\\n"
        "- Use specific, technical, functional descriptions\\n"
        "- [GOOD]: 'Backend Authentication API', 'Frontend User Dashboard', 'Payment Gateway Integration'\\n"
        "- [GOOD]: 'Database Schema Design', 'RESTful API Endpoints', 'Admin Panel UI Components'\\n"
        "- [BAD]: 'Backend Development (Junior)', 'Frontend Work (Senior)', 'Simple Development Tasks'\\n"
        "- [BAD]: 'Development Phase 1', 'Coding Tasks', 'Advanced Features'\\n"
        "- Break down large activities by FEATURE or MODULE, not by developer seniority\\n"
        "- Example: Instead of 'Backend Development' + 'Backend Development (Junior)', use:\\n"
        "  'Backend Core Services & Business Logic' + 'Backend CRUD API Endpoints'\\n\\n"
        "**Project Summary Guidelines:**\\n"
        "- `executive_summary`: 2-3 paragraph high-level summary of project goals, scope, and expected outcomes\\n"
        "- `key_deliverables`: List 5-8 major deliverables (e.g., 'Fully functional mobile app', 'REST API with documentation')\\n"
        "- `success_criteria`: List 4-6 measurable success metrics (e.g., 'System handles 10k concurrent users', 'API response time < 200ms')\\n"
        '- `risks_and_mitigation`: List 4-6 project risks with mitigation strategies as objects with "risk" and "mitigation" fields (e.g., {"risk": "Third-party API downtime", "mitigation": "Implement fallback caching and retry logic"})\\n\\n'
        "**CRITICAL: Output ONLY the schema above. Do NOT add:**\\n"
        "- [NO] \\\"cost_projection\\\" field (this will be auto-generated from resourcing_plan)\\n"
        "- [NO] Any other fields not listed in the schema above\\n"
        "- [NO] No markdown, no commentary, no explanations — ONLY valid JSON matching the schema\\n\\n"
        "Scheduling Rules: \\n"
        f"- The first activity must always start today ({today_str}).\\n"
        "- If two activities are **independent**, overlap their timelines by **70–80%** of their duration (not full overlap)."
        "- If one activity **depends** on another, allow a small overlap of **10-15%** near the end of the predecessor if feasible."
        "- Avoid full serialization unless strictly required by dependency."
        "- Avoid full parallelism where all tasks start together — stagger independent ones by **5-10%**."
        "- Ensure overall project duration stays **≤ 12 months**."
        "- Auto-calculate **End Date = Start Date + Effort Months**.\\n"
        "- Auto-calculate **overview.Duration** as the total span in months from the earliest Start Date to the latest End Date.\\n"
        "- `Complexity` should be simple, medium, or high based on duration of project.\\n"
        "\\n"
         "**[CRITICAL]: Owner and Resources Assignment Rules:**\\n"
        "- `Owner` must ALWAYS be a valid JOB ROLE from the company's rate card.\\n"
        "- `Owner` is NEVER an activity name, activity description, or task name.\\n"
        "- `Resources` must ALWAYS contain at least 1-2 supporting JOB ROLES from the company's rate card.\\n"
        "- `Resources` should list supporting team members who assist the Owner (different from Owner).\\n"
        "- You MUST use ONLY the roles listed below - DO NOT invent new roles.\\n"
        "- [WARNING] NEVER leave `Resources` empty or null - ALWAYS assign at least one supporting role.\\n"
        "- For simple activities, assign 1 supporting resource; for complex activities, assign 2-3 resources.\\n"
        "- Example: If Owner is 'Backend Developer', Resources could be 'QA Engineer' or 'DevOps Engineer'.\\n"
        "\\n"
        f"**[MANDATORY]: Use ONLY these exact roles from the company's rate card:**\\n"
        f"{chr(10).join('  - ' + role for role in (rate_card_roles or []))}\\n"
        "\\n"
        "**Examples of CORRECT Owner and Resources assignment:**\\n"
        "  [CORRECT] Activity: 'Backend API Development'\\n"
        f"     Owner: \\\"{rate_card_roles[0] if (rate_card_roles and len(rate_card_roles) > 0) else 'Unassigned Resource'}\\\"\\n"
        f"     Resources: \\\"{rate_card_roles[1] if (rate_card_roles and len(rate_card_roles) > 1) else 'QA Engineer'}, {rate_card_roles[2] if (rate_card_roles and len(rate_card_roles) > 2) else 'DevOps Engineer'}\\\"\\n"
        "\\n"
        "  [CORRECT] Activity: 'Data Pipeline Development'\\n"
        f"     Owner: \\\"{rate_card_roles[1] if (rate_card_roles and len(rate_card_roles) > 1) else 'Unassigned Resource'}\\\"\\n"
        f"     Resources: \\\"{rate_card_roles[0] if (rate_card_roles and len(rate_card_roles) > 0) else 'Unassigned Resource'}, {rate_card_roles[2] if (rate_card_roles and len(rate_card_roles) > 2) else 'Unassigned Resource'}\\\"\\n"
        "\\n"
        "  [CORRECT] Activity: 'System Architecture Design'\\n"
        f"     Owner: \\\"{rate_card_roles[2] if (rate_card_roles and len(rate_card_roles) > 2) else 'Unassigned Resource'}\\\"\\n"
        f"     Resources: \\\"{rate_card_roles[0] if (rate_card_roles and len(rate_card_roles) > 0) else 'Unassigned Resource'}\\\"\\n"
        "\\n"
        "**Examples of INCORRECT assignment (DO NOT DO THIS):**\\n"
        "  [INCORRECT] Owner: \\\"Infrastructure Setup\\\" (this is an activity, not a role!)\\n"
        "  [INCORRECT] Owner: \\\"Data Ingestion Development\\\" (this is an activity, not a role!)\\n"
        "  [INCORRECT] Resources: \\\"\\\" or null (Resources must NEVER be empty!)\\n"
        "  [INCORRECT] Resources: \\\"Backend Developer\\\" when Owner is also \\\"Backend Developer\\\" (don't duplicate Owner in Resources)\\n"
        "  [INCORRECT] Owner: \\\"John Smith\\\" (this is a person's name, not a role!)\\n"
        "\\n"    
        "Activity Duration Guidelines:\\n"
        "Estimate realistic durations based on activity type and complexity. Use these as reference:\\n"
        "\\n"
        "**Planning & Design Activities:**\\n"
        "- Requirements Gathering & Analysis: 0.5-1 month\\n"
        "- System Architecture Design: 0.5-1 month\\n"
        "- UI/UX Design & Wireframing: 0.75-1.5 months\\n"
        "- Database Schema Design: 0.25-0.5 month\\n"
        "- API Design & Documentation: 0.25-0.5 month\\n"
        "\\n"
        "**Development Activities:**\\n"
        "- Simple CRUD Operations: 0.5-0.75 month\\n"
        "- Complex Feature Development: 1-1.5 months\\n"
        "- API Development (REST/GraphQL): 0.75-1.25 months\\n"
        "- Database Implementation: 0.5-1 month\\n"
        "- Authentication & Authorization: 0.75-1.25 months\\n"
        "- Payment Gateway Integration: 1-1.5 months\\n"
        "- Third-Party API Integrations: 0.5-1 month\\n"
        "- Real-time Features (WebSockets, etc.): 1-1.5 months\\n"
        "- Search Functionality: 0.75-1.25 months\\n"
        "- File Upload/Management: 0.5-0.75 month\\n"
        "- Notification System: 0.75-1 month\\n"
        "- Reporting & Analytics: 1-1.5 months\\n"
        "\\n"
        "**AI/ML & Advanced Features:**\\n"
        "- AI Model Integration: 1.5-2 months\\n"
        "- Machine Learning Pipeline: 1.5-2.5 months\\n"
        "- Natural Language Processing: 1.5-2 months\\n"
        "- Computer Vision Features: 1.5-2 months\\n"
        "- Recommendation Engine: 1-1.5 months\\n"
        "\\n"
        "**Testing & Quality Assurance:**\\n"
        "- Unit Testing: 0.25-0.5 month\\n"
        "- Integration Testing: 0.5-0.75 month\\n"
        "- End-to-End Testing: 0.5-1 month\\n"
        "- Performance Testing: 0.5-0.75 month\\n"
        "- Security Testing: 0.75-1 month\\n"
        "- User Acceptance Testing: 0.5-0.75 month\\n"
        "\\n"
        "**DevOps & Deployment:**\\n"
        "- CI/CD Pipeline Setup: 0.5-0.75 month\\n"
        "- Cloud Infrastructure Setup: 0.75-1 month\\n"
        "- Containerization (Docker/K8s): 0.5-1 month\\n"
        "- Monitoring & Logging Setup: 0.5-0.75 month\\n"
        "- Production Deployment: 0.25-0.5 month\\n"
        "\\n"
        "**Domain-Specific Activity Templates:**\\n"
        "\\n"
        "**E-Commerce Domain:**\\n"
        "- Product Catalog Management: 1-1.5 months\\n"
        "- Shopping Cart & Checkout: 1.25-1.75 months\\n"
        "- Order Management System: 1-1.5 months\\n"
        "- Inventory Management: 1-1.5 months\\n"
        "- Payment Processing: 1-1.5 months\\n"
        "- Shipping Integration: 0.75-1 month\\n"
        "\\n"
        "**Healthcare Domain:**\\n"
        "- Patient Management System: 1.5-2 months\\n"
        "- Electronic Health Records (EHR): 2-2.5 months\\n"
        "- Appointment Scheduling: 1-1.5 months\\n"
        "- Medical Billing: 1.5-2 months\\n"
        "- HIPAA Compliance Implementation: 1-1.5 months\\n"
        "- Telemedicine Features: 1.5-2 months\\n"
        "\\n"
        "**FinTech Domain:**\\n"
        "- Account Management: 1.5-2 months\\n"
        "- Transaction Processing: 1.5-2 months\\n"
        "- KYC/AML Compliance: 1.5-2 months\\n"
        "- Fraud Detection System: 1.5-2.5 months\\n"
        "- Financial Reporting: 1-1.5 months\\n"
        "- Multi-Currency Support: 1-1.5 months\\n"
        "\\n"
        "**Education Domain:**\\n"
        "- Learning Management System (LMS): 2-2.5 months\\n"
        "- Course Management: 1-1.5 months\\n"
        "- Student Portal: 1-1.5 months\\n"
        "- Assessment & Grading: 1-1.5 months\\n"
        "- Video Streaming Integration: 1-1.5 months\\n"
        "- Certificate Generation: 0.5-0.75 month\\n"
        "\\n"
        "**Social Media/Community Domain:**\\n"
        "- User Profiles & Authentication: 1-1.5 months\\n"
        "- Feed/Timeline System: 1.5-2 months\\n"
        "- Content Posting & Sharing: 1-1.5 months\\n"
        "- Messaging/Chat System: 1.5-2 months\\n"
        "- Notifications System: 0.75-1.25 months\\n"
        "- Content Moderation: 1-1.5 months\\n"
        "\\n"
        "**IoT/Smart Systems Domain:**\\n"
        "- Device Management: 1.5-2 months\\n"
        "- Real-time Data Processing: 1.5-2 months\\n"
        "- Sensor Data Analytics: 1.5-2 months\\n"
        "- Remote Control Interface: 1-1.5 months\\n"
        "- Alert & Automation System: 1-1.5 months\\n"
        "\\n"
        "**General Guidelines:**\\n"
        "- For simple projects: Use lower end of duration ranges\\n"
        "- For medium projects: Use mid-range durations\\n"
        "- For complex projects: Use upper end or slightly beyond ranges\\n"
        "- Activities can be split into smaller sub-activities if duration exceeds 2 months\\n"
        "- Total project duration should realistically reflect the sum of critical path activities\\n"
        "- Consider dependencies when scheduling - dependent activities should account for handoff time\\n"
        "\\n"
        "**[CRITICAL]: Infrastructure & Setup Activities - Use SHORT Durations!**\\n"
        "Infrastructure and environment setup tasks are typically QUICK (1-2 weeks, NOT 1 month):\\n"
        "- Azure/AWS/Cloud Infrastructure Setup: 0.25-0.5 month (1-2 weeks)\\n"
        "- Database Environment Setup: 0.25-0.5 month (1-2 weeks)\\n"
        "- CI/CD Pipeline Configuration: 0.25-0.5 month (1-2 weeks)\\n"
        "- Development Environment Setup: 0.25 month (1 week)\\n"
        "- Kubernetes/Container Setup: 0.5 month (2 weeks)\\n"
        "- Monitoring & Logging Tools Setup: 0.25-0.5 month (1-2 weeks)\\n"
        "\\n"
        "**IMPORTANT: Use Granular Durations - NOT Everything is 1 Month!**\\n"
        "Use realistic, varied durations based on actual effort required:\\n"
        "- 0.25 month = 1 week (quick setup, configuration, simple tasks)\\n"
        "- 0.5 month = 2 weeks (moderate complexity, integration work)\\n"
        "- 0.75 month = 3 weeks (moderate to complex features)\\n"
        "- 1 month = 4 weeks (complex features, major development)\\n"
        "- 1.25-1.5 months = 5-6 weeks (very complex features, multiple integrations)\\n"
        "- 1.75-2 months = 7-8 weeks (large system components, AI/ML work)\\n"
        "\\n"
        "**Activity Duration Examples (Realistic Estimates):**\\n"
        "\\n"
        "Example 1 - Infrastructure Setup:\\n"
        "  Activity: \\\"Set up Azure infrastructure with SQL DB and monitoring\\\"\\n"
        "  Duration: 0.5 month (2 weeks) ✓\\n"
        "  NOT: 1 month ✗\\n"
        "\\n"
        "Example 2 - Data Source Analysis:\\n"
        "  Activity: \\\"Analyze 30+ data sources and define integration approach\\\"\\n"
        "  Duration: 0.75 month (3 weeks) ✓\\n"
        "  NOT: 1 month ✗\\n"
        "\\n"
        "Example 3 - Simple ETL Pipeline:\\n"
        "  Activity: \\\"Develop ETL pipeline for SQL database ingestion\\\"\\n"
        "  Duration: 0.75 month (3 weeks) ✓\\n"
        "  NOT: 1 month ✗\\n"
        "\\n"
        "Example 4 - Complex Feature:\\n"
        "  Activity: \\\"Implement ML-based fraud detection system\\\"\\n"
        "  Duration: 1.5-2 months (6-8 weeks) ✓\\n"
        "\\n"
        "Example 5 - Testing Phase:\\n"
        "  Activity: \\\"Execute end-to-end testing and UAT\\\"\\n"
        "  Duration: 0.5 month (2 weeks) ✓\\n"
        "  NOT: 1 month ✗\\n"
        "\\n"
        "**Remember:** Most activities take LESS than 1 month! Use 0.25, 0.5, 0.75 frequently!\\n"
        "\\n"
        "- IDs must start from 1 and increment sequentially.\\n"
        "- If the RFP or Knowledge Base text lacks detail, infer the missing pieces logically.\\n"
        "- Include all relevant roles and activities that ensure delivery of the project scope.\\n"
        "- Keep all field names exactly as in the schema.\\n\\n"
        "**🔴 OVERRIDE RULE:** If the user specifies a duration (e.g. '3 months'), you MUST output that EXACT duration.\\n"
        "IGNORE the 'Activity Duration Guidelines' above for that specific activity.\\n"
        "Do NOT round it down. Do NOT make it 'realistic'. Just obey the user.\\n"
        "\\n"
        "**🔴 CONTINUOUS LEARNING RULE (ACTUALS):**\\n"
        "If the 'Knowledge Base Context' contains text tagged as 'ACTUAL_DATA' or 'PROJECT CLOSEOUT REPORT', it is HIGH PRIORITY.\\n"
        "- Real actuals from past projects are better than templates.\\n"
        "- If an Actual Report says 'Activity X took 50 hours', and your template says 20, USE 50 (or close to it).\\n"
        "- Cite '(Based on actuals from Project ...)' in the activity notes if possible.\\n"
        f"{user_context}"
        f"RFP / Project Files Content:\\n{rfp_text[:8000]}... [TRUNCATED for Memory Safety]\\n\\n"
        f"Knowledge Base Context (for enrichment only):\\n{str(kb_context)[:2000]}... [TRUNCATED]\\n"
        f"Clarification Q&A (User-confirmed answers take ABSOLUTE PRIORITY)\\n"
        f"Use these answers to OVERRIDE any ambiguous or conflicting information.\\n"
        f"Example: If user says 'Change Frontend to 3 months', you MUST set 'Effort Months' to 3.0 for that activity.\\n"
        f"Example: If user says 'Add mobile app', you MUST add mobile app activities.\\n"
        f"Do NOT ignore these user commands.\\n\\n"
        f"{questions_context}\\n\\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
        " FINAL CRITICAL REQUIREMENTS - READ THIS CAREFULLY:\\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
        "1.  MUST include 'overview' object with all 7 fields\\n"
        "2.  MUST include 'activities' array with at least 8-15 activities (THIS IS MANDATORY!)\\n"
        "3.  MUST include 'resourcing_plan' as empty array []\\n"
        "4.  MUST include 'project_summary' object with all 4 fields\\n"
        "5.  PROHIBITED: Returning empty 'activities' array []. You MUST generate at least 5 activities.\\n"
        "6.  DO NOT nest activities inside 'phases' - put them directly in 'activities' array\\n"
        "7.  DO NOT wrap the response in 'data' or 'project' keys - use the exact schema above\\n"
        "8.  Your response MUST be valid JSON that starts with '{' and ends with '}'\\n\\n"
        "REMEMBER: Output ONLY the JSON object. No explanations, no thinking, no markdown, no prose. Start your response with '{' and end with '}'. Nothing else.\\n"
    )

def build_questionnaire_prompt(rfp_text: str, kb_chunks: List[str], project=None) -> str:
    name = getattr(project, "name", "Unnamed Project")
    domain = getattr(project, "domain", "General")
    tech = getattr(project, "tech_stack", "Modern Web Stack")
    compliance = getattr(project, "compliance", "General")
    duration = getattr(project, "duration", "TBD")

    return f"""
You are a **senior business analyst** preparing a requirement-clarification questionnaire
based on an RFP document.

Your goal: identify the main THEMES and subareas discussed in the RFP or Knowledge Base,
and then create **categories of questions** that align with those themes.
Do NOT reuse example categories blindly — derive them from the content itself.

---

### Project Context
- Project Name: {name}
- Domain: {domain}
- Tech Stack: {tech}
- Compliance: {compliance}
- Duration: {duration}

### RFP Content
{rfp_text[:8000]}... [TRUNCATED for Memory Safety]

### Knowledge Base Context
{str(kb_chunks)[:2000]}... [TRUNCATED]

---

### TASK
1. First, analyze the RFP text to identify **key themes or topics** (e.g., Data Governance, SOX Controls,
   Cloud Migration, AI Enablement, Supply Chain Optimization, etc.).
2. For each theme, create a **category** with 5-6 specific questions.
3. Questions should clarify requirements, assumptions, or current-state processes.
4. Avoid repeating generic categories like "Architecture" or "Data & Security"
   unless they are explicitly discussed in the RFP.

---

### OUTPUT FORMAT
Return ONLY valid JSON in this structure:

{{
  "questions": [
    {{
      "category": "Data Governance & Ownership",
      "items": [
        {{
          "question": "Is there a defined data ownership model for finance data?",
          "user_understanding": "",
          "comment": ""
        }},
        {{
          "question": "Do you maintain audit logs for data corrections?",
          "user_understanding": "",
          "comment": ""
        }}
      ]
    }},
    {{
      "category": "Regulatory Readiness and SOX Scope",
      "items": [
        {{
          "question": "What parts of the organization are in SOX scope?",
          "user_understanding": "",
          "comment": ""
        }}
      ]
    }}
  ]
}}

### RULES
- Categories must emerge logically from the RFP and KB text.
- Each category must contain at least 2 context-relevant questions.
- Each question must be concise, unambiguous, and require a short descriptive answer.
- Always include empty strings for 'user_understanding' and 'comment'.
- Output ONLY valid JSON (no explanations or markdown).
"""

def build_architecture_prompt(rfp_text: str, kb_chunks: List[str], project=None) -> str:
    name = (getattr(project, "name", "") or "Untitled Project").strip()
    domain = (getattr(project, "domain", "") or "General").strip()
    tech = (getattr(project, "tech_stack", "") or "Modern Web + Cloud Stack").strip()

    return f"""
    You are a **senior enterprise solution architect**. Your task is to design a logical system architecture for the project described below.
    Instead of drawing the diagram, you must define the **structure components and connections** in a strict JSON format compatible with React Flow.

    ### PROJECT CONTEXT
    - **Project Name:** {name}
    - **Domain:** {domain}
    - **Tech Stack:** {tech}

    ### RFP SUMMARY
    {rfp_text}

    ### KNOWLEDGE BASE CONTEXT
    {kb_chunks}

    ---

    ### INSTRUCTIONS
    1. Identify key components based on the RFP and Tech Stack.
    2. Create nodes for these components. Group them logically by setting their 'type' to one of:
       - **frontend**: User interfaces (Web, Mobile, Admin Panels)
       - **backend**: Application logic, APIs, Microservices, Auth
       - **data**: Databases, File Storage, Caching, Data Warehouses
       - **ai**: AI Models, ML Pipelines, Analytics Engines
       - **security**: Firewalls, Identity Providers, Monitoring, CI/CD tools
    3. Define logical data flow connections (edges) between nodes.

    ### OUTPUT FORMAT (JSON ONLY)
    Return a single valid JSON object with `nodes` and `edges` arrays:
    {{
      "nodes": [
        {{
          "id": "node_web",
          "type": "frontend",
          "position": {{"x": 0, "y": 0}},
          "data": {{"label": "Web App", "tech": "React"}}
        }},
        {{
          "id": "node_api",
          "type": "backend",
          "position": {{"x": 0, "y": 0}},
          "data": {{"label": "Core API", "tech": "FastAPI"}}
        }},
        {{
          "id": "node_db",
          "type": "data",
          "position": {{"x": 0, "y": 0}},
          "data": {{"label": "Main DB", "tech": "PostgreSQL"}}
        }}
      ],
      "edges": [
        {{
          "id": "edge_web_api",
          "source": "node_web",
          "target": "node_api",
          "label": "HTTP/REST"
        }},
        {{
          "id": "edge_api_db",
          "source": "node_api",
          "target": "node_db",
          "label": "SQL Query"
        }}
      ]
    }}

    **RULES**:
    - Every edge MUST have a valid `source` and `target` matching a node `id`.
    - Every node MUST have `id`, `type`, `position: {{"x": 0, "y": 0}}`, and `data` (with `label` and `tech`).
    - The `position` can always just be `x: 0, y: 0` (the frontend will auto-layout).
    """



