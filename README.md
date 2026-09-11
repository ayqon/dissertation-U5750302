# Renbee — Renewable Energy Proposal Extractor & Intelligence Engine

**Architecture:** Multi-Pass Neurosymbolic AI Extraction & Cross-Verification Pipeline  
**Active Model:** Google Gemini 2.5 Flash / 1.5 Flash (Google AI Studio API)  
**Live Production URL:** [https://renbee-extractor-730963128390.europe-west2.run.app](https://renbee-extractor-730963128390.europe-west2.run.app)

---

> ### ⚠️ Note on ENA (Energy Networks Association) Device Register Integration
> 
> * **Portal Migration & Scraping Deprecation:**  
>   The Energy Networks Association (ENA) updated their Connect Direct equipment database portal with dynamic session handling and automated bot protections. Consequently, programmatic headless browser scraping (Selenium) is no longer a viable, stable approach for querying device registrations.
> 
> * **Official Integration:**  
>   The enterprise-grade way to integrate with the ENA database is through their **official REST API**, which requires formal organizational registration, vetting, and API key provisioning.
> 
> * **Implementation Status:**  
>   To guarantee 100% deterministic, high-speed execution and eliminate external browser dependencies in production/CI environments, the Selenium prototype (Step 6e) is disabled in favor of the direct API hooks.
> 
> * **Ready for Activation:**  
>   The pipeline hooks and schema fields (`enaRegistrationNumber`, `enaMatchScore`, `enaProductName`) are fully structured in code and ready to activate as soon as the organizational API key is supplied.

---

## 1. Overview & Neurosymbolic Pipeline Architecture

This platform automates the extraction, financial reconciliation, and multi-registry verification of UK renewable energy proposals (Heat Pump and Solar PV quotes) from unstructured PDF documents into standardized JSON payloads.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           RAW PROPOSAL PDF DOCUMENT                             │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     0. INGESTION & TEXT EXTRACTION LAYER                        │
│   • Digital PDF Parser (pdfplumber)                                             │
│   • OCR Fallback Engine (pytesseract + pdf2image / Poppler)                     │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
               ┌─────────────────────────┴─────────────────────────┐
               │                                                   │
               ▼                                                   ▼
┌───────────────────────────────┐               ┌─────────────────────────────────┐
│ PASS 1: ENTITIES & CUSTOMER   │               │ PASS 2: FINANCIALS & BOM        │
│ • Installer & Prepared By     │               │ • Itemized Materials & Labor    │
│ • Customer Name, Phone, Email │               │ • BUS Grant Deductions (£7,500) │
│ • Site Address & Postcode     │               │ • VAT Calculation & Subtotals   │
│ • Quote Ref & Overall Value   │               │ • Net Customer Payable Total    │
└──────────────┬────────────────┘               └────────────────┬────────────────┘
               │                                                 │
               └─────────────────────────┬───────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ PASS 3: TECHNICAL SPECIFICATIONS & MCS PERFORMANCE                              │
│ • Heat Pump Manufacturer, Model, & System Type (ASHP / GSHP)                    │
│ • Nominal Output (kW), Design Flow Temp (°C), SCoP Heating / Hot Water          │
│ • Cylinder Capacity (L), Sound Power (dB), Emitter Types                        │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 4. DETERMINISTIC CLEANING & MATH RECONCILIATION LAYER                           │
│ • Unit symbol normalization & string stripping                                  │
│ • Currency, quantity & line total arithmetic validation                         │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 5. SYMBOLIC MULTI-REGISTRY VERIFICATION & ENRICHMENT                            │
│ ┌────────────────────────┐  ┌────────────────────────┐  ┌─────────────────────┐ │
│ │     Postcodes.io       │  │  Companies House API   │  │  UK Govt EPC Open   │ │
│ │ • Postal verification  │  │ • Registered legal name│  │ • EPC certificate   │ │
│ │ • Outward/Inward parse │  │ • Company active check │  │ • Floor area (m²)   │ │
│ │ • Geo-coordinates      │  │ • Company registration │  │ • Heat demand kWh   │ │
│ └────────────────────────┘  └────────────────────────┘  └─────────────────────┘ │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ FINAL AUDIT-READY RENBEE JSON OUTPUT (<proposal>-output.json)                   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

### 🔍 Detailed Step-by-Step Breakdown of Pipeline Passes

| Pipeline Stage | Technology / Module | Inputs | Extraction Targets & Responsibilities | Output / Target Schema |
| :--- | :--- | :--- | :--- | :--- |
| **Stage 0: Document Ingestion** | `pdfplumber`, `pytesseract`, `pdf2image` | Unstructured PDF Proposal | Extracts raw text layout; executes OCR on scanned/image-based pages. | Clean text buffer & structured page segments |
| **Pass 1: Customer & Site Entities** | Gemini Structured Output (`PASS1_SCHEMA`) | Document text | Isolates company identity, customer name, contact details, site address, quote reference, and validity date. | `customerInfo`, `proposalDetails` |
| **Pass 2: Financials & BOM Reconciliation** | Gemini Structured Output (`PASS2_SCHEMA`) | Document text | Parses itemized materials, unit prices, quantities, labor hours/rates, BUS grant deductions, VAT amount, and total payable. | `quote` (materials, labor, grants, totals) |
| **Pass 3: Technical & MCS Specs** | Gemini Structured Output (`PASS3_SCHEMA`) | Document text | Extracts heat pump manufacturer, model number, nominal capacity (kW), flow temperature (°C), SCoP rating, cylinder size. | `mcsPerformance`, `devicesToInstall`, `propertyDetails` |
| **Stage 4: Normalization & Math Check** | Python Engine (`clean_value`, Math Assertions) | Raw extracted JSON | Strips unit annotations (`£`, `kW`, `°C`, `dB`, `kWh`), enforces numeric casting, and verifies that `Subtotal - Grant + VAT = Total`. | Cleaned & reconciled JSON payload |
| **Stage 5: Registry Cross-Verification** | REST API Connectors | Normalized address, company, & postcode | Queries **Postcodes.io**, **Companies House API**, and **UK EPC Open Communities API** to enrich payload with official verified records. | `enrichment` (Companies House, EPC Register, Postcodes) |

---

## 2. Directory Structure

```
├── server.py                 # FastAPI backend server & REST API
├── extractor_engine.py       # Core multi-pass extraction pipeline
├── static/
│   └── index.html           # Bespoke Renbee SPA frontend (HTML5/CSS3/JS)
├── Renewable_Energy_...ipynb # Reference Jupyter Notebook (pipeline prototyping)
├── requirements.txt         # Minimal Python dependencies
├── Dockerfile               # Production container configuration for Cloud Run
├── .dockerignore            # Container build ignore rules
├── .env.example             # Template environment variables
├── README.md                # Comprehensive documentation
└── gcp_deploy.zip           # Pre-packaged 1-click GCP deployment archive
```

---

## 3. Required API Keys & Step-by-Step Acquisition Links

To run the pipeline with your own credentials, configure the following external API keys:

| Service | Environment Variable | Purpose | Direct Registration Link |
| :--- | :--- | :--- | :--- |
| **Google Gemini API** | `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Powers semantic extraction passes (Passes 1, 2, and 3) | [Google AI Studio Console](https://aistudio.google.com/) |
| **UK Govt EPC Register** | `EPC_API_KEY` | Official UK Domestic Energy Performance Certificate lookup | [UK Government Open Data EPC Portal](https://epc.opendatacommunities.org/docs/api) |
| **Companies House** | `COMPANIES_HOUSE_API_KEY` | Official UK Government business status & company number lookup | [Companies House Developer Hub](https://developer.company-information.service.gov.uk/) |

---

### 🔑 How to Obtain Each API Key:

1. **Google Gemini API Key**:
   * Visit [Google AI Studio](https://aistudio.google.com/).
   * Sign in with your Google account and click **"Get API key"** -> **"Create API key"**.
   * Copy the generated key and assign it to `GEMINI_API_KEY` (Free tier provides generous limits for development and testing).

2. **UK Government EPC Register Bearer Token**:
   * Visit the [UK Government Open Data Communities EPC Portal](https://epc.opendatacommunities.org/docs/api) (or [Register / Sign In](https://epc.opendatacommunities.org/login)).
   * Register for free with your email address to generate an instant Bearer token.
   * Copy the Bearer Token and assign it to `EPC_API_KEY`.

3. **UK Companies House API Key**:
   * Visit the [Companies House Developer Hub](https://developer.company-information.service.gov.uk/).
   * Create a free developer account and navigate to **"Manage Applications"** -> **"Create an application"**.
   * Select **REST API Service**, create an API key, and assign it to `COMPANIES_HOUSE_API_KEY`.

---

> **Note on Web UI Overrides:**  
> The web interface also includes a **"Save Credentials"** button in the left sidebar that allows users to override and save their own custom API keys directly into browser `localStorage`.

---

## 4. Local Quickstart

### Prerequisites
* Python 3.10+
* `tesseract-ocr` & `poppler-utils` (for scanned PDF fallbacks)

### Installation
```bash
# 1. Clone repository & navigate to directory
git clone https://github.com/Renbee-Tech/warwick_docparse.git
cd warwick_docparse

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables (or copy .env.example)
cp .env.example .env

# 4. Launch application
python server.py
```

Open your browser at **`http://localhost:8000`** to access the web application.

---

## 5. Deployment & Multi-Platform Hosting Guide

The service is packaged with a production-ready **Dockerfile** and can be deployed anywhere containerized or Python web apps run.

---

### Option A: Universal Docker Container (Any Server / Cloud)

Run anywhere Docker is installed (local machine, EC2, Compute Engine, DigitalOcean, or private servers):

```bash
# 1. Build the Docker image
docker build -t renbee-extractor .

# 2. Run the container
docker run -d \
  -p 8080:8080 \
  -e GEMINI_API_KEY="YOUR_GEMINI_API_KEY" \
  -e EPC_API_KEY="YOUR_EPC_API_KEY" \
  -e COMPANIES_HOUSE_API_KEY="YOUR_COMPANIES_HOUSE_KEY" \
  --name renbee-app \
  renbee-extractor
```

Access at `http://<your-server-ip>:8080`.

---

### Option B: Google Cloud Run (Serverless GCP)

Deploy directly using **Google Cloud Shell**:

1. Open **[Google Cloud Shell](https://console.cloud.google.com/)**.
2. Upload `gcp_deploy.zip` or clone the repository.
3. Run the deployment command:

```bash
# Set project & deploy
gcloud config set project YOUR_GCP_PROJECT_ID

gcloud run deploy renbee-extractor \
  --source . \
  --region europe-west2 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars="GEMINI_API_KEY=YOUR_GEMINI_API_KEY,EPC_API_KEY=YOUR_EPC_API_KEY,COMPANIES_HOUSE_API_KEY=YOUR_COMPANIES_HOUSE_KEY"
```

---

### Option C: AWS (App Runner or ECS Fargate)

1. **Push to Amazon ECR**:
   ```bash
   aws ecr get-login-password --region eu-west-2 | docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.eu-west-2.amazonaws.com
   docker tag renbee-extractor:latest <aws_account_id>.dkr.ecr.eu-west-2.amazonaws.com/renbee-extractor:latest
   docker push <aws_account_id>.dkr.ecr.eu-west-2.amazonaws.com/renbee-extractor:latest
   ```
2. **Deploy on AWS App Runner**:
   * Create a new Service -> Select **Container registry** -> **Amazon ECR**.
   * Set Port to `8080`.
   * Add Environment Variables (`GEMINI_API_KEY`, `EPC_API_KEY`, `COMPANIES_HOUSE_API_KEY`).
   * Click **Deploy** to get an instant HTTPS URL.

---

### Option D: One-Click PaaS (Render, Railway, Fly.io)

1. **Connect Repository**: Link `https://github.com/Renbee-Tech/warwick_docparse.git` in Render / Railway / Fly.io.
2. **Environment**: Select **Docker** (the platform will auto-detect the root `Dockerfile`).
3. **Environment Variables**: Add your `GEMINI_API_KEY`, `EPC_API_KEY`, and `COMPANIES_HOUSE_API_KEY` in the dashboard settings.
4. **Port**: Set listening port to `8080` (or leave default).

---

### Option E: Standard Linux VPS (Ubuntu / Debian / Debian-based Server)

```bash
# 1. Update system and install OCR & Poppler binaries
sudo apt update && sudo apt install -y python3-pip python3-venv tesseract-ocr poppler-utils libgl1

# 2. Clone repo & create virtual environment
git clone https://github.com/Renbee-Tech/warwick_docparse.git /opt/renbee-app
cd /opt/renbee-app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
nano .env

# 4. Run with Uvicorn (or manage with systemd / PM2)
uvicorn server:app --host 0.0.0.0 --port 8080
```

## 6. Dataset & Downstream System Integration

### 📁 Input Proposals (`proposals/` Directory)
The `proposals/` folder contains real-world, industry-standard renewable energy installation quotes and heat pump proposals provided directly by our industry partner (**Renbee**). These heterogeneous PDF documents (ranging from multi-page digital estimates to scanned itemized quotes) serve as the empirical benchmark dataset for evaluating the pipeline's extraction recall, financial math reconciliation, and symbolic verification accuracy.

### 🔄 Downstream Renbee Platform Integration
The structured JSON payload generated by this platform (`<input_filename>-output.json`) was **specifically engineered to conform to Renbee's exact internal schema specifications**. 

By producing clean, schema-enforced, and cross-verified JSON data, this extractor directly integrates into Renbee's broader software ecosystem, enabling:
* **Automated Installer Ingestion**: Ingesting quote data directly into Renbee's installer onboarding and quote verification workflows without manual transcription.
* **Downstream Subsystem Development**: Providing structured inputs for Renbee's existing pricing engines, customer management tools, and heat pump sizing verification modules.
* **Subsidy & Compliance Validation**: Supplying pre-verified Boiler Upgrade Scheme (BUS) grant figures and MCS technical parameters for rapid financing and grant compliance checks.

---

## 7. Output JSON Schema Specification

When you click **Download `<filename>-output.json`**, the payload conforms to the standardized downstream schema:

```json
{
  "customerInfo": {
    "customerName": "...",
    "customerPhone": "...",
    "customerEmail": "...",
    "companyName": "...",
    "preparedBy": "...",
    "quoteReference": "...",
    "address_m_line1": "...",
    "address_m_city": "...",
    "address_m_county": "...",
    "address_m_zip": "...",
    "address_fulltext": "...",
    "monetaryValue": 0.0
  },
  "quote": {
    "totalGoodsAndServices": 0.0,
    "vatAmount": 0.0,
    "totalIncludingVAT": 0.0,
    "grant": {
      "name": "BUS",
      "price": 0.0
    },
    "materialItems": [
      {
        "name": "...",
        "quantity": 1,
        "unitCost": 0.0,
        "lineTotal": 0.0
      }
    ]
  },
  "mcsPerformance": {
    "systemType": "Heat Pump",
    "manufacturerName": "...",
    "manufacturerModel": "...",
    "nominalOutput": 0.0,
    "flowTemperature": 0,
    "scopHeating": 0.0,
    "hotWaterCylinderSize": 0,
    "emitterType": "..."
  },
  "propertyDetails": {
    "totalBuildingArea": 0.0,
    "yearBuilt": "..."
  },
  "epcInfo": {
    "energyForHeating": 0,
    "energyForHotWater": 0
  },
  "devicesToInstall": [
    {
      "deviceType": "Heat Pump",
      "manufacturer": "...",
      "deviceRef": "..."
    }
  ],
  "enrichment": {
    "companiesHouse": {
      "companyNumber": "...",
      "registeredName": "...",
      "companyStatus": "active",
      "matchType": "Direct"
    },
    "epcRegister": {
      "epc_rating": "...",
      "floor_area": "...",
      "space_heating_kwh": "...",
      "address_match": "..."
    }
  }
}
```

---

## 8. License & Credits

* Maintained by **Renbee Tech**
* Project: **warwick_docparse**

