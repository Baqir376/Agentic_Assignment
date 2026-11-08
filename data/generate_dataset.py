"""
Synthetic Dataset Generator for PrivacySwarm Evaluation
Generates 100 realistic documents (medical, HR, legal) with ground truth PII labels.
Run: python generate_dataset.py
"""
import sys
import pathlib
import json
import random
import re
from datetime import date, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

try:
    from faker import Faker
except ImportError:
    print("Installing faker...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "faker", "-q"])
    from faker import Faker

fake = Faker("en_US")
random.seed(42)

# ── Load ontologies ──────────────────────────────────────────────────────────
ONT_DIR = pathlib.Path(__file__).parent / "ontology"

with open(ONT_DIR / "names.json") as f:
    NAMES = json.load(f)
with open(ONT_DIR / "locations.json") as f:
    LOCS = json.load(f)
with open(ONT_DIR / "hospitals.json") as f:
    HOSPS = json.load(f)["hospitals"]
with open(ONT_DIR / "medical_terms.json") as f:
    MED = json.load(f)


# ── Helper functions ─────────────────────────────────────────────────────────

def pk_name(gender=None):
    """Generate a Pakistani full name."""
    if gender is None:
        gender = random.choice(["male", "female"])
    if gender == "male":
        first = random.choice(NAMES["male_first"])
    else:
        first = random.choice(NAMES["female_first"])
    last = random.choice(NAMES["last"])
    return f"{first} {last}"

def pk_phone():
    """Pakistani phone number."""
    prefix = random.choice(["0300", "0301", "0302", "0303", "0310", "0311", "0312",
                            "0313", "0320", "0321", "0322", "0323", "0330", "0331",
                            "0332", "0333", "0340", "0341", "0345", "0346"])
    number = "".join([str(random.randint(0, 9)) for _ in range(7)])
    return f"{prefix}-{number}"

def pk_cnic():
    """Pakistani CNIC."""
    p1 = str(random.randint(10000, 99999))
    p2 = str(random.randint(1000000, 9999999))
    p3 = str(random.randint(1, 9))
    return f"{p1}-{p2}-{p3}"

def pk_email(name: str):
    """Generate email from name."""
    n = name.lower().replace(" ", ".")
    domain = random.choice(["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"])
    return f"{n}{random.randint(1, 999)}@{domain}"

def pk_date():
    """Random date in past 10 years."""
    start = date(2015, 1, 1)
    end = date(2026, 10, 31)
    delta = end - start
    random_day = start + timedelta(days=random.randint(0, delta.days))
    fmt = random.choice([
        random_day.strftime("%d/%m/%Y"),
        random_day.strftime("%d-%m-%Y"),
        random_day.strftime("%B %d, %Y"),
    ])
    return fmt

def pk_mrn():
    """Medical record number."""
    return f"MRN-{random.randint(100000, 999999)}"

def pk_emp_id():
    """Employee ID."""
    return f"EMP-{random.randint(10000, 99999)}"

def pk_case_no():
    """Legal case number."""
    return f"CASE-{random.randint(1000, 9999)}/{random.randint(2020, 2026)}"

def find_positions(text, entity):
    """Find all character positions of entity in text."""
    positions = []
    start = 0
    while True:
        idx = text.find(entity, start)
        if idx == -1:
            break
        positions.append({"entity": entity, "start": idx, "end": idx + len(entity)})
        start = idx + 1
    return positions


# ── Document generators ──────────────────────────────────────────────────────

def gen_medical_record():
    """Generate a realistic medical record note."""
    gender = random.choice(["male", "female"])
    patient_name = pk_name(gender)
    doctor_name = "Dr. " + pk_name(random.choice(["male", "female"]))
    hospital = random.choice(HOSPS)
    phone = pk_phone()
    cnic = pk_cnic()
    mrn = pk_mrn()
    dob = pk_date()
    visit_date = pk_date()
    city = random.choice(LOCS["cities"])
    area = random.choice(LOCS["areas"])
    diagnosis = random.choice(MED["diagnoses"])
    med1 = random.choice(MED["medications"])
    med2 = random.choice(MED["medications"])
    dept = random.choice(MED["departments"])

    text = (
        f"PATIENT MEDICAL RECORD\n"
        f"Hospital: {hospital}\n"
        f"Department: {dept}\n\n"
        f"Patient Name: {patient_name}\n"
        f"MRN: {mrn}\n"
        f"Date of Birth: {dob}\n"
        f"CNIC: {cnic}\n"
        f"Contact: {phone}\n"
        f"Address: House #12, {area}, {city}\n\n"
        f"Visit Date: {visit_date}\n"
        f"Attending Physician: {doctor_name}\n\n"
        f"Chief Complaint:\n"
        f"The patient presented with complaints consistent with {diagnosis}. "
        f"The patient reports experiencing symptoms for the past 3-4 weeks. "
        f"Family history is significant. Physical examination revealed elevated vitals.\n\n"
        f"Assessment & Plan:\n"
        f"Diagnosis: {diagnosis}\n"
        f"Prescribed: {med1} and {med2}\n"
        f"Follow-up appointment scheduled. Patient advised to rest and monitor symptoms. "
        f"If symptoms worsen, patient should contact the {dept} department immediately.\n\n"
        f"Notes by: {doctor_name}\n"
        f"This record is strictly confidential."
    )

    pii_entities = []
    for entity, ptype in [
        (patient_name, "PERSON"), (doctor_name, "PERSON"),
        (hospital, "HOSPITAL"), (phone, "PHONE"), (cnic, "CNIC"),
        (mrn, "MED_ID"), (dob, "DATE"), (visit_date, "DATE"),
        (city, "LOCATION"), (area, "LOCATION"),
    ]:
        pii_entities.extend(find_positions(text, entity))
        for p in pii_entities:
            if p["entity"] == entity:
                p["type"] = ptype

    return text, pii_entities


def gen_hr_complaint():
    """Generate a realistic HR complaint letter."""
    complainant = pk_name()
    subject_name = pk_name()
    manager_name = pk_name()
    emp_id_c = pk_emp_id()
    emp_id_s = pk_emp_id()
    phone = pk_phone()
    email = pk_email(complainant)
    complaint_date = pk_date()
    incident_date = pk_date()
    dept = random.choice(["Finance", "Operations", "Marketing", "IT", "HR", "Sales", "Legal"])
    city = random.choice(LOCS["cities"])

    text = (
        f"FORMAL HR COMPLAINT\n"
        f"Date: {complaint_date}\n\n"
        f"To: Human Resources Department\n"
        f"From: {complainant} (Employee ID: {emp_id_c})\n"
        f"Contact: {phone} | {email}\n\n"
        f"Subject: Formal Complaint Against {subject_name} (Employee ID: {emp_id_s})\n\n"
        f"I, {complainant}, am writing to formally report inappropriate workplace conduct "
        f"by {subject_name}, who is a colleague in the {dept} department based in {city}. "
        f"The incident occurred on {incident_date}.\n\n"
        f"Description of Incident:\n"
        f"During a team meeting, {subject_name} made several remarks that I considered "
        f"to be unprofessional and harassing in nature. This behavior has created a hostile "
        f"work environment that is affecting my productivity and mental well-being.\n\n"
        f"Requested Action:\n"
        f"I request that HR conduct a formal investigation into this matter. I am willing "
        f"to cooperate fully. My direct manager, {manager_name}, is aware of this situation.\n\n"
        f"I trust that this matter will be handled with the utmost confidentiality.\n\n"
        f"Sincerely,\n{complainant}\n"
        f"Employee ID: {emp_id_c}"
    )

    pii_entities = []
    for entity, ptype in [
        (complainant, "PERSON"), (subject_name, "PERSON"), (manager_name, "PERSON"),
        (emp_id_c, "MED_ID"), (emp_id_s, "MED_ID"),
        (phone, "PHONE"), (email, "EMAIL"),
        (complaint_date, "DATE"), (incident_date, "DATE"),
        (city, "LOCATION"),
    ]:
        for p in find_positions(text, entity):
            p["type"] = ptype
            pii_entities.append(p)

    return text, pii_entities


def gen_legal_memo():
    """Generate a realistic legal memo excerpt."""
    client_name = pk_name()
    lawyer_name = "Advocate " + pk_name()
    opposing_party = pk_name()
    judge_name = "Honorable Justice " + pk_name()
    cnic = pk_cnic()
    phone = pk_phone()
    case_no = pk_case_no()
    filing_date = pk_date()
    hearing_date = pk_date()
    city = random.choice(LOCS["cities"])
    area = random.choice(LOCS["areas"])
    court = f"{city} High Court"

    text = (
        f"LEGAL MEMORANDUM — CONFIDENTIAL\n"
        f"Case No: {case_no}\n"
        f"Filing Date: {filing_date}\n"
        f"Court: {court}\n\n"
        f"Client: {client_name}\n"
        f"CNIC: {cnic}\n"
        f"Address: Street 7, {area}, {city}\n"
        f"Contact: {phone}\n\n"
        f"Representing Counsel: {lawyer_name}\n"
        f"Opposing Party: {opposing_party}\n"
        f"Presiding Judge: {judge_name}\n\n"
        f"Matter Summary:\n"
        f"This memorandum pertains to the civil dispute filed by {client_name} against "
        f"{opposing_party} regarding property rights in {city}. The next hearing is "
        f"scheduled for {hearing_date} before {judge_name} at {court}.\n\n"
        f"Legal Position:\n"
        f"Based on our review of the facts and applicable statutes, the client, {client_name}, "
        f"has a strong prima facie case. We recommend proceeding with the civil suit. "
        f"All correspondence should be directed through {lawyer_name}.\n\n"
        f"This document is protected by attorney-client privilege and must not be "
        f"disclosed to any third party without written consent of {client_name}."
    )

    pii_entities = []
    for entity, ptype in [
        (client_name, "PERSON"), (lawyer_name, "PERSON"),
        (opposing_party, "PERSON"), (judge_name, "PERSON"),
        (cnic, "CNIC"), (phone, "PHONE"),
        (case_no, "MED_ID"), (filing_date, "DATE"), (hearing_date, "DATE"),
        (city, "LOCATION"), (area, "LOCATION"),
    ]:
        for p in find_positions(text, entity):
            p["type"] = ptype
            pii_entities.append(p)

    return text, pii_entities


# ── Main generation ──────────────────────────────────────────────────────────

def generate_dataset(n_total=100):
    n_medical = 40
    n_hr = 30
    n_legal = 30

    dataset = []
    summary = {"medical": 0, "hr": 0, "legal": 0, "total_pii": 0}

    generators = (
        [("medical", gen_medical_record)] * n_medical +
        [("hr", gen_hr_complaint)] * n_hr +
        [("legal", gen_legal_memo)] * n_legal
    )
    random.shuffle(generators)

    for i, (category, gen_fn) in enumerate(generators):
        doc_id = f"doc_{i+1:03d}"
        text, pii_list = gen_fn()

        # Deduplicate PII entries (same entity may appear multiple times)
        seen = set()
        unique_pii = []
        for p in pii_list:
            key = (p["entity"], p["start"])
            if key not in seen:
                seen.add(key)
                unique_pii.append(p)

        doc = {
            "id": doc_id,
            "category": category,
            "text": text,
            "ground_truth_pii": unique_pii,
            "pii_count": len(unique_pii),
        }
        dataset.append(doc)
        summary[category] += 1
        summary["total_pii"] += len(unique_pii)

    return dataset, summary


if __name__ == "__main__":
    OUT_DIR = pathlib.Path(__file__).parent / "synthetic"
    OUT_DIR.mkdir(exist_ok=True)

    print("Generating 100 synthetic documents...")
    dataset, summary = generate_dataset(100)

    dataset_path = OUT_DIR / "dataset.json"
    with open(dataset_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    summary_path = OUT_DIR / "dataset_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n✅ Dataset generated successfully!")
    print(f"   📄 Medical records : {summary['medical']}")
    print(f"   📋 HR complaints   : {summary['hr']}")
    print(f"   ⚖️  Legal memos     : {summary['legal']}")
    print(f"   🔍 Total PII tagged : {summary['total_pii']}")
    print(f"   💾 Saved to        : {dataset_path}")

