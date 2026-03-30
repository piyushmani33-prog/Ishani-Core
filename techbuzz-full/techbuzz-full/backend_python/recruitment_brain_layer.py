import hashlib
import io
import json
from pathlib import Path
import re
import zipfile
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote, quote_plus

from fastapi import File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


RECRUITMENT_SEED_PACKS: List[Dict[str, Any]] = [
    {
        "key": "techbuzz_mandate",
        "title": "TechBuzz Recruitment Mandate",
        "summary": "TechBuzz Systems Pvt Ltd is a recruitment and talent-delivery company. Every brain should optimize for precise hiring, candidate trust, client outcomes, and repeatable revenue.",
        "content": (
            "TechBuzz Systems Pvt Ltd exists to convert hiring demand into trusted delivery. "
            "The AI should think like a recruitment operator: understand the client brief, define the role sharply, "
            "protect candidate privacy, create strong shortlists, move quickly, communicate clearly, and improve revenue "
            "through repeatable recruiting systems instead of vague promises."
        ),
        "brains": ["mother_brain", "cabinet_brain", "praapti", "ats", "network", "accounts", "action_center"],
        "keywords": ["recruitment", "mandate", "techbuzz", "revenue", "client", "candidate"],
        "workspace": ["bridge", "hq", "agent", "ats", "network"],
    },
    {
        "key": "client_intake",
        "title": "Client Intake Framework",
        "summary": "Every role starts with a tight intake: business goal, must-have skills, team reality, timeline, location, budget, and interview loop.",
        "content": (
            "For every new client role, capture: company context, hiring manager, business outcome, must-have skills, "
            "nice-to-have skills, years of experience, location, work model, compensation band, notice period tolerance, "
            "interview stages, decision makers, and urgency. If any of these are missing, ask before promising precision."
        ),
        "brains": ["mother_brain", "cabinet_brain", "praapti", "ats"],
        "keywords": ["client intake", "job brief", "must-have", "budget", "timeline"],
        "workspace": ["agent", "ats", "praapti", "hq"],
    },
    {
        "key": "role_calibration",
        "title": "Role Calibration Matrix",
        "summary": "Translate a JD into a calibrated search brief: core stack, environment, outcomes, and evidence signals.",
        "content": (
            "A good hiring brief is not a pasted JD. Convert each role into: business outcome, technical or functional stack, "
            "level, reporting line, execution environment, expected outcomes in first 30-60-90 days, red flags, and evidence "
            "signals that prove the candidate can really do the work."
        ),
        "brains": ["mother_brain", "praapti", "ats"],
        "keywords": ["role calibration", "jd", "evidence", "outcomes", "screening"],
        "workspace": ["agent", "ats", "praapti"],
    },
    {
        "key": "sourcing_playbook",
        "title": "Precision Sourcing Playbook",
        "summary": "Use deliberate sourcing, not random volume: target channels, Boolean thinking, referrals, communities, and timing.",
        "content": (
            "Sourcing should be precise. Start with role title variants, skill clusters, company archetypes, market geography, "
            "founder and hiring-manager language, GitHub or portfolio signals, referral paths, and communities. Always explain "
            "why a profile is relevant instead of dumping broad names."
        ),
        "brains": ["mother_brain", "praapti", "network"],
        "keywords": ["sourcing", "boolean", "communities", "referrals", "talent mapping"],
        "workspace": ["agent", "network", "praapti"],
    },
    {
        "key": "screening_rubric",
        "title": "Candidate Screening Rubric",
        "summary": "Candidates should be scored on role fit, execution proof, communication, stability, and joining risk.",
        "content": (
            "Score candidates using a clear rubric: skill fit, domain fit, proof of execution, communication quality, "
            "ownership, stability, notice period risk, compensation fit, location fit, and interview readiness. "
            "Use guided detail by default. Show direct contact data only when the operator explicitly asks for it."
        ),
        "brains": ["mother_brain", "praapti", "ats"],
        "keywords": ["screening", "fit score", "joining risk", "privacy", "evidence"],
        "workspace": ["agent", "ats", "praapti"],
    },
    {
        "key": "outreach_communications",
        "title": "Outreach And Communication Discipline",
        "summary": "Every email, message, or call should be respectful, relevant, and consent-aware.",
        "content": (
            "Candidate outreach must be personalized, brief, and truthful. Mention why the role is relevant, why the profile "
            "was selected, what the next step is, and how to opt out. Never auto-send messages without user confirmation. "
            "Prepare drafts, summaries, and launch links only after explicit user action."
        ),
        "brains": ["mother_brain", "praapti", "network", "action_center"],
        "keywords": ["outreach", "email", "message", "call", "consent", "drafts"],
        "workspace": ["agent", "network", "praapti"],
    },
    {
        "key": "interview_scorecards",
        "title": "Interview And Scorecard SOP",
        "summary": "Interviews should produce comparable evidence, not vague feelings.",
        "content": (
            "Each interview loop should map to specific competencies. Capture structured notes, decision confidence, "
            "critical strengths, concerns, and recommended next step. Keep scorecards consistent so the ATS pipeline "
            "remains useful across multiple roles and recruiters."
        ),
        "brains": ["mother_brain", "cabinet_brain", "ats"],
        "keywords": ["interview", "scorecard", "decision confidence", "ats", "notes"],
        "workspace": ["agent", "ats", "hq"],
    },
    {
        "key": "offer_joining",
        "title": "Offer Closure And Joining Risk",
        "summary": "Winning the candidate is not enough; reduce drop-offs, counter-offers, and joining surprises.",
        "content": (
            "Before closure, assess compensation fit, notice period, buyout possibility, counter-offer risk, family and location "
            "constraints, role clarity, and onboarding readiness. Track these risks explicitly so TechBuzz protects trust "
            "with both clients and candidates."
        ),
        "brains": ["mother_brain", "cabinet_brain", "praapti", "ats"],
        "keywords": ["offer", "closure", "joining", "counter offer", "risk"],
        "workspace": ["agent", "ats", "hq"],
    },
    {
        "key": "ats_governance",
        "title": "ATS Data Hygiene",
        "summary": "ATS should be the source of truth for imported candidates and open roles. Praapti suggestions stay separate until promoted.",
        "content": (
            "Do not mix hunt suggestions with ATS records silently. ATS stores reviewed jobs, candidates, statuses, and notes. "
            "Praapti is the scouting layer. Imported candidates should avoid duplicates, preserve source history, and respect "
            "the chosen disclosure level."
        ),
        "brains": ["mother_brain", "ats", "praapti"],
        "keywords": ["ats", "data hygiene", "duplicates", "import", "disclosure"],
        "workspace": ["agent", "ats", "praapti"],
    },
    {
        "key": "revenue_motion",
        "title": "Recruitment Revenue Motion",
        "summary": "TechBuzz revenue grows through retained searches, repeat hiring wins, account expansion, and faster closures.",
        "content": (
            "Every recruiting activity should connect to revenue: win a role, close a candidate, protect delivery quality, "
            "expand into adjacent roles, keep the client informed, and convert one-off wins into long-term accounts. "
            "The cabinet should prioritize actions that strengthen repeat business and margin discipline."
        ),
        "brains": ["mother_brain", "cabinet_brain", "hq", "accounts", "network"],
        "keywords": ["revenue", "retained search", "account growth", "margin", "repeat business"],
        "workspace": ["bridge", "hq", "accounts", "network"],
    },
    {
        "key": "privacy_policy",
        "title": "Candidate Privacy And Consent Policy",
        "summary": "Show only the minimum necessary candidate data until the user explicitly requests deeper detail.",
        "content": (
            "By default, candidate views should show guided summaries: role, fit, experience, strengths, concerns, and stage. "
            "Direct identifiers, personal notes, or full resume excerpts should only appear when the operator explicitly allows "
            "full context. The AI must never reveal more candidate data than the user asked for."
        ),
        "brains": ["mother_brain", "ats", "action_center", "accounts"],
        "keywords": ["privacy", "consent", "minimal disclosure", "candidate data"],
        "workspace": ["agent", "ats", "bridge"],
    },
    {
        "key": "device_action_policy",
        "title": "Safe Action Center Policy",
        "summary": "The AI may prepare actions for Gmail, Teams, browser pages, messages, and calls, but it must never auto-send or act silently.",
        "content": (
            "Action Center can prepare visible launch intents for Gmail, mailto, Teams, WhatsApp, browser URLs, SMS, and calls. "
            "The system must not silently send, call, message, or operate apps. It should present a prepared action, explain what "
            "will open, and wait for an explicit human click."
        ),
        "brains": ["mother_brain", "action_center", "network"],
        "keywords": ["gmail", "teams", "whatsapp", "browser", "call", "human confirmation"],
        "workspace": ["agent", "network", "bridge"],
    },
    {
        "key": "reviewed_mutation",
        "title": "Reviewed Improvement Loop",
        "summary": "The AI can propose upgrades, but changes must move through research, review, testing, and owner approval.",
        "content": (
            "Upgrades belong in the research and mutation workflow. The AI may draft code, plans, rollouts, migrations, tests, "
            "and plugins, but runtime self-rewriting is not allowed. Improvements should move through proposal, validation, "
            "review, approval, rollout, and learning broadcast."
        ),
        "brains": ["mother_brain", "cabinet_brain", "action_center", "accounts", "network", "praapti"],
        "keywords": ["mutation", "upgrade", "testing", "rollout", "approval"],
        "workspace": ["bridge", "agent", "hq", "research"],
    },
    {
        "key": "tracker_memory_ops",
        "title": "Recruiter Tracker Memory",
        "summary": "Every recruiter conversation, objection, submission, and candidate response should be captured in one tracker-ready memory lane.",
        "content": (
            "Recruiters lose time when submission records, call notes, objections, and acknowledgment states are scattered. "
            "The system should maintain one tracker row per candidate-role flow, remember the latest discussion, detect duplicates, "
            "track client submission state, and surface DSR or HSR summaries without forcing manual recollection."
        ),
        "brains": ["mother_brain", "praapti", "ats", "action_center"],
        "keywords": ["tracker", "dsr", "hsr", "submission", "candidate memory", "duplicate"],
        "workspace": ["agent", "ats", "hq"],
    },
    {
        "key": "candidate_objection_map",
        "title": "Candidate Objection Taxonomy",
        "summary": "The recruiter must separate no-response, not-interested, fitment, salary, location, project, company, duplicate, fake, and screen-reject reasons clearly.",
        "content": (
            "Not every rejection means the same thing. Track whether the candidate is not responding, not interested, duplicate on client portal, "
            "screen rejected, salary-misaligned, location-constrained, project-misaligned, company-sensitive, fake, or wasting time. "
            "This helps TechBuzz improve sourcing quality and recruiter follow-up."
        ),
        "brains": ["mother_brain", "praapti", "ats"],
        "keywords": ["objections", "no response", "screen reject", "salary", "location", "duplicate"],
        "workspace": ["agent", "ats", "praapti"],
    },
    {
        "key": "acknowledgment_flow",
        "title": "Acknowledgment And Confirmation Flow",
        "summary": "After an interested candidate agrees, acknowledgment must be prepared, sent visibly, and tracked until confirmation arrives.",
        "content": (
            "Once a candidate is interested and fit, the recruiter should prepare the acknowledgment mail, share the profile to the client, "
            "and track whether confirmation came back. The AI should draft the mail, log the sent state, and mark the confirmation only when the recruiter approves it."
        ),
        "brains": ["mother_brain", "ats", "action_center"],
        "keywords": ["acknowledgment", "confirmation", "mail draft", "submission"],
        "workspace": ["agent", "ats"],
    },
    {
        "key": "objective_evaluation",
        "title": "Objective Evaluation Doctrine",
        "summary": "Good AI recruitment should evaluate candidates on skills, evidence, experience, and predefined criteria instead of vague instinct.",
        "content": (
            "Objective evaluation means the system should compare candidates against structured criteria: skills, evidence of execution, communication, "
            "experience depth, role relevance, and delivery risk. It should reduce avoidable human bias, keep the same evaluation frame across candidates, "
            "and support structured interviews where each candidate faces comparable questions."
        ),
        "brains": ["mother_brain", "praapti", "ats", "cabinet_brain"],
        "keywords": ["objective evaluation", "bias reduction", "structured interview", "skills evidence", "merit"],
        "workspace": ["agent", "ats", "hq"],
    },
    {
        "key": "enhanced_candidate_sourcing",
        "title": "Enhanced Candidate Sourcing",
        "summary": "AI should widen the talent pool by scanning multiple channels while still keeping sourcing precise and role-led.",
        "content": (
            "Candidate sourcing should combine portals, professional networks, referrals, communities, social platforms, historic database memory, and employer-brand signals. "
            "The goal is not random volume. The goal is to expand the possible talent pool, monitor fresh talent continuously, and surface the best-fit profiles as they appear."
        ),
        "brains": ["mother_brain", "praapti", "network"],
        "keywords": ["candidate sourcing", "talent pool", "job boards", "social platforms", "professional network", "fresh candidates"],
        "workspace": ["agent", "network", "praapti"],
    },
    {
        "key": "time_cost_optimization",
        "title": "Time And Cost Optimization",
        "summary": "Recruitment AI should remove administrative drag so recruiters spend time on human judgment and candidate conversion.",
        "content": (
            "Automation should reduce time-to-hire and the cost of manual process work. Resume screening, tracker updates, scheduling, reminders, DSR, HSR, follow-ups, "
            "and acknowledgment preparation should be system-managed where possible. Recruiters should spend their best energy on fitment, candidate trust, and closure."
        ),
        "brains": ["mother_brain", "cabinet_brain", "ats", "action_center"],
        "keywords": ["time to hire", "cost saving", "automation", "tracker", "scheduling", "productivity"],
        "workspace": ["agent", "ats", "hq"],
    },
    {
        "key": "data_driven_recruitment",
        "title": "Data-Driven Recruitment Insight",
        "summary": "AI should turn recruitment activity into insight: source quality, conversion friction, closure patterns, and future action.",
        "content": (
            "The recruitment system should analyze which sources create the best candidates, which roles stall, which objections repeat, which interview loops create delays, "
            "and where candidate drop-off happens. These insights should shape sourcing plans, recruiter effort, hiring-manager alignment, and account strategy."
        ),
        "brains": ["mother_brain", "cabinet_brain", "ats", "accounts", "network"],
        "keywords": ["data driven", "source quality", "conversion", "drop-off", "recruitment analytics", "insight"],
        "workspace": ["agent", "ats", "hq", "accounts"],
    },
    {
        "key": "personalized_candidate_engagement",
        "title": "Personalized Candidate Engagement",
        "summary": "Candidate communication should feel timely, relevant, and specific to the person and their hiring journey.",
        "content": (
            "Good candidate engagement adapts communication to the person's stage, motivation, concerns, and behavior. It should answer questions quickly, "
            "share only relevant information, personalize updates, and help recruiters build trust. Every message should be respectful, accurate, and consent-aware."
        ),
        "brains": ["mother_brain", "praapti", "network", "action_center"],
        "keywords": ["candidate experience", "personalized engagement", "chatbot", "timely updates", "candidate journey"],
        "workspace": ["agent", "network", "praapti"],
    },
    {
        "key": "machine_learning_hiring_analysis",
        "title": "Machine Learning Hiring Analysis",
        "summary": "Machine learning should help assess historical hiring data, identify patterns, and improve future recruiting decisions.",
        "content": (
            "Recruitment AI should learn from historic submissions, conversions, closures, rejects, delays, and quality outcomes. It should identify what works, what fails, "
            "which signals predict quality, and which workflows waste recruiter effort. This learning should support better sourcing, prioritization, and planning."
        ),
        "brains": ["mother_brain", "cabinet_brain", "ats", "research"],
        "keywords": ["machine learning", "historic hiring data", "pattern analysis", "predictive quality", "decision support"],
        "workspace": ["agent", "ats", "research", "hq"],
    },
    {
        "key": "ai_onboarding_support",
        "title": "AI Onboarding Support",
        "summary": "Recruitment does not end at offer; onboarding should be guided, tracked, and personalized.",
        "content": (
            "The recruitment process should support the candidate after offer release through documentation, joining readiness, onboarding communication, and post-join check-ins. "
            "AI can reduce friction by organizing steps, reminders, and progress visibility for recruiters, candidates, and hiring teams."
        ),
        "brains": ["mother_brain", "ats", "action_center", "cabinet_brain"],
        "keywords": ["onboarding", "documentation", "joining", "post-join", "new hire support"],
        "workspace": ["agent", "ats", "hq"],
    },
    {
        "key": "predictive_workforce_planning",
        "title": "Predictive Workforce Planning",
        "summary": "AI should help forecast talent demand so recruiting becomes proactive instead of reactive.",
        "content": (
            "By analyzing open roles, business growth, historic closures, seasonal hiring, and market behavior, the system should help forecast staffing needs. "
            "This allows TechBuzz to build candidate pipelines early, plan recruiter bandwidth, and guide clients with proactive talent strategy."
        ),
        "brains": ["mother_brain", "cabinet_brain", "hq", "network", "accounts"],
        "keywords": ["predictive analytics", "workforce planning", "forecast", "staffing needs", "proactive recruitment"],
        "workspace": ["hq", "network", "accounts", "agent"],
    },
    {
        "key": "skill_assessment_quality",
        "title": "Skill Assessment And Quality Of Hire",
        "summary": "AI should help assess actual capability through tests, simulations, coding work, scenario questions, and discussion evidence.",
        "content": (
            "Skill assessment should not rely only on a resume. The system should connect role requirements to structured questions, coding challenges, simulation exercises, "
            "and execution evidence. This reduces fake profiles and helps recruiters distinguish claimed knowledge from demonstrated capability."
        ),
        "brains": ["mother_brain", "praapti", "ats", "research"],
        "keywords": ["skill assessment", "quality of hire", "coding challenge", "simulation", "fake profile detection"],
        "workspace": ["agent", "ats", "research"],
    },
    {
        "key": "diversity_inclusion_fairness",
        "title": "Diversity Inclusion And Fairness",
        "summary": "AI recruitment should widen access and reduce unfair filtering while staying focused on skills and role fit.",
        "content": (
            "Fair recruiting should minimize unconscious bias, encourage broader candidate reach, and evaluate applicants on job-relevant signals. "
            "The system should promote inclusion, avoid unnecessary exclusion rules, and keep decision reasoning understandable to recruiters and clients."
        ),
        "brains": ["mother_brain", "cabinet_brain", "ats", "network"],
        "keywords": ["diversity", "inclusion", "fairness", "bias", "job relevant", "equal opportunity"],
        "workspace": ["agent", "ats", "hq", "network"],
    },
    {
        "key": "compliance_and_risk_management",
        "title": "Compliance And Risk Management",
        "summary": "Recruitment AI must respect privacy, consent, labor-law routing, and defensible process behavior.",
        "content": (
            "Compliance includes privacy protection, consent-aware communication, fair handling of candidate information, and awareness that laws vary by geography. "
            "The system should help route legal or policy questions carefully, reduce noncompliance risk, and keep auditable records of process actions."
        ),
        "brains": ["mother_brain", "cabinet_brain", "ats", "accounts", "action_center"],
        "keywords": ["compliance", "privacy", "consent", "labor law", "risk management", "audit trail"],
        "workspace": ["agent", "ats", "accounts", "hq"],
    },
    {
        "key": "continuous_learning_improvement",
        "title": "Continuous Learning And Improvement",
        "summary": "Every recruitment cycle should improve the next one through feedback, outcome review, and process correction.",
        "content": (
            "AI recruitment should improve after every hunt, submission, interview, offer, joining, and backout. The system should absorb feedback, refine scoring, "
            "highlight weak process areas, and teach all relevant brains what improved quality, speed, candidate trust, and revenue."
        ),
        "brains": ["mother_brain", "cabinet_brain", "praapti", "ats", "research"],
        "keywords": ["continuous learning", "improvement", "feedback loop", "recruitment cycle", "outcome review"],
        "workspace": ["agent", "ats", "research", "hq"],
    },
    {
        "key": "ai_recruitment_implementation",
        "title": "AI Recruitment Implementation Blueprint",
        "summary": "Strong recruitment AI should be implemented in stages: define objectives, identify needs, select tools, prepare data, integrate, train, test, monitor, comply, and improve.",
        "content": (
            "Implementation should begin with clear objectives, then identify pain points, choose the right tools, prepare clean data, integrate carefully, train recruiters, "
            "test in a controlled way, monitor KPIs, enforce compliance and ethics, and keep updating the system as hiring reality evolves."
        ),
        "brains": ["mother_brain", "cabinet_brain", "action_center", "research", "hq"],
        "keywords": ["implementation", "objectives", "tool selection", "data preparation", "integration", "training", "monitoring", "ethics"],
        "workspace": ["hq", "research", "agent", "bridge"],
    },
    {
        "key": "ai_recruiting_definition",
        "title": "AI Recruiting Definition",
        "summary": "AI recruiting means using intelligence, automation, learning, and reasoning to augment repetitive hiring work while improving decision quality.",
        "content": (
            "AI recruiting is the use of artificial intelligence to augment and automate repetitive recruiting tasks such as sourcing, screening, scheduling, interviewing, "
            "follow-ups, and pipeline analysis. It is not just automation. It adds learning, reasoning, and adaptation so the system can handle complexity, personalize experiences, "
            "and guide recruiters toward better outcomes."
        ),
        "brains": ["mother_brain", "cabinet_brain", "praapti", "ats", "action_center"],
        "keywords": ["ai recruiting", "definition", "automation", "learning", "reasoning", "adaptation"],
        "workspace": ["agent", "ats", "hq", "bridge"],
    },
    {
        "key": "ai_recruiting_importance",
        "title": "Why AI Matters In Recruitment",
        "summary": "AI matters because recruiting teams must move faster, work smarter, reduce drag, and still deliver quality and trust.",
        "content": (
            "Recruiting AI is important because talent teams are under pressure to reduce time-to-hire, improve quality-of-hire, personalize outreach, and make better decisions "
            "with less manual effort. The right AI should blend into the background as support, allowing recruiters to focus on relationship building, stakeholder alignment, and closure."
        ),
        "brains": ["mother_brain", "cabinet_brain", "hq", "accounts"],
        "keywords": ["importance", "time to hire", "quality of hire", "productivity", "strategic recruiter"],
        "workspace": ["hq", "agent", "bridge", "accounts"],
    },
    {
        "key": "proactive_recruitment_strategy",
        "title": "Proactive Recruitment Strategy",
        "summary": "The strongest use of AI is shifting recruiting from reactive backfilling to proactive pipeline building.",
        "content": (
            "AI should help recruiters discover high-potential candidates before they apply, read intent signals early, nurture talent pools continuously, and build pipelines ahead of demand. "
            "This makes recruiting proactive instead of reactive and improves time-to-fill, candidate experience, and cost efficiency."
        ),
        "brains": ["mother_brain", "praapti", "network", "hq"],
        "keywords": ["proactive recruitment", "passive candidate", "talent pool", "intent signals", "pipeline building"],
        "workspace": ["agent", "network", "praapti", "hq"],
    },
    {
        "key": "automation_personalization_insights",
        "title": "Automation Personalization And Insight",
        "summary": "Recruiting AI should combine automation, personalization, and insights instead of treating them as separate systems.",
        "content": (
            "The highest-value recruitment AI combines three powers: automate repetitive work, personalize the candidate experience, and generate reliable data insights. "
            "Scheduling, screening, follow-ups, and reminders should be automated. Communication and recommendations should feel relevant to the person. "
            "And the whole system should produce insight into source quality, funnel health, candidate intent, and talent market dynamics."
        ),
        "brains": ["mother_brain", "cabinet_brain", "praapti", "ats", "network", "action_center"],
        "keywords": ["automation", "personalization", "insights", "candidate experience", "funnel health"],
        "workspace": ["agent", "ats", "network", "hq"],
    },
    {
        "key": "general_vs_genai_vs_applied_ai",
        "title": "General AI vs Generative AI vs Applied AI",
        "summary": "Recruitment teams must distinguish basic automation, prompt-driven generation, and agentic applied AI that executes workflows.",
        "content": (
            "General AI in recruiting usually means executing defined tasks within fixed boundaries. Generative AI creates content such as job descriptions, outreach, summaries, and interview questions. "
            "Applied AI is more agentic: it reasons within talent workflows, coordinates steps across systems, adapts to context, and executes goal-driven work across sourcing, screening, scheduling, interviewing, "
            "and lifecycle automation."
        ),
        "brains": ["mother_brain", "cabinet_brain", "research", "hq", "action_center"],
        "keywords": ["general ai", "generative ai", "applied ai", "agentic ai", "workflow execution"],
        "workspace": ["research", "hq", "agent", "bridge"],
    },
    {
        "key": "applied_ai_recruiting",
        "title": "Applied AI For Recruiting",
        "summary": "Applied AI in recruiting should act like an autonomous workflow partner across the talent lifecycle, not just a content tool.",
        "content": (
            "Applied AI recruiting means the system proactively reasons, decides, and executes within recruiting workflows. Instead of waiting for prompts, it helps orchestrate sourcing, "
            "screening, scheduling, interview preparation, pipeline movement, feedback capture, offer follow-up, and onboarding support while still escalating critical judgment to humans."
        ),
        "brains": ["mother_brain", "cabinet_brain", "praapti", "ats", "action_center", "network"],
        "keywords": ["applied ai", "autonomous workflow", "talent lifecycle", "agentic recruiter", "orchestration"],
        "workspace": ["agent", "ats", "network", "hq"],
    },
    {
        "key": "ethical_ai_recruiting",
        "title": "Ethical AI In Recruiting",
        "summary": "Trustworthy recruitment AI must be fair, transparent, accountable, and privacy-aware.",
        "content": (
            "Ethical AI in recruiting rests on four pillars: fairness, transparency, accountability, and privacy. The system should reduce bias by focusing on role-relevant signals, "
            "provide understandable reasoning, keep auditable histories, and protect candidate information carefully. Ethical design strengthens trust, reduces legal exposure, and supports long-term employer brand health."
        ),
        "brains": ["mother_brain", "cabinet_brain", "ats", "accounts", "action_center", "network"],
        "keywords": ["ethical ai", "fairness", "transparency", "accountability", "privacy", "trust"],
        "workspace": ["agent", "ats", "hq", "accounts"],
    },
    {
        "key": "ai_recruiting_challenges",
        "title": "AI Recruiting Challenges And Safeguards",
        "summary": "The main AI recruiting challenges are poor data, low trust, black-box recommendations, bias risks, compliance gaps, and weak adoption.",
        "content": (
            "AI will not produce strong recruiting outcomes unless the data is clean, structured, and connected across the talent journey. "
            "Teams also need explainable decisions, bias monitoring, legal and ethical documentation, and internal buy-in. "
            "Recruiters adopt AI faster when they see it as an enabler that removes manual work without removing human judgment."
        ),
        "brains": ["mother_brain", "cabinet_brain", "research", "accounts", "hq"],
        "keywords": ["data quality", "trust", "explainability", "bias detection", "buy-in", "adoption"],
        "workspace": ["research", "hq", "agent", "accounts"],
    },
    {
        "key": "ai_recruiting_tools_map",
        "title": "AI Recruiting Tools Map",
        "summary": "A strong recruiting stack includes personalization, intelligent search, chatbots, CRM, scheduling, screening, scoring, and interview intelligence.",
        "content": (
            "Modern AI recruiting tools should support personalized job recommendations, intelligent search, conversational chatbots, talent CRM, automated interview scheduling, "
            "screening workflows, fit and engagement scoring, candidate rediscovery, interview intelligence, sourcing insights, and talent pipeline tracking. "
            "The system should connect these capabilities instead of leaving them as disconnected point solutions."
        ),
        "brains": ["mother_brain", "praapti", "ats", "network", "action_center", "research"],
        "keywords": ["personalization", "intelligent search", "chatbot", "crm", "scheduling", "fit scoring", "interview intelligence"],
        "workspace": ["agent", "ats", "network", "research"],
    },
    {
        "key": "genai_recruiting_use_cases",
        "title": "Generative AI Use Cases In Recruitment",
        "summary": "GenAI should help create job descriptions, outreach, interview questions, summaries, and recruiter-ready communication at scale.",
        "content": (
            "Generative AI is most valuable when it helps recruiters create: job descriptions, outreach messages, interview guides, candidate summaries, screening notes, follow-up drafts, "
            "report narratives, and stakeholder updates. It is a creative partner, but it should still be grounded in structured recruitment data."
        ),
        "brains": ["mother_brain", "praapti", "action_center", "ats"],
        "keywords": ["genai", "job description", "outreach", "interview questions", "summary", "drafting"],
        "workspace": ["agent", "ats", "praapti"],
    },
    {
        "key": "specialized_ai_agents",
        "title": "Specialized Recruiting Agents",
        "summary": "Recruitment AI should split work into specialized agents with clear roles across the talent lifecycle.",
        "content": (
            "Different AI agents should own different parts of recruiting: Intake Agent, Sourcing Agent, Personalization Agent, Voice Screening Agent, Self-Scheduling Agent, "
            "Interview Agent, Fraud Detection Agent, Compliance Agent, Onboarding Agent, Workforce Planning Agent, and Succession Planning Agent. "
            "These agents should collaborate through a unified orchestration layer and escalate human judgment when needed."
        ),
        "brains": ["mother_brain", "cabinet_brain", "praapti", "ats", "network", "action_center", "research"],
        "keywords": ["intake agent", "sourcing agent", "personalization agent", "voice screening", "scheduling agent", "interview agent", "fraud detection", "compliance agent", "onboarding agent", "workforce planning"],
        "workspace": ["agent", "ats", "network", "research", "hq"],
    },
    {
        "key": "workflow_automation_ecosystem",
        "title": "Workflow Automation Ecosystem",
        "summary": "The real power of recruiting AI comes when CRM, ATS, communication, calendar, and reporting work as one connected workflow.",
        "content": (
            "Recruitment slows down when systems are siloed and handoffs are manual. AI workflow automation should connect the career site, CRM, ATS, calendar, interview flow, "
            "message channels, reporting lane, and candidate memory into one ecosystem. Data should move cleanly so that the candidate journey stays continuous and auditable."
        ),
        "brains": ["mother_brain", "cabinet_brain", "ats", "network", "action_center", "hq"],
        "keywords": ["workflow automation", "ecosystem", "crm", "ats", "calendar", "handoff", "orchestration"],
        "workspace": ["agent", "ats", "network", "hq", "bridge"],
    },
    {
        "key": "evolved_recruiter_model",
        "title": "Evolved Recruiter With AI And Automation",
        "summary": "The best recruiter evolution model keeps empathy, persuasion, assessment, and candidate trust human while shifting repetitive operations into AI and automation.",
        "content": (
            "The evolved recruiter should spend more time on empathy, culture fit, personal interviews, negotiation, persuasion, candidate closing, talent advising, magic moments, "
            "strategic assessment, and ethics management. AI and automation should take more responsibility for screening, parsing, job matching, discover leads, candidate search, "
            "dynamic talent pools, lead scoring, engagement scoring, referral scoring, profile augmentation, rediscovery, and watchlist intelligence."
        ),
        "brains": ["mother_brain", "cabinet_brain", "praapti", "network", "action_center", "hq"],
        "keywords": ["evolved recruiter", "human task", "ai task", "automation", "candidate closing", "talent advisor", "lead scoring"],
        "workspace": ["agent", "hq", "network", "bridge"],
    },
    {
        "key": "recruiter_role_evolution",
        "title": "Recruiter Role Evolution",
        "summary": "AI should free recruiters from manual work so they can become proactive relationship builders and strategic hiring partners.",
        "content": (
            "When AI handles repetitive work, recruiters should become more proactive, spend more time with best-fit candidates, align better with hiring managers, and use visual data "
            "to explain hiring quality and funnel health. The recruiter should evolve, not disappear."
        ),
        "brains": ["mother_brain", "cabinet_brain", "praapti", "ats", "hq"],
        "keywords": ["recruiter evolution", "relationship building", "proactive hiring", "hiring manager alignment", "strategic recruiter"],
        "workspace": ["agent", "ats", "hq"],
    },
    {
        "key": "talent_experience_engine",
        "title": "Talent Experience Engine",
        "summary": "The candidate experience should feel intelligent, relevant, and continuous from first discovery to hiring and beyond.",
        "content": (
            "Talent experience improves when job discovery, communication, screening, interview prep, scheduling, status updates, and onboarding guidance feel seamless. "
            "AI should make candidate interactions more relevant, timely, and reassuring while giving recruiters clean visibility into engagement and conversion."
        ),
        "brains": ["mother_brain", "praapti", "network", "action_center", "ats"],
        "keywords": ["talent experience", "candidate journey", "engagement", "status update", "seamless hiring"],
        "workspace": ["agent", "network", "ats"],
    },
    {
        "key": "ai_recruiting_vendor_landscape",
        "title": "AI Recruiting Vendor Landscape",
        "summary": "The recruitment market includes ATS platforms, sourcing tools, interview tools, staffing-agency systems, and talent-intelligence suites with different strengths.",
        "content": (
            "Top AI recruiting software should be understood by category, not as one flat list. "
            "Structured hiring and scalable ATS leaders include Greenhouse and Workable. "
            "Interview scheduling and candidate communication leaders include GoodTime and HireVue. "
            "Staffing-agency-oriented systems include Recruit CRM and Manatal. "
            "Conversational and chat-led recruiting tools include Humanly and Paradox. "
            "Autonomous or AI-heavy sourcing tools include Hirefly, Juicebox, Findem, Fetcher, Jobin.cloud, hireEZ, and Wellfound. "
            "Broader enterprise talent platforms include Eightfold, while Braintrust represents advanced interviewing capability. "
            "Recooty is an easy-to-use multilingual ATS option. "
            "The system should study these tools as market references so TechBuzz can understand where it should match, exceed, or differentiate."
        ),
        "brains": ["mother_brain", "cabinet_brain", "research", "hq", "praapti", "ats"],
        "keywords": [
            "greenhouse", "workable", "goodtime", "recruit crm", "manatal", "humanly", "paradox", "hirefly",
            "juicebox", "recooty", "wellfound", "findem", "hirevue", "fetcher", "braintrust", "jobin.cloud",
            "hireez", "eightfold", "ats", "sourcing", "interview scheduling", "staffing agency", "talent platform"
        ],
        "workspace": ["research", "hq", "agent", "ats", "bridge"],
    },
    {
        "key": "ai_recruiting_tool_categories",
        "title": "Recruiting Tool Category Map",
        "summary": "Recruitment software should be evaluated by operating category: ATS, CRM, sourcing, screening, scheduling, interviewing, staffing, marketplace, or talent-intelligence platform.",
        "content": (
            "When comparing recruiting tools, first classify the product correctly. ATS tools focus on workflow, requisitions, stages, and auditability. "
            "CRM tools focus on pipeline engagement and rediscovery. Sourcing tools focus on discovery and outreach. Scheduling tools focus on interview coordination. "
            "Interview tools focus on evaluation quality and consistency. Staffing-agency systems focus on submissions, client pipelines, trackers, and delivery speed. "
            "Enterprise talent platforms combine hiring, mobility, and workforce intelligence. "
            "TechBuzz should build its own stack with awareness of category strengths rather than copying one vendor blindly."
        ),
        "brains": ["mother_brain", "cabinet_brain", "research", "ats", "network"],
        "keywords": ["tool category", "ats", "crm", "sourcing", "screening", "scheduling", "interview", "staffing agency", "talent intelligence"],
        "workspace": ["research", "hq", "agent", "ats"],
    },
    {
        "key": "staffing_agency_product_gap",
        "title": "Staffing Agency Product Gap",
        "summary": "Most recruiting tools are strong in ATS or sourcing, but staffing agencies also need client-wise trackers, submission memory, duplicate control, and delivery ops.",
        "content": (
            "A staffing agency like TechBuzz needs more than a normal ATS. It needs recruiter conversation capture, submission trackers, DSR and HSR output, duplicate detection, "
            "client-wise candidate history, acknowledgment flow, interview scheduling, hiring-manager reminders, and post-join tracking. "
            "The system should keep learning from the broader recruiting software market while staying optimized for real staffing delivery work."
        ),
        "brains": ["mother_brain", "cabinet_brain", "ats", "action_center", "hq"],
        "keywords": ["staffing agency", "submission tracker", "duplicate control", "delivery ops", "client-wise memory", "dsr", "hsr"],
        "workspace": ["agent", "ats", "hq", "bridge"],
    },
]


ACTION_CENTER_OPTIONS: List[Dict[str, str]] = [
    {"id": "gmail", "label": "Open Gmail Draft", "description": "Prepare a Gmail compose screen with recipient, subject, and body."},
    {"id": "mailto", "label": "Open Mail Draft", "description": "Use the local mail app through a mailto draft."},
    {"id": "teams", "label": "Open Teams Chat", "description": "Prepare a Microsoft Teams chat deeplink."},
    {"id": "whatsapp", "label": "Open WhatsApp Message", "description": "Prepare a WhatsApp web or app message."},
    {"id": "phone", "label": "Start Phone Call", "description": "Prepare a tel: action for the selected number."},
    {"id": "sms", "label": "Open SMS Draft", "description": "Prepare an SMS draft for the device handler."},
    {"id": "browser", "label": "Open Browser URL", "description": "Open a safe browser URL or web app directly."},
    {"id": "linkedin", "label": "Open LinkedIn Search", "description": "Prepare a LinkedIn search or profile URL."},
]


AI_RECRUITING_VENDOR_GROUPS: List[Dict[str, Any]] = [
    {
        "category": "Structured ATS",
        "focus": "Structured hiring, requisitions, interview plans, and scalable pipeline discipline.",
        "vendors": ["Greenhouse", "Workable", "Manatal", "Recooty"],
    },
    {
        "category": "Scheduling And Interview Ops",
        "focus": "Interview coordination, candidate communication, and evaluation workflow consistency.",
        "vendors": ["GoodTime", "HireVue", "Humanly", "Paradox", "Braintrust"],
    },
    {
        "category": "Staffing Agency CRM And ATS",
        "focus": "Agency delivery, client submissions, recruiter pipelines, and recruiter productivity.",
        "vendors": ["Recruit CRM", "Manatal", "Jobin.cloud"],
    },
    {
        "category": "AI Sourcing And Rediscovery",
        "focus": "Candidate discovery, outbound outreach, shortlist building, and pipeline rediscovery.",
        "vendors": ["Hirefly", "Juicebox", "Wellfound", "Findem", "Fetcher", "hireEZ"],
    },
    {
        "category": "Talent Intelligence And Mobility",
        "focus": "Hiring intelligence, internal mobility, upskilling, and enterprise workforce visibility.",
        "vendors": ["Eightfold", "Findem"],
    },
]


class ActionCenterPrepareReq(BaseModel):
    kind: str = "gmail"
    target: str = ""
    subject: str = ""
    body: str = ""
    url: str = ""
    require_confirmation: bool = True


class AgentConsoleChatReq(BaseModel):
    message: str
    search: str = ""
    stage: str = ""
    detail: str = "guided"
    allow_full_context: bool = False
    date_from: str = ""
    date_to: str = ""
    recruiter: str = ""
    candidate_name: str = ""
    client_name: str = ""
    position: str = ""
    mail_id: str = ""
    contact_no: str = ""
    notice_period: str = ""
    row_id: str = ""
    submission_state: str = ""
    response_status: str = ""
    min_total_exp: str = ""
    max_total_exp: str = ""
    min_ctc: str = ""
    max_ctc: str = ""


TRACKER_ISSUE_OPTIONS = [
    "no_response",
    "not_interested",
    "fitment_issue",
    "salary_issue",
    "location_issue",
    "project_issue",
    "company_issue",
    "screen_rejected",
    "duplicate",
    "fake_profile",
    "timepass",
]


class RecruitmentTrackerUpdateReq(BaseModel):
    row_id: str
    process_stage: str = ""
    response_status: str = ""
    recruiter: str = ""
    sourced_from: str = ""
    client_name: str = ""
    position: str = ""
    contact_no: str = ""
    mail_id: str = ""
    current_company: str = ""
    current_location: str = ""
    preferred_location: str = ""
    total_exp: float = 0
    relevant_exp: float = 0
    notice_period: str = ""
    notice_state: str = ""
    current_ctc: float = 0
    expected_ctc: float = 0
    client_spoc: str = ""
    remarks: str = ""
    last_discussion: str = ""
    issue_flags: List[str] = []
    ack_action: str = ""
    submission_state: str = ""
    resume_document_id: str = ""
    resume_file_name: str = ""
    skill_snapshot: str = ""
    role_scope: str = ""
    follow_up_due_at: str = ""


class RecruitmentConversationCaptureReq(BaseModel):
    transcript: str
    row_id: str = ""
    candidate_id: str = ""
    job_id: str = ""
    candidate_name: str = ""
    position: str = ""
    client_name: str = ""
    recruiter: str = ""
    sourced_from: str = ""
    contact_no: str = ""
    mail_id: str = ""
    auto_prepare_ack: bool = True


class RecruitmentResumeSubmissionReq(BaseModel):
    document_id: str
    row_id: str = ""
    candidate_id: str = ""
    job_id: str = ""
    candidate_name: str = ""
    position: str = ""
    client_name: str = ""
    recruiter: str = ""
    sourced_from: str = ""
    contact_no: str = ""
    mail_id: str = ""
    current_company: str = ""
    current_location: str = ""
    preferred_location: str = ""
    total_exp: float = 0
    relevant_exp: float = 0
    notice_period: str = ""
    notice_state: str = ""
    current_ctc: float = 0
    expected_ctc: float = 0
    client_spoc: str = ""
    transcript: str = ""
    remarks: str = ""
    ack_status: str = "pending"
    candidate_confirmed: bool = False


class RecruitmentInterviewUpdateReq(BaseModel):
    row_id: str
    interview_round: str = "L1"
    scheduled_for: str = ""
    mode: str = "virtual"
    interviewer_name: str = ""
    interviewer_email: str = ""
    feedback_status: str = "pending"
    feedback_summary: str = ""
    next_stage: str = ""


class NetworkCandidateIntentReq(BaseModel):
    content: str = ""
    candidate_name: str = ""
    target_role: str = ""
    current_company: str = ""
    current_location: str = ""
    preferred_location: str = ""
    mail_id: str = ""
    contact_no: str = ""
    total_exp: float = 0
    relevant_exp: float = 0
    notice_period: str = ""
    notice_state: str = ""
    current_ctc: float = 0
    expected_ctc: float = 0
    applications_count: int = 0
    interviews_count: int = 0
    offers_count: int = 0
    source_kind: str = "network_post"
    post_id: str = ""
    auto_forward_to_ats: bool = True


def install_recruitment_brain_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_one = ctx.get("db_one")
    db_all = ctx["db_all"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    generate_text = ctx["generate_text"]
    get_state = ctx["get_state"]
    portal_state_payload = ctx["portal_state_payload"]
    ai_name = ctx["AI_NAME"]
    company_name = ctx["COMPANY_NAME"]
    core_identity = ctx["CORE_IDENTITY"]
    data_dir = Path(ctx["DATA_DIR"])
    document_dir = Path(ctx["DOCUMENT_DIR"])
    world_brain_context = ctx.get("world_brain_context")
    world_brain_status = ctx.get("world_brain_status")
    ishani_generate_text = ctx.get("ishani_generate_text")
    vault_dir = data_dir / "recruitment_vaults"
    vault_dir.mkdir(parents=True, exist_ok=True)

    def require_member(request: Request) -> Dict[str, Any]:
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        return user

    def recruiter_access_enabled(user: Dict[str, Any]) -> bool:
        if user.get("role") == "master":
            return True
        if user.get("plan_id") in {"growth", "empire", "mother-core"}:
            return True
        recruiter_rows = db_all(
            """
            SELECT id
            FROM recruitment_tracker_rows
            WHERE user_id=?
            LIMIT 1
            """,
            (user["id"],),
        ) or []
        return bool(recruiter_rows)

    def recruiter_archive_access_enabled(user: Dict[str, Any]) -> bool:
        if recruiter_access_enabled(user):
            return True
        archive_rows = db_all(
            """
            SELECT id
            FROM recruitment_vault_archives
            WHERE user_id=?
            LIMIT 1
            """,
            (user["id"],),
        ) or []
        return bool(archive_rows)

    def require_recruiter(request: Request) -> Dict[str, Any]:
        user = require_member(request)
        if not recruiter_access_enabled(user):
            raise HTTPException(
                status_code=403,
                detail="Recruiter reporting is available only in the recruiter workspace.",
            )
        return user

    def ensure_column(table: str, column: str, ddl: str) -> None:
        try:
            rows = db_all(f"PRAGMA table_info({table})") or []
            if column not in {row.get("name") for row in rows}:
                db_exec(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
        except Exception:
            pass

    def ensure_tables() -> None:
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS brain_knowledge(
                id TEXT PRIMARY KEY,
                brain_id TEXT NOT NULL,
                source_type TEXT,
                source_url TEXT,
                title TEXT,
                content TEXT,
                summary TEXT,
                keywords TEXT,
                relevance_score REAL DEFAULT 0.7,
                learned_at TEXT
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS action_center_events(
                id TEXT PRIMARY KEY,
                user_id TEXT,
                action_kind TEXT,
                target TEXT,
                subject TEXT,
                body TEXT,
                launch_url TEXT,
                created_at TEXT
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS recruitment_tracker_rows(
                id TEXT PRIMARY KEY,
                user_id TEXT,
                candidate_id TEXT,
                job_id TEXT,
                sourced_from TEXT,
                process_stage TEXT DEFAULT 'sourced',
                recruiter TEXT,
                client_name TEXT,
                position TEXT,
                profile_sharing_date TEXT,
                candidate_name TEXT,
                contact_no TEXT,
                mail_id TEXT,
                current_company TEXT,
                current_location TEXT,
                preferred_location TEXT,
                total_exp REAL DEFAULT 0,
                relevant_exp REAL DEFAULT 0,
                notice_period TEXT,
                notice_state TEXT,
                current_ctc REAL DEFAULT 0,
                expected_ctc REAL DEFAULT 0,
                client_spoc TEXT,
                response_status TEXT DEFAULT 'pending_review',
                issue_flags TEXT,
                duplicate_status TEXT DEFAULT 'clear',
                remarks TEXT,
                last_discussion TEXT,
                ack_mail_sent_at TEXT,
                ack_confirmed_at TEXT,
                submission_state TEXT DEFAULT 'draft',
                resume_document_id TEXT DEFAULT '',
                resume_file_name TEXT DEFAULT '',
                resume_text TEXT DEFAULT '',
                skill_snapshot TEXT DEFAULT '',
                role_scope TEXT DEFAULT '',
                follow_up_due_at TEXT DEFAULT '',
                last_contacted_at TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS recruitment_conversation_logs(
                id TEXT PRIMARY KEY,
                user_id TEXT,
                row_id TEXT,
                transcript TEXT,
                parsed_json TEXT,
                created_at TEXT
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS recruitment_journey_events(
                id TEXT PRIMARY KEY,
                user_id TEXT,
                row_id TEXT,
                event_type TEXT,
                stage TEXT,
                response_status TEXT,
                summary TEXT,
                details_json TEXT,
                actor TEXT,
                created_at TEXT
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS recruitment_interview_events(
                id TEXT PRIMARY KEY,
                user_id TEXT,
                row_id TEXT,
                interview_round TEXT,
                scheduled_for TEXT,
                mode TEXT,
                interviewer_name TEXT,
                interviewer_email TEXT,
                feedback_status TEXT,
                feedback_summary TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS recruitment_report_snapshots(
                id TEXT PRIMARY KEY,
                user_id TEXT,
                report_kind TEXT,
                window_key TEXT,
                window_label TEXT,
                window_start TEXT,
                window_end TEXT,
                row_count INTEGER DEFAULT 0,
                headline TEXT,
                summary TEXT,
                totals_json TEXT,
                filters_json TEXT,
                tsv TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        ensure_column("recruitment_tracker_rows", "submission_state", "TEXT DEFAULT 'draft'")
        ensure_column("recruitment_tracker_rows", "resume_document_id", "TEXT DEFAULT ''")
        ensure_column("recruitment_tracker_rows", "resume_file_name", "TEXT DEFAULT ''")
        ensure_column("recruitment_tracker_rows", "resume_text", "TEXT DEFAULT ''")
        ensure_column("recruitment_tracker_rows", "skill_snapshot", "TEXT DEFAULT ''")
        ensure_column("recruitment_tracker_rows", "role_scope", "TEXT DEFAULT ''")
        ensure_column("recruitment_tracker_rows", "follow_up_due_at", "TEXT DEFAULT ''")
        ensure_column("recruitment_conversation_logs", "event_type", "TEXT DEFAULT 'conversation'")
        ensure_column("recruitment_conversation_logs", "candidate_name", "TEXT DEFAULT ''")
        ensure_column("recruitment_conversation_logs", "position", "TEXT DEFAULT ''")
        ensure_column("recruitment_conversation_logs", "client_name", "TEXT DEFAULT ''")
        ensure_column("recruitment_conversation_logs", "recruiter", "TEXT DEFAULT ''")
        ensure_column("recruitment_conversation_logs", "mail_id", "TEXT DEFAULT ''")
        ensure_column("recruitment_conversation_logs", "contact_no", "TEXT DEFAULT ''")
        ensure_column("recruitment_conversation_logs", "total_exp", "REAL DEFAULT 0")
        ensure_column("recruitment_conversation_logs", "relevant_exp", "REAL DEFAULT 0")
        ensure_column("recruitment_conversation_logs", "notice_period", "TEXT DEFAULT ''")
        ensure_column("recruitment_conversation_logs", "current_ctc", "REAL DEFAULT 0")
        ensure_column("recruitment_conversation_logs", "expected_ctc", "REAL DEFAULT 0")
        ensure_column("recruitment_conversation_logs", "process_stage", "TEXT DEFAULT ''")
        ensure_column("recruitment_conversation_logs", "response_status", "TEXT DEFAULT ''")
        ensure_column("recruitment_conversation_logs", "submission_state", "TEXT DEFAULT ''")
        ensure_column("recruitment_conversation_logs", "discussion_summary", "TEXT DEFAULT ''")
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS recruitment_candidate_signals(
                id TEXT PRIMARY KEY,
                user_id TEXT,
                signal_key TEXT,
                network_post_id TEXT,
                row_id TEXT,
                candidate_id TEXT,
                candidate_name TEXT,
                mail_id TEXT,
                contact_no TEXT,
                target_role TEXT,
                current_company TEXT,
                current_location TEXT,
                preferred_location TEXT,
                total_exp REAL DEFAULT 0,
                relevant_exp REAL DEFAULT 0,
                notice_period TEXT,
                notice_state TEXT,
                current_ctc REAL DEFAULT 0,
                expected_ctc REAL DEFAULT 0,
                job_change_intent TEXT DEFAULT 'unknown',
                intent_confidence REAL DEFAULT 0,
                applications_count INTEGER DEFAULT 0,
                interviews_count INTEGER DEFAULT 0,
                offers_count INTEGER DEFAULT 0,
                fit_note TEXT,
                next_move TEXT,
                source_kind TEXT,
                source_summary TEXT,
                raw_text TEXT,
                source_types TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS recruitment_vault_registry(
                user_id TEXT PRIMARY KEY,
                vault_fingerprint TEXT NOT NULL DEFAULT '',
                local_generation INTEGER NOT NULL DEFAULT 0,
                server_generation INTEGER NOT NULL DEFAULT 0,
                operational_status TEXT NOT NULL DEFAULT 'active',
                local_record_count INTEGER NOT NULL DEFAULT 0,
                local_document_count INTEGER NOT NULL DEFAULT 0,
                last_local_sync_at TEXT DEFAULT '',
                last_server_sync_at TEXT DEFAULT '',
                last_archive_id TEXT DEFAULT '',
                last_archive_hash TEXT DEFAULT '',
                last_archive_summary TEXT DEFAULT '',
                last_imported_at TEXT DEFAULT '',
                local_cache_cleared_at TEXT DEFAULT '',
                created_at TEXT DEFAULT '',
                updated_at TEXT DEFAULT ''
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS recruitment_vault_archives(
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                archive_kind TEXT NOT NULL DEFAULT 'server_sync',
                archive_name TEXT NOT NULL,
                archive_hash TEXT NOT NULL,
                vault_fingerprint TEXT NOT NULL DEFAULT '',
                record_count INTEGER NOT NULL DEFAULT 0,
                document_count INTEGER NOT NULL DEFAULT 0,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                file_path TEXT NOT NULL DEFAULT '',
                summary TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS follow_up_tasks(
                id TEXT PRIMARY KEY,
                user_id TEXT,
                row_id TEXT,
                candidate_name TEXT,
                position TEXT,
                reason TEXT,
                message_draft TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                completed_at TEXT
            )
            """
        )

    def seed_brains() -> None:
        for pack in RECRUITMENT_SEED_PACKS:
            keyword_blob = ",".join(pack["keywords"])
            source_url = f"seed://{pack['key']}"
            for brain_id in pack["brains"]:
                existing = db_all(
                    """
                    SELECT id FROM brain_knowledge
                    WHERE brain_id=? AND source_type='core_seed' AND title=?
                    LIMIT 1
                    """,
                    (brain_id, pack["title"]),
                )
                if existing:
                    continue
                db_exec(
                    """
                    INSERT INTO brain_knowledge(id,brain_id,source_type,source_url,title,content,summary,keywords,relevance_score,learned_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        new_id("bk"),
                        brain_id,
                        "core_seed",
                        source_url,
                        pack["title"],
                        pack["content"],
                        pack["summary"],
                        keyword_blob,
                        0.99,
                        now_iso(),
                    ),
                )

    def brain_scope_for_workspace(workspace: str) -> List[str]:
        scope = {
            "bridge": ["mother_brain", "cabinet_brain", "action_center", "accounts"],
            "hq": ["mother_brain", "cabinet_brain", "accounts", "network"],
            "agent": ["mother_brain", "praapti", "ats", "action_center"],
            "ats": ["mother_brain", "praapti", "ats"],
            "network": ["mother_brain", "network", "action_center"],
            "praapti": ["mother_brain", "praapti", "ats"],
        }
        return scope.get((workspace or "bridge").strip().lower(), scope["bridge"])

    def seed_pack_payload() -> Dict[str, Any]:
        rows = db_all(
            """
            SELECT brain_id, COUNT(*) AS total, MAX(learned_at) AS last_seeded
            FROM brain_knowledge
            WHERE source_type='core_seed'
            GROUP BY brain_id
            ORDER BY brain_id
            """
        )
        coverage = {row["brain_id"]: int(row.get("total", 0) or 0) for row in rows}
        last_seeded = max((row.get("last_seeded", "") for row in rows), default="")
        return {
            "headline": f"{company_name} recruitment core is permanently seeded across the brain mesh.",
            "packs": [
                {
                    "title": pack["title"],
                    "summary": pack["summary"],
                    "brains": pack["brains"],
                    "keywords": pack["keywords"],
                    "workspace": pack["workspace"],
                }
                for pack in RECRUITMENT_SEED_PACKS
            ],
            "coverage": coverage,
            "seeded_brains": sorted(coverage.keys()),
            "seeded_entries": sum(coverage.values()),
            "last_seeded_at": last_seeded,
            "world_atlas": world_brain_status() if callable(world_brain_status) else None,
        }

    def learning_health_snapshot() -> Dict[str, Any]:
        rows = db_all(
            """
            SELECT brain_id,
                   SUM(CASE WHEN source_type='core_seed' THEN 1 ELSE 0 END) AS seed_count,
                   COUNT(*) AS knowledge_count,
                   MAX(learned_at) AS last_learned
            FROM brain_knowledge
            GROUP BY brain_id
            ORDER BY brain_id
            """
        )
        brains = []
        for row in rows:
            seed_count = int(row.get("seed_count", 0) or 0)
            knowledge_count = int(row.get("knowledge_count", 0) or 0)
            status = "healthy" if seed_count >= 3 and knowledge_count >= seed_count else "learning"
            brains.append(
                {
                    "brain_id": row["brain_id"],
                    "seed_count": seed_count,
                    "knowledge_count": knowledge_count,
                    "status": status,
                    "last_learned": row.get("last_learned", ""),
                }
            )
        total_seeded = sum(item["seed_count"] for item in brains)
        total_knowledge = sum(item["knowledge_count"] for item in brains)
        return {
            "headline": "Every important brain starts with recruitment-first knowledge and can then learn beyond it.",
            "brains": brains,
            "seeded_entries": total_seeded,
            "knowledge_entries": total_knowledge,
            "coverage_percent": 100 if brains else 0,
            "loops": [
                "Permanent seed memory for recruitment and revenue work",
                "Praapti and ATS feedback from hunts, imports, and scorecards",
                "Global hiring atlas for regions, role families, candidate intent, and live law-routing",
                "Research and mutation lessons broadcast through reviewed learning",
            ],
        }

    def seed_brief(workspace: str = "bridge", audience: str = "member", limit: int = 4, extra_query: str = "") -> str:
        brain_ids = brain_scope_for_workspace(workspace)
        if not brain_ids:
            return "No recruitment seed loaded yet."
        placeholders = ",".join("?" for _ in brain_ids)
        rows = db_all(
            f"""
            SELECT title, summary, keywords
            FROM brain_knowledge
            WHERE source_type='core_seed' AND brain_id IN ({placeholders})
            """,
            tuple(brain_ids),
        )
        if not rows:
            fallback = [pack["summary"] for pack in RECRUITMENT_SEED_PACKS[:limit]]
            return "\n".join(f"- {line}" for line in fallback)
        phrase = (extra_query or "").lower()
        query_terms = {
            term for term in re.findall(r"[a-zA-Z][a-zA-Z0-9_+-]{2,}", (extra_query or "").lower())
            if len(term) >= 3
        }
        ranked = []
        for row in rows:
            title_lower = str(row.get("title", "")).lower()
            summary_lower = str(row.get("summary", "")).lower()
            keywords_lower = str(row.get("keywords", "")).lower()
            haystack = " ".join(
                [
                    title_lower,
                    summary_lower,
                    keywords_lower,
                ]
            )
            score = 0
            if query_terms:
                score += sum(3 for term in query_terms if term in keywords_lower)
                score += sum(2 for term in query_terms if term in title_lower)
                score += sum(1 for term in query_terms if term in haystack)
            if "what is ai recruiting" in phrase or ("ai recruiting" in phrase and "what is" in phrase):
                if "definition" in title_lower or "ai recruiting" in title_lower:
                    score += 10
            if ("why" in phrase or "important" in phrase) and ("importance" in title_lower or "why ai matters" in title_lower):
                score += 8
            if "applied ai" in phrase or "generative ai" in phrase or "general ai" in phrase:
                if "applied ai" in title_lower or "generative ai" in title_lower or "general ai" in title_lower:
                    score += 9
            if "agent" in phrase and "specialized recruiting agents" in title_lower:
                score += 8
            if "workflow automation" in phrase and "workflow automation" in title_lower:
                score += 8
            if any(term in phrase for term in ("greenhouse", "workable", "goodtime", "recruit crm", "findem", "hirevue", "eightfold", "hireez", "braintrust", "paradox")):
                if "vendor landscape" in title_lower or "tool category map" in title_lower or "product gap" in title_lower:
                    score += 9
            ranked.append((score, row))
        ranked.sort(key=lambda item: (item[0], str(item[1].get("title", ""))), reverse=True)
        selected_rows = []
        seen_titles = set()
        for _, row in ranked:
            title_key = str(row.get("title", "")).strip().lower()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            selected_rows.append(row)
            if len(selected_rows) >= limit:
                break
        lines = []
        for row in selected_rows:
            summary = row.get("summary") or row.get("title") or "Recruitment seed memory"
            if audience == "public":
                summary = summary.replace("direct contact data", "sensitive candidate data")
            lines.append(f"- {summary}")
        if callable(world_brain_context):
            atlas = world_brain_context(extra_query or workspace, limit=4)
            if atlas:
                lines.append("")
                lines.append("Global atlas:")
                lines.extend(atlas.splitlines()[:6])
        return "\n".join(lines)

    def normalize_phone(value: str) -> str:
        return re.sub(r"[^0-9+]", "", value or "")

    def normalize_browser_url(value: str) -> str:
        candidate = (value or "").strip()
        if not candidate:
            return ""
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", candidate):
            return candidate
        return "https://" + candidate.lstrip("/")

    def build_action_url(req: ActionCenterPrepareReq) -> Dict[str, str]:
        kind = (req.kind or "gmail").strip().lower()
        target = (req.target or "").strip()
        subject = (req.subject or "").strip()
        body = (req.body or "").strip()
        url = (req.url or "").strip()

        if kind == "gmail":
            if not target:
                raise HTTPException(status_code=400, detail="Recipient email is required for Gmail drafts.")
            launch_url = (
                "https://mail.google.com/mail/?view=cm&fs=1"
                f"&to={quote(target)}&su={quote(subject)}&body={quote(body)}"
            )
            return {"launch_url": launch_url, "label": "Open Gmail Draft", "summary": f"Draft email to {target}"}
        if kind == "mailto":
            if not target:
                raise HTTPException(status_code=400, detail="Recipient email is required for mail drafts.")
            launch_url = f"mailto:{target}?subject={quote(subject)}&body={quote(body)}"
            return {"launch_url": launch_url, "label": "Open Mail Draft", "summary": f"Mail draft for {target}"}
        if kind == "teams":
            if not target:
                raise HTTPException(status_code=400, detail="Teams user or email is required.")
            launch_url = f"https://teams.microsoft.com/l/chat/0/0?users={quote(target)}&message={quote(body)}"
            return {"launch_url": launch_url, "label": "Open Teams Chat", "summary": f"Teams chat for {target}"}
        if kind == "whatsapp":
            phone = normalize_phone(target)
            if not phone:
                raise HTTPException(status_code=400, detail="Phone number is required for WhatsApp.")
            launch_url = f"https://wa.me/{phone.lstrip('+')}?text={quote(body or subject)}"
            return {"launch_url": launch_url, "label": "Open WhatsApp Message", "summary": f"WhatsApp draft for {phone}"}
        if kind == "phone":
            phone = normalize_phone(target)
            if not phone:
                raise HTTPException(status_code=400, detail="Phone number is required for calls.")
            return {"launch_url": f"tel:{phone}", "label": "Start Phone Call", "summary": f"Call {phone}"}
        if kind == "sms":
            phone = normalize_phone(target)
            if not phone:
                raise HTTPException(status_code=400, detail="Phone number is required for SMS.")
            launch_url = f"sms:{phone}?body={quote(body or subject)}"
            return {"launch_url": launch_url, "label": "Open SMS Draft", "summary": f"SMS draft for {phone}"}
        if kind == "linkedin":
            launch_url = normalize_browser_url(url) if url else f"https://www.linkedin.com/search/results/all/?keywords={quote_plus(target or subject)}"
            return {"launch_url": launch_url, "label": "Open LinkedIn", "summary": "LinkedIn page prepared"}
        if kind == "browser":
            launch_url = normalize_browser_url(url or target)
            if not launch_url:
                raise HTTPException(status_code=400, detail="A browser URL is required.")
            return {"launch_url": launch_url, "label": "Open Browser Page", "summary": "Browser page prepared"}
        raise HTTPException(status_code=400, detail="Unsupported action kind")

    def recent_action_events(user_id: str) -> List[Dict[str, Any]]:
        return db_all(
            """
            SELECT id, action_kind, target, subject, body, launch_url, created_at
            FROM action_center_events
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT 12
            """,
            (user_id,),
        ) or []

    def parse_issue_flags(value: Any) -> List[str]:
        if not value:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except Exception:
            pass
        return [item.strip() for item in str(value).split(",") if item.strip()]

    def parse_iso(value: str) -> Optional[datetime]:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone().replace(tzinfo=None)
            return parsed
        except Exception:
            return None

    def default_recruiter_name(user: Dict[str, Any]) -> str:
        return (
            user.get("name")
            or user.get("identifier")
            or user.get("email")
            or "TechBuzz Recruiter"
        )

    def clean_text(value: Any, limit: int = 400) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]

    def clean_multiline(value: Any, limit: int = 4000) -> str:
        raw = str(value or "").replace("\r", "\n")
        lines = [re.sub(r"\s+", " ", line).strip() for line in raw.split("\n")]
        return "\n".join(line for line in lines if line)[:limit]

    def parse_json_blob(value: Any, fallback: Any) -> Any:
        if value in (None, "", []):
            return fallback
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except Exception:
            return fallback

    def row_recorded_at(row: Dict[str, Any]) -> Optional[datetime]:
        return (
            parse_iso(row.get("updated_at", ""))
            or parse_iso(row.get("created_at", ""))
            or parse_iso(row.get("profile_sharing_date", ""))
        )

    def parse_filter_date(value: Any) -> Optional[datetime]:
        raw = clean_text(value, 40)
        if not raw:
            return None
        parsed = parse_iso(raw)
        if parsed:
            return parsed.replace(hour=0, minute=0, second=0, microsecond=0)
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(raw, fmt)
            except Exception:
                continue
        return None

    def recruitment_row_snapshot(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "row_id": row.get("id", ""),
            "candidate_id": row.get("candidate_id", ""),
            "job_id": row.get("job_id", ""),
            "candidate_name": clean_text(row.get("candidate_name", ""), 120),
            "position": clean_text(row.get("position", ""), 160),
            "client_name": clean_text(row.get("client_name", ""), 160),
            "recruiter": clean_text(row.get("recruiter", ""), 120),
            "mail_id": clean_text(row.get("mail_id", ""), 200),
            "contact_no": clean_text(row.get("contact_no", ""), 40),
            "current_company": clean_text(row.get("current_company", ""), 160),
            "current_location": clean_text(row.get("current_location", ""), 160),
            "preferred_location": clean_text(row.get("preferred_location", ""), 160),
            "total_exp": as_float(row.get("total_exp", 0), 0),
            "relevant_exp": as_float(row.get("relevant_exp", 0), 0),
            "notice_period": clean_text(row.get("notice_period", ""), 80),
            "notice_state": clean_text(row.get("notice_state", ""), 40),
            "current_ctc": as_float(row.get("current_ctc", 0), 0),
            "expected_ctc": as_float(row.get("expected_ctc", 0), 0),
            "process_stage": clean_text(row.get("process_stage", ""), 80),
            "response_status": clean_text(row.get("response_status", ""), 80),
            "submission_state": clean_text(row.get("submission_state", "draft"), 80) or "draft",
            "skill_snapshot": clean_text(row.get("skill_snapshot", ""), 320),
            "role_scope": clean_text(row.get("role_scope", ""), 420),
            "follow_up_due_at": clean_text(row.get("follow_up_due_at", ""), 80),
            "remarks": clean_text(row.get("remarks", ""), 500),
            "last_discussion": clean_multiline(row.get("last_discussion", ""), 1600),
            "updated_at": clean_text(row.get("updated_at", ""), 40),
            "profile_sharing_date": clean_text(row.get("profile_sharing_date", ""), 40),
        }

    def report_window_for_scope(scope: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        now = datetime.now()
        scope_key = clean_text(scope, 20).lower() or "tracker"
        filters = filters or {}
        date_from = parse_filter_date(filters.get("date_from"))
        date_to = parse_filter_date(filters.get("date_to"))
        if scope_key == "dsr":
            start = date_from or now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = (date_to or start) + timedelta(days=1)
            return {
                "kind": "dsr",
                "key": start.strftime("%Y-%m-%d"),
                "label": f"DSR {start.strftime('%d %b %Y')}",
                "start": start,
                "end": end,
            }
        if scope_key == "hsr":
            reference = date_from or now
            bucket_hour = (reference.hour // 2) * 2
            start = reference.replace(hour=bucket_hour, minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=2)
            return {
                "kind": "hsr",
                "key": start.strftime("%Y-%m-%dT%H:00"),
                "label": f"HSR {start.strftime('%d %b %Y %H:%M')} - {end.strftime('%H:%M')}",
                "start": start,
                "end": end,
            }
        return {
            "kind": scope_key,
            "key": "latest",
            "label": "Live tracker",
            "start": None,
            "end": None,
        }

    def default_scope_filters(scope: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        merged = dict(filters or {})
        window = report_window_for_scope(scope, merged)
        if scope == "dsr" and not merged.get("date_from") and not merged.get("date_to"):
            merged["date_from"] = window["start"].date().isoformat()
            merged["date_to"] = (window["end"] - timedelta(seconds=1)).date().isoformat()
        elif scope == "hsr" and not merged.get("date_from") and not merged.get("date_to"):
            merged["date_from"] = window["start"].date().isoformat()
            merged["date_to"] = window["start"].date().isoformat()
            merged["window_start"] = window["start"].isoformat()
            merged["window_end"] = window["end"].isoformat()
        return merged

    def tracker_row_matches_filters(row: Dict[str, Any], filters: Optional[Dict[str, Any]] = None) -> bool:
        filters = filters or {}
        row_id_filter = clean_text(filters.get("row_id") or filters.get("id"), 80).lower()
        if row_id_filter and row_id_filter != clean_text(row.get("id", ""), 80).lower():
            return False
        search_blob = " ".join(
            [
                clean_text(row.get("candidate_name", ""), 120),
                clean_text(row.get("position", ""), 160),
                clean_text(row.get("client_name", ""), 160),
                clean_text(row.get("recruiter", ""), 120),
                clean_text(row.get("sourced_from", ""), 120),
                clean_text(row.get("mail_id", ""), 200),
                clean_text(row.get("contact_no", ""), 40),
                clean_text(row.get("skill_snapshot", ""), 320),
                clean_text(row.get("role_scope", ""), 420),
                clean_text(row.get("remarks", ""), 500),
                clean_text(row.get("last_discussion", ""), 1000),
            ]
        ).lower()
        for key in ("search", "candidate_name", "client_name", "position", "recruiter", "mail_id", "contact_no"):
            value = clean_text(filters.get(key), 160).lower()
            if value and value not in search_blob:
                return False
        notice_filter = clean_text(filters.get("notice_period"), 80).lower()
        if notice_filter:
            notice_blob = " ".join(
                [
                    clean_text(row.get("notice_period", ""), 80),
                    clean_text(row.get("notice_state", ""), 40),
                ]
            ).lower()
            if notice_filter not in notice_blob:
                return False
        submission_filter = clean_text(filters.get("submission_state"), 80).lower()
        if submission_filter and submission_filter != clean_text(row.get("submission_state", "draft"), 80).lower():
            return False
        response_filter = clean_text(filters.get("response_status"), 80).lower()
        if response_filter and response_filter != clean_text(row.get("response_status", ""), 80).lower():
            return False
        stage_filter = clean_text(filters.get("stage"), 80).lower()
        if stage_filter and stage_filter != clean_text(row.get("process_stage", ""), 80).lower():
            return False

        min_total_exp = as_float(filters.get("min_total_exp"), -1)
        if min_total_exp >= 0 and as_float(row.get("total_exp", 0), 0) < min_total_exp:
            return False
        max_total_exp = as_float(filters.get("max_total_exp"), -1)
        if max_total_exp >= 0 and as_float(row.get("total_exp", 0), 0) > max_total_exp:
            return False
        min_relevant_exp = as_float(filters.get("min_relevant_exp"), -1)
        if min_relevant_exp >= 0 and as_float(row.get("relevant_exp", 0), 0) < min_relevant_exp:
            return False
        max_relevant_exp = as_float(filters.get("max_relevant_exp"), -1)
        if max_relevant_exp >= 0 and as_float(row.get("relevant_exp", 0), 0) > max_relevant_exp:
            return False
        min_ctc = as_float(filters.get("min_ctc"), -1)
        if min_ctc >= 0 and max(as_float(row.get("current_ctc", 0), 0), as_float(row.get("expected_ctc", 0), 0)) < min_ctc:
            return False
        max_ctc = as_float(filters.get("max_ctc"), -1)
        if max_ctc >= 0 and max(as_float(row.get("current_ctc", 0), 0), as_float(row.get("expected_ctc", 0), 0)) > max_ctc:
            return False

        recorded_at = row_recorded_at(row)
        date_from = parse_filter_date(filters.get("date_from"))
        if date_from and (not recorded_at or recorded_at < date_from):
            return False
        date_to = parse_filter_date(filters.get("date_to"))
        if date_to and (not recorded_at or recorded_at >= date_to + timedelta(days=1)):
            return False
        window_start = parse_iso(clean_text(filters.get("window_start"), 40))
        if window_start and (not recorded_at or recorded_at < window_start):
            return False
        window_end = parse_iso(clean_text(filters.get("window_end"), 40))
        if window_end and (not recorded_at or recorded_at >= window_end):
            return False
        return True

    def as_float(value: Any, fallback: float = 0) -> float:
        if value in (None, ""):
            return fallback
        try:
            return float(value)
        except Exception:
            match = re.search(r"(\d+(?:\.\d+)?)", str(value))
            if match:
                try:
                    return float(match.group(1))
                except Exception:
                    return fallback
        return fallback

    def extract_count_from_text(text: str, patterns: List[str]) -> int:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.I)
            if match:
                try:
                    return int(match.group(1))
                except Exception:
                    continue
        return 0

    def infer_target_role_from_text(text: str) -> str:
        patterns = [
            r"(?:looking for|seeking|targeting|open to)\s+(?:a|an)?\s*([a-z0-9 /+#._-]{3,80}?)\s+(?:role|position|opportunity|job)\b",
            r"(?:role|position|job title|target role)\s*[:=-]\s*([^\n,;]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.I)
            if match:
                return clean_text(match.group(1), 160)
        return ""

    def infer_job_change_intent(text: str) -> Dict[str, Any]:
        lower = (text or "").lower()
        active_terms = [
            "looking for job change",
            "looking for a job change",
            "looking for change",
            "actively looking",
            "actively exploring",
            "searching for a job",
            "searching for opportunities",
            "want to switch",
            "ready to switch",
            "immediate joiner",
            "open to opportunities",
        ]
        passive_terms = [
            "open to move",
            "open for better opportunity",
            "open for opportunities",
            "can consider a change",
            "exploring the market",
            "evaluating opportunities",
        ]
        closed_terms = [
            "not looking",
            "not open to move",
            "happy in current role",
            "not interested in change",
        ]
        if any(term in lower for term in closed_terms):
            return {"intent": "closed", "confidence": 0.88, "label": "not looking right now"}
        if any(term in lower for term in active_terms):
            return {"intent": "active", "confidence": 0.94, "label": "actively looking for a move"}
        if any(term in lower for term in passive_terms):
            return {"intent": "passive", "confidence": 0.74, "label": "open if the role is strong"}
        return {"intent": "unknown", "confidence": 0.25, "label": "job-change intent not confirmed yet"}

    def candidate_signal_key(
        *,
        candidate_name: str = "",
        mail_id: str = "",
        contact_no: str = "",
        current_company: str = "",
    ) -> str:
        if mail_id:
            return f"mail:{mail_id.strip().lower()}"
        if contact_no:
            return f"phone:{normalize_phone(contact_no)}"
        cleaned_name = clean_text(candidate_name, 120).lower()
        if cleaned_name and cleaned_name not in {"candidate", "network candidate"}:
            company_key = clean_text(current_company, 120).lower() or "unknown"
            return f"name:{cleaned_name}|company:{company_key}"
        return ""

    def merge_source_types(existing: Any, new_value: str) -> str:
        items = set(parse_issue_flags(existing))
        if new_value:
            items.add(clean_text(new_value, 80).lower())
        return json.dumps(sorted(items), ensure_ascii=False)

    def candidate_fit_snapshot(
        *,
        total_exp: float,
        relevant_exp: float,
        response_status: str,
        process_stage: str,
        issue_flags: List[str],
    ) -> Dict[str, Any]:
        score = 55
        total_exp = max(0, as_float(total_exp, 0))
        relevant_exp = max(0, as_float(relevant_exp, 0))
        if total_exp and relevant_exp:
            score += min(20, int((relevant_exp / max(total_exp, 1)) * 20))
        elif total_exp:
            score += min(10, int(total_exp))
        if response_status in {"interested", "shared", "ack_confirmed", "available"}:
            score += 8
        if process_stage in {"profile_shared", "l1_interview", "l2_interview", "l3_interview", "offer"}:
            score += 6
        penalties = {
            "fake_profile": 35,
            "timepass": 18,
            "fitment_issue": 18,
            "screen_rejected": 18,
            "salary_issue": 10,
            "location_issue": 10,
            "project_issue": 8,
            "company_issue": 8,
            "duplicate": 6,
            "no_response": 8,
            "not_interested": 12,
        }
        for flag in issue_flags:
            score -= penalties.get(flag, 0)
        score = max(0, min(99, score))
        if score >= 80:
            label = "strong fit"
        elif score >= 65:
            label = "workable fit"
        elif score >= 45:
            label = "stretch fit"
        else:
            label = "low fit"
        return {"score": score, "label": label}

    def candidate_next_move(
        *,
        job_change_intent: str,
        applications_count: int,
        interviews_count: int,
        offers_count: int,
        response_status: str,
        issue_flags: List[str],
        fit_label: str,
        pending_feedback: bool,
    ) -> str:
        if "fake_profile" in issue_flags or "timepass" in issue_flags:
            return "Pause submission and run a deeper credibility screen before moving further."
        if offers_count > 0:
            return "Close fast, test joining intent, and check counter-offer or offer-shopping risk."
        if pending_feedback or response_status in {"shared", "ack_confirmed"}:
            return "Collect interview or client feedback now and keep at least one backup warm."
        if "no_response" in issue_flags or response_status == "no_response":
            return "Send one timed follow-up, then move the backup pipeline instead of waiting."
        if "screen_rejected" in issue_flags or "fitment_issue" in issue_flags:
            return "Recalibrate the JD match, fix resume proof, and resubmit only if the fit improves."
        if fit_label == "strong fit" and job_change_intent in {"active", "passive"}:
            return "Fast-track screening, line up the best-fit live role, and keep the candidate warm."
        if applications_count >= 4 and interviews_count == 0:
            return "Tighten the pitch, resume, and role targeting before adding more applications."
        if interviews_count >= 2 and offers_count == 0:
            return "Coach story, interview answers, and objection handling before the next round."
        if job_change_intent == "active":
            return "Move into screening quickly and map the candidate to live ATS roles."
        return "Keep this profile in watch mode and update the tracker when new intent or fit data arrives."

    def extract_email(text: str) -> str:
        match = re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", text, flags=re.I)
        return match.group(0) if match else ""

    def extract_phone(text: str) -> str:
        match = re.search(r"(?<!\d)(?:\+91[\s-]*)?[6-9]\d{9}(?!\d)", text)
        return normalize_phone(match.group(0)) if match else ""

    def extract_label_value(text: str, labels: List[str]) -> str:
        for label in labels:
            pattern = rf"{label}\s*[:=-]\s*([^\n,;]+)"
            match = re.search(pattern, text, flags=re.I)
            if match:
                return clean_text(match.group(1), 200)
        return ""

    def extract_number_after_labels(text: str, labels: List[str]) -> float:
        for label in labels:
            pattern = rf"{label}\s*[:=-]?\s*(\d+(?:\.\d+)?)"
            match = re.search(pattern, text, flags=re.I)
            if match:
                return as_float(match.group(1), 0)
        return 0

    def infer_notice_period(text: str) -> str:
        lower = text.lower()
        if "immediate" in lower or "join immediately" in lower:
            return "Immediate"
        if "serving notice" in lower or "serving np" in lower:
            days = re.search(r"(\d{1,3})\s*(?:day|days)", lower)
            return f"Serving {days.group(1)} days" if days else "Serving notice"
        days = re.search(r"(notice period|np|lwd)\s*[:=-]?\s*(\d{1,3})\s*(?:day|days)?", lower)
        if days:
            return f"{days.group(2)} days"
        month = re.search(r"(notice period|np)\s*[:=-]?\s*(\d)\s*(?:month|months)", lower)
        if month:
            return f"{month.group(2)} months"
        return ""

    def infer_notice_state(text: str, notice_period: str = "") -> str:
        lower = text.lower()
        if "immediate" in lower:
            return "immediate"
        if "serving notice" in lower or "serving np" in lower or notice_period.lower().startswith("serving"):
            return "serving"
        if notice_period:
            return "not_serving"
        return ""

    def infer_process_stage(text: str) -> str:
        lower = text.lower()
        if any(term in lower for term in ("post joining", "post-joining", "after joining", "joined and started")):
            return "post_join_followup"
        if any(term in lower for term in ("joined", "joining completed")):
            return "joined"
        if any(term in lower for term in ("joining", "join on", "joining on")):
            return "joining"
        if any(term in lower for term in ("offer released", "offer stage", "offer discussion", "offer in hand")):
            return "offer"
        if any(term in lower for term in ("documentation", "docs pending", "documents pending", "document collection")):
            return "documentation"
        if any(term in lower for term in ("l3", "third round", "final interview")):
            return "l3_interview"
        if any(term in lower for term in ("l2", "second round")):
            return "l2_interview"
        if any(term in lower for term in ("l1", "first round", "interview scheduled", "interview", "technical round", "manager round")):
            return "l1_interview"
        if any(term in lower for term in ("profile shared", "shared to client", "submitted to client", "processed profile")):
            return "profile_shared"
        if any(term in lower for term in ("screening", "screen call", "screened", "screening done")):
            return "screening"
        return "sourced"

    def infer_response_status(text: str) -> str:
        lower = text.lower()
        if any(term in lower for term in ("ack confirmed", "confirmed on mail", "confirmed profile", "candidate confirmed")):
            return "ack_confirmed"
        if any(term in lower for term in ("screen rejected", "screen reject", "rejected in screening")):
            return "screen_rejected"
        if any(term in lower for term in ("not interested", "not looking", "not open to move", "declined")):
            return "not_interested"
        if any(term in lower for term in ("no response", "not answering", "not reachable", "switched off", "unreachable")):
            return "no_response"
        if any(term in lower for term in ("interested", "available", "okay to proceed", "willing to proceed", "shared profile")):
            return "interested"
        return "pending_review"

    def infer_issue_flags_from_text(text: str) -> List[str]:
        lower = text.lower()
        flags: List[str] = []
        keyword_map = {
            "no_response": ["no response", "not responding", "unreachable", "switched off", "not reachable"],
            "not_interested": ["not interested", "not looking", "declined", "not open to move"],
            "fitment_issue": ["fitment issue", "not fit", "not relevant", "lacks relevant experience", "missing skill", "skill gap"],
            "salary_issue": ["salary issue", "budget issue", "ctc mismatch", "expected ctc high", "hike issue", "offer shopping"],
            "location_issue": ["location issue", "relocation issue", "won't relocate", "location mismatch", "preferred location different"],
            "project_issue": ["project issue", "project mismatch", "domain mismatch"],
            "company_issue": ["company issue", "client issue", "company brand issue"],
            "screen_rejected": ["screen rejected", "screen reject"],
            "duplicate": ["duplicate", "already submitted", "duplicate on client portal"],
            "fake_profile": ["fake profile", "fake resume", "unable to answer", "bluffing", "copied resume", "can't explain"],
            "timepass": ["timepass", "just checking market", "not serious"],
        }
        for issue, keywords in keyword_map.items():
            if any(keyword in lower for keyword in keywords):
                flags.append(issue)
        return sorted(set(flags))

    def extract_section(text: str, labels: List[str], limit: int = 500) -> str:
        body = clean_multiline(text, 8000)
        if not body:
            return ""
        patterns = [
            rf"(?:^|\n)\s*{re.escape(label)}\s*[:\-]?\s*(.+?)(?=(?:\n\s*[A-Z][A-Za-z /&]{2,40}\s*[:\-])|\n\s*\n|$)"
            for label in labels
        ]
        for pattern in patterns:
            match = re.search(pattern, body, flags=re.I | re.S)
            if match:
                value = clean_multiline(match.group(1), limit)
                if value:
                    return value
        return ""

    def split_listish(text: str, limit: int = 12) -> List[str]:
        if not text:
            return []
        cleaned = re.sub(r"[\u2022•]", ",", text)
        parts = re.split(r"[,/|;\n]+", cleaned)
        seen = set()
        items: List[str] = []
        for part in parts:
            item = clean_text(part, 60)
            if not item:
                continue
            if ":" in item and item.lower().split(":", 1)[0] in {"roles and responsibilities", "responsibilities", "profile summary"}:
                continue
            if len(item.split()) > 5:
                continue
            lower = item.lower()
            if lower in seen:
                continue
            seen.add(lower)
            items.append(item)
            if len(items) >= limit:
                break
        return items

    def extract_skill_snapshot(text: str) -> str:
        skill_block = extract_section(
            text,
            [
                "skills",
                "technical skills",
                "key skills",
                "core skills",
                "primary skills",
                "tech stack",
            ],
            limit=800,
        )
        skill_block = re.split(r"roles?\s+and\s+responsibilities\s*[:\-]?", skill_block, maxsplit=1, flags=re.I)[0]
        items = split_listish(skill_block, limit=14)
        if items:
            return ", ".join(items)[:320]
        lower = (text or "").lower()
        known = [
            "java",
            "spring boot",
            "microservices",
            "kafka",
            "oracle",
            "sql",
            "python",
            "django",
            "flask",
            "fastapi",
            "react",
            "angular",
            "node",
            "node.js",
            "typescript",
            "javascript",
            "aws",
            "azure",
            "gcp",
            "docker",
            "kubernetes",
            "linux",
            "naukri",
            "linkedin",
            "monster",
            "screening",
            "sourcing",
            "boolean search",
            "it recruitment",
            "talent acquisition",
        ]
        found = []
        for skill in known:
            if skill in lower:
                label = skill.upper() if skill in {"aws", "gcp", "sql"} else skill.title()
                if label not in found:
                    found.append(label)
            if len(found) >= 12:
                break
        return ", ".join(found)[:320]

    def extract_role_scope(text: str) -> str:
        block = extract_section(
            text,
            [
                "roles and responsibilities",
                "responsibilities",
                "current role",
                "role summary",
                "profile summary",
            ],
            limit=700,
        )
        if block:
            return block[:420]
        lines = [
            clean_text(line, 180)
            for line in clean_multiline(text, 1800).split("\n")
            if any(token in line.lower() for token in ("develop", "manage", "lead", "support", "build", "screen", "hire", "source", "deliver"))
        ]
        return " | ".join(lines[:3])[:420]

    def infer_candidate_name_from_resume(text: str) -> str:
        for raw_line in (text or "").splitlines()[:8]:
            line = clean_text(raw_line, 120)
            if not line or "@" in line or any(ch.isdigit() for ch in line):
                continue
            words = [word for word in line.split() if word]
            if 2 <= len(words) <= 4:
                return line
        return ""

    def parse_resume_profile(text: str) -> Dict[str, Any]:
        cleaned = clean_multiline(text, 12000)
        total_exp = extract_number_after_labels(cleaned, ["total exp", "overall exp", "total experience"])
        if not total_exp:
            matches = re.findall(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)", cleaned, flags=re.I)
            if matches:
                total_exp = max(float(match) for match in matches)
        relevant_exp = extract_number_after_labels(cleaned, ["relevant exp", "relevant experience", "rel exp"])
        if total_exp and not relevant_exp:
            relevant_exp = total_exp
        return {
            "candidate_name": infer_candidate_name_from_resume(cleaned),
            "mail_id": clean_text(extract_email(cleaned), 200),
            "contact_no": normalize_phone(extract_phone(cleaned)),
            "current_location": clean_text(
                extract_label_value(cleaned, ["current location", "present location", "location", "base location"]),
                160,
            ),
            "preferred_location": clean_text(
                extract_label_value(cleaned, ["preferred location", "preferred city", "relocation"]),
                160,
            ),
            "current_company": clean_text(
                extract_label_value(cleaned, ["current company", "company", "organization"]),
                160,
            ),
            "total_exp": total_exp,
            "relevant_exp": relevant_exp,
            "notice_period": infer_notice_period(cleaned),
            "notice_state": infer_notice_state(cleaned, infer_notice_period(cleaned)),
            "skill_snapshot": extract_skill_snapshot(cleaned),
            "role_scope": extract_role_scope(cleaned),
            "resume_text": cleaned[:12000],
        }

    def normalized_submission_state(
        *,
        existing_state: str = "",
        ack_action: str = "",
        ack_status: str = "",
        candidate_confirmed: bool = False,
        ack_sent_at: str = "",
        ack_confirmed_at: str = "",
    ) -> str:
        state = clean_text(ack_status or existing_state, 40).lower()
        if ack_action == "confirmed" or candidate_confirmed or ack_confirmed_at:
            return "confirmed"
        if ack_action == "sent" or state == "sent" or ack_sent_at:
            return "ack_sent"
        if ack_action == "prepared" or state in {"prepared", "ack_prepared"}:
            return "ack_prepared"
        return "draft"

    def derive_follow_up_due(
        *,
        process_stage: str = "",
        response_status: str = "",
        submission_state: str = "",
        scheduled_for: str = "",
    ) -> str:
        now = datetime.now()
        stage = clean_text(process_stage, 80).lower()
        response = clean_text(response_status, 80).lower()
        submission = clean_text(submission_state, 40).lower()
        if submission in {"draft", "ack_prepared"} or response in {"pending_review", "interested"}:
            return (now + timedelta(hours=4)).isoformat(timespec="minutes")
        if response == "no_response":
            return (now + timedelta(days=1)).isoformat(timespec="minutes")
        if stage in {"l1_interview", "l2_interview", "l3_interview"}:
            scheduled = parse_iso(scheduled_for)
            anchor = scheduled if scheduled else now
            return (anchor + timedelta(hours=2)).isoformat(timespec="minutes")
        if stage in {"offer", "documentation", "joining", "joined", "post_join_followup"}:
            return (now + timedelta(hours=12)).isoformat(timespec="minutes")
        return (now + timedelta(hours=6)).isoformat(timespec="minutes")

    def load_user_document(user_id: str, document_id: str) -> Dict[str, Any]:
        rows = db_all(
            """
            SELECT *
            FROM documents
            WHERE id=? AND user_id=?
            LIMIT 1
            """,
            (document_id, user_id),
        ) or []
        if not rows:
            raise HTTPException(status_code=404, detail="Resume document not found.")
        return rows[0]

    def conversation_summary(parsed: Dict[str, Any]) -> str:
        parts = []
        if parsed.get("candidate_name"):
            parts.append(parsed["candidate_name"])
        if parsed.get("position"):
            parts.append(parsed["position"])
        if parsed.get("process_stage"):
            parts.append(parsed["process_stage"].replace("_", " "))
        if parsed.get("response_status") and parsed.get("response_status") != "pending_review":
            parts.append(parsed["response_status"].replace("_", " "))
        if parsed.get("notice_period"):
            parts.append(f"NP {parsed['notice_period']}")
        if parsed.get("issue_flags"):
            parts.append("issues: " + ", ".join(parsed["issue_flags"]))
        return " | ".join(parts)[:280] or "Recruiter conversation captured."

    def parse_recruiter_conversation(req: RecruitmentConversationCaptureReq, recruiter_name: str) -> Dict[str, Any]:
        transcript = clean_multiline(req.transcript, 6000)
        current_location = extract_label_value(transcript, ["current location", "present location", "location"])
        preferred_location = extract_label_value(transcript, ["preferred location", "preferred city", "relocation"])
        parsed = {
            "transcript": transcript,
            "candidate_name": clean_text(req.candidate_name or extract_label_value(transcript, ["candidate name", "name"]), 120),
            "position": clean_text(req.position or extract_label_value(transcript, ["position", "role", "job title"]), 160),
            "client_name": clean_text(req.client_name or extract_label_value(transcript, ["client", "company", "client name"]), 160) or company_name,
            "recruiter": clean_text(req.recruiter or recruiter_name, 120),
            "sourced_from": clean_text(req.sourced_from or extract_label_value(transcript, ["source", "portal", "sourced from"]), 80) or "manual",
            "contact_no": normalize_phone(req.contact_no or extract_phone(transcript)),
            "mail_id": clean_text(req.mail_id or extract_email(transcript), 200),
            "current_company": clean_text(extract_label_value(transcript, ["current company", "company"]), 160),
            "current_location": current_location,
            "preferred_location": preferred_location,
            "total_exp": extract_number_after_labels(transcript, ["total exp", "overall exp", "total experience"]),
            "relevant_exp": extract_number_after_labels(transcript, ["relevant exp", "relevant experience", "rel exp"]),
            "notice_period": infer_notice_period(transcript),
            "notice_state": infer_notice_state(transcript, infer_notice_period(transcript)),
            "current_ctc": extract_number_after_labels(transcript, ["current ctc", "ctc", "current salary"]),
            "expected_ctc": extract_number_after_labels(transcript, ["expected ctc", "ectc", "expected salary"]),
            "client_spoc": clean_text(extract_label_value(transcript, ["client spoc", "spoc", "hiring manager"]), 120),
            "remarks": clean_text(extract_label_value(transcript, ["remarks", "note", "notes"]), 280),
            "last_discussion": transcript[:1400],
            "skill_snapshot": extract_skill_snapshot(transcript),
            "role_scope": extract_role_scope(transcript),
            "process_stage": infer_process_stage(transcript),
            "response_status": infer_response_status(transcript),
            "issue_flags": infer_issue_flags_from_text(transcript),
        }
        if parsed["total_exp"] and not parsed["relevant_exp"]:
            parsed["relevant_exp"] = parsed["total_exp"]
        if not parsed["remarks"]:
            parsed["remarks"] = conversation_summary(parsed)
        parsed["summary"] = conversation_summary(parsed)
        parsed["ack_ready"] = bool(
            req.auto_prepare_ack
            and parsed["mail_id"]
            and parsed["response_status"] == "interested"
        )
        return parsed

    def tracker_stage_for_ats(process_stage: str, response_status: str = "") -> str:
        stage = (process_stage or "").strip().lower()
        response = (response_status or "").strip().lower()
        if stage in {"l1_interview", "l2_interview", "l3_interview"}:
            return "interview"
        if stage in {"offer", "documentation", "joining"}:
            return "offer"
        if stage in {"joined", "post_join_followup"}:
            return "hired"
        if response in {"screen_rejected", "not_interested"}:
            return "rejected"
        if stage in {"profile_shared", "screening"}:
            return "screening"
        return "applied"

    def find_tracker_row(
        user: Dict[str, Any],
        *,
        row_id: str = "",
        candidate_id: str = "",
        mail_id: str = "",
        candidate_name: str = "",
        position: str = "",
    ) -> Optional[Dict[str, Any]]:
        if row_id:
            rows = db_all(
                "SELECT * FROM recruitment_tracker_rows WHERE id=? AND user_id=? LIMIT 1",
                (row_id, user["id"]),
            ) or []
            if rows:
                return rows[0]
        if candidate_id:
            rows = db_all(
                "SELECT * FROM recruitment_tracker_rows WHERE candidate_id=? AND user_id=? LIMIT 1",
                (candidate_id, user["id"]),
            ) or []
            if rows:
                return rows[0]
        if mail_id:
            rows = db_all(
                "SELECT * FROM recruitment_tracker_rows WHERE lower(mail_id)=lower(?) AND user_id=? ORDER BY updated_at DESC LIMIT 1",
                (mail_id, user["id"]),
            ) or []
            if rows:
                return rows[0]
        if candidate_name and position:
            rows = db_all(
                """
                SELECT * FROM recruitment_tracker_rows
                WHERE user_id=? AND lower(candidate_name)=lower(?) AND lower(position)=lower(?)
                ORDER BY updated_at DESC LIMIT 1
                """,
                (user["id"], candidate_name, position),
            ) or []
            if rows:
                return rows[0]
        return None

    def append_journey_event(
        user: Dict[str, Any],
        row_id: str,
        *,
        event_type: str,
        stage: str,
        response_status: str,
        summary: str,
        details: Optional[Dict[str, Any]] = None,
        actor: str = "",
    ) -> None:
        db_exec(
            """
            INSERT INTO recruitment_journey_events(id,user_id,row_id,event_type,stage,response_status,summary,details_json,actor,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                new_id("rje"),
                user["id"],
                row_id,
                clean_text(event_type, 80),
                clean_text(stage, 80),
                clean_text(response_status, 80),
                clean_text(summary, 500),
                json.dumps(details or {}, ensure_ascii=False)[:3000],
                clean_text(actor, 160),
                now_iso(),
            ),
        )

    def record_interview_event(
        user: Dict[str, Any],
        row_id: str,
        *,
        interview_round: str,
        scheduled_for: str,
        mode: str,
        interviewer_name: str,
        interviewer_email: str,
        feedback_status: str,
        feedback_summary: str,
    ) -> None:
        existing = db_all(
            """
            SELECT id FROM recruitment_interview_events
            WHERE user_id=? AND row_id=? AND interview_round=?
            ORDER BY updated_at DESC LIMIT 1
            """,
            (user["id"], row_id, interview_round),
        ) or []
        if existing:
            db_exec(
                """
                UPDATE recruitment_interview_events
                SET scheduled_for=?, mode=?, interviewer_name=?, interviewer_email=?, feedback_status=?, feedback_summary=?, updated_at=?
                WHERE id=? AND user_id=?
                """,
                (
                    scheduled_for,
                    clean_text(mode, 80),
                    clean_text(interviewer_name, 160),
                    clean_text(interviewer_email, 200),
                    clean_text(feedback_status, 80),
                    clean_text(feedback_summary, 600),
                    now_iso(),
                    existing[0]["id"],
                    user["id"],
                ),
            )
            return
        db_exec(
            """
            INSERT INTO recruitment_interview_events(id,user_id,row_id,interview_round,scheduled_for,mode,interviewer_name,interviewer_email,feedback_status,feedback_summary,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                new_id("riv"),
                user["id"],
                row_id,
                clean_text(interview_round, 40),
                scheduled_for,
                clean_text(mode, 80),
                clean_text(interviewer_name, 160),
                clean_text(interviewer_email, 200),
                clean_text(feedback_status, 80),
                clean_text(feedback_summary, 600),
                now_iso(),
                now_iso(),
            ),
        )

    def build_ack_content(row: Dict[str, Any]) -> Dict[str, str]:
        subject = f"{row.get('position') or 'Open role'} | TechBuzz profile acknowledgment"
        body = (
            f"Hi {row.get('candidate_name') or 'Candidate'},\n\n"
            f"This is to confirm that your profile is being processed for {row.get('position') or 'the open role'} "
            f"at {row.get('client_name') or company_name}.\n"
            f"Current stage: {(row.get('process_stage') or 'screening').replace('_', ' ')}.\n\n"
            "Please reply with your confirmation and any updates on notice period, current CTC, expected CTC, "
            "preferred location, and last working day if applicable.\n\n"
            "Regards,\nTechBuzz Recruitment Desk"
        )
        return {"subject": subject, "body": body}

    def prepare_ack_event(user: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
        if not row.get("mail_id"):
            raise HTTPException(status_code=400, detail="Candidate email is required before preparing the acknowledgment mail.")
        content = build_ack_content(row)
        built = build_action_url(
            ActionCenterPrepareReq(
                kind="gmail",
                target=row.get("mail_id", ""),
                subject=content["subject"],
                body=content["body"],
                require_confirmation=True,
            )
        )
        event_id = new_id("ace")
        db_exec(
            """
            INSERT INTO action_center_events(id,user_id,action_kind,target,subject,body,launch_url,created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                event_id,
                user["id"],
                "gmail",
                clean_text(row.get("mail_id", ""), 300),
                content["subject"][:300],
                content["body"][:1500],
                built["launch_url"][:1500],
                now_iso(),
            ),
        )
        return {
            "id": event_id,
            "kind": "gmail",
            "launch_url": built["launch_url"],
            "label": built["label"],
            "summary": built["summary"],
            "subject": content["subject"],
            "body": content["body"],
            "message": "Acknowledgment prepared. Review it, then open Gmail when you want to send it.",
        }

    def upsert_candidate_signal(
        user: Dict[str, Any],
        *,
        content: str,
        candidate_name: str = "",
        mail_id: str = "",
        contact_no: str = "",
        target_role: str = "",
        current_company: str = "",
        current_location: str = "",
        preferred_location: str = "",
        total_exp: float = 0,
        relevant_exp: float = 0,
        notice_period: str = "",
        notice_state: str = "",
        current_ctc: float = 0,
        expected_ctc: float = 0,
        applications_count: int = 0,
        interviews_count: int = 0,
        offers_count: int = 0,
        source_kind: str = "manual",
        network_post_id: str = "",
        row_id: str = "",
        candidate_id: str = "",
        auto_forward_to_ats: bool = True,
    ) -> Dict[str, Any]:
        transcript = clean_multiline(content, 5000)
        network_fallback_name = (
            user.get("name")
            or user.get("identifier")
            or user.get("email")
            or "Network Candidate"
        ) if clean_text(source_kind, 80).startswith("network") else "Candidate"
        signal_name = clean_text(
            candidate_name
            or extract_label_value(transcript, ["candidate name", "name"])
            or network_fallback_name,
            120,
        )
        signal_mail = clean_text(
            mail_id
            or extract_email(transcript)
            or ((user.get("email") or "") if clean_text(source_kind, 80).startswith("network") else ""),
            200,
        )
        signal_phone = normalize_phone(contact_no or extract_phone(transcript))
        signal_company = clean_text(current_company or extract_label_value(transcript, ["current company", "company"]), 160)
        signal_role = clean_text(target_role or infer_target_role_from_text(transcript), 160) or "Talent Pool"
        signal_location = clean_text(current_location or extract_label_value(transcript, ["current location", "present location", "location"]), 120)
        signal_pref_location = clean_text(preferred_location or extract_label_value(transcript, ["preferred location", "preferred city", "relocation"]), 120)
        signal_total_exp = as_float(total_exp or extract_number_after_labels(transcript, ["total exp", "overall exp", "total experience"]), 0)
        signal_relevant_exp = as_float(relevant_exp or extract_number_after_labels(transcript, ["relevant exp", "relevant experience", "rel exp"]), 0)
        signal_notice = clean_text(notice_period or infer_notice_period(transcript), 80)
        signal_notice_state = clean_text(notice_state or infer_notice_state(transcript, signal_notice), 40)
        signal_current_ctc = as_float(current_ctc or extract_number_after_labels(transcript, ["current ctc", "ctc", "current salary"]), 0)
        signal_expected_ctc = as_float(expected_ctc or extract_number_after_labels(transcript, ["expected ctc", "ectc", "expected salary"]), 0)
        derived_applications = extract_count_from_text(
            transcript,
            [
                r"appl(?:ied|ications?)\s*(?:in|to|with)?\s*(\d{1,2})\s*(?:companies|company|places)",
                r"(\d{1,2})\s*(?:companies|company|places)\s*(?:applied|applications?)",
                r"companies applied\s*[:=-]?\s*(\d{1,2})",
            ],
        )
        derived_interviews = extract_count_from_text(
            transcript,
            [
                r"(\d{1,2})\s*(?:interviews|interview rounds?|rounds?)",
                r"interviews?\s*[:=-]?\s*(\d{1,2})",
                r"given\s*(\d{1,2})\s*(?:interviews|rounds?)",
            ],
        )
        derived_offers = extract_count_from_text(
            transcript,
            [
                r"(\d{1,2})\s*(?:offer|offers|offer letters?)",
                r"offers?\s*(?:in hand)?\s*[:=-]?\s*(\d{1,2})",
                r"holding\s*(\d{1,2})\s*(?:offer|offers|offer letters?)",
            ],
        )
        intent_snapshot = infer_job_change_intent(transcript)
        explicit_signal = any(
            [
                clean_text(candidate_name, 120),
                clean_text(target_role, 160),
                clean_text(current_company, 160),
                clean_text(mail_id, 200),
                clean_text(contact_no, 40),
                as_float(total_exp, 0) > 0,
                as_float(relevant_exp, 0) > 0,
                clean_text(notice_period, 80),
                int(applications_count or 0) > 0,
                int(interviews_count or 0) > 0,
                int(offers_count or 0) > 0,
                derived_applications > 0,
                derived_interviews > 0,
                derived_offers > 0,
            ]
        )
        if clean_text(source_kind, 80).startswith("network") and intent_snapshot["intent"] == "unknown" and not explicit_signal:
            return {"captured": False, "reason": "No clear job-change signal was detected in the network message."}
        signal_key = candidate_signal_key(
            candidate_name=signal_name,
            mail_id=signal_mail,
            contact_no=signal_phone,
            current_company=signal_company,
        )
        if not signal_key:
            return {"captured": False, "reason": "Candidate identity is too thin to store separately yet."}

        existing_rows = db_all(
            """
            SELECT * FROM recruitment_candidate_signals
            WHERE user_id=? AND signal_key=?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (user["id"], signal_key),
        ) or []
        if not existing_rows and signal_mail:
            existing_rows = db_all(
                """
                SELECT * FROM recruitment_candidate_signals
                WHERE user_id=? AND lower(mail_id)=lower(?)
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (user["id"], signal_mail),
            ) or []
        if not existing_rows and signal_phone:
            existing_rows = db_all(
                """
                SELECT * FROM recruitment_candidate_signals
                WHERE user_id=? AND contact_no=?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (user["id"], signal_phone),
            ) or []
        if not existing_rows and signal_name:
            existing_rows = db_all(
                """
                SELECT * FROM recruitment_candidate_signals
                WHERE user_id=? AND lower(candidate_name)=lower(?) AND (
                    lower(current_company)=lower(?) OR lower(target_role)=lower(?)
                )
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (user["id"], signal_name, signal_company or "", signal_role or ""),
            ) or []
        existing = existing_rows[0] if existing_rows else {}
        applications_total = max(int(existing.get("applications_count", 0) or 0), int(applications_count or 0), int(derived_applications or 0))
        interviews_total = max(int(existing.get("interviews_count", 0) or 0), int(interviews_count or 0), int(derived_interviews or 0))
        offers_total = max(int(existing.get("offers_count", 0) or 0), int(offers_count or 0), int(derived_offers or 0))
        issue_flags = infer_issue_flags_from_text(transcript)
        fit = candidate_fit_snapshot(
            total_exp=signal_total_exp,
            relevant_exp=signal_relevant_exp or signal_total_exp,
            response_status="interested" if intent_snapshot["intent"] in {"active", "passive"} else "pending_review",
            process_stage="sourced",
            issue_flags=issue_flags,
        )
        next_move = candidate_next_move(
            job_change_intent=intent_snapshot["intent"],
            applications_count=applications_total,
            interviews_count=interviews_total,
            offers_count=offers_total,
            response_status="interested" if intent_snapshot["intent"] in {"active", "passive"} else "pending_review",
            issue_flags=issue_flags,
            fit_label=fit["label"],
            pending_feedback=False,
        )
        source_summary = clean_text(transcript or f"{signal_name} shared a career intent signal.", 320)

        signal_id = existing.get("id") or new_id("rcs")
        if existing:
            db_exec(
                """
                UPDATE recruitment_candidate_signals
                SET network_post_id=?, row_id=?, candidate_id=?, candidate_name=?, mail_id=?, contact_no=?, target_role=?,
                    current_company=?, current_location=?, preferred_location=?, total_exp=?, relevant_exp=?, notice_period=?,
                    notice_state=?, current_ctc=?, expected_ctc=?, job_change_intent=?, intent_confidence=?, applications_count=?,
                    interviews_count=?, offers_count=?, fit_note=?, next_move=?, source_kind=?, source_summary=?, raw_text=?,
                    source_types=?, updated_at=?
                WHERE id=? AND user_id=?
                """,
                (
                    network_post_id or existing.get("network_post_id", ""),
                    row_id or existing.get("row_id", ""),
                    candidate_id or existing.get("candidate_id", ""),
                    signal_name,
                    signal_mail or existing.get("mail_id", ""),
                    signal_phone or existing.get("contact_no", ""),
                    signal_role or existing.get("target_role", ""),
                    signal_company or existing.get("current_company", ""),
                    signal_location or existing.get("current_location", ""),
                    signal_pref_location or existing.get("preferred_location", ""),
                    signal_total_exp or existing.get("total_exp", 0),
                    signal_relevant_exp or existing.get("relevant_exp", 0),
                    signal_notice or existing.get("notice_period", ""),
                    signal_notice_state or existing.get("notice_state", ""),
                    signal_current_ctc or existing.get("current_ctc", 0),
                    signal_expected_ctc or existing.get("expected_ctc", 0),
                    intent_snapshot["intent"],
                    intent_snapshot["confidence"],
                    applications_total,
                    interviews_total,
                    offers_total,
                    f"{fit['label']} ({fit['score']})",
                    next_move,
                    clean_text(source_kind, 80),
                    source_summary,
                    transcript[:4000],
                    merge_source_types(existing.get("source_types"), source_kind),
                    now_iso(),
                    signal_id,
                    user["id"],
                ),
            )
        else:
            db_exec(
                """
                INSERT INTO recruitment_candidate_signals(
                    id,user_id,signal_key,network_post_id,row_id,candidate_id,candidate_name,mail_id,contact_no,target_role,
                    current_company,current_location,preferred_location,total_exp,relevant_exp,notice_period,notice_state,
                    current_ctc,expected_ctc,job_change_intent,intent_confidence,applications_count,interviews_count,offers_count,
                    fit_note,next_move,source_kind,source_summary,raw_text,source_types,created_at,updated_at
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    signal_id,
                    user["id"],
                    signal_key,
                    network_post_id,
                    row_id,
                    candidate_id,
                    signal_name,
                    signal_mail,
                    signal_phone,
                    signal_role,
                    signal_company,
                    signal_location,
                    signal_pref_location,
                    signal_total_exp,
                    signal_relevant_exp or signal_total_exp,
                    signal_notice,
                    signal_notice_state,
                    signal_current_ctc,
                    signal_expected_ctc,
                    intent_snapshot["intent"],
                    intent_snapshot["confidence"],
                    applications_total,
                    interviews_total,
                    offers_total,
                    f"{fit['label']} ({fit['score']})",
                    next_move,
                    clean_text(source_kind, 80),
                    source_summary,
                    transcript[:4000],
                    merge_source_types([], source_kind),
                    now_iso(),
                    now_iso(),
                ),
            )

        ats_candidate = None
        tracker_row_id = row_id or ""
        if auto_forward_to_ats and intent_snapshot["intent"] in {"active", "passive"}:
            ats_rows = []
            if signal_mail:
                ats_rows = db_all(
                    """
                    SELECT * FROM ats_candidates
                    WHERE user_id=? AND lower(email)=lower(?)
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (user["id"], signal_mail),
                ) or []
            if not ats_rows and signal_name:
                ats_rows = db_all(
                    """
                    SELECT * FROM ats_candidates
                    WHERE user_id=? AND lower(name)=lower(?) AND lower(role)=lower(?)
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (user["id"], signal_name, signal_role),
                ) or []
            ats_id = ats_rows[0]["id"] if ats_rows else new_id("cand")
            fit_score = max(60, fit["score"])
            ai_strength = clean_text(
                f"Network intent {intent_snapshot['label']} | {signal_role} | {signal_location or signal_pref_location or 'location open'} | NP {signal_notice or 'not shared'}",
                220,
            )
            ai_concern = clean_text(", ".join(issue_flags), 220)
            notes = clean_text(
                f"Network signal captured locally. Applications {applications_total}, interviews {interviews_total}, offers {offers_total}. {source_summary}",
                600,
            )
            if ats_rows:
                db_exec(
                    """
                    UPDATE ats_candidates
                    SET name=?, email=?, role=?, experience=?, fit_score=?, status=?, ai_strength=?, ai_concern=?, source=?, notes=?, updated_at=?
                    WHERE id=? AND user_id=?
                    """,
                    (
                        signal_name,
                        signal_mail or ats_rows[0].get("email", ""),
                        signal_role,
                        int(signal_total_exp or ats_rows[0].get("experience", 0) or 0),
                        fit_score,
                        "applied",
                        ai_strength,
                        ai_concern,
                        "network_intent",
                        notes,
                        now_iso(),
                        ats_id,
                        user["id"],
                    ),
                )
            else:
                db_exec(
                    """
                    INSERT INTO ats_candidates(id,user_id,job_id,name,email,role,experience,fit_score,status,ai_strength,ai_concern,source,resume_text,notes,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        ats_id,
                        user["id"],
                        "",
                        signal_name,
                        signal_mail,
                        signal_role,
                        int(signal_total_exp or 0),
                        fit_score,
                        "applied",
                        ai_strength,
                        ai_concern,
                        "network_intent",
                        "",
                        notes,
                        now_iso(),
                        now_iso(),
                    ),
                )
            ats_candidate = {"id": ats_id, "name": signal_name, "role": signal_role}
            tracker_row = find_tracker_row(
                user,
                candidate_id=ats_id,
                mail_id=signal_mail,
                candidate_name=signal_name,
                position=signal_role,
            )
            if tracker_row:
                tracker_row_id = tracker_row["id"]
                db_exec(
                    """
                    UPDATE recruitment_tracker_rows
                    SET candidate_id=?, sourced_from=?, recruiter=?, client_name=?, position=?, candidate_name=?, contact_no=?, mail_id=?,
                        current_company=?, current_location=?, preferred_location=?, total_exp=?, relevant_exp=?, notice_period=?,
                        notice_state=?, current_ctc=?, expected_ctc=?, response_status=?, remarks=?, last_discussion=?, last_contacted_at=?, updated_at=?
                    WHERE id=? AND user_id=?
                    """,
                    (
                        ats_id,
                        "network",
                        default_recruiter_name(user),
                        tracker_row.get("client_name") or company_name,
                        signal_role,
                        signal_name,
                        signal_phone,
                        signal_mail,
                        signal_company,
                        signal_location,
                        signal_pref_location,
                        signal_total_exp,
                        signal_relevant_exp or signal_total_exp,
                        signal_notice,
                        signal_notice_state,
                        signal_current_ctc,
                        signal_expected_ctc,
                        "interested" if intent_snapshot["intent"] in {"active", "passive"} else "pending_review",
                        next_move,
                        source_summary,
                        now_iso(),
                        now_iso(),
                        tracker_row_id,
                        user["id"],
                    ),
                )
            else:
                tracker_row_id = new_id("trk")
                db_exec(
                    """
                    INSERT INTO recruitment_tracker_rows(
                        id,user_id,candidate_id,job_id,sourced_from,process_stage,recruiter,client_name,position,profile_sharing_date,
                        candidate_name,contact_no,mail_id,current_company,current_location,preferred_location,total_exp,relevant_exp,
                        notice_period,notice_state,current_ctc,expected_ctc,client_spoc,response_status,issue_flags,duplicate_status,
                        remarks,last_discussion,ack_mail_sent_at,ack_confirmed_at,last_contacted_at,created_at,updated_at
                    )
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        tracker_row_id,
                        user["id"],
                        ats_id,
                        "",
                        "network",
                        "sourced",
                        default_recruiter_name(user),
                        company_name,
                        signal_role,
                        "",
                        signal_name,
                        signal_phone,
                        signal_mail,
                        signal_company,
                        signal_location,
                        signal_pref_location,
                        signal_total_exp,
                        signal_relevant_exp or signal_total_exp,
                        signal_notice,
                        signal_notice_state,
                        signal_current_ctc,
                        signal_expected_ctc,
                        "",
                        "interested" if intent_snapshot["intent"] in {"active", "passive"} else "pending_review",
                        json.dumps(issue_flags, ensure_ascii=False),
                        "clear",
                        next_move,
                        source_summary,
                        "",
                        "",
                        now_iso(),
                        now_iso(),
                        now_iso(),
                    ),
                )
                append_journey_event(
                    user,
                    tracker_row_id,
                    event_type="network_intent",
                    stage="sourced",
                    response_status="interested" if intent_snapshot["intent"] in {"active", "passive"} else "pending_review",
                    summary=clean_text(f"Network career intent captured for {signal_name}.", 260),
                    details={
                        "target_role": signal_role,
                        "job_change_intent": intent_snapshot["intent"],
                        "applications_count": applications_total,
                        "interviews_count": interviews_total,
                        "offers_count": offers_total,
                    },
                    actor=default_recruiter_name(user),
                )

        return {
            "captured": True,
            "signal_id": signal_id,
            "signal_key": signal_key,
            "candidate_name": signal_name,
            "target_role": signal_role,
            "job_change_intent": intent_snapshot["intent"],
            "intent_confidence": intent_snapshot["confidence"],
            "applications_count": applications_total,
            "interviews_count": interviews_total,
            "offers_count": offers_total,
            "fit": fit,
            "next_move": next_move,
            "ats_candidate": ats_candidate,
            "tracker_row_id": tracker_row_id,
            "source_summary": source_summary,
        }

    def sync_recruitment_tracker(user: Dict[str, Any], jobs: List[Dict[str, Any]], candidates: List[Dict[str, Any]]) -> None:
        jobs_by_id = {row["id"]: row for row in jobs}
        recruiter_name = default_recruiter_name(user)
        duplicate_counts: Dict[Any, int] = {}
        for row in candidates:
            role_label = row.get("role") or jobs_by_id.get(row.get("job_id", ""), {}).get("title") or ""
            key = (str(row.get("name", "")).strip().lower(), str(role_label).strip().lower())
            duplicate_counts[key] = duplicate_counts.get(key, 0) + 1

        for row in candidates:
            role_label = row.get("role") or jobs_by_id.get(row.get("job_id", ""), {}).get("title") or "Open role"
            key = (str(row.get("name", "")).strip().lower(), str(role_label).strip().lower())
            duplicate_status = "duplicate" if duplicate_counts.get(key, 0) > 1 else "clear"
            existing = db_all(
                """
                SELECT * FROM recruitment_tracker_rows
                WHERE user_id=? AND candidate_id=?
                LIMIT 1
                """,
                (user["id"], row["id"]),
            ) or []
            if existing:
                tracker = existing[0]
                issue_flags = parse_issue_flags(tracker.get("issue_flags"))
                if duplicate_status == "duplicate" and "duplicate" not in issue_flags:
                    issue_flags.append("duplicate")
                db_exec(
                    """
                    UPDATE recruitment_tracker_rows
                    SET job_id=?,
                        sourced_from=?,
                        process_stage=?,
                        recruiter=?,
                        client_name=?,
                        position=?,
                        candidate_name=?,
                        mail_id=?,
                        total_exp=?,
                        duplicate_status=?,
                        issue_flags=?,
                        updated_at=?
                    WHERE id=? AND user_id=?
                    """,
                    (
                        row.get("job_id", ""),
                        tracker.get("sourced_from") or row.get("source", "manual"),
                        tracker.get("process_stage") or row.get("status", "applied"),
                        tracker.get("recruiter") or recruiter_name,
                        tracker.get("client_name") or company_name,
                        tracker.get("position") or role_label,
                        tracker.get("candidate_name") or row.get("name", "Candidate"),
                        tracker.get("mail_id") or row.get("email", ""),
                        tracker.get("total_exp") or row.get("experience", 0),
                        duplicate_status,
                        json.dumps(issue_flags, ensure_ascii=False),
                        now_iso(),
                        tracker["id"],
                        user["id"],
                    ),
                )
                continue

            issue_flags = ["duplicate"] if duplicate_status == "duplicate" else []
            db_exec(
                """
                INSERT INTO recruitment_tracker_rows(
                    id,user_id,candidate_id,job_id,sourced_from,process_stage,recruiter,client_name,position,
                    profile_sharing_date,candidate_name,contact_no,mail_id,current_company,current_location,
                    preferred_location,total_exp,relevant_exp,notice_period,notice_state,current_ctc,expected_ctc,
                    client_spoc,response_status,issue_flags,duplicate_status,remarks,last_discussion,ack_mail_sent_at,
                    ack_confirmed_at,last_contacted_at,created_at,updated_at
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    new_id("trk"),
                    user["id"],
                    row["id"],
                    row.get("job_id", ""),
                    row.get("source", "manual"),
                    row.get("status", "applied"),
                    recruiter_name,
                    company_name,
                    role_label,
                    "",
                    row.get("name", "Candidate"),
                    "",
                    row.get("email", ""),
                    "",
                    "",
                    jobs_by_id.get(row.get("job_id", ""), {}).get("location", ""),
                    row.get("experience", 0),
                    0,
                    "",
                    "",
                    0,
                    0,
                    "",
                    "pending_review",
                    json.dumps(issue_flags, ensure_ascii=False),
                    duplicate_status,
                    clean_text(row.get("notes", ""), 500),
                    clean_text(row.get("ai_strength", ""), 500),
                    "",
                    "",
                    "",
                    now_iso(),
                    now_iso(),
                ),
            )

    def tracker_summary_payload(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        now = datetime.now()
        two_hours_ago = now - timedelta(hours=2)
        today = now.date().isoformat()
        issue_counts = {issue: 0 for issue in TRACKER_ISSUE_OPTIONS}
        totals = {
            "rows": len(rows),
            "submitted": 0,
            "drafts": 0,
            "duplicates": 0,
            "ack_sent": 0,
            "ack_confirmed": 0,
            "interested": 0,
            "no_response": 0,
            "screen_rejected": 0,
            "follow_ups_due": 0,
        }
        dsr = {"profiles_processed": 0, "interested": 0, "no_response": 0, "duplicates": 0, "screen_rejected": 0}
        hsr = {"profiles_processed": 0, "submitted": 0, "ack_sent": 0, "interested": 0, "duplicates": 0}

        for row in rows:
            issue_flags = parse_issue_flags(row.get("issue_flags"))
            updated_at = parse_iso(row.get("updated_at", "") or row.get("created_at", ""))
            profile_date = str(row.get("profile_sharing_date", "") or "")
            response_status = str(row.get("response_status", "")).lower()
            process_stage = str(row.get("process_stage", "")).lower()
            submission_state = str(row.get("submission_state", "")).lower() or "draft"
            follow_up_due = parse_iso(row.get("follow_up_due_at", ""))

            if row.get("duplicate_status") == "duplicate" and "duplicate" not in issue_flags:
                issue_flags.append("duplicate")
            for issue in issue_flags:
                if issue in issue_counts:
                    issue_counts[issue] += 1

            if submission_state == "draft":
                totals["drafts"] += 1
            if profile_date.startswith(today) or submission_state == "confirmed" or process_stage in {"submitted", "screening", "interview", "offer", "hired", "profile_shared"}:
                totals["submitted"] += 1
            if row.get("duplicate_status") == "duplicate":
                totals["duplicates"] += 1
            if row.get("ack_mail_sent_at"):
                totals["ack_sent"] += 1
            if row.get("ack_confirmed_at"):
                totals["ack_confirmed"] += 1
            if follow_up_due and follow_up_due <= now:
                totals["follow_ups_due"] += 1
            if response_status in {"interested", "available", "shared", "ack_confirmed"}:
                totals["interested"] += 1
            if "no_response" in issue_flags or response_status == "no_response":
                totals["no_response"] += 1
            if "screen_rejected" in issue_flags or response_status == "screen_rejected":
                totals["screen_rejected"] += 1

            if updated_at and updated_at.date().isoformat() == today:
                dsr["profiles_processed"] += 1
                if response_status in {"interested", "available", "shared", "ack_confirmed"}:
                    dsr["interested"] += 1
                if "no_response" in issue_flags or response_status == "no_response":
                    dsr["no_response"] += 1
                if row.get("duplicate_status") == "duplicate":
                    dsr["duplicates"] += 1
                if "screen_rejected" in issue_flags or response_status == "screen_rejected":
                    dsr["screen_rejected"] += 1

            if updated_at and updated_at >= two_hours_ago:
                hsr["profiles_processed"] += 1
                if profile_date:
                    hsr["submitted"] += 1
                if row.get("ack_mail_sent_at"):
                    hsr["ack_sent"] += 1
                if response_status in {"interested", "available", "shared", "ack_confirmed"}:
                    hsr["interested"] += 1
                if row.get("duplicate_status") == "duplicate":
                    hsr["duplicates"] += 1

        return {
            "headline": "Recruiter tracker is now the working memory for sourcing, submissions, objections, and acknowledgment flow.",
            "totals": totals,
            "issue_counts": issue_counts,
            "dsr": dsr,
            "hsr": hsr,
        }

    def tracker_rows_for_console(
        user: Dict[str, Any],
        *,
        search: str = "",
        stage: str = "",
        detail: str = "guided",
        allow_full: bool = False,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        rows = db_all(
            """
            SELECT *
            FROM recruitment_tracker_rows
            WHERE user_id=?
            ORDER BY updated_at DESC, created_at DESC
            """,
            (user["id"],),
        ) or []
        search_lower = (search or "").strip().lower()
        stage_lower = (stage or "").strip().lower()
        filters = dict(filters or {})
        if search_lower:
            filters.setdefault("search", search)
        if stage_lower:
            filters.setdefault("stage", stage)
        visible = []
        for row in rows:
            if not tracker_row_matches_filters(row, filters):
                continue
            issue_flags = parse_issue_flags(row.get("issue_flags"))
            item = {
                "id": row["id"],
                "candidate_id": row.get("candidate_id", ""),
                "job_id": row.get("job_id", ""),
                "candidate_name": row.get("candidate_name", "Candidate"),
                "position": row.get("position", "Open role"),
                "client_name": row.get("client_name", company_name),
                "recruiter": row.get("recruiter", ""),
                "sourced_from": row.get("sourced_from", "manual"),
                "process_stage": row.get("process_stage", "sourced"),
                "response_status": row.get("response_status", "pending_review"),
                "issue_flags": issue_flags,
                "duplicate_status": row.get("duplicate_status", "clear"),
                "submission_state": row.get("submission_state", "draft") or "draft",
                "total_exp": row.get("total_exp", 0),
                "relevant_exp": row.get("relevant_exp", 0),
                "notice_period": row.get("notice_period", ""),
                "notice_state": row.get("notice_state", ""),
                "current_ctc": row.get("current_ctc", 0),
                "expected_ctc": row.get("expected_ctc", 0),
                "current_location": row.get("current_location", ""),
                "preferred_location": row.get("preferred_location", ""),
                "profile_sharing_date": row.get("profile_sharing_date", ""),
                "client_spoc": row.get("client_spoc", ""),
                "remarks": row.get("remarks", ""),
                "last_discussion": row.get("last_discussion", ""),
                "ack_mail_sent_at": row.get("ack_mail_sent_at", ""),
                "ack_confirmed_at": row.get("ack_confirmed_at", ""),
                "resume_document_id": row.get("resume_document_id", ""),
                "resume_file_name": row.get("resume_file_name", ""),
                "skill_snapshot": row.get("skill_snapshot", ""),
                "role_scope": row.get("role_scope", ""),
                "follow_up_due_at": row.get("follow_up_due_at", ""),
                "updated_at": row.get("updated_at", ""),
            }
            if detail != "minimal":
                item["summary"] = (
                    row.get("last_discussion")
                    or row.get("remarks")
                    or row.get("role_scope")
                    or row.get("response_status")
                    or "Tracker row ready for recruiter action."
                )[:280]
            item["mail_ready"] = bool(row.get("mail_id"))
            if detail == "full" and allow_full:
                item["contact_no"] = row.get("contact_no", "")
                item["mail_id"] = row.get("mail_id", "")
                item["current_company"] = row.get("current_company", "")
            visible.append(item)
        return visible

    def upsert_conversation_capture(user: Dict[str, Any], req: RecruitmentConversationCaptureReq) -> Dict[str, Any]:
        recruiter_name = default_recruiter_name(user)
        parsed = parse_recruiter_conversation(req, recruiter_name)
        existing = find_tracker_row(
            user,
            row_id=req.row_id,
            candidate_id=req.candidate_id,
            mail_id=parsed.get("mail_id", ""),
            candidate_name=parsed.get("candidate_name", ""),
            position=parsed.get("position", ""),
        )

        row_id = existing["id"] if existing else new_id("trk")
        merged = dict(existing or {})
        merged.update(
            {
                "candidate_id": req.candidate_id or merged.get("candidate_id", ""),
                "job_id": req.job_id or merged.get("job_id", ""),
                "sourced_from": parsed.get("sourced_from") or merged.get("sourced_from", "manual"),
                "process_stage": parsed.get("process_stage") or merged.get("process_stage", "sourced"),
                "recruiter": parsed.get("recruiter") or merged.get("recruiter", recruiter_name),
                "client_name": parsed.get("client_name") or merged.get("client_name", company_name),
                "position": parsed.get("position") or merged.get("position", "Open role"),
                "profile_sharing_date": merged.get("profile_sharing_date", ""),
                "candidate_name": parsed.get("candidate_name") or merged.get("candidate_name", "Candidate"),
                "contact_no": parsed.get("contact_no") or merged.get("contact_no", ""),
                "mail_id": parsed.get("mail_id") or merged.get("mail_id", ""),
                "current_company": parsed.get("current_company") or merged.get("current_company", ""),
                "current_location": parsed.get("current_location") or merged.get("current_location", ""),
                "preferred_location": parsed.get("preferred_location") or merged.get("preferred_location", ""),
                "total_exp": parsed.get("total_exp") or merged.get("total_exp", 0),
                "relevant_exp": parsed.get("relevant_exp") or merged.get("relevant_exp", 0),
                "notice_period": parsed.get("notice_period") or merged.get("notice_period", ""),
                "notice_state": parsed.get("notice_state") or merged.get("notice_state", ""),
                "current_ctc": parsed.get("current_ctc") or merged.get("current_ctc", 0),
                "expected_ctc": parsed.get("expected_ctc") or merged.get("expected_ctc", 0),
                "client_spoc": parsed.get("client_spoc") or merged.get("client_spoc", ""),
                "response_status": parsed.get("response_status") or merged.get("response_status", "pending_review"),
                "duplicate_status": merged.get("duplicate_status", "clear"),
                "remarks": parsed.get("remarks") or merged.get("remarks", ""),
                "last_discussion": parsed.get("last_discussion") or merged.get("last_discussion", ""),
                "ack_mail_sent_at": merged.get("ack_mail_sent_at", ""),
                "ack_confirmed_at": merged.get("ack_confirmed_at", ""),
                "submission_state": merged.get("submission_state", "draft"),
                "resume_document_id": merged.get("resume_document_id", ""),
                "resume_file_name": merged.get("resume_file_name", ""),
                "resume_text": merged.get("resume_text", ""),
                "skill_snapshot": parsed.get("skill_snapshot") or merged.get("skill_snapshot", ""),
                "role_scope": parsed.get("role_scope") or merged.get("role_scope", ""),
                "follow_up_due_at": merged.get("follow_up_due_at", ""),
                "last_contacted_at": now_iso(),
                "created_at": merged.get("created_at", now_iso()),
                "updated_at": now_iso(),
            }
        )
        if merged["response_status"] == "ack_confirmed":
            if not merged.get("ack_mail_sent_at"):
                merged["ack_mail_sent_at"] = now_iso()
            if not merged.get("ack_confirmed_at"):
                merged["ack_confirmed_at"] = now_iso()
            if not merged.get("profile_sharing_date"):
                merged["profile_sharing_date"] = now_iso()
            if merged.get("process_stage") in {"", "sourced"}:
                merged["process_stage"] = "profile_shared"
        merged["submission_state"] = normalized_submission_state(
            existing_state=merged.get("submission_state", "draft"),
            candidate_confirmed=merged.get("response_status") == "ack_confirmed",
            ack_sent_at=merged.get("ack_mail_sent_at", ""),
            ack_confirmed_at=merged.get("ack_confirmed_at", ""),
        )
        merged_issue_flags = sorted(set(parse_issue_flags(merged.get("issue_flags")) + parsed.get("issue_flags", [])))
        if merged.get("duplicate_status") == "duplicate" and "duplicate" not in merged_issue_flags:
            merged_issue_flags.append("duplicate")
        merged["issue_flags"] = merged_issue_flags
        merged["follow_up_due_at"] = derive_follow_up_due(
            process_stage=merged.get("process_stage", ""),
            response_status=merged.get("response_status", ""),
            submission_state=merged.get("submission_state", "draft"),
        )

        if existing:
            db_exec(
                """
                UPDATE recruitment_tracker_rows
                SET candidate_id=?, job_id=?, sourced_from=?, process_stage=?, recruiter=?, client_name=?, position=?,
                    candidate_name=?, contact_no=?, mail_id=?, current_company=?, current_location=?, preferred_location=?,
                    total_exp=?, relevant_exp=?, notice_period=?, notice_state=?, current_ctc=?, expected_ctc=?, client_spoc=?,
                    response_status=?, issue_flags=?, duplicate_status=?, remarks=?, last_discussion=?, ack_mail_sent_at=?,
                    ack_confirmed_at=?, submission_state=?, resume_document_id=?, resume_file_name=?, resume_text=?, skill_snapshot=?,
                    role_scope=?, follow_up_due_at=?, last_contacted_at=?, profile_sharing_date=?, updated_at=?
                WHERE id=? AND user_id=?
                """,
                (
                    merged["candidate_id"],
                    merged["job_id"],
                    merged["sourced_from"],
                    merged["process_stage"],
                    merged["recruiter"],
                    merged["client_name"],
                    merged["position"],
                    merged["candidate_name"],
                    merged["contact_no"],
                    merged["mail_id"],
                    merged["current_company"],
                    merged["current_location"],
                    merged["preferred_location"],
                    merged["total_exp"],
                    merged["relevant_exp"],
                    merged["notice_period"],
                    merged["notice_state"],
                    merged["current_ctc"],
                    merged["expected_ctc"],
                    merged["client_spoc"],
                    merged["response_status"],
                    json.dumps(merged_issue_flags, ensure_ascii=False),
                    merged["duplicate_status"],
                    merged["remarks"],
                    merged["last_discussion"],
                    merged["ack_mail_sent_at"],
                    merged["ack_confirmed_at"],
                    merged["submission_state"],
                    merged["resume_document_id"],
                    merged["resume_file_name"],
                    merged["resume_text"],
                    merged["skill_snapshot"],
                    merged["role_scope"],
                    merged["follow_up_due_at"],
                    merged["last_contacted_at"],
                    merged["profile_sharing_date"],
                    merged["updated_at"],
                    row_id,
                    user["id"],
                ),
            )
        else:
            db_exec(
                """
                INSERT INTO recruitment_tracker_rows(
                    id,user_id,candidate_id,job_id,sourced_from,process_stage,recruiter,client_name,position,profile_sharing_date,
                    candidate_name,contact_no,mail_id,current_company,current_location,preferred_location,total_exp,relevant_exp,
                    notice_period,notice_state,current_ctc,expected_ctc,client_spoc,response_status,issue_flags,duplicate_status,
                    remarks,last_discussion,ack_mail_sent_at,ack_confirmed_at,submission_state,resume_document_id,resume_file_name,
                    resume_text,skill_snapshot,role_scope,follow_up_due_at,last_contacted_at,created_at,updated_at
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    row_id,
                    user["id"],
                    merged["candidate_id"],
                    merged["job_id"],
                    merged["sourced_from"],
                    merged["process_stage"],
                    merged["recruiter"],
                    merged["client_name"],
                    merged["position"],
                    merged["profile_sharing_date"],
                    merged["candidate_name"],
                    merged["contact_no"],
                    merged["mail_id"],
                    merged["current_company"],
                    merged["current_location"],
                    merged["preferred_location"],
                    merged["total_exp"],
                    merged["relevant_exp"],
                    merged["notice_period"],
                    merged["notice_state"],
                    merged["current_ctc"],
                    merged["expected_ctc"],
                    merged["client_spoc"],
                    merged["response_status"],
                    json.dumps(merged_issue_flags, ensure_ascii=False),
                    merged["duplicate_status"],
                    merged["remarks"],
                    merged["last_discussion"],
                    merged["ack_mail_sent_at"],
                    merged["ack_confirmed_at"],
                    merged["submission_state"],
                    merged["resume_document_id"],
                    merged["resume_file_name"],
                    merged["resume_text"],
                    merged["skill_snapshot"],
                    merged["role_scope"],
                    merged["follow_up_due_at"],
                    merged["last_contacted_at"],
                    merged["created_at"],
                    merged["updated_at"],
                ),
            )

        merged["id"] = row_id
        record_discussion_log(
            user,
            merged,
            event_type="conversation_capture",
            transcript=parsed["transcript"],
            parsed=parsed,
            summary=parsed["summary"],
        )
        append_journey_event(
            user,
            row_id,
            event_type="conversation_capture",
            stage=merged["process_stage"],
            response_status=merged["response_status"],
            summary=parsed["summary"],
            details={
                "issue_flags": merged_issue_flags,
                "notice_period": merged["notice_period"],
                "current_ctc": merged["current_ctc"],
                "expected_ctc": merged["expected_ctc"],
                "submission_state": merged.get("submission_state", "draft"),
                "skill_snapshot": merged.get("skill_snapshot", ""),
                "row_snapshot": recruitment_row_snapshot(merged),
            },
            actor=merged["recruiter"],
        )
        if merged.get("candidate_id"):
            db_exec(
                "UPDATE ats_candidates SET status=?, updated_at=? WHERE id=? AND user_id=?",
                (tracker_stage_for_ats(merged["process_stage"], merged["response_status"]), now_iso(), merged["candidate_id"], user["id"]),
            )
        signal = upsert_candidate_signal(
            user,
            content=parsed.get("transcript", req.transcript),
            candidate_name=merged.get("candidate_name", ""),
            mail_id=merged.get("mail_id", ""),
            contact_no=merged.get("contact_no", ""),
            target_role=merged.get("position", ""),
            current_company=merged.get("current_company", ""),
            current_location=merged.get("current_location", ""),
            preferred_location=merged.get("preferred_location", ""),
            total_exp=merged.get("total_exp", 0),
            relevant_exp=merged.get("relevant_exp", 0),
            notice_period=merged.get("notice_period", ""),
            notice_state=merged.get("notice_state", ""),
            current_ctc=merged.get("current_ctc", 0),
            expected_ctc=merged.get("expected_ctc", 0),
            source_kind="recruiter_conversation",
            row_id=row_id,
            candidate_id=merged.get("candidate_id", ""),
            auto_forward_to_ats=not bool(merged.get("candidate_id")),
        )
        reporting = refresh_recruitment_reporting(user)
        return {"row_id": row_id, "row": merged, "parsed": parsed, "signal": signal, "reporting": reporting}

    def tracker_row_summary(row: Dict[str, Any]) -> str:
        parts = [
            clean_text(row.get("candidate_name", ""), 120),
            clean_text(row.get("position", ""), 120),
            clean_text((row.get("submission_state", "draft") or "draft").replace("_", " "), 60),
        ]
        if row.get("total_exp"):
            parts.append(f"{row['total_exp']} yrs")
        if row.get("notice_period"):
            parts.append(f"NP {row['notice_period']}")
        if row.get("skill_snapshot"):
            parts.append(f"skills {clean_text(row['skill_snapshot'], 120)}")
        return " | ".join([part for part in parts if part])[:320]

    def record_discussion_log(
        user: Dict[str, Any],
        row: Dict[str, Any],
        *,
        event_type: str,
        transcript: str,
        parsed: Optional[Dict[str, Any]] = None,
        summary: str = "",
    ) -> None:
        snapshot = recruitment_row_snapshot(row)
        db_exec(
            """
            INSERT INTO recruitment_conversation_logs(
                id,user_id,row_id,transcript,parsed_json,event_type,candidate_name,position,client_name,recruiter,
                mail_id,contact_no,total_exp,relevant_exp,notice_period,current_ctc,expected_ctc,process_stage,
                response_status,submission_state,discussion_summary,created_at
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                new_id("rcl"),
                user["id"],
                row.get("id", ""),
                clean_multiline(transcript, 4000),
                json.dumps(parsed or {}, ensure_ascii=False)[:4000],
                clean_text(event_type, 80),
                snapshot["candidate_name"],
                snapshot["position"],
                snapshot["client_name"],
                snapshot["recruiter"],
                snapshot["mail_id"],
                snapshot["contact_no"],
                snapshot["total_exp"],
                snapshot["relevant_exp"],
                snapshot["notice_period"],
                snapshot["current_ctc"],
                snapshot["expected_ctc"],
                snapshot["process_stage"],
                snapshot["response_status"],
                snapshot["submission_state"],
                clean_text(summary or transcript or tracker_row_summary(row), 500),
                now_iso(),
            ),
        )

    def tracker_export_headers() -> List[str]:
        return [
            "Sr. No.",
            "Date",
            "Recruiter",
            "Client",
            "Position",
            "Candidate Name",
            "Contact No",
            "Email ID",
            "Current Company",
            "Current Location",
            "Preferred Location",
            "Total Exp",
            "Relevant Exp",
            "Notice Period",
            "Current CTC",
            "Expected CTC",
            "Skills",
            "Roles And Responsibilities",
            "Source",
            "Process Stage",
            "Response Status",
            "Submission State",
            "Follow Up Due",
            "Client SPOC",
            "Remarks",
        ]

    def _tsv_cell(value: Any) -> str:
        """Sanitise a value for safe inclusion in a TSV cell (no tabs or newlines)."""
        return str(value or "").replace("\r\n", " ").replace("\r", " ").replace("\n", " ").replace("\t", " ")

    def tracker_export_lines(rows: List[Dict[str, Any]]) -> List[str]:
        lines = ["\t".join(tracker_export_headers())]
        for index, row in enumerate(rows, start=1):
            lines.append(
                "\t".join(
                    [
                        str(index),
                        str(row.get("updated_at", "") or row.get("profile_sharing_date", ""))[:19],
                        _tsv_cell(row.get("recruiter", "")),
                        _tsv_cell(row.get("client_name", "")),
                        _tsv_cell(row.get("position", "")),
                        _tsv_cell(row.get("candidate_name", "")),
                        _tsv_cell(row.get("contact_no", "")),
                        _tsv_cell(row.get("mail_id", "")),
                        _tsv_cell(row.get("current_company", "")),
                        _tsv_cell(row.get("current_location", "")),
                        _tsv_cell(row.get("preferred_location", "")),
                        _tsv_cell(row.get("total_exp", "")),
                        _tsv_cell(row.get("relevant_exp", "")),
                        _tsv_cell(row.get("notice_period", "")),
                        _tsv_cell(row.get("current_ctc", "")),
                        _tsv_cell(row.get("expected_ctc", "")),
                        _tsv_cell(row.get("skill_snapshot", "")),
                        _tsv_cell(row.get("role_scope", "")),
                        _tsv_cell(row.get("sourced_from", "")),
                        _tsv_cell(row.get("process_stage", "")),
                        _tsv_cell(row.get("response_status", "")),
                        _tsv_cell(row.get("submission_state", "")),
                        _tsv_cell(row.get("follow_up_due_at", "")),
                        _tsv_cell(row.get("client_spoc", "")),
                        _tsv_cell(row.get("remarks", "")),
                    ]
                )
            )
        return lines

    def _csv_cell(value: Any) -> str:
        """Wrap a value in double-quotes for RFC 4180 CSV, escaping internal quotes."""
        text = str(value or "").replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
        if "," in text or '"' in text:
            text = '"' + text.replace('"', '""') + '"'
        return text

    def tracker_export_csv_lines(rows: List[Dict[str, Any]]) -> List[str]:
        """Return CSV (comma-separated) lines for the same tracker data as the TSV export."""
        lines = [",".join(_csv_cell(h) for h in tracker_export_headers())]
        for index, row in enumerate(rows, start=1):
            lines.append(
                ",".join(
                    [
                        str(index),
                        _csv_cell(str(row.get("updated_at", "") or row.get("profile_sharing_date", ""))[:19]),
                        _csv_cell(row.get("recruiter", "")),
                        _csv_cell(row.get("client_name", "")),
                        _csv_cell(row.get("position", "")),
                        _csv_cell(row.get("candidate_name", "")),
                        _csv_cell(row.get("contact_no", "")),
                        _csv_cell(row.get("mail_id", "")),
                        _csv_cell(row.get("current_company", "")),
                        _csv_cell(row.get("current_location", "")),
                        _csv_cell(row.get("preferred_location", "")),
                        _csv_cell(row.get("total_exp", "")),
                        _csv_cell(row.get("relevant_exp", "")),
                        _csv_cell(row.get("notice_period", "")),
                        _csv_cell(row.get("current_ctc", "")),
                        _csv_cell(row.get("expected_ctc", "")),
                        _csv_cell(row.get("skill_snapshot", "")),
                        _csv_cell(row.get("role_scope", "")),
                        _csv_cell(row.get("sourced_from", "")),
                        _csv_cell(row.get("process_stage", "")),
                        _csv_cell(row.get("response_status", "")),
                        _csv_cell(row.get("submission_state", "")),
                        _csv_cell(row.get("follow_up_due_at", "")),
                        _csv_cell(row.get("client_spoc", "")),
                        _csv_cell(row.get("remarks", "")),
                    ]
                )
            )
        return lines

    def history_discussion_payload(
        user: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
        *,
        limit: int = 30,
    ) -> Dict[str, Any]:
        filters = filters or {}
        logs = db_all(
            """
            SELECT *
            FROM recruitment_conversation_logs
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT 400
            """,
            (user["id"],),
        ) or []
        items: List[Dict[str, Any]] = []
        for log in logs:
            pseudo_row = {
                "id": log.get("row_id", ""),
                "candidate_name": log.get("candidate_name", ""),
                "position": log.get("position", ""),
                "client_name": log.get("client_name", ""),
                "recruiter": log.get("recruiter", ""),
                "mail_id": log.get("mail_id", ""),
                "contact_no": log.get("contact_no", ""),
                "total_exp": log.get("total_exp", 0),
                "relevant_exp": log.get("relevant_exp", 0),
                "notice_period": log.get("notice_period", ""),
                "current_ctc": log.get("current_ctc", 0),
                "expected_ctc": log.get("expected_ctc", 0),
                "process_stage": log.get("process_stage", ""),
                "response_status": log.get("response_status", ""),
                "submission_state": log.get("submission_state", ""),
                "updated_at": log.get("created_at", ""),
                "created_at": log.get("created_at", ""),
                "remarks": log.get("discussion_summary", ""),
                "last_discussion": log.get("transcript", ""),
            }
            if not tracker_row_matches_filters(pseudo_row, filters):
                continue
            parsed = parse_json_blob(log.get("parsed_json"), {})
            items.append(
                {
                    "id": log.get("id", ""),
                    "row_id": log.get("row_id", ""),
                    "event_type": log.get("event_type", "conversation"),
                    "candidate_name": log.get("candidate_name", "Candidate"),
                    "position": log.get("position", "Open role"),
                    "client_name": log.get("client_name", company_name),
                    "recruiter": log.get("recruiter", ""),
                    "summary": clean_text(log.get("discussion_summary", "") or parsed.get("summary", "") or log.get("transcript", ""), 280),
                    "transcript": clean_multiline(log.get("transcript", ""), 900),
                    "process_stage": log.get("process_stage", ""),
                    "response_status": log.get("response_status", ""),
                    "submission_state": log.get("submission_state", "") or "draft",
                    "created_at": log.get("created_at", ""),
                }
            )
            if len(items) >= limit:
                break
        return {
            "count": len(items),
            "items": items,
        }

    def report_snapshots_payload(
        user: Dict[str, Any],
        *,
        kind: str = "",
        limit: int = 20,
    ) -> Dict[str, Any]:
        rows = db_all(
            """
            SELECT *
            FROM recruitment_report_snapshots
            WHERE user_id=?
            ORDER BY window_start DESC, updated_at DESC
            LIMIT ?
            """,
            (user["id"], limit),
        ) or []
        if kind:
            rows = [row for row in rows if clean_text(row.get("report_kind", ""), 20).lower() == clean_text(kind, 20).lower()]
        snapshots = [
            {
                "id": row.get("id", ""),
                "kind": row.get("report_kind", ""),
                "window_key": row.get("window_key", ""),
                "window_label": row.get("window_label", ""),
                "headline": row.get("headline", ""),
                "summary": row.get("summary", ""),
                "row_count": int(row.get("row_count", 0) or 0),
                "updated_at": row.get("updated_at", ""),
            }
            for row in rows
        ]
        return {"count": len(snapshots), "items": snapshots}

    def vault_fingerprint(user: Dict[str, Any]) -> str:
        raw = f"{user.get('id', '')}|{clean_text(user.get('email', ''), 200)}|{company_name}|techbuzz-recruitment-vault-v1"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def linked_recruitment_document_ids(user_id: str) -> List[str]:
        rows = db_all(
            """
            SELECT DISTINCT resume_document_id
            FROM recruitment_tracker_rows
            WHERE user_id=? AND resume_document_id != ''
            """,
            (user_id,),
        ) or []
        return [row.get("resume_document_id", "") for row in rows if row.get("resume_document_id")]

    def linked_recruitment_documents(user_id: str) -> List[Dict[str, Any]]:
        doc_ids = linked_recruitment_document_ids(user_id)
        if not doc_ids:
            return []
        placeholders = ",".join("?" for _ in doc_ids)
        return db_all(
            f"SELECT * FROM documents WHERE user_id=? AND id IN ({placeholders}) ORDER BY created_at DESC",
            (user_id, *doc_ids),
        ) or []

    def recruitment_operational_counts(user_id: str) -> Dict[str, Any]:
        def count_for(table: str) -> int:
            row = db_all(f"SELECT COUNT(*) AS count FROM {table} WHERE user_id=?", (user_id,)) or []
            return int((row[0] or {}).get("count", 0) or 0) if row else 0

        tables = {
            "tracker_rows": count_for("recruitment_tracker_rows"),
            "conversation_logs": count_for("recruitment_conversation_logs"),
            "journey_events": count_for("recruitment_journey_events"),
            "interview_events": count_for("recruitment_interview_events"),
            "report_snapshots": count_for("recruitment_report_snapshots"),
            "candidate_signals": count_for("recruitment_candidate_signals"),
            "action_center_events": count_for("action_center_events"),
        }
        document_count = len(linked_recruitment_documents(user_id))
        return {
            "tables": tables,
            "documents": document_count,
            "records_total": sum(tables.values()),
        }

    def ensure_vault_registry(user: Dict[str, Any]) -> Dict[str, Any]:
        existing = db_all("SELECT * FROM recruitment_vault_registry WHERE user_id=? LIMIT 1", (user["id"],)) or []
        if existing:
            return existing[0]
        record = {
            "user_id": user["id"],
            "vault_fingerprint": vault_fingerprint(user),
            "local_generation": 0,
            "server_generation": 0,
            "operational_status": "active",
            "local_record_count": 0,
            "local_document_count": 0,
            "last_local_sync_at": "",
            "last_server_sync_at": "",
            "last_archive_id": "",
            "last_archive_hash": "",
            "last_archive_summary": "",
            "last_imported_at": "",
            "local_cache_cleared_at": "",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        db_exec(
            """
            INSERT INTO recruitment_vault_registry(
                user_id,vault_fingerprint,local_generation,server_generation,operational_status,
                local_record_count,local_document_count,last_local_sync_at,last_server_sync_at,
                last_archive_id,last_archive_hash,last_archive_summary,last_imported_at,local_cache_cleared_at,
                created_at,updated_at
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                record["user_id"],
                record["vault_fingerprint"],
                record["local_generation"],
                record["server_generation"],
                record["operational_status"],
                record["local_record_count"],
                record["local_document_count"],
                record["last_local_sync_at"],
                record["last_server_sync_at"],
                record["last_archive_id"],
                record["last_archive_hash"],
                record["last_archive_summary"],
                record["last_imported_at"],
                record["local_cache_cleared_at"],
                record["created_at"],
                record["updated_at"],
            ),
        )
        return record

    def sync_recruitment_vault_registry(
        user: Dict[str, Any],
        *,
        bump_local: bool = False,
        status_override: Optional[str] = None,
        archive: Optional[Dict[str, Any]] = None,
        imported_at: str = "",
        cleared_at: str = "",
    ) -> Dict[str, Any]:
        registry = ensure_vault_registry(user)
        counts = recruitment_operational_counts(user["id"])
        local_generation = int(registry.get("local_generation", 0) or 0) + (1 if bump_local else 0)
        server_generation = int(registry.get("server_generation", 0) or 0) + (1 if archive else 0)
        operational_status = status_override or registry.get("operational_status") or ("active" if counts["records_total"] or counts["documents"] else "cleared")
        last_local_sync_at = now_iso() if bump_local or counts["records_total"] or counts["documents"] else (registry.get("last_local_sync_at") or "")
        last_server_sync_at = archive.get("created_at", "") if archive else (registry.get("last_server_sync_at") or "")
        db_exec(
            """
            UPDATE recruitment_vault_registry
            SET vault_fingerprint=?, local_generation=?, server_generation=?, operational_status=?,
                local_record_count=?, local_document_count=?, last_local_sync_at=?, last_server_sync_at=?,
                last_archive_id=?, last_archive_hash=?, last_archive_summary=?, last_imported_at=?,
                local_cache_cleared_at=?, updated_at=?
            WHERE user_id=?
            """,
            (
                vault_fingerprint(user),
                local_generation,
                server_generation,
                operational_status,
                counts["records_total"],
                counts["documents"],
                last_local_sync_at,
                last_server_sync_at,
                (archive or {}).get("id", registry.get("last_archive_id", "")),
                (archive or {}).get("archive_hash", registry.get("last_archive_hash", "")),
                (archive or {}).get("summary", registry.get("last_archive_summary", "")),
                imported_at or registry.get("last_imported_at", ""),
                cleared_at or registry.get("local_cache_cleared_at", ""),
                now_iso(),
                user["id"],
            ),
        )
        rows = db_all("SELECT * FROM recruitment_vault_registry WHERE user_id=? LIMIT 1", (user["id"],)) or []
        return rows[0] if rows else ensure_vault_registry(user)

    def vault_rows_payload(user_id: str) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "recruitment_tracker_rows": db_all("SELECT * FROM recruitment_tracker_rows WHERE user_id=? ORDER BY updated_at DESC, created_at DESC", (user_id,)) or [],
            "recruitment_conversation_logs": db_all("SELECT * FROM recruitment_conversation_logs WHERE user_id=? ORDER BY created_at DESC", (user_id,)) or [],
            "recruitment_journey_events": db_all("SELECT * FROM recruitment_journey_events WHERE user_id=? ORDER BY created_at DESC", (user_id,)) or [],
            "recruitment_interview_events": db_all("SELECT * FROM recruitment_interview_events WHERE user_id=? ORDER BY created_at DESC", (user_id,)) or [],
            "recruitment_report_snapshots": db_all("SELECT * FROM recruitment_report_snapshots WHERE user_id=? ORDER BY updated_at DESC", (user_id,)) or [],
            "recruitment_candidate_signals": db_all("SELECT * FROM recruitment_candidate_signals WHERE user_id=? ORDER BY updated_at DESC, created_at DESC", (user_id,)) or [],
            "action_center_events": db_all("SELECT * FROM action_center_events WHERE user_id=? ORDER BY created_at DESC", (user_id,)) or [],
        }

    def build_recruitment_vault_payload(user: Dict[str, Any]) -> Dict[str, Any]:
        data_rows = vault_rows_payload(user["id"])
        documents = linked_recruitment_documents(user["id"])
        counts = recruitment_operational_counts(user["id"])
        return {
            "format": "techbuzz-recruitment-vault-v1",
            "exported_at": now_iso(),
            "company_name": company_name,
            "vault_fingerprint": vault_fingerprint(user),
            "user": {
                "id": user.get("id", ""),
                "email": clean_text(user.get("email", ""), 200),
                "name": clean_text(user.get("name", ""), 160),
                "role": clean_text(user.get("role", "member"), 40),
                "plan_id": clean_text(user.get("plan_id", ""), 80),
            },
            "counts": counts,
            "tables": data_rows,
            "documents": [
                {
                    "id": row.get("id", ""),
                    "original_name": row.get("original_name", ""),
                    "mime_type": row.get("mime_type", "application/octet-stream"),
                    "extension": row.get("extension", ""),
                    "size_bytes": int(row.get("size_bytes", 0) or 0),
                    "storage_path": row.get("storage_path", ""),
                    "extracted_text": row.get("extracted_text", ""),
                    "summary": row.get("summary", ""),
                    "kind": row.get("kind", "upload"),
                    "created_at": row.get("created_at", ""),
                    "updated_at": row.get("updated_at", ""),
                }
                for row in documents
            ],
        }

    def build_recruitment_vault_zip_bytes(user: Dict[str, Any]) -> tuple[bytes, Dict[str, Any]]:
        payload = build_recruitment_vault_payload(user)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr("manifest.json", json.dumps(payload, ensure_ascii=False, indent=2))
            for document in payload["documents"]:
                path = Path(document.get("storage_path", ""))
                if path.exists() and path.is_file():
                    archive_name = f"documents/{document['id']}_{Path(document.get('original_name', 'document')).name}"
                    bundle.writestr(archive_name, path.read_bytes())
        return buffer.getvalue(), payload

    def create_recruitment_vault_archive(user: Dict[str, Any], *, archive_kind: str) -> Dict[str, Any]:
        archive_bytes, payload = build_recruitment_vault_zip_bytes(user)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        archive_name = f"{archive_kind}-{stamp}.zip"
        user_dir = vault_dir / user["id"]
        user_dir.mkdir(parents=True, exist_ok=True)
        archive_path = user_dir / archive_name
        archive_path.write_bytes(archive_bytes)
        archive_hash = hashlib.sha256(archive_bytes).hexdigest()
        record_count = int(payload.get("counts", {}).get("records_total", 0) or 0)
        document_count = int(payload.get("counts", {}).get("documents", 0) or 0)
        summary = (
            f"{record_count} operational records and {document_count} linked document(s) "
            f"sealed into {archive_kind.replace('_', ' ')}."
        )
        archive = {
            "id": new_id("rva"),
            "user_id": user["id"],
            "archive_kind": archive_kind,
            "archive_name": archive_name,
            "archive_hash": archive_hash,
            "vault_fingerprint": vault_fingerprint(user),
            "record_count": record_count,
            "document_count": document_count,
            "size_bytes": len(archive_bytes),
            "file_path": str(archive_path),
            "summary": summary,
            "created_at": now_iso(),
        }
        db_exec(
            """
            INSERT INTO recruitment_vault_archives(
                id,user_id,archive_kind,archive_name,archive_hash,vault_fingerprint,record_count,
                document_count,size_bytes,file_path,summary,created_at
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                archive["id"],
                archive["user_id"],
                archive["archive_kind"],
                archive["archive_name"],
                archive["archive_hash"],
                archive["vault_fingerprint"],
                archive["record_count"],
                archive["document_count"],
                archive["size_bytes"],
                archive["file_path"],
                archive["summary"],
                archive["created_at"],
            ),
        )
        sync_recruitment_vault_registry(user, archive=archive)
        return archive

    def recent_recruitment_archives(user_id: str, limit: int = 8) -> List[Dict[str, Any]]:
        rows = db_all(
            """
            SELECT id, archive_kind, archive_name, archive_hash, record_count, document_count, size_bytes, summary, created_at
            FROM recruitment_vault_archives
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ) or []
        return rows

    def recruitment_archive_record(user_id: str, archive_id: str = "") -> Optional[Dict[str, Any]]:
        if archive_id:
            rows = db_all(
                """
                SELECT *
                FROM recruitment_vault_archives
                WHERE id=? AND user_id=?
                LIMIT 1
                """,
                (archive_id, user_id),
            ) or []
        else:
            rows = db_all(
                """
                SELECT *
                FROM recruitment_vault_archives
                WHERE user_id=?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id,),
            ) or []
        return rows[0] if rows else None

    def archive_preview_payload(archive: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not archive:
            return {}
        return {
            "id": archive.get("id", ""),
            "archive_kind": archive.get("archive_kind", ""),
            "archive_name": archive.get("archive_name", ""),
            "archive_hash": archive.get("archive_hash", ""),
            "record_count": int(archive.get("record_count", 0) or 0),
            "document_count": int(archive.get("document_count", 0) or 0),
            "size_bytes": int(archive.get("size_bytes", 0) or 0),
            "summary": archive.get("summary", ""),
            "created_at": archive.get("created_at", ""),
        }

    def load_recruitment_archive_manifest(archive: Dict[str, Any]) -> Dict[str, Any]:
        file_path = Path(archive.get("file_path", ""))
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Vault archive file is missing.")
        try:
            with zipfile.ZipFile(file_path, "r") as bundle:
                manifest_bytes = bundle.read("manifest.json")
        except KeyError as exc:
            raise HTTPException(status_code=400, detail="Vault archive manifest is missing.") from exc
        except zipfile.BadZipFile as exc:
            raise HTTPException(status_code=400, detail="Vault archive is not a valid zip bundle.") from exc
        try:
            manifest = json.loads(manifest_bytes.decode("utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Vault archive manifest is not readable.") from exc
        if not isinstance(manifest, dict):
            raise HTTPException(status_code=400, detail="Vault archive manifest is malformed.")
        return manifest

    def archived_tracker_rows(
        manifest: Dict[str, Any],
        *,
        scope: str = "tracker",
        search: str = "",
        stage: str = "",
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        scoped_filters = default_scope_filters(scope, filters)
        if search:
            scoped_filters.setdefault("search", search)
        if stage:
            scoped_filters.setdefault("stage", stage)
        rows = (manifest.get("tables", {}) or {}).get("recruitment_tracker_rows", []) or []
        visible: List[Dict[str, Any]] = []
        for row in rows:
            if tracker_row_matches_filters(row, scoped_filters):
                visible.append(dict(row))
        return visible

    def archived_discussion_payload(
        manifest: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
        *,
        limit: int = 30,
    ) -> Dict[str, Any]:
        filters = filters or {}
        logs = (manifest.get("tables", {}) or {}).get("recruitment_conversation_logs", []) or []
        items: List[Dict[str, Any]] = []
        for log in logs:
            pseudo_row = {
                "id": log.get("row_id", ""),
                "candidate_name": log.get("candidate_name", ""),
                "position": log.get("position", ""),
                "client_name": log.get("client_name", ""),
                "recruiter": log.get("recruiter", ""),
                "mail_id": log.get("mail_id", ""),
                "contact_no": log.get("contact_no", ""),
                "total_exp": log.get("total_exp", 0),
                "relevant_exp": log.get("relevant_exp", 0),
                "notice_period": log.get("notice_period", ""),
                "current_ctc": log.get("current_ctc", 0),
                "expected_ctc": log.get("expected_ctc", 0),
                "process_stage": log.get("process_stage", ""),
                "response_status": log.get("response_status", ""),
                "submission_state": log.get("submission_state", ""),
                "updated_at": log.get("created_at", ""),
                "created_at": log.get("created_at", ""),
                "remarks": log.get("discussion_summary", ""),
                "last_discussion": log.get("transcript", ""),
            }
            if not tracker_row_matches_filters(pseudo_row, filters):
                continue
            parsed = parse_json_blob(log.get("parsed_json"), {})
            items.append(
                {
                    "id": log.get("id", ""),
                    "row_id": log.get("row_id", ""),
                    "event_type": log.get("event_type", "conversation"),
                    "candidate_name": log.get("candidate_name", "Candidate"),
                    "position": log.get("position", "Open role"),
                    "client_name": log.get("client_name", company_name),
                    "recruiter": log.get("recruiter", ""),
                    "summary": clean_text(log.get("discussion_summary", "") or parsed.get("summary", "") or log.get("transcript", ""), 280),
                    "transcript": clean_multiline(log.get("transcript", ""), 900),
                    "process_stage": log.get("process_stage", ""),
                    "response_status": log.get("response_status", ""),
                    "submission_state": log.get("submission_state", "") or "draft",
                    "created_at": log.get("created_at", ""),
                }
            )
            if len(items) >= limit:
                break
        return {"count": len(items), "items": items}

    def archived_report_snapshots_payload(
        manifest: Dict[str, Any],
        *,
        kind: str = "",
        limit: int = 20,
    ) -> Dict[str, Any]:
        rows = list(((manifest.get("tables", {}) or {}).get("recruitment_report_snapshots", []) or []))
        if kind:
            rows = [row for row in rows if clean_text(row.get("report_kind", ""), 20).lower() == clean_text(kind, 20).lower()]
        snapshots = [
            {
                "id": row.get("id", ""),
                "kind": row.get("report_kind", ""),
                "window_key": row.get("window_key", ""),
                "window_label": row.get("window_label", ""),
                "headline": row.get("headline", ""),
                "summary": row.get("summary", ""),
                "row_count": int(row.get("row_count", 0) or 0),
                "updated_at": row.get("updated_at", ""),
            }
            for row in rows[:limit]
        ]
        return {"count": len(snapshots), "items": snapshots}

    def archive_tracker_export_payload(
        user: Dict[str, Any],
        *,
        scope: str = "tracker",
        search: str = "",
        stage: str = "",
        filters: Optional[Dict[str, Any]] = None,
        archive_id: str = "",
    ) -> Dict[str, Any]:
        archive = recruitment_archive_record(user["id"], archive_id)
        if not archive:
            raise HTTPException(status_code=404, detail="No sealed recruiter archive is available for recall yet.")
        manifest = load_recruitment_archive_manifest(archive)
        rows = archived_tracker_rows(manifest, scope=scope, search=search, stage=stage, filters=filters)
        export = tracker_export_payload(
            user,
            scope=scope,
            search=search,
            stage=stage,
            filters=filters,
            rows_override=rows,
        )
        scope_label = {"tracker": "tracker", "dsr": "DSR", "hsr": "HSR"}.get(scope, "tracker")
        export["source_mode"] = "archive"
        export["archive"] = archive_preview_payload(archive)
        export["headline"] = (
            f"Read-only archive {scope_label} is ready. "
            "The live operational lane is cleared, so this recall is coming from the sealed server archive."
        )
        return export

    def archive_reporting_payload(
        user: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
        *,
        archive_id: str = "",
    ) -> Dict[str, Any]:
        filters = dict(filters or {})
        archive = recruitment_archive_record(user["id"], archive_id)
        if not archive:
            return {
                "allowed": False,
                "source_mode": "archive",
                "filters": filters,
                "discussion_trail": {"count": 0, "items": []},
                "snapshots": {"count": 0, "items": []},
                "latest_export": {"scope": "tracker", "row_count": 0, "tsv": "", "headline": "No sealed recruiter archive is available yet."},
                "stats": {"discussion_events": 0, "report_snapshots": 0, "filtered_rows": 0},
                "headline": "No sealed recruiter archive is available yet.",
                "archive": {},
            }
        manifest = load_recruitment_archive_manifest(archive)
        discussion = archived_discussion_payload(manifest, filters)
        snapshots = archived_report_snapshots_payload(manifest, limit=18)
        filtered_tracker = archive_tracker_export_payload(user, scope="tracker", filters=filters, archive_id=archive.get("id", ""))
        return {
            "allowed": True,
            "source_mode": "archive",
            "filters": filters,
            "discussion_trail": discussion,
            "snapshots": snapshots,
            "latest_export": filtered_tracker,
            "stats": {
                "discussion_events": discussion.get("count", 0),
                "report_snapshots": snapshots.get("count", 0),
                "filtered_rows": filtered_tracker.get("row_count", 0),
            },
            "headline": "Live operational lane is cleared. Showing read-only recruiter recall from the sealed server archive.",
            "archive": archive_preview_payload(archive),
        }

    def recruitment_vault_status_payload(user: Dict[str, Any]) -> Dict[str, Any]:
        registry = sync_recruitment_vault_registry(user, bump_local=False)
        counts = recruitment_operational_counts(user["id"])
        archives = recent_recruitment_archives(user["id"])
        latest_archive = archive_preview_payload(recruitment_archive_record(user["id"]))
        return {
            "headline": "Recruitment vault keeps an operational local lane for the recruiter and a sealed server archive for the mother brain.",
            "fingerprint": registry.get("vault_fingerprint", "")[:16],
            "operational_status": registry.get("operational_status", "active"),
            "local_generation": int(registry.get("local_generation", 0) or 0),
            "server_generation": int(registry.get("server_generation", 0) or 0),
            "local_record_count": int(registry.get("local_record_count", 0) or 0),
            "local_document_count": int(registry.get("local_document_count", 0) or 0),
            "last_local_sync_at": registry.get("last_local_sync_at", ""),
            "last_server_sync_at": registry.get("last_server_sync_at", ""),
            "last_archive_summary": registry.get("last_archive_summary", ""),
            "last_imported_at": registry.get("last_imported_at", ""),
            "local_cache_cleared_at": registry.get("local_cache_cleared_at", ""),
            "counts": counts,
            "archives": archives,
            "latest_archive": latest_archive,
            "archive_recall_ready": bool(latest_archive),
            "local_cache_key": f"techbuzz-recruitment-vault::{user['id']}",
            "policy": [
                "Operational recruiter data can be cleared from the local lane.",
                "The mother-brain archive remains sealed on the server and is not used as the live company workspace.",
                "Vault bundles can be downloaded as compressed zip files and restored later into the same account.",
                "After local clear, recruiters can still use read-only archive recall without restoring the live operational lane.",
            ],
        }

    def delete_linked_recruitment_documents(user_id: str) -> int:
        documents = linked_recruitment_documents(user_id)
        for document in documents:
            path = Path(document.get("storage_path", ""))
            if path.exists() and path.is_file():
                try:
                    path.unlink()
                except Exception:
                    pass
        db_exec("DELETE FROM documents WHERE user_id=? AND id IN (SELECT resume_document_id FROM recruitment_tracker_rows WHERE user_id=? AND resume_document_id != '')", (user_id, user_id))
        return len(documents)

    def clear_recruitment_operational_data(user: Dict[str, Any], *, archive_before_clear: bool = True) -> Dict[str, Any]:
        archive = None
        counts = recruitment_operational_counts(user["id"])
        if archive_before_clear and (counts["records_total"] or counts["documents"]):
            archive = create_recruitment_vault_archive(user, archive_kind="pre_clear")
        deleted_documents = delete_linked_recruitment_documents(user["id"])
        for table in (
            "recruitment_interview_events",
            "recruitment_journey_events",
            "recruitment_conversation_logs",
            "recruitment_report_snapshots",
            "recruitment_candidate_signals",
            "recruitment_tracker_rows",
            "action_center_events",
        ):
            db_exec(f"DELETE FROM {table} WHERE user_id=?", (user["id"],))
        registry = sync_recruitment_vault_registry(
            user,
            bump_local=True,
            status_override="cleared",
            cleared_at=now_iso(),
            archive=archive,
        )
        return {
            "message": "Operational recruiter data was cleared from the local lane. The sealed server archive is still preserved for the mother brain.",
            "deleted_records": counts["records_total"],
            "deleted_documents": deleted_documents,
            "archive": archive,
            "vault": recruitment_vault_status_payload(user),
            "registry": registry,
        }

    def insert_row(table: str, row: Dict[str, Any]) -> None:
        keys = list(row.keys())
        placeholders = ",".join("?" for _ in keys)
        db_exec(
            f"INSERT INTO {table}({','.join(keys)}) VALUES({placeholders})",
            tuple(row[key] for key in keys),
        )

    def restore_recruitment_vault(user: Dict[str, Any], archive_bytes: bytes) -> Dict[str, Any]:
        with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as bundle:
            manifest = json.loads(bundle.read("manifest.json").decode("utf-8"))
            if manifest.get("format") != "techbuzz-recruitment-vault-v1":
                raise HTTPException(status_code=400, detail="Unsupported vault format.")
            if manifest.get("vault_fingerprint") != vault_fingerprint(user):
                raise HTTPException(status_code=403, detail="This vault belongs to a different account.")

            clear_recruitment_operational_data(user, archive_before_clear=True)

            for table, rows in (manifest.get("tables") or {}).items():
                for row in rows or []:
                    payload = dict(row or {})
                    payload["user_id"] = user["id"]
                    insert_row(table, payload)

            user_document_dir = document_dir / user["id"]
            user_document_dir.mkdir(parents=True, exist_ok=True)
            for document in manifest.get("documents", []) or []:
                payload = dict(document or {})
                original_name = Path(payload.get("original_name", "document")).name
                extension = payload.get("extension") or Path(original_name).suffix or ".bin"
                storage_path = user_document_dir / f"{new_id('rdoc')}{extension}"
                archive_name = f"documents/{payload.get('id', '')}_{original_name}"
                if archive_name in bundle.namelist():
                    storage_path.write_bytes(bundle.read(archive_name))
                else:
                    storage_path.write_text(payload.get("extracted_text", ""), encoding="utf-8")
                payload["user_id"] = user["id"]
                payload["storage_path"] = str(storage_path)
                insert_row("documents", payload)

        registry = sync_recruitment_vault_registry(
            user,
            bump_local=True,
            status_override="active",
            imported_at=now_iso(),
        )
        archive = create_recruitment_vault_archive(user, archive_kind="post_import")
        return {
            "message": "Recruitment vault restored into the operational lane.",
            "vault": recruitment_vault_status_payload(user),
            "archive": archive,
            "registry": registry,
        }

    def upsert_resume_submission(user: Dict[str, Any], req: RecruitmentResumeSubmissionReq) -> Dict[str, Any]:
        recruiter_name = default_recruiter_name(user)
        document = load_user_document(user["id"], req.document_id)
        resume = parse_resume_profile(document.get("extracted_text", ""))
        existing = find_tracker_row(
            user,
            row_id=req.row_id,
            candidate_id=req.candidate_id,
            mail_id=req.mail_id or resume.get("mail_id", ""),
            candidate_name=req.candidate_name or resume.get("candidate_name", ""),
            position=req.position,
        )
        row_id = existing["id"] if existing else new_id("trk")
        merged = dict(existing or {})
        transcript = clean_multiline(req.transcript or req.remarks, 2400)
        ack_status = clean_text(req.ack_status or "", 40).lower()
        ack_action = "confirmed" if req.candidate_confirmed or ack_status == "confirmed" else ("sent" if ack_status == "sent" else ("prepared" if ack_status == "prepared" else ""))
        merged.update(
            {
                "candidate_id": req.candidate_id or merged.get("candidate_id", ""),
                "job_id": req.job_id or merged.get("job_id", ""),
                "sourced_from": clean_text(req.sourced_from or merged.get("sourced_from", "resume_upload"), 80) or "resume_upload",
                "process_stage": merged.get("process_stage", "sourced"),
                "recruiter": clean_text(req.recruiter or merged.get("recruiter", recruiter_name), 120),
                "client_name": clean_text(req.client_name or merged.get("client_name", company_name), 160) or company_name,
                "position": clean_text(req.position or merged.get("position", "Open role"), 160) or "Open role",
                "profile_sharing_date": merged.get("profile_sharing_date", ""),
                "candidate_name": clean_text(req.candidate_name or resume.get("candidate_name", "") or merged.get("candidate_name", "Candidate"), 120) or "Candidate",
                "contact_no": normalize_phone(req.contact_no or resume.get("contact_no", "") or merged.get("contact_no", "")),
                "mail_id": clean_text(req.mail_id or resume.get("mail_id", "") or merged.get("mail_id", ""), 200),
                "current_company": clean_text(req.current_company or resume.get("current_company", "") or merged.get("current_company", ""), 160),
                "current_location": clean_text(req.current_location or resume.get("current_location", "") or merged.get("current_location", ""), 160),
                "preferred_location": clean_text(req.preferred_location or resume.get("preferred_location", "") or merged.get("preferred_location", ""), 160),
                "total_exp": req.total_exp or resume.get("total_exp", 0) or merged.get("total_exp", 0),
                "relevant_exp": req.relevant_exp or resume.get("relevant_exp", 0) or merged.get("relevant_exp", 0),
                "notice_period": clean_text(req.notice_period or resume.get("notice_period", "") or merged.get("notice_period", ""), 80),
                "notice_state": clean_text(req.notice_state or resume.get("notice_state", "") or merged.get("notice_state", ""), 40),
                "current_ctc": req.current_ctc or merged.get("current_ctc", 0),
                "expected_ctc": req.expected_ctc or merged.get("expected_ctc", 0),
                "client_spoc": clean_text(req.client_spoc or merged.get("client_spoc", ""), 120),
                "response_status": merged.get("response_status", "interested" if req.candidate_confirmed else "pending_review"),
                "duplicate_status": merged.get("duplicate_status", "clear"),
                "remarks": clean_text(req.remarks or merged.get("remarks", ""), 500),
                "last_discussion": transcript or merged.get("last_discussion", ""),
                "ack_mail_sent_at": merged.get("ack_mail_sent_at", ""),
                "ack_confirmed_at": merged.get("ack_confirmed_at", ""),
                "submission_state": merged.get("submission_state", "draft"),
                "resume_document_id": document.get("id", ""),
                "resume_file_name": document.get("original_name", ""),
                "resume_text": clean_multiline(resume.get("resume_text", ""), 12000),
                "skill_snapshot": clean_text(resume.get("skill_snapshot", "") or merged.get("skill_snapshot", ""), 320),
                "role_scope": clean_text(resume.get("role_scope", "") or merged.get("role_scope", ""), 420),
                "follow_up_due_at": merged.get("follow_up_due_at", ""),
                "last_contacted_at": now_iso(),
                "created_at": merged.get("created_at", now_iso()),
                "updated_at": now_iso(),
            }
        )
        issue_flags = parse_issue_flags(merged.get("issue_flags"))
        if not merged.get("skill_snapshot"):
            issue_flags = add_issue_flag(issue_flags, "fitment_issue")
        if req.candidate_confirmed or ack_status == "confirmed":
            merged["response_status"] = "ack_confirmed"
            merged["process_stage"] = "profile_shared"
        elif ack_status == "sent":
            merged["response_status"] = merged.get("response_status", "interested") or "interested"
        merged["submission_state"] = normalized_submission_state(
            existing_state=merged.get("submission_state", "draft"),
            ack_action=ack_action,
            ack_status=ack_status,
            candidate_confirmed=req.candidate_confirmed,
            ack_sent_at=merged.get("ack_mail_sent_at", ""),
            ack_confirmed_at=merged.get("ack_confirmed_at", ""),
        )
        if ack_action == "sent":
            merged["ack_mail_sent_at"] = merged.get("ack_mail_sent_at") or now_iso()
        elif ack_action == "confirmed":
            merged["ack_mail_sent_at"] = merged.get("ack_mail_sent_at") or now_iso()
            merged["ack_confirmed_at"] = merged.get("ack_confirmed_at") or now_iso()
            merged["profile_sharing_date"] = merged.get("profile_sharing_date") or now_iso()
        merged["issue_flags"] = sorted(set(issue_flags))
        merged["follow_up_due_at"] = derive_follow_up_due(
            process_stage=merged.get("process_stage", ""),
            response_status=merged.get("response_status", ""),
            submission_state=merged.get("submission_state", "draft"),
        )

        if existing:
            db_exec(
                """
                UPDATE recruitment_tracker_rows
                SET candidate_id=?, job_id=?, sourced_from=?, process_stage=?, recruiter=?, client_name=?, position=?,
                    profile_sharing_date=?, candidate_name=?, contact_no=?, mail_id=?, current_company=?, current_location=?,
                    preferred_location=?, total_exp=?, relevant_exp=?, notice_period=?, notice_state=?, current_ctc=?,
                    expected_ctc=?, client_spoc=?, response_status=?, issue_flags=?, duplicate_status=?, remarks=?,
                    last_discussion=?, ack_mail_sent_at=?, ack_confirmed_at=?, submission_state=?, resume_document_id=?,
                    resume_file_name=?, resume_text=?, skill_snapshot=?, role_scope=?, follow_up_due_at=?, last_contacted_at=?,
                    updated_at=?
                WHERE id=? AND user_id=?
                """,
                (
                    merged["candidate_id"],
                    merged["job_id"],
                    merged["sourced_from"],
                    merged["process_stage"],
                    merged["recruiter"],
                    merged["client_name"],
                    merged["position"],
                    merged["profile_sharing_date"],
                    merged["candidate_name"],
                    merged["contact_no"],
                    merged["mail_id"],
                    merged["current_company"],
                    merged["current_location"],
                    merged["preferred_location"],
                    merged["total_exp"],
                    merged["relevant_exp"],
                    merged["notice_period"],
                    merged["notice_state"],
                    merged["current_ctc"],
                    merged["expected_ctc"],
                    merged["client_spoc"],
                    merged["response_status"],
                    json.dumps(merged["issue_flags"], ensure_ascii=False),
                    merged["duplicate_status"],
                    merged["remarks"],
                    merged["last_discussion"],
                    merged["ack_mail_sent_at"],
                    merged["ack_confirmed_at"],
                    merged["submission_state"],
                    merged["resume_document_id"],
                    merged["resume_file_name"],
                    merged["resume_text"],
                    merged["skill_snapshot"],
                    merged["role_scope"],
                    merged["follow_up_due_at"],
                    merged["last_contacted_at"],
                    merged["updated_at"],
                    row_id,
                    user["id"],
                ),
            )
        else:
            db_exec(
                """
                INSERT INTO recruitment_tracker_rows(
                    id,user_id,candidate_id,job_id,sourced_from,process_stage,recruiter,client_name,position,profile_sharing_date,
                    candidate_name,contact_no,mail_id,current_company,current_location,preferred_location,total_exp,relevant_exp,
                    notice_period,notice_state,current_ctc,expected_ctc,client_spoc,response_status,issue_flags,duplicate_status,
                    remarks,last_discussion,ack_mail_sent_at,ack_confirmed_at,submission_state,resume_document_id,resume_file_name,
                    resume_text,skill_snapshot,role_scope,follow_up_due_at,last_contacted_at,created_at,updated_at
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    row_id,
                    user["id"],
                    merged["candidate_id"],
                    merged["job_id"],
                    merged["sourced_from"],
                    merged["process_stage"],
                    merged["recruiter"],
                    merged["client_name"],
                    merged["position"],
                    merged["profile_sharing_date"],
                    merged["candidate_name"],
                    merged["contact_no"],
                    merged["mail_id"],
                    merged["current_company"],
                    merged["current_location"],
                    merged["preferred_location"],
                    merged["total_exp"],
                    merged["relevant_exp"],
                    merged["notice_period"],
                    merged["notice_state"],
                    merged["current_ctc"],
                    merged["expected_ctc"],
                    merged["client_spoc"],
                    merged["response_status"],
                    json.dumps(merged["issue_flags"], ensure_ascii=False),
                    merged["duplicate_status"],
                    merged["remarks"],
                    merged["last_discussion"],
                    merged["ack_mail_sent_at"],
                    merged["ack_confirmed_at"],
                    merged["submission_state"],
                    merged["resume_document_id"],
                    merged["resume_file_name"],
                    merged["resume_text"],
                    merged["skill_snapshot"],
                    merged["role_scope"],
                    merged["follow_up_due_at"],
                    merged["last_contacted_at"],
                    merged["created_at"],
                    merged["updated_at"],
                ),
            )

        append_journey_event(
            user,
            row_id,
            event_type="resume_submission",
            stage=merged.get("process_stage", "sourced"),
            response_status=merged.get("response_status", "pending_review"),
            summary=clean_text(
                req.remarks
                or f"Resume {merged.get('resume_file_name', 'document')} uploaded with submission state {merged.get('submission_state', 'draft').replace('_', ' ')}.",
                500,
            ),
            details={
                "document_id": merged.get("resume_document_id", ""),
                "submission_state": merged.get("submission_state", "draft"),
                "skill_snapshot": merged.get("skill_snapshot", ""),
                "row_snapshot": recruitment_row_snapshot({**merged, "id": row_id}),
            },
            actor=merged.get("recruiter", recruiter_name),
        )
        record_discussion_log(
            user,
            {**merged, "id": row_id},
            event_type="resume_submission",
            transcript=transcript or merged.get("role_scope", "") or merged.get("skill_snapshot", ""),
            parsed={
                "resume_document_id": merged.get("resume_document_id", ""),
                "resume_file_name": merged.get("resume_file_name", ""),
                "submission_state": merged.get("submission_state", "draft"),
                "skill_snapshot": merged.get("skill_snapshot", ""),
            },
            summary=tracker_row_summary(merged),
        )
        signal = upsert_candidate_signal(
            user,
            content=merged.get("last_discussion", "") or merged.get("role_scope", "") or merged.get("skill_snapshot", ""),
            candidate_name=merged.get("candidate_name", ""),
            mail_id=merged.get("mail_id", ""),
            contact_no=merged.get("contact_no", ""),
            target_role=merged.get("position", ""),
            current_company=merged.get("current_company", ""),
            current_location=merged.get("current_location", ""),
            preferred_location=merged.get("preferred_location", ""),
            total_exp=merged.get("total_exp", 0),
            relevant_exp=merged.get("relevant_exp", 0),
            notice_period=merged.get("notice_period", ""),
            notice_state=merged.get("notice_state", ""),
            current_ctc=merged.get("current_ctc", 0),
            expected_ctc=merged.get("expected_ctc", 0),
            source_kind="recruiter_resume",
            row_id=row_id,
            candidate_id=merged.get("candidate_id", ""),
            auto_forward_to_ats=not bool(merged.get("candidate_id")),
        )
        ack = None
        if merged.get("submission_state") in {"draft", "ack_prepared"} and merged.get("mail_id"):
            try:
                ack = prepare_ack_event(user, merged)
                merged["submission_state"] = "ack_prepared"
                merged["follow_up_due_at"] = derive_follow_up_due(
                    process_stage=merged.get("process_stage", ""),
                    response_status=merged.get("response_status", ""),
                    submission_state="ack_prepared",
                )
                db_exec(
                    """
                    UPDATE recruitment_tracker_rows
                    SET submission_state=?, follow_up_due_at=?, updated_at=?
                    WHERE id=? AND user_id=?
                    """,
                    (
                        merged["submission_state"],
                        merged["follow_up_due_at"],
                        now_iso(),
                        row_id,
                        user["id"],
                    ),
                )
            except HTTPException:
                ack = None
        return {
            "row_id": row_id,
            "row": merged,
            "signal": signal,
            "acknowledgment": ack,
            "summary": tracker_row_summary(merged),
            "reporting": refresh_recruitment_reporting(user),
        }

    def journey_payload(user: Dict[str, Any], limit: int = 18) -> Dict[str, Any]:
        rows = db_all(
            """
            SELECT e.*, t.candidate_name, t.position
            FROM recruitment_journey_events e
            LEFT JOIN recruitment_tracker_rows t ON t.id=e.row_id
            WHERE e.user_id=?
            ORDER BY e.created_at DESC
            LIMIT ?
            """,
            (user["id"], limit),
        ) or []
        stage_counts: Dict[str, int] = {}
        visible = []
        for row in rows:
            stage = clean_text(row.get("stage", ""), 80) or "sourced"
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
            visible.append(
                {
                    "row_id": row.get("row_id", ""),
                    "candidate_name": row.get("candidate_name", "Candidate"),
                    "position": row.get("position", "Open role"),
                    "event_type": row.get("event_type", "update"),
                    "stage": stage,
                    "response_status": row.get("response_status", ""),
                    "summary": row.get("summary", ""),
                    "actor": row.get("actor", ""),
                    "created_at": row.get("created_at", ""),
                }
            )
        return {
            "headline": "Every candidate move is now stored in one sequence, from sourcing to joining and post-join follow-up.",
            "events": visible,
            "stage_counts": stage_counts,
        }

    def interview_desk_payload(user: Dict[str, Any], limit: int = 16) -> Dict[str, Any]:
        rows = db_all(
            """
            SELECT i.*, t.candidate_name, t.position, t.response_status, t.process_stage, t.updated_at
            FROM recruitment_interview_events i
            LEFT JOIN recruitment_tracker_rows t ON t.id=i.row_id
            WHERE i.user_id=?
            ORDER BY i.updated_at DESC, i.created_at DESC
            LIMIT ?
            """,
            (user["id"], limit),
        ) or []
        upcoming = []
        pending_feedback = []
        for row in rows:
            item = {
                "row_id": row.get("row_id", ""),
                "candidate_name": row.get("candidate_name", "Candidate"),
                "position": row.get("position", "Open role"),
                "interview_round": row.get("interview_round", "L1"),
                "scheduled_for": row.get("scheduled_for", ""),
                "mode": row.get("mode", "virtual"),
                "interviewer_name": row.get("interviewer_name", ""),
                "feedback_status": row.get("feedback_status", "pending"),
                "feedback_summary": row.get("feedback_summary", ""),
            }
            if item["feedback_status"] in {"pending", "requested"}:
                pending_feedback.append(item)
            upcoming.append(item)
        follow_up_rows = tracker_rows_for_console(user, detail="guided", allow_full=False)[:36]
        follow_ups = [
            {
                "row_id": row["id"],
                "candidate_name": row["candidate_name"],
                "position": row["position"],
                "process_stage": row["process_stage"],
                "response_status": row["response_status"],
                "submission_state": row.get("submission_state", "draft"),
                "follow_up_due_at": row.get("follow_up_due_at", ""),
                "summary": row.get("summary", ""),
            }
            for row in follow_up_rows
            if row.get("response_status") in {"pending_review", "shared", "ack_confirmed", "no_response"}
            or row.get("process_stage") in {"documentation", "offer", "joining", "joined", "post_join_followup"}
        ][:10]
        return {
            "headline": "Interview scheduling, feedback chase, and candidate follow-up now share one desk.",
            "upcoming": upcoming[:10],
            "pending_feedback": pending_feedback[:8],
            "follow_ups": follow_ups,
            "stats": {
                "upcoming": len(upcoming),
                "pending_feedback": len(pending_feedback),
                "follow_ups": len(follow_ups),
            },
        }

    def candidate_intelligence_payload(
        user: Dict[str, Any],
        *,
        search: str = "",
        stage: str = "",
        limit: int = 18,
    ) -> Dict[str, Any]:
        tracker_rows = db_all(
            """
            SELECT *
            FROM recruitment_tracker_rows
            WHERE user_id=?
            ORDER BY updated_at DESC, created_at DESC
            """,
            (user["id"],),
        ) or []
        interview_rows = db_all(
            """
            SELECT i.*, t.candidate_name, t.mail_id, t.contact_no, t.current_company, t.client_name, t.position, t.response_status, t.process_stage
            FROM recruitment_interview_events i
            LEFT JOIN recruitment_tracker_rows t ON t.id=i.row_id
            WHERE i.user_id=?
            ORDER BY i.updated_at DESC, i.created_at DESC
            """,
            (user["id"],),
        ) or []
        signal_rows = db_all(
            """
            SELECT *
            FROM recruitment_candidate_signals
            WHERE user_id=?
            ORDER BY updated_at DESC, created_at DESC
            """,
            (user["id"],),
        ) or []
        search_lower = clean_text(search, 160).lower()
        stage_lower = clean_text(stage, 80).lower()
        grouped: Dict[str, Dict[str, Any]] = {}

        def ensure_group(key: str, defaults: Dict[str, Any]) -> Dict[str, Any]:
            if key not in grouped:
                grouped[key] = {
                    "signal_key": key,
                    "candidate_name": defaults.get("candidate_name", "Candidate"),
                    "mail_id": defaults.get("mail_id", ""),
                    "contact_no": defaults.get("contact_no", ""),
                    "target_role": defaults.get("target_role", "Talent Pool"),
                    "current_company": defaults.get("current_company", ""),
                    "current_location": defaults.get("current_location", ""),
                    "preferred_location": defaults.get("preferred_location", ""),
                    "total_exp": defaults.get("total_exp", 0),
                    "relevant_exp": defaults.get("relevant_exp", 0),
                    "notice_period": defaults.get("notice_period", ""),
                    "notice_state": defaults.get("notice_state", ""),
                    "current_ctc": defaults.get("current_ctc", 0),
                    "expected_ctc": defaults.get("expected_ctc", 0),
                    "job_change_intent": defaults.get("job_change_intent", "unknown"),
                    "intent_confidence": defaults.get("intent_confidence", 0),
                    "applications_count": defaults.get("applications_count", 0),
                    "interviews_count": 0,
                    "offers_count": 0,
                    "response_status": defaults.get("response_status", "pending_review"),
                    "process_stage": defaults.get("process_stage", "sourced"),
                    "latest_signal": defaults.get("latest_signal", ""),
                    "fit_note": defaults.get("fit_note", ""),
                    "next_move": defaults.get("next_move", ""),
                    "source_types": set(defaults.get("source_types", [])),
                    "client_names": set(),
                    "issue_flags": set(defaults.get("issue_flags", [])),
                    "roles": set(),
                    "pending_feedback": False,
                    "updated_at": defaults.get("updated_at", ""),
                }
            return grouped[key]

        for row in signal_rows:
            key = row.get("signal_key") or candidate_signal_key(
                candidate_name=row.get("candidate_name", ""),
                mail_id=row.get("mail_id", ""),
                contact_no=row.get("contact_no", ""),
                current_company=row.get("current_company", ""),
            )
            if not key:
                continue
            group = ensure_group(
                key,
                {
                    "candidate_name": row.get("candidate_name", "Candidate"),
                    "mail_id": row.get("mail_id", ""),
                    "contact_no": row.get("contact_no", ""),
                    "target_role": row.get("target_role", "Talent Pool"),
                    "current_company": row.get("current_company", ""),
                    "current_location": row.get("current_location", ""),
                    "preferred_location": row.get("preferred_location", ""),
                    "total_exp": row.get("total_exp", 0),
                    "relevant_exp": row.get("relevant_exp", 0),
                    "notice_period": row.get("notice_period", ""),
                    "notice_state": row.get("notice_state", ""),
                    "current_ctc": row.get("current_ctc", 0),
                    "expected_ctc": row.get("expected_ctc", 0),
                    "job_change_intent": row.get("job_change_intent", "unknown"),
                    "intent_confidence": row.get("intent_confidence", 0),
                    "applications_count": row.get("applications_count", 0),
                    "latest_signal": row.get("source_summary", ""),
                    "fit_note": row.get("fit_note", ""),
                    "next_move": row.get("next_move", ""),
                    "source_types": parse_issue_flags(row.get("source_types")),
                    "updated_at": row.get("updated_at", ""),
                },
            )
            group["applications_count"] = max(group["applications_count"], int(row.get("applications_count", 0) or 0))
            group["interviews_count"] = max(group["interviews_count"], int(row.get("interviews_count", 0) or 0))
            group["offers_count"] = max(group["offers_count"], int(row.get("offers_count", 0) or 0))
            if row.get("target_role"):
                group["roles"].add(clean_text(row.get("target_role", ""), 160))
            group["source_types"].update(parse_issue_flags(row.get("source_types")))
            group["updated_at"] = max(group["updated_at"], row.get("updated_at", ""))

        for row in tracker_rows:
            key = candidate_signal_key(
                candidate_name=row.get("candidate_name", ""),
                mail_id=row.get("mail_id", ""),
                contact_no=row.get("contact_no", ""),
                current_company=row.get("current_company", ""),
            )
            if not key:
                continue
            group = ensure_group(
                key,
                {
                    "candidate_name": row.get("candidate_name", "Candidate"),
                    "mail_id": row.get("mail_id", ""),
                    "contact_no": row.get("contact_no", ""),
                    "target_role": row.get("position", "Talent Pool"),
                    "current_company": row.get("current_company", ""),
                    "current_location": row.get("current_location", ""),
                    "preferred_location": row.get("preferred_location", ""),
                    "total_exp": row.get("total_exp", 0),
                    "relevant_exp": row.get("relevant_exp", 0),
                    "notice_period": row.get("notice_period", ""),
                    "notice_state": row.get("notice_state", ""),
                    "current_ctc": row.get("current_ctc", 0),
                    "expected_ctc": row.get("expected_ctc", 0),
                    "response_status": row.get("response_status", "pending_review"),
                    "process_stage": row.get("process_stage", "sourced"),
                    "latest_signal": row.get("last_discussion", "") or row.get("remarks", ""),
                    "issue_flags": parse_issue_flags(row.get("issue_flags")),
                    "updated_at": row.get("updated_at", ""),
                },
            )
            group["candidate_name"] = row.get("candidate_name") or group["candidate_name"]
            group["target_role"] = row.get("position") or group["target_role"]
            group["current_company"] = row.get("current_company") or group["current_company"]
            group["current_location"] = row.get("current_location") or group["current_location"]
            group["preferred_location"] = row.get("preferred_location") or group["preferred_location"]
            group["total_exp"] = max(as_float(group["total_exp"], 0), as_float(row.get("total_exp", 0), 0))
            group["relevant_exp"] = max(as_float(group["relevant_exp"], 0), as_float(row.get("relevant_exp", 0), 0))
            group["notice_period"] = row.get("notice_period") or group["notice_period"]
            group["notice_state"] = row.get("notice_state") or group["notice_state"]
            group["current_ctc"] = max(as_float(group["current_ctc"], 0), as_float(row.get("current_ctc", 0), 0))
            group["expected_ctc"] = max(as_float(group["expected_ctc"], 0), as_float(row.get("expected_ctc", 0), 0))
            group["response_status"] = row.get("response_status") or group["response_status"]
            group["process_stage"] = row.get("process_stage") or group["process_stage"]
            if row.get("client_name"):
                group["client_names"].add(clean_text(row.get("client_name", ""), 160))
            if row.get("position"):
                group["roles"].add(clean_text(row.get("position", ""), 160))
            group["issue_flags"].update(parse_issue_flags(row.get("issue_flags")))
            group["source_types"].add(clean_text(row.get("sourced_from", "tracker"), 80))
            if row.get("process_stage") in {"offer", "documentation", "joining", "joined", "post_join_followup"}:
                group["offers_count"] += 1
            group["updated_at"] = max(group["updated_at"], row.get("updated_at", ""))

        for row in interview_rows:
            key = candidate_signal_key(
                candidate_name=row.get("candidate_name", ""),
                mail_id=row.get("mail_id", ""),
                contact_no=row.get("contact_no", ""),
                current_company=row.get("current_company", ""),
            )
            if not key:
                continue
            group = ensure_group(
                key,
                {
                    "candidate_name": row.get("candidate_name", "Candidate"),
                    "mail_id": row.get("mail_id", ""),
                    "contact_no": row.get("contact_no", ""),
                    "target_role": row.get("position", "Talent Pool"),
                    "current_company": row.get("current_company", ""),
                    "response_status": row.get("response_status", "pending_review"),
                    "process_stage": row.get("process_stage", "sourced"),
                },
            )
            group["interviews_count"] += 1
            if row.get("feedback_status") in {"pending", "requested"}:
                group["pending_feedback"] = True
            if row.get("position"):
                group["roles"].add(clean_text(row.get("position", ""), 160))

        merged_groups: Dict[str, Dict[str, Any]] = {}
        for group in grouped.values():
            alias = (
                clean_text(group.get("candidate_name", ""), 120).lower()
                + "|"
                + (clean_text(group.get("current_company", ""), 120).lower() or clean_text(group.get("target_role", ""), 120).lower() or "unknown")
            )
            if alias not in merged_groups:
                merged_groups[alias] = group
                continue
            target = merged_groups[alias]
            target["applications_count"] = max(target["applications_count"], group["applications_count"])
            target["interviews_count"] = max(target["interviews_count"], group["interviews_count"])
            target["offers_count"] = max(target["offers_count"], group["offers_count"])
            target["total_exp"] = max(as_float(target["total_exp"], 0), as_float(group["total_exp"], 0))
            target["relevant_exp"] = max(as_float(target["relevant_exp"], 0), as_float(group["relevant_exp"], 0))
            target["notice_period"] = target["notice_period"] or group["notice_period"]
            target["notice_state"] = target["notice_state"] or group["notice_state"]
            target["current_ctc"] = max(as_float(target["current_ctc"], 0), as_float(group["current_ctc"], 0))
            target["expected_ctc"] = max(as_float(target["expected_ctc"], 0), as_float(group["expected_ctc"], 0))
            if group["job_change_intent"] == "active" or (target["job_change_intent"] == "unknown" and group["job_change_intent"] != "unknown"):
                target["job_change_intent"] = group["job_change_intent"]
                target["intent_confidence"] = max(target["intent_confidence"], group["intent_confidence"])
            target["response_status"] = group["response_status"] if group["response_status"] != "pending_review" else target["response_status"]
            target["process_stage"] = group["process_stage"] if group["process_stage"] != "sourced" else target["process_stage"]
            target["latest_signal"] = group["latest_signal"] or target["latest_signal"]
            target["fit_note"] = target["fit_note"] or group["fit_note"]
            target["next_move"] = target["next_move"] or group["next_move"]
            target["source_types"].update(group["source_types"])
            target["client_names"].update(group["client_names"])
            target["issue_flags"].update(group["issue_flags"])
            target["roles"].update(group["roles"])
            target["pending_feedback"] = target["pending_feedback"] or group["pending_feedback"]
            target["updated_at"] = max(target["updated_at"], group["updated_at"])

        visible = []
        for group in merged_groups.values():
            group["applications_count"] = max(group["applications_count"], len(group["client_names"]))
            fit = candidate_fit_snapshot(
                total_exp=group["total_exp"],
                relevant_exp=group["relevant_exp"] or group["total_exp"],
                response_status=group["response_status"],
                process_stage=group["process_stage"],
                issue_flags=sorted(group["issue_flags"]),
            )
            next_move = group["next_move"] or candidate_next_move(
                job_change_intent=group["job_change_intent"],
                applications_count=group["applications_count"],
                interviews_count=group["interviews_count"],
                offers_count=group["offers_count"],
                response_status=group["response_status"],
                issue_flags=sorted(group["issue_flags"]),
                fit_label=fit["label"],
                pending_feedback=group["pending_feedback"],
            )
            searchable = " ".join(
                [
                    group["candidate_name"],
                    group["target_role"],
                    group["current_company"],
                    ",".join(sorted(group["client_names"])),
                    ",".join(sorted(group["roles"])),
                    group["job_change_intent"],
                ]
            ).lower()
            if stage_lower and group["process_stage"].lower() != stage_lower:
                continue
            if search_lower and search_lower not in searchable:
                continue
            visible.append(
                {
                    "signal_key": group["signal_key"],
                    "candidate_name": group["candidate_name"],
                    "mail_id": group["mail_id"],
                    "contact_no": group["contact_no"],
                    "target_role": group["target_role"],
                    "current_company": group["current_company"],
                    "current_location": group["current_location"],
                    "preferred_location": group["preferred_location"],
                    "total_exp": round(as_float(group["total_exp"], 0), 1),
                    "relevant_exp": round(as_float(group["relevant_exp"], 0), 1),
                    "notice_period": group["notice_period"],
                    "job_change_intent": group["job_change_intent"],
                    "applications_count": group["applications_count"],
                    "interviews_count": group["interviews_count"],
                    "offers_count": group["offers_count"],
                    "response_status": group["response_status"],
                    "process_stage": group["process_stage"],
                    "fit_score": fit["score"],
                    "fit_label": fit["label"],
                    "fit_note": group["fit_note"] or f"{fit['label'].title()} ({fit['score']})",
                    "next_move": next_move,
                    "latest_signal": group["latest_signal"] or "No recent signal captured yet.",
                    "client_count": len(group["client_names"]),
                    "client_names": sorted(item for item in group["client_names"] if item),
                    "role_count": len(group["roles"]),
                    "roles": sorted(item for item in group["roles"] if item),
                    "issue_flags": sorted(item for item in group["issue_flags"] if item),
                    "pending_feedback": group["pending_feedback"],
                    "source_types": sorted(item for item in group["source_types"] if item),
                    "updated_at": group["updated_at"],
                }
            )

        visible.sort(
            key=lambda item: (
                item["fit_score"],
                item["offers_count"],
                item["interviews_count"],
                item["applications_count"],
                item["updated_at"],
            ),
            reverse=True,
        )
        stats = {
            "tracked_candidates": len(visible),
            "active_job_change": len([item for item in visible if item["job_change_intent"] == "active"]),
            "pending_feedback": len([item for item in visible if item["pending_feedback"]]),
            "offers_live": sum(int(item["offers_count"] or 0) for item in visible),
            "strong_fit": len([item for item in visible if item["fit_label"] == "strong fit"]),
        }
        return {
            "headline": "Candidate intelligence now combines tracker memory, interviews, offers, and network intent in one live recruiter view.",
            "stats": stats,
            "candidates": visible[:limit],
            "policy": [
                "Counts mix recruiter-tracked flow and candidate-declared market signals.",
                "All intelligence is stored per user on the local system.",
                "Use this to decide next move, not as blind truth without recruiter judgment.",
            ],
        }

    def query_terms(text: str) -> List[str]:
        return [term for term in re.findall(r"[a-z0-9+#.]{2,}", (text or "").lower()) if len(term) >= 2]

    def intelligent_search_payload(
        *,
        search: str,
        stage: str,
        jobs: List[Dict[str, Any]],
        candidates: List[Dict[str, Any]],
        tracker_rows: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        terms = query_terms(search)
        role_terms = sorted({clean_text(row.get("title", ""), 80) for row in jobs if row.get("title")})[:8]
        source_terms = sorted({clean_text(row.get("source", ""), 40) for row in candidates if row.get("source")})[:8]
        stage_counts: Dict[str, int] = {}
        for row in tracker_rows:
            item_stage = clean_text(row.get("process_stage", "sourced"), 80) or "sourced"
            stage_counts[item_stage] = stage_counts.get(item_stage, 0) + 1
        suggestions: List[str] = []
        if not terms:
            suggestions.extend(role_terms[:4])
        else:
            if len(candidates) <= 2:
                suggestions.extend(role_terms[:3])
                if "java" in terms:
                    suggestions.append("spring boot")
                if "react" in terms:
                    suggestions.append("frontend ui")
                if "oracle" in terms:
                    suggestions.append("plsql")
            if len(jobs) == 0 and role_terms:
                suggestions.append(role_terms[0])
        suggestions = [item for item in suggestions if item]
        seen = set()
        deduped = []
        for item in suggestions:
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return {
            "headline": "Intelligent search now reads roles, candidates, sources, and tracker stages together instead of plain text matching only.",
            "search": search,
            "stage": stage or "all",
            "stats": {
                "query_terms": len(terms),
                "matched_candidates": len(candidates),
                "matched_roles": len(jobs),
                "tracker_rows": len(tracker_rows),
            },
            "stage_counts": stage_counts,
            "suggestions": deduped[:6],
            "known_sources": source_terms[:6],
        }

    def talent_crm_payload(tracker_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        hot = []
        warm = []
        watch = []
        submitted = []
        for row in tracker_rows:
            issue_flags = parse_issue_flags(row.get("issue_flags"))
            item = {
                "row_id": row.get("id", ""),
                "candidate_name": row.get("candidate_name", "Candidate"),
                "position": row.get("position", "Open role"),
                "response_status": row.get("response_status", "pending_review"),
                "process_stage": row.get("process_stage", "sourced"),
                "summary": clean_text(row.get("last_discussion") or row.get("remarks") or row.get("response_status"), 220),
            }
            if row.get("process_stage") in {"profile_shared", "l1_interview", "l2_interview", "l3_interview", "offer", "documentation"}:
                submitted.append(item)
            if row.get("response_status") in {"interested", "shared", "ack_confirmed"} and not any(flag in issue_flags for flag in ("salary_issue", "location_issue", "fake_profile", "duplicate")):
                hot.append(item)
            elif row.get("process_stage") in {"screening", "profile_shared"} or row.get("response_status") in {"pending_review", "available"}:
                warm.append(item)
            if any(flag in issue_flags for flag in ("no_response", "salary_issue", "location_issue", "duplicate", "fake_profile", "timepass")):
                watch.append(item)
        return {
            "headline": "Talent CRM pools are built from live tracker behavior, not static candidate lists.",
            "stats": {
                "hot": len(hot),
                "warm": len(warm),
                "watch": len(watch),
                "submitted": len(submitted),
            },
            "hot_pool": hot[:6],
            "warm_pool": warm[:6],
            "watch_pool": watch[:6],
            "submitted_pool": submitted[:6],
        }

    def fraud_and_compliance_payload(
        tracker_rows: List[Dict[str, Any]],
        interviews: Dict[str, Any],
        *,
        detail_mode: str,
        allow_full_context: bool,
    ) -> Dict[str, Any]:
        fraud_watch = []
        missing_info = []
        ack_pending = []
        for row in tracker_rows:
            issues = parse_issue_flags(row.get("issue_flags"))
            suspicious = []
            if "fake_profile" in issues:
                suspicious.append("fake profile flag")
            if "timepass" in issues:
                suspicious.append("timepass risk")
            if as_float(row.get("total_exp"), 0) >= 5 and as_float(row.get("relevant_exp"), 0) <= 0:
                suspicious.append("relevant exp missing")
            if suspicious:
                fraud_watch.append(
                    {
                        "candidate_name": row.get("candidate_name", "Candidate"),
                        "position": row.get("position", "Open role"),
                        "signals": suspicious,
                    }
                )
            missing = []
            if not row.get("mail_id"):
                missing.append("email")
            if not row.get("notice_period"):
                missing.append("notice")
            if not row.get("expected_ctc"):
                missing.append("ectc")
            if missing:
                missing_info.append(
                    {
                        "candidate_name": row.get("candidate_name", "Candidate"),
                        "position": row.get("position", "Open role"),
                        "missing": missing,
                    }
                )
            if row.get("response_status") in {"interested", "shared"} and not row.get("ack_mail_sent_at"):
                ack_pending.append(
                    {
                        "candidate_name": row.get("candidate_name", "Candidate"),
                        "position": row.get("position", "Open role"),
                    }
                )
        return {
            "headline": "Fraud watch and compliance watch now sit beside the tracker so quality and audit gaps surface earlier.",
            "stats": {
                "fraud_watch": len(fraud_watch),
                "missing_info": len(missing_info),
                "ack_pending": len(ack_pending),
                "pending_feedback": (((interviews or {}).get("stats") or {}).get("pending_feedback") or 0),
            },
            "fraud_watch": fraud_watch[:6],
            "missing_info": missing_info[:6],
            "ack_pending": ack_pending[:6],
            "policy": [
                "Prepare actions visibly and send manually.",
                "Use guided disclosure by default for candidate privacy.",
                "Treat legal and rule questions as live-check topics when exact jurisdiction matters.",
                f"Current disclosure mode: {'full' if detail_mode == 'full' and allow_full_context else detail_mode}.",
            ],
        }

    def workforce_planning_payload(jobs: List[Dict[str, Any]], tracker_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        roles = []
        open_roles = [row for row in jobs if str(row.get("status", "open")).lower() == "open"]
        for row in open_roles:
            title = row.get("title", "Open role")
            linked = [
                item for item in tracker_rows
                if clean_text(item.get("position", ""), 160).lower() == clean_text(title, 160).lower()
            ]
            hot_count = len([item for item in linked if item.get("response_status") in {"interested", "shared", "ack_confirmed"}])
            interview_count = len([item for item in linked if "interview" in str(item.get("process_stage", ""))])
            risk = "covered"
            if hot_count == 0:
                risk = "high_risk"
            elif hot_count < 2 or interview_count == 0:
                risk = "watch"
            roles.append(
                {
                    "title": title,
                    "location": row.get("location", ""),
                    "urgency": row.get("urgency", "normal"),
                    "linked_candidates": len(linked),
                    "hot_candidates": hot_count,
                    "interviews": interview_count,
                    "risk": risk,
                }
            )
        risk_roles = [row for row in roles if row["risk"] != "covered"]
        return {
            "headline": "Workforce planning now flags roles where pipeline depth is too thin for dependable delivery.",
            "stats": {
                "open_roles": len(open_roles),
                "risk_roles": len(risk_roles),
                "covered_roles": len([row for row in roles if row["risk"] == "covered"]),
            },
            "roles": roles[:10],
            "priority_actions": [
                "Run fresh sourcing on high-risk roles first.",
                "Keep at least 2 interested backups for each urgent role.",
                "Push feedback collection on interview-stage roles before opening new sourcing loops.",
            ],
        }

    def vendor_market_map_payload() -> Dict[str, Any]:
        categories = []
        all_vendors = set()
        staffing_focused = set()
        enterprise_focused = set()
        for item in AI_RECRUITING_VENDOR_GROUPS:
            vendors = list(item.get("vendors", []))
            categories.append(
                {
                    "category": item.get("category", "Category"),
                    "focus": item.get("focus", ""),
                    "vendors": vendors,
                }
            )
            all_vendors.update(vendors)
            category_label = str(item.get("category", "")).lower()
            if "staffing" in category_label or "agency" in category_label:
                staffing_focused.update(vendors)
            if "structured" in category_label or "intelligence" in category_label or "mobility" in category_label:
                enterprise_focused.update(vendors)
        benchmark = [
            {
                "name": "Greenhouse",
                "reason": "Benchmark structured hiring discipline and enterprise ATS workflow rigor.",
            },
            {
                "name": "Recruit CRM",
                "reason": "Benchmark staffing-agency pipeline handling, client submission flow, and recruiter usability.",
            },
            {
                "name": "GoodTime",
                "reason": "Benchmark interview scheduling reliability and candidate communication speed.",
            },
            {
                "name": "Findem",
                "reason": "Benchmark sourcing intelligence, attribute search, and discovery depth.",
            },
            {
                "name": "Eightfold",
                "reason": "Benchmark workforce intelligence, mobility, and strategic talent planning.",
            },
        ]
        positioning = [
            "Match ATS-grade discipline from Greenhouse and Workable for structured hiring.",
            "Stay stronger than staffing tools by combining recruiter conversation memory, DSR, HSR, and duplicate control in one place.",
            "Borrow sourcing depth patterns from Findem, Hirefly, Juicebox, Fetcher, hireEZ, and Wellfound without losing human control.",
            "Borrow scheduling and interview coordination quality from GoodTime, Humanly, Paradox, HireVue, and Braintrust.",
            "Keep TechBuzz differentiated by optimizing for real staffing delivery, not only enterprise HR administration.",
        ]
        return {
            "headline": "The recruiting software market is now mapped by category, benchmark, and TechBuzz positioning.",
            "stats": {
                "vendors": len(all_vendors),
                "categories": len(categories),
                "staffing_focused": len(staffing_focused),
                "enterprise_focused": len(enterprise_focused),
            },
            "categories": categories,
            "benchmark": benchmark,
            "positioning": positioning,
        }

    def tracker_export_payload(
        user: Dict[str, Any],
        *,
        scope: str = "tracker",
        search: str = "",
        stage: str = "",
        filters: Optional[Dict[str, Any]] = None,
        rows_override: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        scoped_filters = default_scope_filters(scope, filters)
        rows = rows_override or tracker_rows_for_console(
            user,
            search=search,
            stage=stage,
            detail="full",
            allow_full=True,
            filters=scoped_filters,
        )
        lines = tracker_export_lines(rows)
        csv_lines = tracker_export_csv_lines(rows)
        window = report_window_for_scope(scope, scoped_filters)
        scope_label = {"tracker": "Tracker", "dsr": "DSR", "hsr": "HSR"}.get(scope, "Tracker")
        summary = tracker_summary_payload(rows)
        return {
            "scope": scope,
            "label": f"{scope_label} export",
            "row_count": len(rows),
            "tsv": "\n".join(lines),
            "csv": "\n".join(csv_lines),
            "headline": f"{scope_label} copy sheet is ready. Paste the tab-separated block into Excel or chat.",
            "summary": summary,
            "filters": scoped_filters,
            "window": {
                "key": window["key"],
                "label": window["label"],
                "start": window["start"].isoformat() if window.get("start") else "",
                "end": window["end"].isoformat() if window.get("end") else "",
            },
        }

    def upsert_report_snapshot(
        user: Dict[str, Any],
        *,
        scope: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        export = tracker_export_payload(user, scope=scope, filters=filters)
        window = export.get("window", {})
        summary = export.get("summary", {})
        existing = db_all(
            """
            SELECT id
            FROM recruitment_report_snapshots
            WHERE user_id=? AND report_kind=? AND window_key=?
            LIMIT 1
            """,
            (user["id"], clean_text(scope, 20), clean_text(window.get("key", "latest"), 80)),
        ) or []
        snapshot_id = existing[0]["id"] if existing else new_id("rrs")
        totals_blob = json.dumps(summary.get("totals", {}), ensure_ascii=False)[:3000]
        filters_blob = json.dumps(export.get("filters", {}), ensure_ascii=False)[:3000]
        summary_text = clean_text(
            f"Rows {summary.get('totals', {}).get('rows', 0)} | submitted {summary.get('totals', {}).get('submitted', 0)} | interested {summary.get('totals', {}).get('interested', 0)}",
            300,
        )
        params = (
            clean_text(window.get("label", ""), 160),
            clean_text(window.get("start", ""), 40),
            clean_text(window.get("end", ""), 40),
            int(export.get("row_count", 0) or 0),
            clean_text(export.get("headline", ""), 300),
            summary_text,
            totals_blob,
            filters_blob,
            export.get("tsv", "")[:60000],
            now_iso(),
            snapshot_id,
            user["id"],
        )
        if existing:
            db_exec(
                """
                UPDATE recruitment_report_snapshots
                SET window_label=?, window_start=?, window_end=?, row_count=?, headline=?, summary=?, totals_json=?, filters_json=?, tsv=?, updated_at=?
                WHERE id=? AND user_id=?
                """,
                params,
            )
        else:
            db_exec(
                """
                INSERT INTO recruitment_report_snapshots(
                    id,user_id,report_kind,window_key,window_label,window_start,window_end,row_count,headline,summary,totals_json,filters_json,tsv,created_at,updated_at
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    snapshot_id,
                    user["id"],
                    clean_text(scope, 20),
                    clean_text(window.get("key", "latest"), 80),
                    clean_text(window.get("label", ""), 160),
                    clean_text(window.get("start", ""), 40),
                    clean_text(window.get("end", ""), 40),
                    int(export.get("row_count", 0) or 0),
                    clean_text(export.get("headline", ""), 300),
                    summary_text,
                    totals_blob,
                    filters_blob,
                    export.get("tsv", "")[:60000],
                    now_iso(),
                    now_iso(),
                ),
            )
        return {
            "id": snapshot_id,
            "kind": scope,
            "window_label": window.get("label", ""),
            "row_count": export.get("row_count", 0),
            "summary": summary_text,
        }

    def refresh_recruitment_reporting(user: Dict[str, Any]) -> Dict[str, Any]:
        sync_recruitment_vault_registry(user, bump_local=True, status_override="active")
        return {
            "tracker": upsert_report_snapshot(user, scope="tracker"),
            "dsr": upsert_report_snapshot(user, scope="dsr"),
            "hsr": upsert_report_snapshot(user, scope="hsr"),
        }

    def recruiter_reporting_payload(
        user: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        filters = dict(filters or {})
        if not recruiter_access_enabled(user):
            if recruiter_archive_access_enabled(user):
                return archive_reporting_payload(user, filters)
            return {
                "allowed": False,
                "filters": filters,
                "discussion_trail": {"count": 0, "items": []},
                "snapshots": {"count": 0, "items": []},
                "latest_export": {"scope": "tracker", "row_count": 0, "tsv": "", "headline": "Recruiter reporting is available only inside the recruiter workspace."},
                "stats": {"discussion_events": 0, "report_snapshots": 0, "filtered_rows": 0},
                "headline": "Recruiter reporting is available only inside the recruiter workspace.",
            }
        discussion = history_discussion_payload(user, filters)
        snapshots = report_snapshots_payload(user, limit=18)
        filtered_tracker = tracker_export_payload(user, scope="tracker", filters=filters)
        return {
            "allowed": recruiter_access_enabled(user),
            "filters": filters,
            "discussion_trail": discussion,
            "snapshots": snapshots,
            "latest_export": filtered_tracker,
            "stats": {
                "discussion_events": discussion.get("count", 0),
                "report_snapshots": snapshots.get("count", 0),
                "filtered_rows": filtered_tracker.get("row_count", 0),
            },
            "headline": "Recruiter memory keeps discussion trails, DSR, HSR, and tracker exports ready for long-term retrieval.",
        }

    def parse_report_request_filters_from_message(message: str) -> Dict[str, Any]:
        filters: Dict[str, Any] = {}
        lower = clean_text(message, 1200).lower()
        today = datetime.now().date()
        if "today" in lower:
            filters["date_from"] = today.isoformat()
            filters["date_to"] = today.isoformat()
        elif "yesterday" in lower:
            day = today - timedelta(days=1)
            filters["date_from"] = day.isoformat()
            filters["date_to"] = day.isoformat()
        elif "last 7 days" in lower or "past 7 days" in lower or "this week" in lower:
            filters["date_from"] = (today - timedelta(days=6)).isoformat()
            filters["date_to"] = today.isoformat()
        date_matches = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", message)
        if date_matches:
            filters["date_from"] = date_matches[0]
            filters["date_to"] = date_matches[-1]
        row_match = re.search(r"\btrk_[a-z0-9]+\b", message, flags=re.I)
        if row_match:
            filters["row_id"] = row_match.group(0)
        mail_match = re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", message, flags=re.I)
        if mail_match:
            filters["mail_id"] = mail_match.group(0)
        phone_match = re.search(r"(?<!\d)(?:\+91[\s-]*)?[6-9]\d{9}(?!\d)", message)
        if phone_match:
            filters["contact_no"] = normalize_phone(phone_match.group(0))
        if "immediate" in lower:
            filters["notice_period"] = "immediate"
        elif "serving" in lower:
            filters["notice_period"] = "serving"
        elif "not serving" in lower:
            filters["notice_period"] = "not_serving"
        exp_match = re.search(r"(above|more than|over|less than|below)?\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", lower)
        if exp_match:
            value = exp_match.group(2)
            if exp_match.group(1) in {"less than", "below"}:
                filters["max_total_exp"] = value
            else:
                filters["min_total_exp"] = value
        ctc_match = re.search(r"(above|more than|over|less than|below)?\s*(\d+(?:\.\d+)?)\s*(?:lpa|ctc|lakhs?|lakh)", lower)
        if ctc_match:
            value = ctc_match.group(2)
            if ctc_match.group(1) in {"less than", "below"}:
                filters["max_ctc"] = value
            else:
                filters["min_ctc"] = value
        return filters

    def agent_console_state(user: Dict[str, Any], filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        base = portal_state_payload(user)
        filters = filters or {}
        search = (filters.get("search") or "").strip().lower()
        stage = (filters.get("stage") or "").strip().lower()
        detail = (filters.get("detail") or "guided").strip().lower()
        allow_full = bool(filters.get("allow_full_context"))

        jobs = db_all(
            """
            SELECT * FROM ats_jobs
            WHERE user_id=?
            ORDER BY updated_at DESC, created_at DESC
            """,
            (user["id"],),
        ) or []
        candidates = db_all(
            """
            SELECT * FROM ats_candidates
            WHERE user_id=?
            ORDER BY fit_score DESC, updated_at DESC, created_at DESC
            """,
            (user["id"],),
        ) or []
        jobs_by_id = {row["id"]: row for row in jobs}
        sync_recruitment_tracker(user, jobs, candidates)

        filtered_candidates: List[Dict[str, Any]] = []
        for row in candidates:
            role_label = row.get("role") or jobs_by_id.get(row.get("job_id", ""), {}).get("title") or "Open role"
            searchable = " ".join(
                [
                    str(row.get("name", "")),
                    str(role_label),
                    str(row.get("status", "")),
                    str(row.get("ai_strength", "")),
                    str(row.get("source", "")),
                    str(jobs_by_id.get(row.get("job_id", ""), {}).get("department", "")),
                ]
            ).lower()
            if stage and str(row.get("status", "")).lower() != stage:
                continue
            if search and search not in searchable:
                continue
            item = {
                "id": row["id"],
                "name": row.get("name", "Candidate"),
                "title": role_label,
                "stage": row.get("status", "applied"),
                "fit_score": int(row.get("fit_score", 0) or 0),
                "experience": int(row.get("experience", 0) or 0),
                "client_company": company_name,
                "source": row.get("source", "manual"),
                "ai_strength": row.get("ai_strength", ""),
                "ai_concern": row.get("ai_concern", ""),
            }
            if detail != "minimal":
                item["summary"] = (
                    clean_text(row.get("resume_text", ""), 320)
                    or clean_text(row.get("notes", ""), 220)
                    or clean_text(row.get("ai_strength", ""), 220)
                    or "ATS candidate ready for review."
                )
            if detail == "full" and allow_full:
                item["email"] = row.get("email", "")
                item["resume_excerpt"] = clean_text(row.get("resume_text", ""), 800)
                item["notes"] = clean_text(row.get("notes", ""), 500)
            filtered_candidates.append(item)

        filtered_jobs: List[Dict[str, Any]] = []
        for row in jobs:
            searchable = " ".join(
                [
                    str(row.get("title", "")),
                    str(row.get("department", "")),
                    str(row.get("location", "")),
                    str(row.get("urgency", "")),
                    str(row.get("description", ""))[:200],
                ]
            ).lower()
            if search and search not in searchable:
                continue
            filtered_jobs.append(
                {
                    "id": row["id"],
                    "client_company": company_name,
                    "title": row.get("title", "Open role"),
                    "department": row.get("department", ""),
                    "location": row.get("location", ""),
                    "urgency": row.get("urgency", "normal"),
                    "summary": row.get("description", "")[:220] or "ATS role waiting for pipeline action.",
                    "created_at": row.get("created_at", ""),
                    "status": row.get("status", "open"),
                    "candidate_count": len([cand for cand in candidates if cand.get("job_id") == row["id"]]),
                }
            )

        latest_hunt = (get_state().get("praapti_hunts", []) or [])[-1:] or []
        hunt = latest_hunt[0] if latest_hunt else None
        existing_pairs = {
            (
                str(row.get("name", "")).strip().lower(),
                str((row.get("role") or jobs_by_id.get(row.get("job_id", ""), {}).get("title") or "")).strip().lower(),
            )
            for row in candidates
        }
        suggestions: List[Dict[str, Any]] = []
        if hunt:
            for candidate in hunt.get("candidates", [])[:6]:
                key = (
                    str(candidate.get("name", "")).strip().lower(),
                    str(candidate.get("title", "")).strip().lower(),
                )
                if key in existing_pairs:
                    continue
                suggestions.append(
                    {
                        "name": candidate.get("name", "Candidate"),
                        "title": candidate.get("title", "Role"),
                        "fit_score": int(candidate.get("fit_score", 0) or 0),
                        "experience": int(candidate.get("experience", 0) or 0),
                        "source": "praapti_suggestion",
                    }
                )

        tracker_rows = tracker_rows_for_console(
            user,
            search=search,
            stage=stage,
            detail=detail,
            allow_full=allow_full,
            filters=filters,
        )
        tracker_all_rows = db_all(
            """
            SELECT * FROM recruitment_tracker_rows
            WHERE user_id=?
            ORDER BY updated_at DESC, created_at DESC
            """,
            (user["id"],),
        ) or []
        tracker_summary = tracker_summary_payload(tracker_all_rows)
        journey = journey_payload(user)
        interviews = interview_desk_payload(user)
        candidate_intelligence = candidate_intelligence_payload(user, search=search, stage=stage)

        base["candidates"] = filtered_candidates[:36]
        base["jobs"] = filtered_jobs[:18]
        base["candidate_intelligence"] = candidate_intelligence
        base["recruitment_tracker"] = {
            "rows": tracker_rows[:42],
            "summary": tracker_summary,
            "issue_options": TRACKER_ISSUE_OPTIONS,
        }
        base["recruitment_ops"] = {
            "journey": journey,
            "interviews": interviews,
            "exports": {
                "tracker": tracker_export_payload(user, scope="tracker", search=search, stage=stage, filters=filters),
                "dsr": tracker_export_payload(user, scope="dsr", search=search, stage=stage, filters=filters),
                "hsr": tracker_export_payload(user, scope="hsr", search=search, stage=stage, filters=filters),
            },
            "capture_defaults": {
                "client_name": company_name,
                "recruiter": default_recruiter_name(user),
                "source": "naukri",
            },
            "tools": {
                "intelligent_search": intelligent_search_payload(
                    search=search,
                    stage=stage,
                    jobs=filtered_jobs,
                    candidates=filtered_candidates,
                    tracker_rows=tracker_rows,
                ),
                "talent_crm": talent_crm_payload(tracker_all_rows),
                "fraud_and_compliance": fraud_and_compliance_payload(
                    tracker_all_rows,
                    interviews,
                    detail_mode=detail,
                    allow_full_context=allow_full,
                ),
                "workforce_planning": workforce_planning_payload(jobs, tracker_all_rows),
                "candidate_intelligence": candidate_intelligence,
                "vendor_landscape": vendor_market_map_payload(),
            },
        }
        base["recruitment_vault"] = recruitment_vault_status_payload(user)
        base["recruiter_reporting"] = recruiter_reporting_payload(user, filters)
        base["ats_console"] = {
            "search": search,
            "stage": stage,
            "detail": detail,
            "allow_full_context": allow_full,
            "disclosure_note": (
                "Full candidate context is enabled for this session."
                if allow_full and detail == "full"
                else "Candidate views are privacy-filtered. Enable full context only when you need deeper data."
            ),
            "suggestions": suggestions,
            "stats": {
                "ats_candidates": len(candidates),
                "visible_candidates": len(filtered_candidates),
                "open_roles": len([row for row in jobs if row.get("status") == "open"]),
                "visible_roles": len(filtered_jobs),
                "tracker_rows": tracker_summary["totals"]["rows"],
                "tracker_duplicates": tracker_summary["totals"]["duplicates"],
                "intelligence_candidates": candidate_intelligence["stats"]["tracked_candidates"],
            },
        }
        return base

    def agent_console_seed_context(filters: Optional[Dict[str, Any]] = None, message: str = "") -> str:
        filters = filters or {}
        detail = (filters.get("detail") or "guided").strip().lower()
        allow_full = bool(filters.get("allow_full_context"))
        search = (filters.get("search") or "").strip()
        stage = (filters.get("stage") or "").strip()
        disclosure = "full" if detail == "full" and allow_full else detail
        return (
            f"Recruitment core:\n{seed_brief('agent', audience='member', limit=5, extra_query=f'{search} {stage} {message}'.strip())}\n\n"
            f"Disclosure mode: {disclosure}\n"
            f"Filtered search: {search or 'none'}\n"
            f"Stage focus: {stage or 'all'}\n"
            "Use ATS data precisely. Do not reveal more candidate information than requested."
        )

    ensure_tables()
    seed_brains()

    @app.get("/api/agent/seed-pack")
    async def get_agent_seed_pack(request: Request):
        require_member(request)
        return seed_pack_payload()

    @app.get("/api/agent/learning-health")
    async def get_agent_learning_health(request: Request):
        require_member(request)
        return learning_health_snapshot()

    @app.get("/api/agent/console/state")
    async def get_agent_console_state(
        request: Request,
        search: str = "",
        stage: str = "",
        detail: str = "guided",
        allow_full_context: bool = False,
        date_from: str = "",
        date_to: str = "",
        recruiter: str = "",
        candidate_name: str = "",
        client_name: str = "",
        position: str = "",
        mail_id: str = "",
        contact_no: str = "",
        notice_period: str = "",
        row_id: str = "",
        submission_state: str = "",
        response_status: str = "",
        min_total_exp: str = "",
        max_total_exp: str = "",
        min_ctc: str = "",
        max_ctc: str = "",
    ):
        user = require_member(request)
        return agent_console_state(
            user,
            {
                "search": search,
                "stage": stage,
                "detail": detail,
                "allow_full_context": allow_full_context,
                "date_from": date_from,
                "date_to": date_to,
                "recruiter": recruiter,
                "candidate_name": candidate_name,
                "client_name": client_name,
                "position": position,
                "mail_id": mail_id,
                "contact_no": contact_no,
                "notice_period": notice_period,
                "row_id": row_id,
                "submission_state": submission_state,
                "response_status": response_status,
                "min_total_exp": min_total_exp,
                "max_total_exp": max_total_exp,
                "min_ctc": min_ctc,
                "max_ctc": max_ctc,
            },
        )

    @app.get("/api/recruitment/candidate-intelligence")
    async def get_candidate_intelligence(request: Request, search: str = "", stage: str = ""):
        user = require_member(request)
        return candidate_intelligence_payload(user, search=search, stage=stage)

    def capture_candidate_intent_for_user(user: Dict[str, Any], req: NetworkCandidateIntentReq) -> Dict[str, Any]:
        signal = upsert_candidate_signal(
            user,
            content=req.content,
            candidate_name=req.candidate_name,
            mail_id=req.mail_id,
            contact_no=req.contact_no,
            target_role=req.target_role,
            current_company=req.current_company,
            current_location=req.current_location,
            preferred_location=req.preferred_location,
            total_exp=req.total_exp,
            relevant_exp=req.relevant_exp,
            notice_period=req.notice_period,
            notice_state=req.notice_state,
            current_ctc=req.current_ctc,
            expected_ctc=req.expected_ctc,
            applications_count=req.applications_count,
            interviews_count=req.interviews_count,
            offers_count=req.offers_count,
            source_kind=req.source_kind,
            network_post_id=req.post_id,
            auto_forward_to_ats=req.auto_forward_to_ats,
        )
        if not signal.get("captured"):
            return {"captured": False, "message": signal.get("reason", "No clear candidate intent was stored.")}
        refresh_recruitment_reporting(user)
        return {
            "captured": True,
            "message": "Candidate career intent was stored locally and forwarded into the ATS memory lane.",
            "signal": signal,
        }

    @app.post("/api/network/candidate-intent")
    async def capture_network_candidate_intent(req: NetworkCandidateIntentReq, request: Request):
        user = require_member(request)
        return capture_candidate_intent_for_user(user, req)

    @app.post("/api/member-network/candidate-intent")
    async def capture_member_network_candidate_intent(req: NetworkCandidateIntentReq, request: Request):
        user = require_member(request)
        return capture_candidate_intent_for_user(user, req)

    @app.post("/api/agent/console/chat")
    async def agent_console_chat(req: AgentConsoleChatReq, request: Request):
        user = require_member(request)
        message = (req.message or "").strip()
        if not message:
            raise HTTPException(status_code=400, detail="Message is required.")
        message_lower = message.lower()
        chat_filters = {
            "search": req.search,
            "stage": req.stage,
            "detail": req.detail,
            "allow_full_context": req.allow_full_context,
            "date_from": req.date_from,
            "date_to": req.date_to,
            "recruiter": req.recruiter,
            "candidate_name": req.candidate_name,
            "client_name": req.client_name,
            "position": req.position,
            "mail_id": req.mail_id,
            "contact_no": req.contact_no,
            "notice_period": req.notice_period,
            "row_id": req.row_id,
            "submission_state": req.submission_state,
            "response_status": req.response_status,
            "min_total_exp": req.min_total_exp,
            "max_total_exp": req.max_total_exp,
            "min_ctc": req.min_ctc,
            "max_ctc": req.max_ctc,
        }
        console_state = agent_console_state(
            user,
            chat_filters,
        )
        visible_candidates = console_state.get("candidates", [])
        visible_jobs = console_state.get("jobs", [])
        concept_terms = (
            "what is", "explain", "difference", "meaning", "notice period", "active candidate", "passive candidate",
            "total experience", "relevant experience", "work culture", "language", "religion", "rights",
            "government job", "private job", "screening", "interview", "sourcing", "region", "country",
            "population", "location", "district", "state", "why people", "next job", "lifestyle",
        )
        lookup_terms = (
            "find candidate", "show candidate", "shortlist", "share profile", "who fits", "hire for",
            "recruit for", "candidate for", "profiles for", "source candidate", "search candidate",
        )
        is_concept_query = any(term in message_lower for term in concept_terms)
        is_lookup_query = any(term in message_lower for term in lookup_terms)
        if not visible_candidates and is_lookup_query and not is_concept_query:
            if not visible_jobs:
                return {
                    "reply": (
                        "ATS does not have any imported roles or candidates in the current scope yet. "
                        "Run a Praapti hunt, add an ATS role, or import reviewed candidates first. "
                        "If you want precision, tell me the exact role, must-have skills, location, and experience band."
                    ),
                    "provider": "agent-console/local",
                }
            return {
                "reply": (
                    "I can help, but the current ATS slice is still narrow. "
                    "Tell me the exact role title, must-have skills, location, experience range, and stage filter, "
                    "and I will answer only from the visible ATS candidates."
                ),
                "provider": "agent-console/local",
            }
        candidate_lines = "\n".join(
            f"- {row['name']} | {row['title']} | stage {row['stage']} | fit {row['fit_score']} | exp {row['experience']} years"
            for row in visible_candidates[:10]
        ) or "- No visible ATS candidates."
        role_lines = "\n".join(
            f"- {row['title']} | {row['location']} | {row['urgency']} | {row['candidate_count']} linked candidates"
            for row in visible_jobs[:8]
        ) or "- No visible ATS roles."
        tracker_rows = console_state.get("recruitment_tracker", {}).get("rows", [])
        tracker_summary = console_state.get("recruitment_tracker", {}).get("summary", {})
        tools = console_state.get("recruitment_ops", {}).get("tools", {})
        intelligence_rows = console_state.get("candidate_intelligence", {}).get("candidates", [])
        intelligence_focus = any(
            term in message_lower
            for term in (
                "companies applied",
                "applied in",
                "interviews given",
                "offers collected",
                "offer collected",
                "next move",
                "fit for the role",
                "fit for role",
                "candidate intelligence",
                "job change",
            )
        )
        export_scope = ""
        report_filters = parse_report_request_filters_from_message(message)
        merged_report_filters = dict(chat_filters)
        merged_report_filters.update({key: value for key, value in report_filters.items() if value not in {"", None, False}})
        if any(term in message_lower for term in ("dsr", "daily tracker", "daily sheet", "daily report")):
            export_scope = "dsr"
        elif any(term in message_lower for term in ("hsr", "2 hour", "two hour", "2-hour")):
            export_scope = "hsr"
        elif any(term in message_lower for term in ("tracker", "excel", "sheet", "copy paste", "copy-paste", "submission tracker")):
            export_scope = "tracker"
        wants_trail = any(
            term in message_lower
            for term in (
                "complete data",
                "complete trail",
                "discussion",
                "history",
                "what discussed",
                "what did i discuss",
                "who discussed",
                "manager is asking",
            )
        )
        if export_scope:
            if recruiter_access_enabled(user):
                export_data = tracker_export_payload(
                    user,
                    scope=export_scope,
                    search=req.search,
                    stage=req.stage,
                    filters=merged_report_filters,
                )
            elif recruiter_archive_access_enabled(user):
                export_data = archive_tracker_export_payload(
                    user,
                    scope=export_scope,
                    search=req.search,
                    stage=req.stage,
                    filters=merged_report_filters,
                )
            else:
                return {
                    "reply": "Tracker, DSR, HSR, and discussion history are available only inside the recruiter workspace.",
                    "provider": "agent-console/local",
                }
            return {
                "reply": (
                    f"{export_data['headline']}\n\n"
                    "Copy the tab-separated block below into Excel.\n\n"
                    f"{export_data['tsv']}"
                ),
                "provider": "agent-console/local",
            }
        if wants_trail:
            if recruiter_access_enabled(user):
                history = recruiter_reporting_payload(user, merged_report_filters)
            elif recruiter_archive_access_enabled(user):
                history = archive_reporting_payload(user, merged_report_filters)
            else:
                return {
                    "reply": "Discussion trail memory is available only inside the recruiter workspace.",
                    "provider": "agent-console/local",
                }
            lines = [
                f"{item['created_at'][:19]} | {item['candidate_name']} | {item['position']} | {item['summary']}"
                for item in history.get("discussion_trail", {}).get("items", [])[:12]
            ] or ["No discussion trail found for the requested slice."]
            return {
                "reply": (
                    f"{history.get('headline')}\n\n"
                    f"Filtered rows: {history.get('stats', {}).get('filtered_rows', 0)} | "
                    f"Discussion events: {history.get('stats', {}).get('discussion_events', 0)}\n\n"
                    "Recent trail:\n" + "\n".join(lines)
                ),
                "provider": "agent-console/local",
            }
        if intelligence_focus and intelligence_rows:
            lines = [
                (
                    f"{row['candidate_name']}: applied in {row['applications_count']} companies, "
                    f"given {row['interviews_count']} interviews, collected {row['offers_count']} offers, "
                    f"{row['fit_label']} ({row['fit_score']}), next move: {row['next_move']}"
                )
                for row in intelligence_rows[:4]
            ]
            return {
                "reply": "Live candidate intelligence:\n" + "\n".join(lines),
                "provider": "agent-console/local",
            }
        tracker_lines = "\n".join(
            f"- {row['candidate_name']} | {row['position']} | {row['process_stage']} | {row['response_status']} | issues: {', '.join(row.get('issue_flags', [])) or 'none'}"
            for row in tracker_rows[:10]
        ) or "- No tracker rows yet."
        intelligence_lines = "\n".join(
            f"- {row['candidate_name']} | role {row['target_role']} | intent {row['job_change_intent']} | companies {row['applications_count']} | interviews {row['interviews_count']} | offers {row['offers_count']} | fit {row['fit_label']} {row['fit_score']} | next move {row['next_move']}"
            for row in intelligence_rows[:10]
        ) or "- No candidate intelligence rows yet."
        tools_snapshot = json.dumps(
            {
                "search": (tools.get("intelligent_search") or {}).get("stats", {}),
                "crm": (tools.get("talent_crm") or {}).get("stats", {}),
                "fraud": (tools.get("fraud_and_compliance") or {}).get("stats", {}),
                "workforce": (tools.get("workforce_planning") or {}).get("stats", {}),
                "intelligence": (tools.get("candidate_intelligence") or {}).get("stats", {}),
                "market": (tools.get("vendor_landscape") or {}).get("stats", {}),
            },
            ensure_ascii=False,
        )
        generated = await generate_text(
            (
                f"You are {ai_name}, the recruitment operating brain for {company_name}.\n"
                f"Identity: {core_identity}\n\n"
                f"{agent_console_seed_context(req.model_dump(), message=message)}\n\n"
                f"Visible ATS roles:\n{role_lines}\n\n"
                f"Visible ATS candidates:\n{candidate_lines}\n\n"
                f"Recruiter tracker summary:\n{json.dumps(tracker_summary.get('totals', {}), ensure_ascii=False)}\n\n"
                f"Recruiter tracker rows:\n{tracker_lines}\n\n"
                f"Candidate intelligence:\n{intelligence_lines}\n\n"
                f"Recruitment tools snapshot:\n{tools_snapshot}\n\n"
                f"Operator request:\n{message}\n\n"
                "Answer precisely from the visible slice. Default to short human language. If data is missing, ask for the minimum extra detail needed."
            ),
            system=(
                f"You are {ai_name} for {company_name}. "
                "Be exact, privacy-aware, practical, and human. Default to concise replies unless the user asks for depth."
            ),
            max_tokens=320,
            use_web_search=False,
            workspace="agent",
            source="agent_console",
        )
        return {"reply": generated["text"], "provider": generated["provider"]}

    @app.post("/api/recruitment-tracker/update")
    async def update_recruitment_tracker(req: RecruitmentTrackerUpdateReq, request: Request):
        user = require_member(request)
        rows = db_all(
            """
            SELECT * FROM recruitment_tracker_rows
            WHERE id=? AND user_id=?
            LIMIT 1
            """,
            (req.row_id, user["id"]),
        ) or []
        if not rows:
            raise HTTPException(status_code=404, detail="Tracker row not found.")
        row = rows[0]
        previous_stage = row.get("process_stage", "sourced")
        previous_status = row.get("response_status", "pending_review")
        issue_flags = [item for item in req.issue_flags if item in TRACKER_ISSUE_OPTIONS] or parse_issue_flags(row.get("issue_flags"))
        process_stage = req.process_stage or row.get("process_stage", "sourced")
        response_status = req.response_status or row.get("response_status", "pending_review")
        ack_sent_at = row.get("ack_mail_sent_at", "")
        ack_confirmed_at = row.get("ack_confirmed_at", "")
        submission_state = normalized_submission_state(
            existing_state=req.submission_state or row.get("submission_state", "draft"),
            ack_action=req.ack_action,
            ack_sent_at=ack_sent_at,
            ack_confirmed_at=ack_confirmed_at,
        )
        profile_sharing_date = row.get("profile_sharing_date", "")
        if req.ack_action == "sent":
            ack_sent_at = now_iso()
            submission_state = "ack_sent"
            if response_status in {"pending_review", "pending_outreach"}:
                response_status = "shared"
        elif req.ack_action == "confirmed":
            ack_confirmed_at = now_iso()
            if not ack_sent_at:
                ack_sent_at = now_iso()
            submission_state = "confirmed"
            response_status = "ack_confirmed"
            if not profile_sharing_date:
                profile_sharing_date = now_iso()
            if process_stage in {"", "sourced"}:
                process_stage = "profile_shared"
        elif req.ack_action == "prepared":
            submission_state = "ack_prepared"
        follow_up_due_at = clean_text(req.follow_up_due_at or row.get("follow_up_due_at", ""), 80) or derive_follow_up_due(
            process_stage=process_stage,
            response_status=response_status,
            submission_state=submission_state,
        )

        db_exec(
            """
            UPDATE recruitment_tracker_rows
            SET process_stage=?,
                response_status=?,
                recruiter=?,
                sourced_from=?,
                client_name=?,
                position=?,
                contact_no=?,
                mail_id=?,
                current_company=?,
                current_location=?,
                preferred_location=?,
                total_exp=?,
                relevant_exp=?,
                notice_period=?,
                notice_state=?,
                current_ctc=?,
                expected_ctc=?,
                client_spoc=?,
                remarks=?,
                last_discussion=?,
                issue_flags=?,
                ack_mail_sent_at=?,
                ack_confirmed_at=?,
                submission_state=?,
                resume_document_id=?,
                resume_file_name=?,
                skill_snapshot=?,
                role_scope=?,
                follow_up_due_at=?,
                profile_sharing_date=?,
                updated_at=?
            WHERE id=? AND user_id=?
            """,
            (
                process_stage,
                response_status,
                req.recruiter or row.get("recruiter", default_recruiter_name(user)),
                req.sourced_from or row.get("sourced_from", "manual"),
                req.client_name or row.get("client_name", company_name),
                req.position or row.get("position", ""),
                req.contact_no or row.get("contact_no", ""),
                req.mail_id or row.get("mail_id", ""),
                req.current_company or row.get("current_company", ""),
                req.current_location or row.get("current_location", ""),
                req.preferred_location or row.get("preferred_location", ""),
                req.total_exp or row.get("total_exp", 0),
                req.relevant_exp or row.get("relevant_exp", 0),
                req.notice_period or row.get("notice_period", ""),
                req.notice_state or row.get("notice_state", ""),
                req.current_ctc or row.get("current_ctc", 0),
                req.expected_ctc or row.get("expected_ctc", 0),
                req.client_spoc or row.get("client_spoc", ""),
                req.remarks or row.get("remarks", ""),
                req.last_discussion or row.get("last_discussion", ""),
                json.dumps(issue_flags, ensure_ascii=False),
                ack_sent_at,
                ack_confirmed_at,
                submission_state,
                req.resume_document_id or row.get("resume_document_id", ""),
                req.resume_file_name or row.get("resume_file_name", ""),
                req.skill_snapshot or row.get("skill_snapshot", ""),
                req.role_scope or row.get("role_scope", ""),
                follow_up_due_at,
                profile_sharing_date,
                now_iso(),
                req.row_id,
                user["id"],
            ),
        )
        if row.get("candidate_id"):
            db_exec(
                "UPDATE ats_candidates SET status=?, updated_at=? WHERE id=? AND user_id=?",
                (tracker_stage_for_ats(process_stage, response_status), now_iso(), row.get("candidate_id"), user["id"]),
            )
        if (
            process_stage != previous_stage
            or response_status != previous_status
            or req.last_discussion
            or req.remarks
            or req.ack_action
        ):
            append_journey_event(
                user,
                req.row_id,
                event_type="tracker_update",
                stage=process_stage,
                response_status=response_status,
                summary=clean_text(req.last_discussion or req.remarks or f"{process_stage} | {response_status}", 500),
                details={
                    "issue_flags": issue_flags,
                    "ack_action": req.ack_action,
                    "notice_period": req.notice_period or row.get("notice_period", ""),
                    "expected_ctc": req.expected_ctc or row.get("expected_ctc", 0),
                    "submission_state": submission_state,
                    "follow_up_due_at": follow_up_due_at,
                    "row_snapshot": recruitment_row_snapshot(
                        {
                            **row,
                            "id": req.row_id,
                            "process_stage": process_stage,
                            "response_status": response_status,
                            "submission_state": submission_state,
                            "follow_up_due_at": follow_up_due_at,
                            "remarks": req.remarks or row.get("remarks", ""),
                            "last_discussion": req.last_discussion or row.get("last_discussion", ""),
                            "current_ctc": req.current_ctc or row.get("current_ctc", 0),
                            "expected_ctc": req.expected_ctc or row.get("expected_ctc", 0),
                            "total_exp": req.total_exp or row.get("total_exp", 0),
                            "relevant_exp": req.relevant_exp or row.get("relevant_exp", 0),
                            "notice_period": req.notice_period or row.get("notice_period", ""),
                            "notice_state": req.notice_state or row.get("notice_state", ""),
                            "updated_at": now_iso(),
                        }
                    ),
                },
                actor=req.recruiter or row.get("recruiter", default_recruiter_name(user)),
            )
            record_discussion_log(
                user,
                {
                    **row,
                    "id": req.row_id,
                    "process_stage": process_stage,
                    "response_status": response_status,
                    "submission_state": submission_state,
                    "follow_up_due_at": follow_up_due_at,
                    "remarks": req.remarks or row.get("remarks", ""),
                    "last_discussion": req.last_discussion or row.get("last_discussion", ""),
                    "current_ctc": req.current_ctc or row.get("current_ctc", 0),
                    "expected_ctc": req.expected_ctc or row.get("expected_ctc", 0),
                    "total_exp": req.total_exp or row.get("total_exp", 0),
                    "relevant_exp": req.relevant_exp or row.get("relevant_exp", 0),
                    "notice_period": req.notice_period or row.get("notice_period", ""),
                    "notice_state": req.notice_state or row.get("notice_state", ""),
                    "updated_at": now_iso(),
                },
                event_type="tracker_update",
                transcript=req.last_discussion or req.remarks or f"{process_stage} | {response_status}",
                parsed={
                    "issue_flags": issue_flags,
                    "ack_action": req.ack_action,
                    "submission_state": submission_state,
                    "follow_up_due_at": follow_up_due_at,
                },
                summary=clean_text(req.last_discussion or req.remarks or f"{process_stage} | {response_status}", 500),
            )
        reporting = refresh_recruitment_reporting(user)
        return {"ok": True, "message": "Recruitment tracker updated.", "reporting": reporting}

    @app.post("/api/recruitment-tracker/capture")
    async def capture_recruitment_conversation(req: RecruitmentConversationCaptureReq, request: Request):
        user = require_member(request)
        if not clean_multiline(req.transcript, 6000):
            raise HTTPException(status_code=400, detail="Conversation notes or transcript are required.")
        captured = upsert_conversation_capture(user, req)
        ack = None
        if captured["parsed"].get("ack_ready"):
            try:
                ack = prepare_ack_event(user, captured["row"])
                db_exec(
                    """
                    UPDATE recruitment_tracker_rows
                    SET submission_state=?, follow_up_due_at=?, updated_at=?
                    WHERE id=? AND user_id=?
                    """,
                    (
                        "ack_prepared",
                        derive_follow_up_due(
                            process_stage=captured["row"].get("process_stage", ""),
                            response_status=captured["row"].get("response_status", ""),
                            submission_state="ack_prepared",
                        ),
                        now_iso(),
                        captured["row_id"],
                        user["id"],
                    ),
                )
                captured["row"]["submission_state"] = "ack_prepared"
                append_journey_event(
                    user,
                    captured["row_id"],
                    event_type="ack_prepared",
                    stage=captured["row"].get("process_stage", "screening"),
                    response_status=captured["row"].get("response_status", "interested"),
                    summary="Acknowledgment draft prepared after recruiter conversation.",
                    details={"launch_url": ack.get("launch_url", ""), "subject": ack.get("subject", "")},
                    actor=captured["row"].get("recruiter", default_recruiter_name(user)),
                )
            except HTTPException:
                ack = None
        return {
            "ok": True,
            "message": (
                "Recruiter conversation captured into draft tracker memory."
                if captured["row"].get("submission_state") != "confirmed"
                else "Recruiter conversation captured and confirmed tracker updated."
            ),
            "row_id": captured["row_id"],
            "summary": captured["parsed"].get("summary", ""),
            "parsed": captured["parsed"],
            "candidate_signal": captured.get("signal"),
            "acknowledgment": ack,
            "tracker_export": tracker_export_payload(user, scope="tracker"),
            "reporting": refresh_recruitment_reporting(user),
        }

    @app.post("/api/recruitment-tracker/submit-resume")
    async def submit_recruitment_resume(req: RecruitmentResumeSubmissionReq, request: Request):
        user = require_member(request)
        result = upsert_resume_submission(user, req)
        return {
            "ok": True,
            "message": (
                "Confirmed resume recorded and tracker finalized."
                if result["row"].get("submission_state") == "confirmed"
                else "Resume stored. Tracker is being held in draft memory until acknowledgment is confirmed."
            ),
            "row_id": result["row_id"],
            "summary": result["summary"],
            "row": result["row"],
            "candidate_signal": result["signal"],
            "acknowledgment": result.get("acknowledgment"),
            "tracker_export": tracker_export_payload(user, scope="tracker"),
            "reporting": result.get("reporting") or refresh_recruitment_reporting(user),
        }

    @app.post("/api/recruitment-tracker/prepare-ack")
    async def prepare_recruitment_ack(req: RecruitmentTrackerUpdateReq, request: Request):
        user = require_member(request)
        row = find_tracker_row(user, row_id=req.row_id)
        if not row:
            raise HTTPException(status_code=404, detail="Tracker row not found.")
        ack = prepare_ack_event(user, row)
        db_exec(
            """
            UPDATE recruitment_tracker_rows
            SET submission_state=?, follow_up_due_at=?, updated_at=?
            WHERE id=? AND user_id=?
            """,
            (
                "ack_prepared",
                derive_follow_up_due(
                    process_stage=row.get("process_stage", ""),
                    response_status=row.get("response_status", ""),
                    submission_state="ack_prepared",
                ),
                now_iso(),
                req.row_id,
                user["id"],
            ),
        )
        updated_row = {
            **row,
            "id": req.row_id,
            "submission_state": "ack_prepared",
            "follow_up_due_at": derive_follow_up_due(
                process_stage=row.get("process_stage", ""),
                response_status=row.get("response_status", ""),
                submission_state="ack_prepared",
            ),
            "updated_at": now_iso(),
        }
        append_journey_event(
            user,
            req.row_id,
            event_type="ack_prepared",
            stage=row.get("process_stage", "screening"),
            response_status=row.get("response_status", "interested"),
            summary="Acknowledgment draft prepared manually from recruiter desk.",
            details={"subject": ack.get("subject", ""), "row_snapshot": recruitment_row_snapshot(updated_row)},
            actor=row.get("recruiter", default_recruiter_name(user)),
        )
        record_discussion_log(
            user,
            updated_row,
            event_type="ack_prepared",
            transcript=ack.get("body", ""),
            parsed={"subject": ack.get("subject", ""), "launch_url": ack.get("launch_url", "")},
            summary="Acknowledgment draft prepared manually from recruiter desk.",
        )
        refresh_recruitment_reporting(user)
        return ack

    @app.post("/api/recruitment-tracker/interview")
    async def update_recruitment_interview(req: RecruitmentInterviewUpdateReq, request: Request):
        user = require_member(request)
        row = find_tracker_row(user, row_id=req.row_id)
        if not row:
            raise HTTPException(status_code=404, detail="Tracker row not found.")
        round_label = clean_text(req.interview_round or "L1", 40).upper()
        scheduled_for = clean_text(req.scheduled_for, 80)
        feedback_status = clean_text(req.feedback_status or "pending", 80).lower()
        next_stage = clean_text(req.next_stage, 80) or row.get("process_stage", "screening")
        if feedback_status in {"pending", "requested"}:
            next_stage = {"L1": "l1_interview", "L2": "l2_interview", "L3": "l3_interview"}.get(round_label, "l1_interview")
        record_interview_event(
            user,
            req.row_id,
            interview_round=round_label,
            scheduled_for=scheduled_for,
            mode=req.mode,
            interviewer_name=req.interviewer_name,
            interviewer_email=req.interviewer_email,
            feedback_status=feedback_status,
            feedback_summary=req.feedback_summary,
        )
        db_exec(
            """
            UPDATE recruitment_tracker_rows
            SET process_stage=?, remarks=?, updated_at=?
            WHERE id=? AND user_id=?
            """,
            (
                next_stage,
                clean_text(req.feedback_summary or row.get("remarks", ""), 500),
                now_iso(),
                req.row_id,
                user["id"],
            ),
        )
        if row.get("candidate_id"):
            db_exec(
                "UPDATE ats_candidates SET status=?, updated_at=? WHERE id=? AND user_id=?",
                (tracker_stage_for_ats(next_stage, row.get("response_status", "")), now_iso(), row.get("candidate_id"), user["id"]),
            )
        append_journey_event(
            user,
            req.row_id,
            event_type="interview_update",
            stage=next_stage,
            response_status=row.get("response_status", "pending_review"),
            summary=clean_text(
                req.feedback_summary
                or f"{round_label} interview {'scheduled' if scheduled_for else 'updated'} with feedback status {feedback_status}.",
                500,
            ),
            details={
                "interview_round": round_label,
                "scheduled_for": scheduled_for,
                "mode": req.mode,
                "interviewer_name": req.interviewer_name,
                "feedback_status": feedback_status,
                "row_snapshot": recruitment_row_snapshot(
                    {
                        **row,
                        "id": req.row_id,
                        "process_stage": next_stage,
                        "remarks": clean_text(req.feedback_summary or row.get("remarks", ""), 500),
                        "updated_at": now_iso(),
                    }
                ),
            },
            actor=default_recruiter_name(user),
        )
        record_discussion_log(
            user,
            {
                **row,
                "id": req.row_id,
                "process_stage": next_stage,
                "remarks": clean_text(req.feedback_summary or row.get("remarks", ""), 500),
                "updated_at": now_iso(),
            },
            event_type="interview_update",
            transcript=req.feedback_summary or f"{round_label} interview {feedback_status}",
            parsed={
                "interview_round": round_label,
                "scheduled_for": scheduled_for,
                "mode": req.mode,
                "interviewer_name": req.interviewer_name,
                "feedback_status": feedback_status,
            },
            summary=clean_text(
                req.feedback_summary
                or f"{round_label} interview {'scheduled' if scheduled_for else 'updated'} with feedback status {feedback_status}.",
                500,
            ),
        )
        reporting = refresh_recruitment_reporting(user)
        return {
            "ok": True,
            "message": f"{round_label} interview desk updated.",
            "interview_desk": interview_desk_payload(user),
            "reporting": reporting,
        }

    @app.get("/api/recruitment-tracker/export")
    async def export_recruitment_tracker(
        request: Request,
        scope: str = "tracker",
        search: str = "",
        stage: str = "",
        date_from: str = "",
        date_to: str = "",
        recruiter: str = "",
        candidate_name: str = "",
        client_name: str = "",
        position: str = "",
        mail_id: str = "",
        contact_no: str = "",
        notice_period: str = "",
        row_id: str = "",
        submission_state: str = "",
        response_status: str = "",
        min_total_exp: str = "",
        max_total_exp: str = "",
        min_ctc: str = "",
        max_ctc: str = "",
    ):
        user = require_member(request)
        filters = {
            "date_from": date_from,
            "date_to": date_to,
            "recruiter": recruiter,
            "candidate_name": candidate_name,
            "client_name": client_name,
            "position": position,
            "mail_id": mail_id,
            "contact_no": contact_no,
            "notice_period": notice_period,
            "row_id": row_id,
            "submission_state": submission_state,
            "response_status": response_status,
            "min_total_exp": min_total_exp,
            "max_total_exp": max_total_exp,
            "min_ctc": min_ctc,
            "max_ctc": max_ctc,
        }
        if recruiter_access_enabled(user):
            return tracker_export_payload(user, scope=scope, search=search, stage=stage, filters=filters)
        if recruiter_archive_access_enabled(user):
            return archive_tracker_export_payload(user, scope=scope, search=search, stage=stage, filters=filters)
        raise HTTPException(status_code=403, detail="Recruiter reporting is available only inside the recruiter workspace.")

    @app.get("/api/recruitment-tracker/history")
    async def recruitment_tracker_history(
        request: Request,
        date_from: str = "",
        date_to: str = "",
        recruiter: str = "",
        candidate_name: str = "",
        client_name: str = "",
        position: str = "",
        mail_id: str = "",
        contact_no: str = "",
        notice_period: str = "",
        row_id: str = "",
        submission_state: str = "",
        response_status: str = "",
        min_total_exp: str = "",
        max_total_exp: str = "",
        min_ctc: str = "",
        max_ctc: str = "",
    ):
        user = require_member(request)
        filters = {
            "date_from": date_from,
            "date_to": date_to,
            "recruiter": recruiter,
            "candidate_name": candidate_name,
            "client_name": client_name,
            "position": position,
            "mail_id": mail_id,
            "contact_no": contact_no,
            "notice_period": notice_period,
            "row_id": row_id,
            "submission_state": submission_state,
            "response_status": response_status,
            "min_total_exp": min_total_exp,
            "max_total_exp": max_total_exp,
            "min_ctc": min_ctc,
            "max_ctc": max_ctc,
        }
        if recruiter_access_enabled(user):
            return recruiter_reporting_payload(user, filters)
        if recruiter_archive_access_enabled(user):
            return archive_reporting_payload(user, filters)
        raise HTTPException(status_code=403, detail="Recruiter reporting is available only inside the recruiter workspace.")

    @app.get("/api/recruitment-vault/status")
    async def recruitment_vault_status(request: Request):
        user = require_member(request)
        return recruitment_vault_status_payload(user)

    @app.get("/api/recruitment-vault/archive-status")
    async def recruitment_vault_archive_status(request: Request, archive_id: str = ""):
        user = require_member(request)
        if not recruiter_archive_access_enabled(user):
            raise HTTPException(status_code=403, detail="No sealed recruiter archive is available for this account.")
        archive = recruitment_archive_record(user["id"], archive_id)
        if not archive:
            return {
                "available": False,
                "headline": "No sealed recruiter archive is available yet.",
                "archive": {},
            }
        manifest = load_recruitment_archive_manifest(archive)
        tracker_rows = archived_tracker_rows(manifest)
        discussion = archived_discussion_payload(manifest, limit=12)
        snapshots = archived_report_snapshots_payload(manifest, limit=8)
        return {
            "available": True,
            "headline": "Read-only recruiter archive recall is ready.",
            "archive": archive_preview_payload(archive),
            "stats": {
                "records": len(tracker_rows),
                "discussion_events": discussion.get("count", 0),
                "snapshots": snapshots.get("count", 0),
            },
        }

    @app.post("/api/recruitment-vault/server-sync")
    async def recruitment_vault_server_sync(request: Request):
        user = require_member(request)
        archive = create_recruitment_vault_archive(user, archive_kind="server_sync")
        return {
            "message": "The mother-brain server archive was refreshed from the operational local lane.",
            "archive": archive,
            "vault": recruitment_vault_status_payload(user),
        }

    @app.get("/api/recruitment-vault/export")
    async def recruitment_vault_export(request: Request, archive_id: str = ""):
        user = require_member(request)
        archive = None
        if archive_id:
            rows = db_all(
                """
                SELECT *
                FROM recruitment_vault_archives
                WHERE id=? AND user_id=?
                LIMIT 1
                """,
                (archive_id, user["id"]),
            ) or []
            if not rows:
                raise HTTPException(status_code=404, detail="Vault archive not found.")
            archive = rows[0]
            file_path = Path(archive.get("file_path", ""))
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="Vault archive file is missing.")
            archive_bytes = file_path.read_bytes()
            archive_name = archive.get("archive_name", "recruitment-vault.zip")
        else:
            archive = create_recruitment_vault_archive(user, archive_kind="manual_export")
            file_path = Path(archive.get("file_path", ""))
            archive_bytes = file_path.read_bytes()
            archive_name = archive.get("archive_name", "recruitment-vault.zip")
        headers = {
            "Content-Disposition": f'attachment; filename="{archive_name}"',
            "X-TechBuzz-Vault": archive.get("archive_hash", ""),
        }
        return StreamingResponse(io.BytesIO(archive_bytes), media_type="application/zip", headers=headers)

    @app.get("/api/recruitment-vault/archive-export")
    async def recruitment_vault_archive_export(
        request: Request,
        scope: str = "tracker",
        search: str = "",
        stage: str = "",
        date_from: str = "",
        date_to: str = "",
        recruiter: str = "",
        candidate_name: str = "",
        client_name: str = "",
        position: str = "",
        mail_id: str = "",
        contact_no: str = "",
        notice_period: str = "",
        row_id: str = "",
        submission_state: str = "",
        response_status: str = "",
        min_total_exp: str = "",
        max_total_exp: str = "",
        min_ctc: str = "",
        max_ctc: str = "",
        archive_id: str = "",
    ):
        user = require_member(request)
        if not recruiter_archive_access_enabled(user):
            raise HTTPException(status_code=403, detail="No sealed recruiter archive is available for this account.")
        filters = {
            "date_from": date_from,
            "date_to": date_to,
            "recruiter": recruiter,
            "candidate_name": candidate_name,
            "client_name": client_name,
            "position": position,
            "mail_id": mail_id,
            "contact_no": contact_no,
            "notice_period": notice_period,
            "row_id": row_id,
            "submission_state": submission_state,
            "response_status": response_status,
            "min_total_exp": min_total_exp,
            "max_total_exp": max_total_exp,
            "min_ctc": min_ctc,
            "max_ctc": max_ctc,
        }
        return archive_tracker_export_payload(user, scope=scope, search=search, stage=stage, filters=filters, archive_id=archive_id)

    @app.get("/api/recruitment-vault/archive-history")
    async def recruitment_vault_archive_history(
        request: Request,
        date_from: str = "",
        date_to: str = "",
        recruiter: str = "",
        candidate_name: str = "",
        client_name: str = "",
        position: str = "",
        mail_id: str = "",
        contact_no: str = "",
        notice_period: str = "",
        row_id: str = "",
        submission_state: str = "",
        response_status: str = "",
        min_total_exp: str = "",
        max_total_exp: str = "",
        min_ctc: str = "",
        max_ctc: str = "",
        archive_id: str = "",
    ):
        user = require_member(request)
        if not recruiter_archive_access_enabled(user):
            raise HTTPException(status_code=403, detail="No sealed recruiter archive is available for this account.")
        filters = {
            "date_from": date_from,
            "date_to": date_to,
            "recruiter": recruiter,
            "candidate_name": candidate_name,
            "client_name": client_name,
            "position": position,
            "mail_id": mail_id,
            "contact_no": contact_no,
            "notice_period": notice_period,
            "row_id": row_id,
            "submission_state": submission_state,
            "response_status": response_status,
            "min_total_exp": min_total_exp,
            "max_total_exp": max_total_exp,
            "min_ctc": min_ctc,
            "max_ctc": max_ctc,
        }
        return archive_reporting_payload(user, filters, archive_id=archive_id)

    @app.post("/api/recruitment-vault/import")
    async def recruitment_vault_import(request: Request, file: UploadFile = File(...)):
        user = require_member(request)
        archive_bytes = await file.read()
        if not archive_bytes:
            raise HTTPException(status_code=400, detail="Vault archive file is empty.")
        restored = restore_recruitment_vault(user, archive_bytes)
        return restored

    @app.post("/api/recruitment-vault/clear-local")
    async def recruitment_vault_clear_local(request: Request):
        user = require_member(request)
        return clear_recruitment_operational_data(user, archive_before_clear=True)

    @app.get("/api/action-center/status")
    async def action_center_status(request: Request):
        user = require_member(request)
        return {
            "user": {"id": user["id"], "role": user.get("role", "member")},
            "headline": "Prepare visible actions for mail, browser, Teams, messaging, and calls. Nothing is auto-sent.",
            "actions": ACTION_CENTER_OPTIONS,
            "policy": [
                "Prepare first, open second, send manually.",
                "No hidden app control, no silent calling, no silent messaging.",
                "Use full candidate context only when explicitly enabled.",
            ],
        }

    @app.post("/api/action-center/prepare")
    async def action_center_prepare(req: ActionCenterPrepareReq, request: Request):
        user = require_member(request)
        built = build_action_url(req)
        event_id = new_id("ace")
        db_exec(
            """
            INSERT INTO action_center_events(id,user_id,action_kind,target,subject,body,launch_url,created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                event_id,
                user["id"],
                req.kind,
                req.target[:300],
                req.subject[:300],
                req.body[:1500],
                built["launch_url"][:1500],
                now_iso(),
            ),
        )
        return {
            "id": event_id,
            "kind": req.kind,
            "launch_url": built["launch_url"],
            "label": built["label"],
            "summary": built["summary"],
            "require_confirmation": bool(req.require_confirmation),
            "message": "Action prepared. Review it, then click open when you want the browser or device handler to take over.",
        }

    @app.get("/api/action-center/recent")
    async def action_center_recent(request: Request):
        user = require_member(request)
        events = recent_action_events(user["id"])
        return {"events": events, "count": len(events)}

    async def detect_followup_candidates(user: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow()
        rows = db_all(
            """
            SELECT id, user_id, candidate_name, position, process_stage,
                   response_status, follow_up_due_at, last_contacted_at, updated_at
            FROM recruitment_tracker_rows
            WHERE user_id=?
              AND response_status IN ('interested', 'pending_review', 'no_response')
            """,
            (user["id"],),
        ) or []
        candidates_to_followup = []
        for row in rows:
            follow_up_due_at = (row.get("follow_up_due_at") or "").strip()
            updated_at = (row.get("updated_at") or "").strip()
            response_status = (row.get("response_status") or "").strip()
            is_overdue = False
            reason = ""
            if follow_up_due_at:
                due_dt = parse_iso(follow_up_due_at)
                if due_dt and due_dt <= now:
                    is_overdue = True
                    reason = "Follow-up overdue"
            if not is_overdue and response_status == "interested" and updated_at:
                updated_dt = parse_iso(updated_at)
                if updated_dt and updated_dt <= (now - timedelta(hours=48)):
                    is_overdue = True
                    reason = "No activity for 48+ hours"
            if not is_overdue:
                continue
            candidates_to_followup.append((row, reason))
        new_detected = 0
        tasks = []
        for row, reason in candidates_to_followup:
            existing = db_all(
                "SELECT id FROM follow_up_tasks WHERE user_id=? AND row_id=? AND status='pending' LIMIT 1",
                (user["id"], row["id"]),
            ) or []
            if existing:
                existing_task = db_all(
                    "SELECT * FROM follow_up_tasks WHERE id=? LIMIT 1",
                    (existing[0]["id"],),
                ) or []
                if existing_task:
                    tasks.append(dict(existing_task[0]))
                continue
            prompt = (
                f"Generate a professional follow-up message for a recruitment candidate.\n"
                f"Candidate: {row.get('candidate_name', '')}\n"
                f"Position: {row.get('position', '')}\n"
                f"Current stage: {row.get('process_stage', '')}\n"
                f"Last contact: {row.get('last_contacted_at', '')}\n"
                f"Status: {row.get('response_status', '')}\n"
                f"Keep it warm, professional, and under 100 words. Include a clear call to action."
            )
            try:
                if ishani_generate_text:
                    generated = await ishani_generate_text(
                        prompt,
                        brain_id="recruitment_brain",
                        options={
                            "max_tokens": 200,
                            "mode": "hybrid",
                        },
                    )
                else:
                    generated = await generate_text(
                        prompt,
                        system="You are a professional recruitment assistant. Write concise, warm, and professional follow-up messages.",
                        max_tokens=200,
                        use_web_search=False,
                        workspace="agent",
                        source="followup_assistant",
                    )
                message_draft = generated.get("text", "").strip()
            except Exception:
                message_draft = (
                    f"Hi {row.get('candidate_name', 'there')}, I wanted to follow up regarding the "
                    f"{row.get('position', 'position')} opportunity. Please let me know if you are still interested "
                    f"and if you have any questions. Looking forward to hearing from you."
                )
            task_id = new_id("fut")
            db_exec(
                """
                INSERT INTO follow_up_tasks(id, user_id, row_id, candidate_name, position, reason, message_draft, status, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    task_id,
                    user["id"],
                    row["id"],
                    row.get("candidate_name", ""),
                    row.get("position", ""),
                    reason,
                    message_draft,
                    now_iso(),
                ),
            )
            new_detected += 1
            tasks.append({
                "id": task_id,
                "user_id": user["id"],
                "row_id": row["id"],
                "candidate_name": row.get("candidate_name", ""),
                "position": row.get("position", ""),
                "reason": reason,
                "message_draft": message_draft,
                "status": "pending",
                "created_at": now_iso(),
                "completed_at": None,
            })
        return {"tasks": tasks, "total": len(tasks), "new_detected": new_detected}

    @app.get("/api/recruitment/followup-assistant/scan")
    async def followup_scan(request: Request):
        user = require_member(request)
        result = await detect_followup_candidates(user)
        return result

    @app.get("/api/recruitment/followup-assistant/tasks")
    async def followup_tasks(request: Request, status: str = "pending"):
        user = require_member(request)
        allowed_statuses = {"pending", "completed", "dismissed"}
        status = status if status in allowed_statuses else "pending"
        rows = db_all(
            "SELECT * FROM follow_up_tasks WHERE user_id=? AND status=? ORDER BY created_at DESC",
            (user["id"], status),
        ) or []
        return {"tasks": [dict(r) for r in rows], "total": len(rows)}

    @app.post("/api/recruitment/followup-assistant/complete")
    async def followup_complete(request: Request):
        user = require_member(request)
        body = await request.json()
        task_id = clean_text(body.get("task_id", ""), 80)
        if not task_id:
            raise HTTPException(status_code=400, detail="task_id is required")
        row = db_all("SELECT * FROM follow_up_tasks WHERE id=? AND user_id=? LIMIT 1", (task_id, user["id"])) or []
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        db_exec(
            "UPDATE follow_up_tasks SET status='completed', completed_at=? WHERE id=? AND user_id=?",
            (now_iso(), task_id, user["id"]),
        )
        updated = db_all("SELECT * FROM follow_up_tasks WHERE id=? AND user_id=? LIMIT 1", (task_id, user["id"])) or []
        return {"task": dict(updated[0])}

    @app.post("/api/recruitment/followup-assistant/dismiss")
    async def followup_dismiss(request: Request):
        user = require_member(request)
        body = await request.json()
        task_id = clean_text(body.get("task_id", ""), 80)
        if not task_id:
            raise HTTPException(status_code=400, detail="task_id is required")
        row = db_all("SELECT * FROM follow_up_tasks WHERE id=? AND user_id=? LIMIT 1", (task_id, user["id"])) or []
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        db_exec(
            "UPDATE follow_up_tasks SET status='dismissed', completed_at=? WHERE id=? AND user_id=?",
            (now_iso(), task_id, user["id"]),
        )
        updated = db_all("SELECT * FROM follow_up_tasks WHERE id=? AND user_id=? LIMIT 1", (task_id, user["id"])) or []
        return {"task": dict(updated[0])}

    @app.post("/api/recruitment/followup-assistant/regenerate")
    async def followup_regenerate(request: Request):
        user = require_member(request)
        body = await request.json()
        task_id = clean_text(body.get("task_id", ""), 80)
        if not task_id:
            raise HTTPException(status_code=400, detail="task_id is required")
        row = db_all("SELECT * FROM follow_up_tasks WHERE id=? AND user_id=? LIMIT 1", (task_id, user["id"])) or []
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        task = dict(row[0])
        prompt = (
            f"Generate a professional follow-up message for a recruitment candidate.\n"
            f"Candidate: {task.get('candidate_name', '')}\n"
            f"Position: {task.get('position', '')}\n"
            f"Reason for follow-up: {task.get('reason', '')}\n"
            f"Keep it warm, professional, and under 100 words. Include a clear call to action."
        )
        try:
            generated = await generate_text(
                prompt,
                system="You are a professional recruitment assistant. Write concise, warm, and professional follow-up messages.",
                max_tokens=200,
                use_web_search=False,
                workspace="agent",
                source="followup_assistant",
            )
            message_draft = generated.get("text", "").strip()
        except Exception:
            message_draft = task.get("message_draft", "")
        db_exec(
            "UPDATE follow_up_tasks SET message_draft=? WHERE id=? AND user_id=?",
            (message_draft, task_id, user["id"]),
        )
        updated = db_all("SELECT * FROM follow_up_tasks WHERE id=? AND user_id=? LIMIT 1", (task_id, user["id"])) or []
        return {"task": dict(updated[0]) if updated else task}

    return {
        "seed_brief": seed_brief,
        "learning_health_snapshot": learning_health_snapshot,
        "seed_pack_payload": seed_pack_payload,
        "agent_console_state": agent_console_state,
    }
