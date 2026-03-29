import io
import uuid
from typing import Any, Dict

from fastapi.testclient import TestClient

import app as techbuzz_app


MASTER_IDENTIFIER = "MasterPiyushMani"
MASTER_PASSWORD = "icbaq00538"


def json_of(response) -> Dict[str, Any]:
    try:
        return response.json()
    except Exception:
        return {}


def main() -> int:
    public_client = TestClient(techbuzz_app.app)
    master_client = TestClient(techbuzz_app.app)
    member_client = TestClient(techbuzz_app.app)

    checks_run = 0

    def check(condition: bool, message: str) -> None:
        nonlocal checks_run
        checks_run += 1
        if not condition:
            raise AssertionError(f"[{checks_run}] {message}")

    suffix = uuid.uuid4().hex[:8]
    member_email = f"candidate.{suffix}@example.com"
    company_email = f"company.owner.{suffix}@example.com"
    company_name = f"TechBuzz Scenario Lab {suffix}"

    # Public and auth scenarios
    response = public_client.get("/")
    check(response.status_code == 200, "Landing page should be public.")
    response = public_client.get("/login")
    check(response.status_code == 200, "Login page should be public.")
    response = public_client.get("/career")
    check(response.status_code == 200, "Career page should be public.")
    response = public_client.get("/jobs")
    check(response.status_code == 200, "Jobs page should be public.")
    response = public_client.get("/company/portal")
    check(response.status_code == 200, "Company portal should be public.")
    response = public_client.get("/network")
    check(response.status_code == 200, "Member network page should be public/readable.")
    response = public_client.get("/network/intel", follow_redirects=False)
    check(response.status_code in {302, 307}, "Recruiter intel page should be protected.")
    response = public_client.get("/leazy", follow_redirects=False)
    check(response.status_code in {302, 307}, "Leazy should be protected.")
    response = public_client.get("/ats", follow_redirects=False)
    check(response.status_code in {302, 307}, "ATS should be protected.")
    response = public_client.get("/agent/console", follow_redirects=False)
    check(response.status_code in {302, 307}, "Agent console should be protected.")
    response = public_client.get("/api/member-network/public-state")
    check(response.status_code == 200, "Public member-network state should be readable.")
    response = public_client.get("/api/member-network/state")
    check(response.status_code == 401, "Private member-network state should require login.")
    response = public_client.post("/api/member-network/connect", json={"name": "Blocked", "title": "Guest"})
    check(response.status_code == 401, "Guest should not add member-network connections.")
    response = public_client.post("/api/network/candidate-intent", json={"content": "I want a change"})
    check(response.status_code in {401, 403}, "Guest should not capture candidate intent.")

    # Master + member login flows
    response = master_client.post(
        "/api/auth/master-login",
        json={"identifier": MASTER_IDENTIFIER, "password": MASTER_PASSWORD},
    )
    check(response.status_code == 200, "Master login should succeed.")
    response = member_client.post(
        "/api/auth/register",
        json={"name": "Rahul Sharma", "email": member_email, "password": "TechBuzz123!", "plan_id": "starter"},
    )
    check(response.status_code == 200, "Member registration should succeed.")
    response = member_client.post(
        "/api/auth/login",
        json={"email": member_email, "password": "TechBuzz123!"},
    )
    check(response.status_code == 200, "Member login should succeed.")
    response = member_client.get("/network")
    check(response.status_code == 200, "Member should access the community network page.")
    response = member_client.get("/network/intel", follow_redirects=False)
    check(response.status_code in {302, 307}, "Non-master member should be redirected away from recruiter intel.")
    response = member_client.get("/api/network/state")
    check(response.status_code in {403, 401}, "Non-master member should not access recruiter intel API.")

    # Company and jobs
    response = master_client.post(
        "/api/company/register",
        json={
            "name": company_name,
            "owner_name": "Piyush Mani",
            "owner_email": company_email,
            "plan": "growth",
        },
    )
    company_json = json_of(response)
    check(response.status_code == 200, "Company registration should succeed.")
    slug = company_json["slug"]
    api_key = company_json["api_key"]
    check(bool(slug), "Company slug should be returned.")
    check(bool(api_key), "Company API key should be returned.")

    job_payloads = [
        {
            "title": "Senior Java Developer",
            "location": "Bangalore",
            "remote": "hybrid",
            "job_type": "full-time",
            "experience_min": 5,
            "experience_max": 9,
            "salary_min": 1800000,
            "salary_max": 2600000,
            "skills": "java, spring boot, microservices, kafka, oracle",
            "description": "Need a strong backend engineer for product and delivery ownership.",
            "requirements": "Must have core Java, Spring Boot, Microservices and hands-on production support.",
            "department": "Engineering",
            "openings": 2,
            "closes_at": "",
        },
        {
            "title": "Tech Recruiter",
            "location": "Noida",
            "remote": "onsite",
            "job_type": "full-time",
            "experience_min": 2,
            "experience_max": 6,
            "salary_min": 500000,
            "salary_max": 900000,
            "skills": "it recruitment, sourcing, naukri, linkedin, screening",
            "description": "Own end-to-end sourcing and submission flow for niche hiring.",
            "requirements": "Need recruiter who can manage tracker, sourcing, and stakeholder communication.",
            "department": "Talent Acquisition",
            "openings": 1,
            "closes_at": "",
        },
    ]
    job_ids = []
    for payload in job_payloads:
        response = master_client.post(f"/api/company/{slug}/job", json=payload)
        data = json_of(response)
        check(response.status_code == 200, f"Company job post should succeed for {payload['title']}.")
        check(bool(data.get("job_id")), f"Job ID should be returned for {payload['title']}.")
        job_ids.append(data["job_id"])

    response = master_client.get(f"/api/company/{slug}/jobs")
    jobs_json = json_of(response)
    check(response.status_code == 200, "Company jobs endpoint should work.")
    check(len(jobs_json.get("jobs", [])) >= 2, "Company should see both posted jobs.")
    response = public_client.get("/api/member-network/public-state")
    public_state = json_of(response)
    check(public_state.get("stats", {}).get("openings", 0) >= 2, "Public member network should expose live openings.")
    check(public_state.get("stats", {}).get("companies", 0) >= 1, "Public member network should expose active companies.")

    # Member network lane
    response = member_client.get("/api/member-network/state")
    member_state = json_of(response)
    check(response.status_code == 200, "Member network state should load after login.")
    check(member_state.get("auth", {}).get("authenticated") is True, "Member network state should report auth true.")
    check(member_state.get("viewer", {}).get("email") == member_email, "Member state should map the logged-in member.")
    check(member_state.get("stats", {}).get("connections", 0) == 0, "Fresh member should start with zero connections.")

    response = member_client.post(
        "/api/member-network/connect",
        json={"name": "Ritu Sinha", "title": "Talent Lead", "company": "FinEdge", "linkedin": "linkedin.com/in/ritu"},
    )
    check(response.status_code == 200, "Member should add a network connection.")
    response = member_client.get("/api/member-network/state")
    member_state = json_of(response)
    check(member_state.get("stats", {}).get("connections", 0) == 1, "Connection count should increment.")

    response = member_client.post(
        "/api/member-network/post",
        json={"content": "Learning advanced Java and open to product engineering roles in Bangalore.", "kind": "career_update"},
    )
    post_json = json_of(response)
    check(response.status_code == 200, "Member should publish a network update.")
    check(bool(post_json.get("id")), "Member post should return an id.")
    check(bool(post_json.get("enhanced")), "Member post should return enhanced text.")
    response = member_client.post(f"/api/member-network/posts/{post_json['id']}/like", json={})
    check(response.status_code == 200, "Member should be able to like a stored post.")
    response = member_client.get("/api/member-network/state")
    member_state = json_of(response)
    check(member_state.get("stats", {}).get("posts", 0) >= 1, "Member network state should show stored posts.")

    response = member_client.post(
        "/api/member-network/candidate-intent",
        json={
            "content": "Sharing a market update about Java hiring this week.",
            "source_kind": "network_post",
            "auto_forward_to_ats": True,
        },
    )
    generic_intent = json_of(response)
    check(response.status_code == 200, "Generic member network capture should respond.")
    check(generic_intent.get("captured") is False, "Generic network chatter should not create a candidate record.")

    response = member_client.post(
        "/api/candidate/resume-sync",
        json={
            "email": member_email,
            "full_name": "Rahul Sharma",
            "phone": "+919999999999",
            "resume_text": "8 years Java Spring Boot Microservices Kafka Oracle. Production support. Backend APIs. Team handling.",
            "target_role": "Senior Java Developer",
            "target_jd": "Need a strong backend engineer for product engineering, microservices, Kafka and Oracle support.",
            "current_company": "Infosys",
            "current_role": "Senior Software Engineer",
            "current_location": "Pune",
            "preferred_location": "Bangalore",
            "notice_period": "30 days",
            "current_ctc": "18 LPA",
            "expected_ctc": "24 LPA",
            "linkedin_url": "https://linkedin.com/in/rahulsharma",
            "job_change_intent": "active",
        },
    )
    resume_sync = json_of(response)
    check(response.status_code == 200, "Resume sync should succeed.")
    check(resume_sync.get("stats", {}).get("applications") == 0, "Resume sync should not create fake applications.")
    check(bool(resume_sync.get("alignment", {}).get("aligned_resume")), "Resume sync should produce aligned resume text.")
    check(bool(resume_sync.get("recommended_jobs")), "Resume sync should recommend jobs.")

    response = member_client.post(
        "/api/member-network/candidate-intent",
        json={
            "content": "Rahul Sharma is actively looking for job change for Senior Java Developer role. Current company Infosys. Current location Pune. Preferred location Bangalore. Total exp 8 years. Relevant exp 6 years. Notice period 30 days. Applied in 4 companies. Given 2 interviews. Holding 1 offer.",
            "candidate_name": "Rahul Sharma",
            "mail_id": member_email,
            "contact_no": "+919999999999",
            "source_kind": "member_network_post",
            "auto_forward_to_ats": True,
        },
    )
    intent_json = json_of(response)
    check(response.status_code == 200, "Explicit job-change intent should be captured.")
    check(intent_json.get("captured") is True, "Explicit job-change intent should create a candidate signal.")
    check(intent_json.get("signal", {}).get("job_change_intent") == "active", "Intent should be marked active.")
    check(intent_json.get("signal", {}).get("offers_count") == 1, "Offer count should be stored from intent.")

    # Applications and dashboards
    application_ids = []
    for job_id in job_ids:
        response = member_client.post(
            f"/api/jobs/{job_id}/apply",
            json={
                "applicant_name": "Rahul Sharma",
                "applicant_email": member_email,
                "applicant_phone": "+919999999999",
                "resume_text": "8 years Java Spring Boot Microservices Kafka Oracle. Production support. Backend APIs. Team handling.",
                "cover_letter": "Open for product engineering roles in Bangalore and recruitment automation roles.",
                "experience_years": 8,
                "current_company": "Infosys",
                "current_role": "Senior Software Engineer",
                "notice_period": "30 days",
                "expected_salary": "24 LPA",
                "linkedin_url": "https://linkedin.com/in/rahulsharma",
                "portfolio_url": "",
            },
        )
        apply_json = json_of(response)
        check(response.status_code == 200, f"Applying to {job_id} should succeed.")
        check(bool(apply_json.get("verdict")), "Apply should return screening verdict.")
        check(bool(apply_json.get("profile_id")), "Apply should return linked profile id.")
        check(bool(apply_json.get("journey_id")), "Apply should return linked journey id.")
        application_ids.append(apply_json["application_id"])

    response = member_client.get(f"/api/candidate/dashboard?email={member_email}")
    dashboard_json = json_of(response)
    check(response.status_code == 200, "Candidate dashboard should load.")
    check(dashboard_json.get("stats", {}).get("applications") == 2, "Candidate dashboard should show both applications.")
    check(dashboard_json.get("stats", {}).get("companies") >= 1, "Candidate dashboard should count companies.")
    check(len(dashboard_json.get("journeys", [])) >= 2, "Candidate dashboard should include journey rows.")
    check(bool(dashboard_json.get("recommended_jobs")), "Candidate dashboard should include recommended jobs.")

    response = member_client.get("/api/member-network/state")
    member_state = json_of(response)
    check(member_state.get("stats", {}).get("applications") == 2, "Member network state should sync application count.")
    check(bool(member_state.get("profile", {}).get("full_name")), "Member network state should include profile summary.")
    check(bool(member_state.get("next_move")), "Member network state should include next move guidance.")
    check(len(member_state.get("journeys", [])) >= 2, "Member network state should surface journey history.")

    # Company-side review
    response = master_client.get(f"/api/company/{slug}/analytics")
    analytics_json = json_of(response)
    check(response.status_code == 200, "Company analytics should load.")
    check(analytics_json.get("stats", {}).get("applications", 0) >= 2, "Company analytics should count both applications.")
    check(analytics_json.get("stats", {}).get("jobs", 0) >= 2, "Company analytics should count both jobs.")
    check(len(analytics_json.get("talent_map_preview", {}).get("matches", [])) >= 1, "Company analytics should expose talent preview.")

    response = master_client.get(f"/api/company/{slug}/candidates")
    candidates_json = json_of(response)
    check(response.status_code == 200, "Company candidates endpoint should load.")
    check(len(candidates_json.get("candidates", [])) >= 2, "Company candidates endpoint should list applications.")

    response = master_client.put(
        f"/api/company/{slug}/candidate/{application_ids[0]}/stage",
        json={"stage": "screening", "note": "Initial shortlist created"},
    )
    check(response.status_code == 200, "Stage update to screening should succeed.")
    response = master_client.put(
        f"/api/company/{slug}/candidate/{application_ids[0]}/stage",
        json={"stage": "interview", "note": "L1 scheduled"},
    )
    check(response.status_code == 200, "Stage update to interview should succeed.")
    response = member_client.get(f"/api/candidate/dashboard?email={member_email}")
    dashboard_json = json_of(response)
    check(dashboard_json.get("stats", {}).get("interviews", 0) >= 1, "Candidate dashboard should update interview count.")
    check(any((row.get("stage") or "") == "interview" for row in dashboard_json.get("journeys", [])), "Candidate journey should show interview stage.")

    response = master_client.get(f"/api/company/{slug}/talent-map?available_by=2026-04-30")
    talent_map = json_of(response)
    check(response.status_code == 200, "Talent map should load.")
    check(talent_map.get("stats", {}).get("candidate_pool", 0) >= 1, "Talent map should show candidate pool.")
    check(len(talent_map.get("matches", [])) >= 1, "Talent map should return matches.")

    response = master_client.post(f"/api/company/{slug}/ai-screen-all")
    ai_screen = json_of(response)
    check(response.status_code == 200, "Bulk AI screen should work.")
    check(ai_screen.get("screened", 0) >= 1, "Bulk AI screen should process candidates.")

    response = master_client.post(
        "/api/v1/screen-candidate",
        headers={"X-API-Key": api_key},
        json={
            "job_title": "Senior Java Developer",
            "job_description": "Core Java Spring Boot Microservices Oracle role",
            "skills": "java, spring boot, microservices, oracle",
            "resume": "8 years Java, Spring Boot, Microservices, Oracle, Kafka experience",
        },
    )
    api_screen = json_of(response)
    check(response.status_code == 200, "API screening endpoint should work.")
    check(api_screen.get("fit_score") is not None, "API screening should return fit score.")

    # Recruiter tracker + intelligence flows
    response = member_client.post(
        "/api/recruitment-tracker/capture",
        json={
            "transcript": "Candidate Name: Rahul Sharma\nPosition: Senior Java Developer\nClient: TechBuzz Scenario Lab\nRecruiter: Aarti\nSource: Naukri\nCurrent Company: Infosys\nCurrent Location: Pune\nPreferred Location: Bangalore\nTotal Exp: 8\nRelevant Exp: 6\nNotice Period: 30 days\nCurrent CTC: 18\nExpected CTC: 24\nCandidate is interested and okay to proceed. Shared profile and confirmed on mail. Applied in 4 companies. Given 2 interviews. Holding 1 offer.",
            "candidate_name": "Rahul Sharma",
            "position": "Senior Java Developer",
            "client_name": company_name,
            "recruiter": "Aarti",
            "sourced_from": "Naukri",
            "mail_id": member_email,
            "contact_no": "+919999999999",
        },
    )
    capture_json = json_of(response)
    check(response.status_code == 200, "Recruitment tracker capture should work.")
    check(bool(capture_json.get("row_id")), "Recruitment tracker capture should return row id.")
    check(bool(capture_json.get("candidate_signal")), "Recruitment tracker capture should update candidate signal.")
    row_id = capture_json["row_id"]

    response = member_client.post(
        "/api/recruitment-tracker/interview",
        json={
            "row_id": row_id,
            "interview_round": "L1",
            "scheduled_for": "2026-03-30 15:00",
            "mode": "virtual",
            "interviewer_name": "Hiring Manager",
            "interviewer_email": "hm@example.com",
            "feedback_status": "requested",
        },
    )
    check(response.status_code == 200, "Recruitment interview scheduler should work.")

    response = member_client.post(
        "/api/recruitment-tracker/capture",
        json={
            "transcript": "Candidate Name: Amit Verma\nPosition: Senior Java Developer\nClient: TechBuzz Scenario Lab\nRecruiter: Aarti\nSource: Naukri\nCurrent Company: Wipro\nCurrent Location: Hyderabad\nPreferred Location: Bangalore\nTotal Exp: 7\nRelevant Exp: 6\nNotice Period: 45 days\nCurrent CTC: 16\nExpected CTC: 22\nCandidate is interested and asked for acknowledgment mail.",
            "candidate_name": "Amit Verma",
            "position": "Senior Java Developer",
            "client_name": company_name,
            "recruiter": "Aarti",
            "sourced_from": "Naukri",
            "mail_id": f"amit.{suffix}@example.com",
            "contact_no": "+919888888888",
        },
    )
    draft_capture = json_of(response)
    check(response.status_code == 200, "Draft recruiter capture should work.")
    check(draft_capture.get("acknowledgment") is not None, "Draft recruiter capture should prepare acknowledgment.")
    draft_row_id = draft_capture["row_id"]

    response = member_client.get("/api/agent/console/state?search=Amit%20Verma")
    draft_console = json_of(response)
    draft_row = next((item for item in draft_console.get("recruitment_tracker", {}).get("rows", []) if item.get("id") == draft_row_id), None)
    check(draft_row is not None, "Draft tracker row should appear in console state.")
    check(draft_row.get("submission_state") == "ack_prepared", "Draft tracker row should stay in acknowledgment-prepared state.")

    response = member_client.post(
        "/api/documents/upload",
        files={
            "files": (
                "amit_resume.txt",
                io.BytesIO(
                    (
                        (
                            "AMIT VERMA\n"
                            "amit.%s@example.com\n"
                            "9888888888\n"
                            "Current Location: Hyderabad\n"
                            "Preferred Location: Bangalore\n"
                            "Total Experience: 7 years\n"
                            "Relevant Experience: 6 years\n"
                            "Skills: Java, Spring Boot, Microservices, Kafka, SQL\n"
                            "Roles and Responsibilities: Built APIs, handled production issues, mentored analysts.\n"
                        )
                        % suffix
                    ).encode("utf-8")
                ),
                "text/plain",
            )
        },
    )
    upload_json = json_of(response)
    check(response.status_code == 200, "Recruiter resume upload should work.")
    resume_document_id = upload_json.get("documents", [{}])[0].get("id")
    check(bool(resume_document_id), "Recruiter resume upload should return a document id.")

    response = member_client.post(
        "/api/recruitment-tracker/submit-resume",
        json={
            "document_id": resume_document_id,
            "row_id": draft_row_id,
            "candidate_name": "Amit Verma",
            "position": "Senior Java Developer",
            "client_name": company_name,
            "recruiter": "Aarti",
            "sourced_from": "Naukri",
            "mail_id": f"amit.{suffix}@example.com",
            "contact_no": "+919888888888",
            "current_ctc": 16,
            "expected_ctc": 22,
            "notice_period": "45 days",
            "ack_status": "confirmed",
            "candidate_confirmed": True,
            "remarks": "Candidate confirmed on acknowledgment mail and resume uploaded.",
        },
    )
    resume_json = json_of(response)
    check(response.status_code == 200, "Confirmed resume submission should work.")
    check(resume_json.get("row", {}).get("submission_state") == "confirmed", "Resume flow should finalize the tracker after acknowledgment.")
    check(bool(resume_json.get("row", {}).get("ack_confirmed_at")), "Confirmed resume flow should stamp acknowledgment confirmation.")
    check("Java" in (resume_json.get("row", {}).get("skill_snapshot") or ""), "Resume flow should extract skills into the tracker.")
    check(bool(resume_json.get("row", {}).get("resume_file_name")), "Resume flow should attach the uploaded resume file.")

    response = member_client.get("/api/recruitment/candidate-intelligence")
    intelligence_json = json_of(response)
    check(response.status_code == 200, "Candidate intelligence endpoint should load.")
    rows = intelligence_json.get("candidates", [])
    rahul = next((row for row in rows if row.get("mail_id") == member_email or row.get("candidate_name") == "Rahul Sharma"), None)
    check(rahul is not None, "Candidate intelligence should include Rahul Sharma.")
    check(rahul.get("applications_count") == 4, "Candidate intelligence should reflect intent applications count.")
    check(rahul.get("offers_count") == 1, "Candidate intelligence should reflect offer count.")
    check(rahul.get("interviews_count", 0) >= 3, "Candidate intelligence should accumulate interviews from intent + scheduling.")
    check(bool(rahul.get("next_move")), "Candidate intelligence should include next move.")
    check(bool(rahul.get("fit_note")), "Candidate intelligence should include fit note.")

    response = member_client.get("/api/agent/console/state?search=Rahul%20Sharma")
    console_json = json_of(response)
    check(response.status_code == 200, "Agent console state should load.")
    check(len(console_json.get("candidates", [])) >= 1, "Agent console should surface ATS candidate rows.")

    response = member_client.post(
        "/api/agent/console/chat",
        json={
            "message": "For Rahul Sharma tell me companies applied, interviews given, offers collected, fit, and next move in short.",
            "search": "Rahul Sharma",
            "detail": "guided",
            "allow_full_context": False,
        },
    )
    chat_json = json_of(response)
    reply = chat_json.get("reply", "")
    check(response.status_code == 200, "Agent chat should respond.")
    check("Rahul Sharma" in reply, "Agent chat should mention the candidate.")
    check("applied" in reply.lower(), "Agent chat should mention application context.")
    check("offer" in reply.lower(), "Agent chat should mention offers.")
    check("next" in reply.lower(), "Agent chat should mention the next move.")

    response = member_client.get("/api/recruitment-tracker/export?scope=tracker&search=Rahul%20Sharma")
    tracker_export = json_of(response)
    check(response.status_code == 200, "Tracker export should work.")
    check(tracker_export.get("row_count", 0) >= 1, "Tracker export should include the candidate.")
    check("Candidate Name" in (tracker_export.get("tsv") or ""), "Tracker export should return Excel-style TSV headers.")

    response = member_client.get("/api/recruitment-tracker/export?scope=dsr&search=Rahul%20Sharma")
    dsr_export = json_of(response)
    check(response.status_code == 200, "DSR export should work.")
    check(dsr_export.get("row_count", 0) >= 1, "DSR export should include the candidate.")
    check("Submitted" in (dsr_export.get("headline") or "") or dsr_export.get("row_count", 0) >= 1, "DSR export should summarize visible submission data.")

    response = member_client.get("/api/recruitment-tracker/history?candidate_name=Rahul%20Sharma")
    history_json = json_of(response)
    check(response.status_code == 200, "Recruiter history endpoint should work.")
    check(history_json.get("allowed") is True, "Recruiter history should be available after recruiter tracker activity exists.")
    check(history_json.get("discussion_trail", {}).get("count", 0) >= 1, "Recruiter history should include discussion events.")
    check(history_json.get("stats", {}).get("report_snapshots", 0) >= 1, "Recruiter history should include saved report snapshots.")

    response = member_client.post(
        "/api/agent/console/chat",
        json={
            "message": "manager is asking complete data of today for Rahul Sharma",
            "candidate_name": "Rahul Sharma",
            "date_from": "2026-03-28",
            "date_to": "2026-03-28",
            "detail": "guided",
            "allow_full_context": False,
        },
    )
    history_chat = json_of(response)
    check(response.status_code == 200, "Agent chat should return recruiter history on request.")
    check("Recent trail" in (history_chat.get("reply") or ""), "Agent chat should return the recent discussion trail.")

    response = member_client.post(
        "/api/agent/console/chat",
        json={
            "message": "give me today tracker in excel format for Rahul Sharma",
            "candidate_name": "Rahul Sharma",
            "date_from": "2026-03-28",
            "date_to": "2026-03-28",
            "detail": "guided",
            "allow_full_context": False,
        },
    )
    export_chat = json_of(response)
    check(response.status_code == 200, "Agent chat should return tracker export on request.")
    check("Copy the tab-separated block below into Excel." in (export_chat.get("reply") or ""), "Agent chat should return an Excel-style export block.")

    response = member_client.get("/api/recruitment-vault/status")
    vault_status = json_of(response)
    check(response.status_code == 200, "Recruitment vault status should load.")
    check(vault_status.get("local_record_count", 0) >= 1, "Recruitment vault should see local recruiter records.")

    response = member_client.post("/api/recruitment-vault/server-sync", json={})
    vault_sync = json_of(response)
    check(response.status_code == 200, "Recruitment vault server sync should work.")
    check(bool(vault_sync.get("archive", {}).get("id")), "Recruitment vault server sync should create an archive.")

    response = member_client.get("/api/recruitment-vault/export")
    check(response.status_code == 200, "Recruitment vault export should work.")
    check(response.headers.get("content-type") == "application/zip", "Recruitment vault export should return a zip file.")
    archive_bytes = response.content
    check(archive_bytes[:2] == b"PK", "Recruitment vault export should be a valid zip payload.")

    response = member_client.post("/api/recruitment-vault/clear-local", json={})
    clear_json = json_of(response)
    check(response.status_code == 200, "Recruitment vault local clear should work.")
    check(clear_json.get("vault", {}).get("operational_status") == "cleared", "Local clear should mark the operational vault as cleared.")

    response = member_client.get("/api/recruitment-tracker/export?scope=tracker&search=Rahul%20Sharma")
    cleared_export = json_of(response)
    check(response.status_code == 200, "Tracker export should still work after local clear through archive recall.")
    check(cleared_export.get("source_mode") == "archive", "Cleared local tracker export should fall back to archive recall.")
    check(cleared_export.get("row_count", 0) >= 1, "Cleared local tracker export should still return archived recruiter visibility.")

    response = member_client.get("/api/recruitment-tracker/history?candidate_name=Rahul%20Sharma")
    cleared_history = json_of(response)
    check(response.status_code == 200, "Recruiter history should still work after local clear through archive recall.")
    check(cleared_history.get("source_mode") == "archive", "Cleared recruiter history should come from archive recall.")
    check(cleared_history.get("discussion_trail", {}).get("count", 0) >= 1, "Archive recall should preserve recruiter discussion trail.")

    response = member_client.get("/api/recruitment-vault/archive-status")
    archive_status = json_of(response)
    check(response.status_code == 200, "Recruitment archive status should work after local clear.")
    check(archive_status.get("available") is True, "Recruitment archive status should confirm read-only recall is available.")

    response = member_client.get("/api/recruitment-vault/archive-export?scope=tracker&search=Rahul%20Sharma")
    archive_export = json_of(response)
    check(response.status_code == 200, "Recruitment archive export should work.")
    check(archive_export.get("source_mode") == "archive", "Explicit archive export should be marked as archive mode.")
    check(archive_export.get("row_count", 0) >= 1, "Explicit archive export should return recruiter rows.")

    response = member_client.post(
        "/api/recruitment-vault/import",
        files={"file": ("recruitment-vault.zip", io.BytesIO(archive_bytes), "application/zip")},
    )
    import_json = json_of(response)
    check(response.status_code == 200, "Recruitment vault import should work.")
    check(import_json.get("vault", {}).get("operational_status") == "active", "Vault import should reactivate the operational lane.")

    response = member_client.get("/api/recruitment-tracker/export?scope=tracker&search=Rahul%20Sharma")
    restored_export = json_of(response)
    check(restored_export.get("row_count", 0) >= 1, "Imported vault should restore recruiter tracker visibility.")

    response = master_client.get("/network/intel")
    check(response.status_code == 200, "Master should access recruiter intel page.")
    check("TechBuzz Network Intel" in response.text, "Recruiter intel page should render the new shell.")
    response = member_client.get("/network")
    check("TechBuzz Network" in response.text, "Member network page should render the new shell.")

    print("PASS recruitment scenario audit")
    print(f"Checks: {checks_run}")
    print(f"Company: {slug}")
    print(
        "Candidate intelligence: "
        f"applications={rahul['applications_count']} "
        f"interviews={rahul['interviews_count']} "
        f"offers={rahul['offers_count']}"
    )
    print(f"Next move: {rahul['next_move']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"FAIL recruitment scenario audit: {error}")
        raise SystemExit(1)
