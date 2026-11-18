# CyberRisk
### AI-Powered Continuous Cyber Risk Quantification and Investment Optimization Platform

CyberRisk is a cybersecurity risk management platform designed to help organizations identify security weaknesses, assess asset-level risks, monitor system activity, and prioritize security investments within a limited budget.

The platform combines asset management, network scanning, vulnerability intelligence, explainable risk assessment, monitoring, and mathematical investment optimization in one application.

## Key Features

- **Organization & Asset Management:** Manage organizations and their IT assets, including servers, databases, applications, workstations, and network devices.
- **Network Scanning:** Use Nmap to discover hosts, open ports, and running services on authorized networks.
- **Vulnerability Intelligence:** Integrate NVD vulnerability information and CISA Known Exploited Vulnerabilities (KEV) data.
- **Risk Quantification:** Calculate explainable asset-level and organization-level cyber risk using security findings, asset criticality, exposure, and verified control assessments.
- **Security Controls:** Maintain security controls and assess their implementation status and effectiveness.
- **System Monitoring:** Collect Windows system metrics such as CPU, memory, disk, and network activity.
- **Predictive Risk Analysis:** Use explainable statistical and rule-based analysis to identify unusual observations and emerging risk indicators.
- **Security Investment Optimization:** Use Google OR-Tools to prioritize investment options under an available budget.
- **External Security Data Integration:** Support OpenVAS XML report imports and Wazuh finding integration.

## Technology Stack

| Component | Technologies |
|---|---|
| Frontend | React, Vite, JavaScript, Tailwind CSS |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Network Scanning | Nmap |
| Vulnerability Intelligence | NVD, CISA KEV |
| Optimization | Google OR-Tools |
| Monitoring & Scheduling | Python monitoring agent, APScheduler |
| External Data Integration | OpenVAS XML, Wazuh |

## System Architecture

```text
                React Frontend
                      |
                      | REST API
                      |
                FastAPI Backend
                      |
       +--------------+--------------+
       |              |              |
   Risk Engine    Monitoring     Optimization
       |              |              |
       +--------------+--------------+
                      |
                  PostgreSQL
                      |
        External Security Information
        Nmap | NVD | CISA KEV
        OpenVAS XML | Wazuh
```

## Project Structure

```text
CyberRisk/
│
├── backend/
│   ├── routers/
│   ├── services/
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

*The structure above highlights the main application components.*

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js and npm
- PostgreSQL
- Nmap
- Git


### 2. Backend Setup

```bash
cd backend

python -m venv .venv
```

Activate the environment:

**Windows PowerShell**
```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Configure the PostgreSQL connection using your local environment configuration. Refer to the project's database configuration for the required environment variable names.

Start the backend:

```bash
python -m uvicorn main:app --reload
```

Backend API documentation:

```text
http://127.0.0.1:8000/docs
```

### 3. Frontend Setup

Open another terminal:

```bash
cd frontend

npm install
npm run dev
```

Open the frontend:

```text
http://localhost:5173/
```

## Important Notes

- Configure your own database and environment variables before running the application.
- Network scanning must only be performed on systems and networks for which you have authorization.
- NVD and CISA KEV information depends on the available external vulnerability data.
- OpenVAS and Wazuh functionality supports external finding/report integration; this repository does not include a complete live deployment of those platforms.
- Predictive analysis currently uses explainable statistical and rule-based methods, not a trained machine-learning model.
- Investment costs and expected risk reductions are estimates configured for the optimization model, not guaranteed real-world outcomes.
- Demonstration findings and organization records may contain simulated data.

## Future Enhancements

- Trained machine-learning models using larger historical datasets.
- Live integrations with external security monitoring platforms.
- Multi-asset shared-budget investment optimization.
- Automated security remediation.
- Cloud security integrations and advanced reporting.

## Project Purpose

CyberRisk aims to connect technical cybersecurity findings with organizational risk management and budget-aware security decision-making.

**Identify risks. Understand their impact. Prioritize security investments.**

## Developed By 
Abhishek Ghadge
