"""
Slalom Capabilities Management System API

A FastAPI application that enables Slalom consultants to register their
capabilities and manage consulting expertise across the organization.
"""

from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import os
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import hmac
import json
import secrets

app = FastAPI(title="Slalom Capabilities Management API",
              description="API for managing consulting capabilities and consultant expertise")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev-only-session-secret-change-me"),
    max_age=60 * 60 * 8,
)

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

practice_leads_path = current_dir / "practice_leads.json"
audit_log_path = current_dir / "audit.log"


class LoginRequest(BaseModel):
    username: str
    password: str


class RegistrationRequestCreate(BaseModel):
    email: str
    capability_name: str


registration_requests = []
next_request_id = 1


def log_audit(action: str, actor: str, metadata: dict):
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "actor": actor,
        "metadata": metadata,
    }
    with audit_log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(payload) + "\n")


def hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 210000)
    return digest.hex()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    candidate = hash_password(password, salt)
    return hmac.compare_digest(candidate, expected_hash)


def load_practice_leads() -> dict:
    if not practice_leads_path.exists():
        return {"practice_leads": []}

    with practice_leads_path.open("r", encoding="utf-8") as creds_file:
        return json.load(creds_file)


def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_practice_lead(user=Depends(get_current_user)):
    if user.get("role") != "practice_lead":
        raise HTTPException(status_code=403, detail="Practice lead role required")
    return user

# In-memory capabilities database
capabilities = {
    "Cloud Architecture": {
        "description": "Design and implement scalable cloud solutions using AWS, Azure, and GCP",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["AWS Solutions Architect", "Azure Architect Expert"],
        "industry_verticals": ["Healthcare", "Financial Services", "Retail"],
        "capacity": 40,  # hours per week available across team
        "consultants": ["alice.smith@slalom.com", "bob.johnson@slalom.com"]
    },
    "Data Analytics": {
        "description": "Advanced data analysis, visualization, and machine learning solutions",
        "practice_area": "Technology", 
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Tableau Desktop Specialist", "Power BI Expert", "Google Analytics"],
        "industry_verticals": ["Retail", "Healthcare", "Manufacturing"],
        "capacity": 35,
        "consultants": ["emma.davis@slalom.com", "sophia.wilson@slalom.com"]
    },
    "DevOps Engineering": {
        "description": "CI/CD pipeline design, infrastructure automation, and containerization",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"], 
        "certifications": ["Docker Certified Associate", "Kubernetes Admin", "Jenkins Certified"],
        "industry_verticals": ["Technology", "Financial Services"],
        "capacity": 30,
        "consultants": ["john.brown@slalom.com", "olivia.taylor@slalom.com"]
    },
    "Digital Strategy": {
        "description": "Digital transformation planning and strategic technology roadmaps",
        "practice_area": "Strategy",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Digital Transformation Certificate", "Agile Certified Practitioner"],
        "industry_verticals": ["Healthcare", "Financial Services", "Government"],
        "capacity": 25,
        "consultants": ["liam.anderson@slalom.com", "noah.martinez@slalom.com"]
    },
    "Change Management": {
        "description": "Organizational change leadership and adoption strategies",
        "practice_area": "Operations",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Prosci Certified", "Lean Six Sigma Black Belt"],
        "industry_verticals": ["Healthcare", "Manufacturing", "Government"],
        "capacity": 20,
        "consultants": ["ava.garcia@slalom.com", "mia.rodriguez@slalom.com"]
    },
    "UX/UI Design": {
        "description": "User experience design and digital product innovation",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Adobe Certified Expert", "Google UX Design Certificate"],
        "industry_verticals": ["Retail", "Healthcare", "Technology"],
        "capacity": 30,
        "consultants": ["amelia.lee@slalom.com", "harper.white@slalom.com"]
    },
    "Cybersecurity": {
        "description": "Information security strategy, risk assessment, and compliance",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["CISSP", "CISM", "CompTIA Security+"],
        "industry_verticals": ["Financial Services", "Healthcare", "Government"],
        "capacity": 25,
        "consultants": ["ella.clark@slalom.com", "scarlett.lewis@slalom.com"]
    },
    "Business Intelligence": {
        "description": "Enterprise reporting, data warehousing, and business analytics",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Microsoft BI Certification", "Qlik Sense Certified"],
        "industry_verticals": ["Retail", "Manufacturing", "Financial Services"],
        "capacity": 35,
        "consultants": ["james.walker@slalom.com", "benjamin.hall@slalom.com"]
    },
    "Agile Coaching": {
        "description": "Agile transformation and team coaching for scaled delivery",
        "practice_area": "Operations",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Certified Scrum Master", "SAFe Agilist", "ICAgile Certified"],
        "industry_verticals": ["Technology", "Financial Services", "Healthcare"],
        "capacity": 20,
        "consultants": ["charlotte.young@slalom.com", "henry.king@slalom.com"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/capabilities")
def get_capabilities():
    return capabilities


@app.post("/auth/login")
def login(payload: LoginRequest, request: Request):
    leads_data = load_practice_leads()
    matched_lead = next(
        (lead for lead in leads_data.get("practice_leads", []) if lead.get("username") == payload.username),
        None,
    )

    if not matched_lead:
        log_audit("login_failed", payload.username, {"reason": "user_not_found"})
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_password(payload.password, matched_lead["salt"], matched_lead["password_hash"]):
        log_audit("login_failed", payload.username, {"reason": "bad_password"})
        raise HTTPException(status_code=401, detail="Invalid username or password")

    session_user = {
        "username": matched_lead["username"],
        "role": matched_lead.get("role", "practice_lead"),
        "practice_areas": matched_lead.get("practice_areas", []),
    }
    request.session["user"] = session_user
    log_audit("login_success", session_user["username"], {"role": session_user["role"]})
    return {"message": "Login successful", "user": session_user}


@app.post("/auth/logout")
def logout(request: Request):
    user = request.session.get("user")
    if user:
        log_audit("logout", user.get("username", "unknown"), {})
    request.session.clear()
    return {"message": "Logged out"}


@app.get("/auth/session")
def get_session(request: Request):
    user = request.session.get("user")
    return {"authenticated": bool(user), "user": user}


@app.post("/registration-requests")
def create_registration_request(payload: RegistrationRequestCreate):
    global next_request_id

    if payload.capability_name not in capabilities:
        raise HTTPException(status_code=404, detail="Capability not found")

    new_request = {
        "id": next_request_id,
        "email": payload.email,
        "capability_name": payload.capability_name,
        "status": "pending",
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }
    registration_requests.append(new_request)
    next_request_id += 1
    log_audit("registration_requested", payload.email, {"capability_name": payload.capability_name})
    return {"message": "Registration request submitted for practice lead approval", "request": new_request}


@app.get("/registration-requests")
def list_registration_requests(practice_lead=Depends(require_practice_lead)):
    pending = [request for request in registration_requests if request["status"] == "pending"]
    return {"pending_requests": pending, "count": len(pending), "viewer": practice_lead["username"]}


@app.post("/registration-requests/{request_id}/approve")
def approve_registration_request(request_id: int, practice_lead=Depends(require_practice_lead)):
    request_record = next((request for request in registration_requests if request["id"] == request_id), None)
    if not request_record:
        raise HTTPException(status_code=404, detail="Request not found")

    if request_record["status"] != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be approved")

    capability = capabilities[request_record["capability_name"]]
    if request_record["email"] not in capability["consultants"]:
        capability["consultants"].append(request_record["email"])

    request_record["status"] = "approved"
    request_record["reviewed_by"] = practice_lead["username"]
    request_record["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    log_audit(
        "registration_approved",
        practice_lead["username"],
        {"request_id": request_id, "email": request_record["email"], "capability_name": request_record["capability_name"]},
    )
    return {"message": f"Approved request #{request_id}"}


@app.post("/registration-requests/{request_id}/reject")
def reject_registration_request(request_id: int, practice_lead=Depends(require_practice_lead)):
    request_record = next((request for request in registration_requests if request["id"] == request_id), None)
    if not request_record:
        raise HTTPException(status_code=404, detail="Request not found")

    if request_record["status"] != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be rejected")

    request_record["status"] = "rejected"
    request_record["reviewed_by"] = practice_lead["username"]
    request_record["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    log_audit(
        "registration_rejected",
        practice_lead["username"],
        {"request_id": request_id, "email": request_record["email"], "capability_name": request_record["capability_name"]},
    )
    return {"message": f"Rejected request #{request_id}"}


@app.post("/capabilities/{capability_name}/register")
def register_for_capability(capability_name: str, email: str, practice_lead=Depends(require_practice_lead)):
    """Register a consultant for a capability"""
    # Validate capability exists
    if capability_name not in capabilities:
        raise HTTPException(status_code=404, detail="Capability not found")

    # Get the specific capability
    capability = capabilities[capability_name]

    # Validate consultant is not already registered
    if email in capability["consultants"]:
        raise HTTPException(
            status_code=400,
            detail="Consultant is already registered for this capability"
        )

    # Add consultant
    capability["consultants"].append(email)
    log_audit(
        "consultant_registered",
        practice_lead["username"],
        {"email": email, "capability_name": capability_name},
    )
    return {"message": f"Registered {email} for {capability_name}"}


@app.delete("/capabilities/{capability_name}/unregister")
def unregister_from_capability(capability_name: str, email: str, practice_lead=Depends(require_practice_lead)):
    """Unregister a consultant from a capability"""
    # Validate capability exists
    if capability_name not in capabilities:
        raise HTTPException(status_code=404, detail="Capability not found")

    # Get the specific capability
    capability = capabilities[capability_name]

    # Validate consultant is registered
    if email not in capability["consultants"]:
        raise HTTPException(
            status_code=400,
            detail="Consultant is not registered for this capability"
        )

    # Remove consultant
    capability["consultants"].remove(email)
    log_audit(
        "consultant_unregistered",
        practice_lead["username"],
        {"email": email, "capability_name": capability_name},
    )
    return {"message": f"Unregistered {email} from {capability_name}"}
