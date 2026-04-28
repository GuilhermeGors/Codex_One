import os
from fpdf import FPDF

content = """CONFIDENTIAL — INTERNAL AUDIT REPORT
Enterprise Cybersecurity & Data Governance Division
TechVault Solutions Inc. — Q1 2024 Annual Review
Classification: HIGHLY RESTRICTED — C-LEVEL ONLY

1. EXECUTIVE SUMMARY

This report presents the findings of the internal cybersecurity and data governance audit conducted across all departments of TechVault Solutions Inc. during Q1 2024. The assessment covers employee data handling compliance, access control violations, third-party vendor risk analysis, and AI model deployment security.

Key Finding: Three critical incidents were identified involving unauthorized data access and potential exposure of Personally Identifiable Information (PII). Immediate remediation actions have been initiated.

2. SCOPE AND METHODOLOGY

The audit was conducted by the Internal Security Operations Center (SOC) under the supervision of Chief Information Security Officer (CISO) Jonathan Mitchell (jonathan.mitchell@techvault.com, Employee ID: TV-4821). The review covered 14 business units across 3 geographic regions.

Methodology included:
- Automated log analysis from Splunk SIEM (January 1 - March 31, 2024)
- Manual review of access control lists (ACLs) for sensitive document repositories
- Penetration testing of internal AI inference endpoints
- Employee interviews and compliance questionnaire analysis

3. CRITICAL INCIDENTS

INCIDENT INC-2024-001: Unauthorized Database Export
Date: February 12, 2024
Severity: CRITICAL
Involved Personnel: Senior Data Analyst Sarah Chen (sarah.chen@techvault.com, SSN: 412-68-9203)

Description: On February 12th, monitoring systems detected a bulk export of 45,000 customer records from the production CRM database. The export was initiated by Sarah Chen's workstation at 02:47 AM EST, outside of normal business hours. The exported dataset included full names, email addresses, phone numbers, and purchase histories.

Investigation Status: Forensic analysis revealed that Ms. Chen's credentials were compromised through a phishing attack targeting her personal email. The actual threat actor has not yet been identified. All affected customer accounts have been flagged for enhanced monitoring.

Remediation: Mandatory 2FA enrollment completed for all database administrators. Session timeout reduced from 8 hours to 30 minutes for production systems.

---

INCIDENT INC-2024-002: AI Model Prompt Injection Attack
Date: March 3, 2024
Severity: HIGH
Involved Personnel: ML Engineer David Rodriguez (david.rodriguez@techvault.com, Phone: +1-555-0192)

Description: During routine red-team testing of TechVault's internal customer support chatbot (built on GPT-4 fine-tuned model), the assessment team discovered that carefully crafted prompts could bypass the system's guardrails and extract portions of the training dataset, which contained actual customer support tickets with PII.

The vulnerable endpoint was accessible from the internal network without authentication. David Rodriguez, the lead ML engineer responsible for deployment, had disabled the API gateway authentication layer during a debugging session on February 28th and failed to re-enable it.

Impact Assessment: Approximately 2,300 customer support tickets containing names, account numbers, and complaint details were potentially accessible for a 72-hour window. No evidence of external exploitation was found.

Remediation: API gateway authentication restored immediately. Implemented automated drift detection to alert when security configurations deviate from baseline. Rodriguez received a formal written warning and mandatory security training.

---

INCIDENT INC-2024-003: Third-Party Vendor Data Leak
Date: March 18, 2024
Severity: HIGH
Involved Personnel: Procurement Manager Lisa Park (lisa.park@techvault.com, Badge ID: TV-7734)

Description: Analytics vendor DataPulse Analytics (contract managed by Lisa Park) was found to be storing anonymized user behavioral data in an S3 bucket with public read access. The data, while pseudonymized, contained sufficient metadata (timestamps, IP addresses, user agent strings) to potentially re-identify individual users when cross-referenced with other datasets.

The misconfiguration had been active since November 2023, approximately 4 months before discovery. DataPulse's Data Processing Agreement (DPA) explicitly prohibited public storage of any TechVault data.

Financial Impact: Estimated regulatory exposure of $2.4M under GDPR Article 83, potential class-action liability estimated at $8.1M.

Remediation: DataPulse contract terminated effective immediately. All data retrieved and securely deleted with cryptographic verification. Legal team initiated breach notification process for 12,400 affected EU users.

4. ACCESS CONTROL AUDIT FINDINGS

4.1 Privileged Account Analysis
Total privileged accounts audited: 847
Accounts with excessive permissions: 123 (14.5%)
Orphaned accounts (no active employee): 34 (4.0%)
Accounts without MFA enabled: 67 (7.9%)

Notable Finding: Chief Financial Officer Robert Kim (robert.kim@techvault.com) had retained full administrative access to the engineering CI/CD pipeline (Jenkins, GitHub Enterprise) despite having no operational need. This access was provisioned during an emergency in 2022 and never revoked.

4.2 Document Classification Compliance
Documents audited: 23,450
Properly classified: 18,760 (80.0%)
Missing classification labels: 3,240 (13.8%)
Incorrectly classified (under-classified): 1,450 (6.2%)

The Sales department showed the lowest compliance rate at 62%, with 847 documents containing customer financial data stored in general-access SharePoint folders without encryption.

5. AI MODEL SECURITY ASSESSMENT

5.1 Model Inventory
The organization currently operates 7 AI/ML models in production:
- Customer Support Chatbot (GPT-4 fine-tuned)
- Fraud Detection Engine (XGBoost)
- Document Classification Pipeline (BERT-based)
- Sales Forecasting Model (Prophet + LSTM)
- Resume Screening Tool (Custom transformer)
- Network Anomaly Detection (Autoencoder)
- Content Recommendation Engine (Collaborative filtering)

5.2 Security Findings
- 3 of 7 models lack proper input validation
- 5 of 7 models have no adversarial robustness testing
- Model versioning inconsistent: 2 production models running deprecated versions
- No model provenance tracking (ModelScan or equivalent) implemented
- Training data lineage undocumented for 4 models

5.3 Recommendations
PRIORITY 1: Implement NeMo Guardrails for all customer-facing LLM deployments
PRIORITY 2: Deploy ModelScan for pre-deployment security scanning of all model artifacts
PRIORITY 3: Establish red-team testing cadence (quarterly) using Garak framework
PRIORITY 4: Implement Llama Guard as secondary content filter for chatbot endpoints

6. REGULATORY COMPLIANCE STATUS

6.1 GDPR (EU Operations)
- Data Protection Impact Assessments: 8 of 12 required DPIAs completed
- Data Subject Access Requests: Average response time 18 days (target: 30 days)
- Data retention policy violations: 3 departments retaining data beyond approved periods

6.2 SOC 2 Type II
- Annual audit scheduled for June 2024
- 4 control gaps identified in preliminary assessment
- Estimated remediation timeline: 8 weeks

7. BUDGET AND RESOURCE ALLOCATION

Security infrastructure investment for FY2024: $4.2M
- Endpoint Detection & Response (EDR): $890K
- SIEM & Log Management: $650K
- Identity & Access Management: $520K
- AI Security Tooling: $340K
- Employee Security Training: $180K
- Penetration Testing (External): $240K
- Incident Response Retainer: $380K
- Compliance & Audit: $1.0M

8. RECOMMENDATIONS AND NEXT STEPS

8.1 Immediate Actions (0-30 days)
- Complete MFA enrollment for remaining 67 privileged accounts
- Revoke all orphaned accounts identified in Section 4.1
- Deploy emergency patch for AI chatbot authentication bypass

8.2 Short-term (30-90 days)
- Implement zero-trust architecture for all AI inference endpoints
- Deploy Langfuse for comprehensive LLM observability
- Establish vendor security assessment program with quarterly reviews
- Complete remaining 4 Data Protection Impact Assessments

8.3 Long-term (90-365 days)
- Migrate to hardware security modules (HSM) for model signing
- Implement continuous red-team testing program
- Deploy comprehensive AI governance framework aligned with EU AI Act
- Establish AI Ethics Board with quarterly review cadence

DOCUMENT CLASSIFICATION: CONFIDENTIAL
DISTRIBUTION: C-Level Executives, Board of Directors, Legal Counsel
RETENTION PERIOD: 7 years per regulatory requirements
PREPARED BY: Internal SOC Team — TechVault Solutions Inc.
APPROVED BY: Jonathan Mitchell, CISO (jonathan.mitchell@techvault.com)
DATE: April 1, 2024
"""

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, 'CONFIDENTIAL - TechVault Solutions Inc. - Internal Audit Report Q1 2024', 0, 0, 'C')
        self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

pdf = PDF()
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=20)

# Split content into sections by lines
lines = content.strip().split('\n')

pdf.add_page()

for line in lines:
    stripped = line.strip()
    
    if not stripped:
        pdf.ln(3)
        continue
    
    # Section headers (numbered sections)
    if stripped and (stripped[0].isdigit() and '.' in stripped[:3] and stripped.split('.')[0].isdigit()):
        pdf.set_font('Arial', 'B', 13)
        pdf.set_text_color(0, 80, 120)
        pdf.ln(4)
        pdf.multi_cell(0, 7, stripped.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(2)
    # Sub-headers
    elif stripped.startswith('INCIDENT') or stripped.startswith('PRIORITY') or stripped.startswith('Notable'):
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(180, 50, 50)
        pdf.multi_cell(0, 6, stripped.encode('latin-1', 'replace').decode('latin-1'))
    # Bullet points
    elif stripped.startswith('-'):
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(8)
        pdf.multi_cell(0, 5, stripped.encode('latin-1', 'replace').decode('latin-1'))
    # Separator
    elif stripped == '---':
        pdf.ln(3)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(3)
    # Title lines (all caps)
    elif stripped.isupper() and len(stripped) > 10:
        pdf.set_font('Arial', 'B', 14)
        pdf.set_text_color(0, 50, 80)
        pdf.multi_cell(0, 8, stripped.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(1)
    else:
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 5, stripped.encode('latin-1', 'replace').decode('latin-1'))

output_path = os.path.join(os.path.expanduser("~"), "Desktop", "TechVault_Cybersecurity_Audit_Q1_2024.pdf")
pdf.output(output_path)
print(f"PDF generated: {output_path}")
print(f"Pages: {pdf.page_no()}")
