# Renbee — Renewable Energy Proposal Extractor & Intelligence Engine

**Author & Developer:** Ioannis Konstantinou ([github.com/ayqon](https://github.com/ayqon))  
**Project:** `dissertation-U5750302`  
**Architecture:** Multi-Pass Neurosymbolic AI Extraction & Cross-Verification Pipeline  
**Active Model:** Google Gemini 3.6 Flash (Google AI Studio API)  
**Live Production URL:** [https://renbee-extractor-730963128390.europe-west2.run.app](https://renbee-extractor-730963128390.europe-west2.run.app)

---

> ### ⚠️ Note on ENA (Energy Networks Association) Device Register Integration
> 
> * **Portal Migration & Scraping Deprecation:**  
>   During the final evaluation cycle, the Energy Networks Association (ENA) updated their Connect Direct equipment database portal with dynamic session handling and automated bot protections. Consequently, programmatic headless browser scraping (Selenium) is no longer a viable, stable approach for querying device registrations.
> 
> * **Official Solution & Academic Scope:**  
>   The legitimate, enterprise-grade way to integrate with the ENA database is through their **official REST API**, which requires formal organizational registration, vetting, and API key provisioning (a process currently requested and pending organizational review).
> 
> * **Implementation Status in this Submission:**  
>   ENA registry cross-matching was **not part of the original formal research objectives or methodology defined in the dissertation proposal**; it was explored as an experimental industry add-on requested by company stakeholders. To guarantee 100% deterministic, high-speed execution and eliminate external browser dependencies for examiners, the Selenium prototype (Step 6e) is safely **commented out**.
> 
> * **Ready for Activation:**  
>   The pipeline hooks and schema fields (`enaRegistrationNumber`, `enaMatchScore`, `enaProductName`) are fully structured in code and ready to activate as soon as the organizational API key is supplied.

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

## 3. Required API Keys & Step-by-Step Acquisition Links

To run the pipeline with your own credentials, configure the following external API keys:

| Service | Environment Variable | Purpose | Direct Registration Link |
| :--- | :--- | :--- | :--- |
| **Google Gemini API** | `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Powers semantic extraction passes (Passes 1, 2, and 3) | [Google AI Studio Console](https://aistudio.google.com/) |
| **UK Govt EPC Register** | `EPC_API_KEY` | Official UK Domestic Energy Performance Certificate lookup | [UK Government EPC Register Developer Portal](https://api.get-energy-performance-data.communities.gov.uk/) |
| **Companies House** | `COMPANIES_HOUSE_API_KEY` | Official UK Government business status & company number lookup | [Companies House Developer Hub](https://developer.company-information.service.gov.uk/) |

---

### 🔑 How to Obtain Each API Key:

1. **Google Gemini API Key**:
   * Visit [Google AI Studio](https://aistudio.google.com/).
   * Sign in with your Google account and click **"Get API key"** -> **"Create API key"**.
   * Copy the generated key and assign it to `GEMINI_API_KEY` (Free tier provides generous limits for development and research).

2. **UK Government EPC Register Bearer Token**:
   * Visit the [UK Government Open Data Communities Register](https://api.get-energy-performance-data.communities.gov.uk/).
   * Register with your email address to generate an instant Bearer token.
   * Copy the Bearer Token and assign it to `EPC_API_KEY`.

3. **UK Companies House API Key**:
   * Visit the [Companies House Developer Hub](https://developer.company-information.service.gov.uk/).
   * Create a free developer account and navigate to **"Manage Applications"** -> **"Create an application"**.
   * Select **REST API Service**, create an API key, and assign it to `COMPANIES_HOUSE_API_KEY`.

---

> 📧 **Direct Evaluation Access & Author Contact:**  
> If examiners, reviewers, or evaluators wish to test and run the exact codebase immediately without creating external UK Government and AI developer accounts, you are welcome to contact the author directly to request pre-authenticated evaluation credentials:  
> **Contact Email:** [`Ioannis.Konstantinou@warwick.ac.uk`](mailto:Ioannis.Konstantinou@warwick.ac.uk)

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

* Developed for Academic Dissertation research (`dissertation-U5750302`).
* Industry Partner: **Renbee**
* Author: **Ioannis Konstantinou** ([github.com/ayqon](https://github.com/ayqon)).

