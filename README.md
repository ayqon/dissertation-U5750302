# Renbee — Renewable Energy Proposal Extractor & Intelligence Engine

**Author & Developer:** Ioannis Konstantinou ([github.com/ayqon](https://github.com/ayqon))  
**Project:** `dissertation-U5750302`  
**Architecture:** Multi-Pass Neurosymbolic AI Extraction & Cross-Verification Pipeline  
**Active Model:** Google Gemini 3.6 Flash (Google AI Studio API)  

---

## 1. Overview & Neurosymbolic Architecture

This platform automates the extraction and validation of UK renewable energy proposals (Heat Pump and Solar PV installation quotes) from unstructured PDF documents into standardized, audit-ready JSON payloads.

Unlike basic single-pass LLM prompts, this system implements a **multi-pass neurosymbolic architecture**:
1. **Pass 1 — Customer & Property Entity Extraction**: Isolates installer companies, customers, quote references, and full installation site addresses.
2. **Pass 2 — Financials & BOM Reconciliation**: Extracts itemized bills of materials, applies UK Boiler Upgrade Scheme (BUS) grant deductions, and verifies VAT math consistency.
3. **Pass 3 — Technical & MCS Specifications**: Extracts heat pump manufacturer, model names, nominal output (kW), design flow temperature (°C), seasonal efficiency (SCoP), and annual heat demand (kWh).
4. **Symbolic Verification & Knowledge Graph Cross-Check**:
   * **UK Postcodes.io**: Validates and normalizes outward/inward UK postal codes.
   * **Companies House API**: Performs live business lookup, verifying company number and status.
   * **UK Government Domestic EPC Register**: Queries live national energy performance certificates to verify property floor area and benchmark annual space heating demand.

---

## 2. Directory Structure

```
├── server.py                 # FastAPI backend server & REST API
├── extractor_engine.py       # Core multi-pass extraction pipeline
├── static/
│   └── index.html           # Bespoke Renbee SPA frontend (HTML5/CSS3/JS)
├── Renewable_Energy_...ipynb # Academic Jupyter Notebook (identical pipeline)
├── requirements.txt         # Minimal Python dependencies
├── Dockerfile               # Production container configuration for Cloud Run
├── .dockerignore            # Container build ignore rules
├── .env.example             # Template environment variables
├── README.md                # Comprehensive documentation
└── gcp_deploy.zip           # Pre-packaged 1-click GCP deployment archive
```

---

## 3. Required API Keys & Credentials

To run the pipeline locally or in production, configure the following credentials:

| Service | Environment Variable | Purpose | How to Obtain |
| :--- | :--- | :--- | :--- |
| **Google Gemini API** | `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Powers semantic extraction passes | [Google AI Studio](https://aistudio.google.com/) |
| **UK Govt EPC Register** | `EPC_API_KEY` | Official Domestic EPC certificate lookup | [Get Energy Performance Data](https://get-energy-performance-data.communities.gov.uk/) |
| **Companies House** | `COMPANIES_HOUSE_API_KEY` | Live installer business registration check | [Companies House Developer Hub](https://developer.company-information.service.gov.uk/) |

> **Note:** The UI includes a **"Save Credentials"** button in the left sidebar that saves your API keys directly in browser `localStorage` for convenience.

---

## 4. Local Quickstart

### Prerequisites
* Python 3.10+
* `tesseract-ocr` & `poppler-utils` (for scanned PDF fallbacks)

### Installation
```bash
# 1. Clone repository & navigate to directory
cd extrfiles

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch application
python server.py
```

Open your browser at **`http://localhost:8000`** to access the web application.

---

## 5. Hosting Live on Google Cloud Platform (GCP)

Deploy to **Google Cloud Run** in minutes using **Google Cloud Shell**:

### Step 1: Open Google Cloud Shell
Go to [console.cloud.google.com](https://console.cloud.google.com/) and open the **Cloud Shell** terminal (terminal icon in top-right).

### Step 2: Upload Deployment Package
Click the three-dot menu (**More**) in the Cloud Shell top-right corner, select **Upload**, and upload `gcp_deploy.zip`.

### Step 3: Unzip & Deploy
Run the following commands in Cloud Shell:

```bash
# 1. Unzip the deployment files
unzip -o gcp_deploy.zip -d renbee-app && cd renbee-app

# 2. Set active project
gcloud config set project dissertation-u5750302

# 3. Build & Deploy to Google Cloud Run
gcloud run deploy renbee-extractor \
  --source . \
  --region europe-west2 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars="GEMINI_API_KEY=AQ.Ab8RN6JltpDU46s_E2_fPZDmY6yUB1owVZ05R8vertb2WL_qMg,EPC_API_KEY=XYlKmNQRV88aE8tjUymz64f5sXIY1DC9MFPiBpCPaqXL1s5sCqRv9sSydFUhWgpV,COMPANIES_HOUSE_API_KEY=1770d9fc-eb1e-48cf-99fc-24d515535c30"
```

Once deployment completes, Cloud Run outputs your live public HTTPS URL:
```
https://renbee-extractor-730963128390.europe-west2.run.app
```

**Live Production Deployment:** [https://renbee-extractor-730963128390.europe-west2.run.app](https://renbee-extractor-730963128390.europe-west2.run.app)


---

## 6. Output JSON Schema

When you click **Download `<filename>-output.json`**, the payload conforms to the standard schema:

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
    "monetaryValue": 4500.0
  },
  "quote": {
    "totalGoodsAndServices": 12000.0,
    "vatAmount": 0.0,
    "totalIncludingVAT": 12000.0,
    "grant": { "name": "BUS", "price": 7500.0 },
    "materialItems": [
      { "name": "...", "quantity": 1, "unitCost": 0.0, "lineTotal": 0.0 }
    ]
  },
  "mcsPerformance": {
    "systemType": "Heat Pump",
    "manufacturerName": "...",
    "manufacturerModel": "...",
    "nominalOutput": 8.0,
    "flowTemperature": 45,
    "scopHeating": 3.8,
    "hotWaterCylinderSize": 200,
    "emitterType": "Radiators"
  },
  "propertyDetails": {
    "totalBuildingArea": 157.0,
    "yearBuilt": "1980-1990"
  },
  "epcInfo": {
    "energyForHeating": 21131,
    "energyForHotWater": 2500
  },
  "enrichment": {
    "companiesHouse": { ... },
    "epcRegister": { ... }
  }
}
```

---

## 7. License & Credits

* Developed for Academic Dissertation research (`dissertation-U5750302`).
* Author: **Ioannis Konstantinou** ([github.com/ayqon](https://github.com/ayqon)).
