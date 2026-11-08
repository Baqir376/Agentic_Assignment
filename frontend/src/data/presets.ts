import type { PresetDocument } from "../types";

export const PRESET_DOCUMENTS: PresetDocument[] = [
  {
    id: "med-01",
    title: "Oncology Patient Record",
    category: "Medical",
    badge: "High PII Density",
    task: "Summarize clinical status, medication regimen, and next consultation.",
    text: `PATIENT MEDICAL RECORD
Hospital: Shaukat Khanum Memorial Cancer Hospital, Lahore
Department: Oncology

Patient Name: Javed Durrani
MRN: MRN-884129
Date of Birth: 14/06/1981
CNIC: 35202-9481234-7
Contact: 0300-8472910 | javed.durrani@yahoo.com
Address: House #42, Model Town, Lahore

Visit Date: 03-11-2026
Attending Physician: Dr. Ayesha Malik

Chief Complaint & Progress:
Patient presented for 6-month oncology follow-up. Vital signs stable, ECOG performance score 1.
Physical examination shows no new palpable lymphadenopathy. Blood chemistry and CBC within acceptable parameters.

Assessment & Plan:
Diagnosis: Stage II Colorectal Carcinoma (Post-Resection Surveillance)
Prescribed: Capecitabine 500mg twice daily and Ondansetron 8mg PRN for nausea.
Scheduled for repeat contrast-enhanced CT abdomen and pelvis in 12 weeks.
Attending Sign-off: Dr. Ayesha Malik`
  },
  {
    id: "legal-02",
    title: "High Court Affidavit",
    category: "Legal",
    badge: "Judicial / Sensitive",
    task: "Extract case merits, party claims, and mandatory hearing deadlines.",
    text: `IN THE LAHORE HIGH COURT, BENCH AT ISLAMABAD
CASE NO: CASE-4892/2026
Date of Filing: 22/10/2026

PETITIONER:
Hamza Tariq (CNIC: 61101-7391823-1)
Resident of Sector F-7, Islamabad
Represented by: Advocate Asad Khan (Phone: 0333-5129481)

RESPONDENT:
Federal Board of Revenue & Fariha Jalil (Director General Tax Audit)
Office: G-9 Blue Area, Islamabad

AFFIDAVIT OF COMPLIANCE:
I, Hamza Tariq, do hereby solemnly declare on oath that the audited accounts for fiscal years 2024-2025 were fully surrendered to the audit committee.
The proceedings conducted by Fariha Jalil violated natural justice.
BEFORE: Honorable Justice Zahid Dogar
Next Date of Hearing: 15/12/2026`
  },
  {
    id: "hr-03",
    title: "Internal Workplace Grievance",
    category: "HR",
    badge: "Confidential Grievance",
    task: "Summarize the grievance incident, persons involved, and remedy sought.",
    text: `CONFIDENTIAL INTERNAL HR GRIEVANCE
Submission Date: 28-09-2026
Company: TechLogix Systems Pakistan

To: Human Resources Ethics Committee
Complainant: Sana Raza (Employee ID: EMP-19402)
Contact: 0321-4920194 | sana.raza@techlogix.pk
Department: FinTech Solutions, Gulberg III, Lahore

Subject: Formal Grievance against Bilal Sheikh (EMP-10294)

Dear HR Committee,
I am filing this formal grievance regarding verbal misconduct during the quarterly financial review on 24-09-2026.
Bilal Sheikh made unprofessional personal remarks concerning team compensation.
Witness present: Urwa Baloch (EMP-18239).
I request an impartial inquiry chaired by HR Director Fatima Khan.`
  },
  {
    id: "finance-04",
    title: "Commercial Loan Guarantee",
    category: "Financial",
    badge: "Monetary Liability",
    task: "Outline guarantor obligations, loan amount, and default clauses.",
    text: `COMMERCIAL LOAN GUARANTEE AGREEMENT
Bank: Habib Bank Limited, Corporate Banking Branch, I.I. Chundrigar Road, Karachi
Agreement Date: 12-08-2026

Principal Borrower: Apex Logistics Pvt Ltd
Guarantor Name: Tariq Mansoor (CNIC: 42101-8392019-3)
Contact: 0345-2910482 | address: Flat 3B, Clifton Block 4, Karachi
Loan Facility Amount: PKR 45,000,000/- (Forty-Five Million Rupees)

Terms:
In consideration of HBL granting credit facilities to the Borrower, Tariq Mansoor irrevocably guarantees unconditional payment upon first demand in case of default.
Witnessed by: Advocate Salman Farooqi (Bar No. 29104)`
  }
];
