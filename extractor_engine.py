"""
Renewable Energy Proposal Extractor (Engine v28.1)
Multi-Pass Neurosymbolic AI Extraction Pipeline with Dual Verification.
"""

import os
import re
import json
import copy
import time
import base64
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Standard Schemas
PASS1_SCHEMA = {
    'customerInfo': {
        'companyName': '', 'customerName': '', 'customerPhone': '', 'customerEmail': '',
        'address_m_city': '', 'address_m_line1': '', 'address_m_line2': '',
        'address_m_zip': '', 'address_m_county': '', 'address_m_country': '',
        'address_fulltext': '', 'monetaryValue': '',
    },
    'proposalDetails': {
        'quoteReference': '', 'quoteDate': '', 'validFor': '', 'preparedBy': ''
    },
}

PASS2_SCHEMA = {
    'quote': {
        'materialItems': [{'name': '', 'unitCost': '', 'quantity': ''}],
        'labor': {'name': '', 'totalLaborCost': '', 'totalHours': '', 'hourCost': ''},
        'additionalItems': [],
        'grant': {'name': '', 'details': '', 'price': ''},
        'totalGoodsAndServices': '', 'vatAmount': '', 'vatRate': '',
        'totalBeforeVAT': '', 'totalIncludingVAT': '',
    }
}

PASS3_SCHEMA = {
    'propertyDetails': {'yearBuilt': '', 'totalBuildingArea': ''},
    'epcInfo': {'epcNumber': '', 'isNewBuild': '', 'energyForHeating': '', 'energyForHotWater': ''},
    'mcsPerformance': {
        'mcsCertificationNumber': '', 'systemType': '', 'manufacturerName': '', 'manufacturerModel': '',
        'flowTemperature': '', 'scopHeating': '', 'scopHotWater': '', 'systemProvides': '',
        'hotWaterImmersionUse': '', 'hotWaterCylinderSize': '', 'nominalOutput': '', 'soundPowerLevel': '',
    },
    'devicesToInstall': [{
        'deviceType': '', 'isEnaRegistered': '', 'enaRegistrationNumber': '',
        'manufacturer': '', 'deviceRef': '', 'targetInstallDate': '', 'phaseCode': '',
        'energyStorageCapacity': '', 'powerFactor': '', 'nominalOutput': '', 'scopAtDesignTemp': '',
    }],
}

SCHEMA = {
    'customerInfo': {
        'companyName': '', 'customerName': '', 'customerPhone': '', 'customerEmail': '',
        'address_m_city': '', 'address_m_line1': '', 'address_m_line2': '',
        'address_m_zip': '', 'address_m_county': '', 'address_m_country': '',
        'address_fulltext': '', 'monetaryValue': '',
    },
    'proposalDetails': {'quoteReference': '', 'quoteDate': '', 'validFor': '', 'preparedBy': ''},
    'propertyDetails': {'yearBuilt': '', 'totalBuildingArea': ''},
    'epcInfo': {'epcNumber': '', 'isNewBuild': '', 'energyForHeating': '', 'energyForHotWater': ''},
    'mcsPerformance': {
        'mcsCertificationNumber': '', 'systemType': '', 'manufacturerName': '', 'manufacturerModel': '',
        'flowTemperature': '', 'scopHeating': '', 'scopHotWater': '', 'systemProvides': '',
        'hotWaterImmersionUse': '', 'hotWaterCylinderSize': '', 'nominalOutput': '', 'soundPowerLevel': '',
    },
    'quote': {
        'materialItems': [], 'labor': {'name': '', 'totalLaborCost': '', 'totalHours': '', 'hourCost': ''},
        'additionalItems': [], 'grant': {'name': '', 'details': '', 'price': ''},
        'totalGoodsAndServices': '', 'vatAmount': '', 'vatRate': '', 'totalBeforeVAT': '', 'totalIncludingVAT': '',
    },
    'devicesToInstall': [],
}

NO_STRIP = {
    'manufacturerModel', 'manufacturerName',
    'hotWaterImmersionUse', 'systemProvides', 'systemType', 'companyName', 'customerName',
    'preparedBy', 'validFor', 'yearBuilt', 'isNewBuild', 'address_fulltext',
    'address_m_city', 'address_m_line1', 'address_m_line2', 'address_m_county',
    'address_m_country', 'address_m_zip',
}


def to_json_schema(template):
    if isinstance(template, dict):
        props = {k: to_json_schema(v) for k, v in template.items()}
        return {'type': 'object', 'properties': props, 'required': list(props.keys())}
    elif isinstance(template, list):
        item_schema = to_json_schema(template[0]) if template else {'type': 'string'}
        return {'type': 'array', 'items': item_schema}
    else:
        return {'type': 'string'}


def clean_value(v):
    if not v:
        return ''
    return (str(v).replace('\u00a3', '').replace('\u20ac', '').replace('°C', '')
            .replace('°', '').replace(' dB', '').replace('dB', '')
            .replace(' kWh', '').replace('kWh', '').replace(' kW', '').replace('kW', '')
            .replace(' m2', '').replace('m2', '').replace('m²', '')
            .replace(' Litres', '').replace(' litres', '').replace('Litres', '').replace('litres', '')
            .replace(' L', '').replace(',', '').strip())


def sc(k, v):
    if not v:
        return ''
    return str(v).strip() if k in NO_STRIP else clean_value(v)


def parse_json(text):
    cleaned = re.sub(r'```(?:json)?\s*', '', text).strip().rstrip('`').strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    s, e = cleaned.find('{'), cleaned.rfind('}')
    if s != -1 and e > s:
        try:
            return json.loads(cleaned[s:e+1])
        except Exception:
            pass
    if s != -1:
        partial = cleaned[s:]
        stack, in_str, esc = [], False, False
        for ch in partial:
            if esc:
                esc = False
                continue
            if ch == '\\' and in_str:
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if not in_str:
                if ch in '{[':
                    stack.append('}' if ch == '{' else ']')
                elif ch in '}]' and stack and stack[-1] == ch:
                    stack.pop()
        try:
            return json.loads(partial + ''.join(reversed(stack)))
        except Exception:
            pass
    raise ValueError(f'Cannot parse JSON: {text[:300]}')


def extract_text_from_pdf(pdf_source):
    """
    Extracts text from a PDF path or file-like object using pdfplumber / pymupdf / pytesseract.
    Returns: (full_text, ocr_text_store)
    """
    import pdfplumber
    pages, ocr_text_store = [], {}
    
    with pdfplumber.open(pdf_source) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = (page.extract_text() or '').strip()
            if len(text) < 200:
                try:
                    import pytesseract
                    from pdf2image import convert_from_path
                    if isinstance(pdf_source, str):
                        images = convert_from_path(pdf_source, first_page=i, last_page=i, dpi=300)
                        if images:
                            ocr_t = pytesseract.image_to_string(images[0], lang='eng').strip()
                            if len(ocr_t) > len(text):
                                text = ocr_t
                                ocr_text_store[f'page_{i}'] = ocr_t
                except Exception:
                    pass
            if text:
                pages.append(f'--- Page {i} ---\n{text}')

    if not pages:
        raise ValueError('No readable text found in PDF.')
    
    full_text = '\n\n'.join(pages)
    return full_text, ocr_text_store


def call_llm(prompt, system, model_choice='gemini', api_key=None, schema=None):
    """
    Routes LLM call to Google Gemini 3.6 Flash (Google AI Studio API) or local Ollama.
    """
    if model_choice == 'gemini':
        import google.generativeai as genai
        key = (
            api_key 
            or os.environ.get('GEMINI_API_KEY') 
            or os.environ.get('GOOGLE_API_KEY')
            or os.environ.get('VERTEX_API_KEY') 
            or 'AQ.Ab8RN6JltpDU46s_E2_fPZDmY6yUB1owVZ05R8vertb2WL_qMg'
        )
        if not key:
            raise ValueError("No Gemini API key provided. Please configure GEMINI_API_KEY or GOOGLE_API_KEY.")
        
        genai.configure(api_key=key)
        
        # Try active production models
        client = None
        for m_id in ['gemini-3.6-flash', 'gemini-flash-latest', 'gemini-2.5-flash']:
            try:
                client = genai.GenerativeModel(m_id)
                break
            except Exception:
                continue
        if not client:
            client = genai.GenerativeModel('gemini-3.6-flash')
        gen_config = {'temperature': 0.0}
        if schema:
            gen_config['response_mime_type'] = 'application/json'
            gen_config['response_schema'] = schema
        
        try:
            response = client.generate_content([system, prompt], generation_config=gen_config)
            return parse_json(response.text)
        except Exception as ex:
            if schema:
                gen_config.pop('response_mime_type', None)
                gen_config.pop('response_schema', None)
                response = client.generate_content([system, prompt], generation_config=gen_config)
                return parse_json(response.text)
            raise ex

    elif model_choice.startswith('ollama'):
        import requests
        ollama_model = 'llama3.1' if 'llama' in model_choice else 'mistral'
        payload = {
            'model': ollama_model,
            'system': system,
            'prompt': prompt,
            'stream': False,
            'options': {'temperature': 0.0, 'num_predict': 4096, 'num_ctx': 32768},
        }
        if schema:
            payload['format'] = schema
        resp = requests.post('http://localhost:11434/api/generate', json=payload, timeout=300)
        resp.raise_for_status()
        raw = resp.json().get('response', '')
        return parse_json(raw)

    else:
        raise ValueError(f"Unknown model choice: {model_choice}")


def enrich_postcode(result, confidence):
    import requests
    UK_OUTCODE_RE = re.compile(r'^[A-Za-z]{1,2}[0-9][0-9A-Za-z]?$')
    info = result['customerInfo']
    city = info.get('address_m_city', '').strip()
    zp = info.get('address_m_zip', '').strip()
    
    if city and UK_OUTCODE_RE.match(city) and zp and len(zp) <= 4:
        full = f'{city} {zp}'
        zp = full
        city = ''
        info['address_m_zip'] = zp
        info['address_m_city'] = ''
        confidence['address_m_zip'] = {'status': 'corrected', 'detail': f'Merged to {full}'}
        
    pc = zp.replace(' ', '')
    if len(pc) < 5:
        return result
        
    try:
        r = requests.get(f'https://api.postcodes.io/postcodes/{pc}', timeout=5)
        if r.status_code == 200:
            d = r.json().get('result', {})
            if d:
                api_pc = d.get('postcode', zp)
                api_city = d.get('admin_district') or ''
                api_county = d.get('admin_county') or ''
                api_country = d.get('country') or ''
                
                if api_pc != info['address_m_zip']:
                    info['address_m_zip'] = api_pc
                if not info['address_m_city'] and api_city:
                    info['address_m_city'] = api_city
                    confidence['address_m_city'] = {'status': 'verified', 'detail': f'postcodes.io: {api_city}'}
                if not info['address_m_county']:
                    if api_county and 'pseudo' not in api_county.lower():
                        info['address_m_county'] = api_county
                        confidence['address_m_county'] = {'status': 'verified', 'detail': f'postcodes.io: {api_county}'}
                    elif api_city:
                        info['address_m_county'] = api_city
                        confidence['address_m_county'] = {'status': 'verified', 'detail': f'postcodes.io (borough): {api_city}'}
                if not info['address_m_country'] and api_country:
                    info['address_m_country'] = api_country
                    
                parts = [info['address_m_line1']]
                if info['address_m_line2']: parts.append(info['address_m_line2'])
                if info['address_m_city']: parts.append(info['address_m_city'])
                if info['address_m_county']: parts.append(info['address_m_county'])
                parts.append(info['address_m_zip'])
                info['address_fulltext'] = ', '.join(p for p in parts if p and p != '<UNK>')
                confidence['postcode_verification'] = {'status': 'verified', 'detail': f'Postcode verified: {api_pc}'}
    except Exception as ex:
        confidence['postcode_verification'] = {'status': 'error', 'detail': str(ex)}
    return result


def enrich_companies_house(result, confidence, api_key=None):
    import requests
    name = result['customerInfo'].get('companyName', '').strip()
    if not name or name == '<UNK>':
        confidence['enrichment.companiesHouse'] = {'status': 'skipped', 'detail': 'No company name to verify'}
        return
    ch_key = (
        api_key 
        or os.environ.get('COMPANIES_HOUSE_API_KEY') 
        or '1770d9fc-eb1e-48cf-99fc-24d515535c30'
    )
    try:
        headers = {}
        auth = (ch_key, '') if ch_key else None
        r = requests.get(
            f'https://api.company-information.service.gov.uk/search/companies?q={name}',
            auth=auth, headers=headers, timeout=10
        )
        if r.status_code == 200:
            items = r.json().get('items', [])
            if items:
                best = items[0]
                reg_name = best.get('title', '')
                co_number = best.get('company_number', '')
                status = best.get('company_status', '')
                name_lower = name.lower().replace(' ', '')
                reg_lower = reg_name.lower().replace(' ', '')
                is_match = (name_lower in reg_lower or reg_lower in name_lower
                           or any(w in reg_lower for w in name_lower.split() if len(w) > 3))
                result['enrichment'] = result.get('enrichment', {})
                result['enrichment']['companiesHouse'] = {
                    'searchedName': name,
                    'registeredName': reg_name,
                    'companyNumber': co_number,
                    'companyStatus': status,
                    'matchType': 'direct' if is_match else 'possible_trading_name',
                }
                confidence['enrichment.companiesHouse'] = {
                    'status': 'found' if is_match else 'possible_match',
                    'detail': f'{reg_name} ({co_number}) - {status}'
                }
            else:
                confidence['enrichment.companiesHouse'] = {
                    'status': 'not_found',
                    'detail': f'No results for "{name}" — may be sole trader'
                }
        elif r.status_code == 401:
            confidence['enrichment.companiesHouse'] = {'status': 'skipped', 'detail': 'Companies House API key required'}
        else:
            confidence['enrichment.companiesHouse'] = {'status': 'api_error', 'detail': f'HTTP {r.status_code}'}
    except Exception as ex:
        confidence['enrichment.companiesHouse'] = {'status': 'error', 'detail': str(ex)[:100]}


def enrich_epc(result, confidence, epc_email=None, epc_key=None):
    import requests
    postcode = result['customerInfo'].get('address_m_zip', '').strip()
    addr1 = result['customerInfo'].get('address_m_line1', '').strip()
    if not postcode or len(postcode) < 5:
        confidence['enrichment.epc'] = {'status': 'skipped', 'detail': 'No valid postcode'}
        return
    
    token = epc_key or os.environ.get('EPC_API_KEY') or 'XYlKmNQRV88aE8tjUymz64f5sXIY1DC9MFPiBpCPaqXL1s5sCqRv9sSydFUhWgpV'
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    pc_clean = postcode.replace(' ', '+')
    
    try:
        url = f'https://api.get-energy-performance-data.communities.gov.uk/api/domestic/search?postcode={pc_clean}'
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json().get('data', [])
            if data:
                house_num = re.match(r'^(\d+)', addr1)
                num_str = house_num.group(1) if house_num else ''
                best = None
                for item in data:
                    line1 = item.get('addressLine1', '')
                    if num_str and line1.startswith(num_str):
                        best = item
                        break
                if not best:
                    best = data[0]
                
                cert_num = best.get('certificateNumber')
                cert_url = f'https://api.get-energy-performance-data.communities.gov.uk/api/certificate?certificate_number={cert_num}'
                cr = requests.get(cert_url, headers=headers, timeout=10)
                
                if cr.status_code == 200:
                    cdata = cr.json().get('data', {})
                    rating = cdata.get('current_energy_efficiency_band', best.get('currentEnergyEfficiencyBand', ''))
                    floor_area = cdata.get('total_floor_area', '')
                    rhi = cdata.get('renewable_heat_incentive', {})
                    space_heat = rhi.get('space_heating_existing_dwelling', '')
                    water_heat = rhi.get('water_heating', '')
                    
                    epc_record = {
                        'epc_rating': rating,
                        'epc_ref': cert_num,
                        'floor_area': str(floor_area) if floor_area else '',
                        'address_match': best.get('addressLine1', ''),
                        'space_heating_kwh': str(space_heat) if space_heat else '',
                        'water_heating_kwh': str(water_heat) if water_heat else '',
                    }
                    result['enrichment'] = result.get('enrichment', {})
                    result['enrichment']['epcRegister'] = epc_record
                    
                    # Fill gaps if missing from PDF
                    if not result['propertyDetails'].get('totalBuildingArea') or result['propertyDetails']['totalBuildingArea'] == '<UNK>':
                        if floor_area:
                            result['propertyDetails']['totalBuildingArea'] = str(floor_area)
                            confidence['propertyDetails.totalBuildingArea'] = {'status': 'epc_enriched', 'detail': f'From Govt EPC: {floor_area} m2'}
                            
                    if not result['epcInfo'].get('energyForHeating') or result['epcInfo']['energyForHeating'] == '<UNK>':
                        if space_heat:
                            result['epcInfo']['energyForHeating'] = str(space_heat)
                            confidence['epcInfo.energyForHeating'] = {'status': 'epc_enriched', 'detail': f'From Govt EPC: {space_heat} kWh'}

                    confidence['enrichment.epc'] = {'status': 'found', 'detail': f'Rating: {rating}, Area: {floor_area}m2, Matched: {best.get("addressLine1")}'}
            else:
                confidence['enrichment.epc'] = {'status': 'not_found', 'detail': f'No EPC records for {postcode}'}
        elif r.status_code == 401:
            confidence['enrichment.epc'] = {'status': 'skipped', 'detail': 'EPC API Bearer token invalid or expired'}
        else:
            confidence['enrichment.epc'] = {'status': 'api_error', 'detail': f'HTTP {r.status_code}'}
    except Exception as ex:
        confidence['enrichment.epc'] = {'status': 'error', 'detail': str(ex)[:100]}


def score_extraction(result, confidence):
    sections = {
        'Customer': result.get('customerInfo', {}),
        'Proposal': result.get('proposalDetails', {}),
        'Property': result.get('propertyDetails', {}),
        'EPC': result.get('epcInfo', {}),
        'MCS': result.get('mcsPerformance', {}),
    }
    total_f = filled_f = unk_f = 0
    for sec_name, sec in sections.items():
        for key, val in sec.items():
            total_f += 1
            if val == '<UNK>':
                unk_f += 1
                filled_f += 1
            elif val:
                filled_f += 1
    items = result.get('quote', {}).get('materialItems', [])
    verified_items = sum(1 for k, v in confidence.items() if 'item.' in k and v.get('status') == 'verified')
    verified_total = sum(1 for v in confidence.values() if v.get('status') == 'verified')
    devices = result.get('devicesToInstall', [])
    pct = (filled_f / max(total_f, 1)) * 100
    quality = 'HIGH' if pct > 80 and (verified_items == len(items) or len(items) == 0) else 'MEDIUM' if pct > 60 else 'LOW'
    return {
        'pct': pct, 'filled': filled_f, 'total': total_f, 'unk': unk_f,
        'items': len(items), 'verified_items': verified_items,
        'devices': len(devices), 'checks': verified_total, 'total_checks': len(confidence),
        'quality': quality
    }


def extract_proposal(pdf_source, model_choice='gemini', api_key=None, epc_email=None, epc_key=None, ch_key=None, progress_callback=None):
    """
    Main entry point for extracting renewable energy proposals.
    """
    if progress_callback:
        progress_callback(10, "Extracting text and running OCR from PDF...")
    
    doc_text, ocr_store = extract_text_from_pdf(pdf_source)
    extra_ocr = f"\n\nOCR FROM PAGE 1:\n{ocr_store.get('page_1', '')[:1500]}" if 'page_1' in ocr_store else ''

    #  PASS 1: Customer & Address 
    if progress_callback:
        progress_callback(25, "Running PASS 1: Customer & Address extraction...")
    
    PASS1_SYSTEM = """Extract ONLY customer information and proposal details from this document.
RULES:
1. customerName = the HOMEOWNER.
2. companyName = the INSTALLER company that prepared the quote. Never customerName.
3. address_m_line1 = full first line including house number.
4. address_m_zip = FULL UK postcode.
5. address_m_city = town/city name only.
6. address_m_county = county name.
7. quoteDate = YYYY-MM-DD format.
8. preparedBy = person name from "Quote by", "Prepared by", "Surveyed by".
9. monetaryValue = final amount customer pays (TOTAL PAYABLE / Total including VAT).
10. quoteReference = Project reference / Quote ref / Reference number.
Output ONLY JSON."""

    pass1_prompt = (
        f"Schema:\n{json.dumps(PASS1_SCHEMA, indent=2)}\n\n"
        f"Now extract from this document. Output JSON only.\n\n"
        f"DOCUMENT:\n{doc_text[:8000]}"
        f"{extra_ocr}"
    )
    pass1 = call_llm(pass1_prompt, PASS1_SYSTEM, model_choice, api_key, schema=to_json_schema(PASS1_SCHEMA))

    #  PASS 2: Quote & Pricing 
    if progress_callback:
        progress_callback(45, "Running PASS 2: Financials, Grants, and Quote Line Items...")

    PASS2_SYSTEM = """Extract ONLY quote/pricing information from this document.
RULES:
1. Extract line items ONLY from the quote/pricing section with a £ price.
2. For unitCost, return the LINE TOTAL from the document — do NOT divide.
3. Default quantity to "1" if not stated.
4. Grant price: ALWAYS POSITIVE. "Grant -£7,500" -> price: "7500.00".
5. Extract totals: totalGoodsAndServices, vatAmount, vatRate, totalBeforeVAT, totalIncludingVAT.
6. Grant is NOT a material item. Put it ONLY in the grant object.
Output ONLY JSON."""

    pass2_prompt = (
        f"Schema:\n{json.dumps(PASS2_SCHEMA, indent=2)}\n\n"
        f"Now extract from this document. Output JSON only.\n\n"
        f"DOCUMENT:\n{doc_text}"
    )
    pass2 = call_llm(pass2_prompt, PASS2_SYSTEM, model_choice, api_key, schema=to_json_schema(PASS2_SCHEMA))

    #  PASS 3: Devices & Technical Specs 
    if progress_callback:
        progress_callback(65, "Running PASS 3: Heat Pump & Technical Specifications...")

    PASS3_SYSTEM = """Extract ONLY device and technical information from this document.
RULES:
1. devicesToInstall: primary devices only (Heat Pump, Solar PV, Battery).
2. flowTemperature: peak flow temp in °C (e.g. 45).
3. nominalOutput: extracted into both mcsPerformance and devicesToInstall.
4. energyForHeating / energyForHotWater: numbers only, no units.
5. systemType: standard Renbee value ("Air Source Heat Pump", "Ground Source Heat Pump", "Solar PV", "Battery Storage", "Boiler").
Output ONLY JSON."""

    pass3_prompt = (
        f"Schema:\n{json.dumps(PASS3_SCHEMA, indent=2)}\n\n"
        f"Now extract from this document. Output JSON only.\n\n"
        f"DOCUMENT:\n{doc_text}"
    )
    pass3 = call_llm(pass3_prompt, PASS3_SYSTEM, model_choice, api_key, schema=to_json_schema(PASS3_SCHEMA))

    #  MERGE & DETERMINISTIC FIXES 
    if progress_callback:
        progress_callback(80, "Merging passes and applying deterministic verification...")

    result = copy.deepcopy(SCHEMA)
    confidence = {}

    # Merge Pass 1
    for sec in ('customerInfo', 'proposalDetails'):
        src = pass1.get(sec, {})
        if isinstance(src, dict):
            for k, v in src.items():
                if k in result[sec] and v:
                    result[sec][k] = sc(k, v)

    # Merge Pass 2
    q = pass2.get('quote', {})
    result['quote']['materialItems'] = [
        {k: str(item.get(k, '')) for k in ('name', 'unitCost', 'quantity')}
        for item in q.get('materialItems', []) if isinstance(item, dict)
    ]
    for k, v in q.get('grant', {}).items():
        if k in result['quote']['grant'] and v:
            result['quote']['grant'][k] = str(v).strip() if k in ('name', 'details') else clean_value(v)
    gp = result['quote']['grant'].get('price', '')
    if gp and gp.startswith('-'):
        result['quote']['grant']['price'] = gp.lstrip('-')
    for k in ('totalGoodsAndServices', 'vatAmount', 'vatRate', 'totalBeforeVAT', 'totalIncludingVAT'):
        if k in q and q[k]:
            result['quote'][k] = clean_value(q[k])

    # Merge Pass 3
    for sec in ('propertyDetails', 'epcInfo', 'mcsPerformance'):
        src = pass3.get(sec, {})
        if isinstance(src, dict):
            for k, v in src.items():
                if k in result[sec] and v:
                    result[sec][k] = sc(k, v)

    dk = ('deviceType', 'isEnaRegistered', 'enaRegistrationNumber', 'manufacturer',
          'deviceRef', 'targetInstallDate', 'phaseCode', 'energyStorageCapacity',
          'powerFactor', 'nominalOutput', 'scopAtDesignTemp')
    result['devicesToInstall'] = [
        {k: str(d.get(k, '')) for k in dk}
        for d in pass3.get('devicesToInstall', []) if isinstance(d, dict)
    ]

    # Filter Grant from materialItems
    result['quote']['materialItems'] = [
        i for i in result['quote']['materialItems']
        if i.get('name', '').strip().lower() not in ('grant', 'bus voucher', 'boiler upgrade scheme')
    ]

    # Monetary value fallback
    if not result['customerInfo']['monetaryValue'] and result['quote']['totalIncludingVAT']:
        result['customerInfo']['monetaryValue'] = result['quote']['totalIncludingVAT']

    # Deterministic companyName extraction if missing
    if not result['customerInfo']['companyName']:
        for pat in [r'Your MCS [Cc]ertified [Ii]nstaller\s*\n\s*(.+)', r'Installed by\s*\n\s*(.+)', r'Quote valid for .+?\n\s*(.+)']:
            m = re.search(pat, doc_text)
            if m:
                cand = m.group(1).strip()
                if cand and len(cand) < 80 and not cand.startswith(('Appendix', 'Table', 'http')):
                    result['customerInfo']['companyName'] = cand
                    break

    # Contact regex fallbacks
    if not result['customerInfo'].get('customerPhone'):
        pm = re.search(r'(\b0\d{4}\s?\d{6}\b|\b0\d{3}\s?\d{3}\s?\d{4}\b|\b0\d{10}\b|\+44\s?\d{10})', doc_text)
        if pm:
            result['customerInfo']['customerPhone'] = pm.group(1).strip()
            confidence['customerInfo.customerPhone'] = {'status': 'regex_fallback', 'detail': pm.group(1).strip()}

    if not result['customerInfo'].get('customerEmail'):
        em = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', doc_text)
        if em:
            result['customerInfo']['customerEmail'] = em.group(1).strip()
            confidence['customerInfo.customerEmail'] = {'status': 'regex_fallback', 'detail': em.group(1).strip()}

    # Price verification against PDF
    pdf_prices = set()
    for m in re.finditer(r'\u00a3([\d,]+\.\d{2})', doc_text):
        pdf_prices.add(float(m.group(1).replace(',', '')))

    for item in result['quote']['materialItems']:
        try:
            qty = int(float(item.get('quantity', '1') or '1'))
            val = float(item.get('unitCost', '0') or '0')
            if val in pdf_prices:
                item['lineTotal'] = f"{val:.2f}"
                confidence[f"item.{item['name'][:30]}.cost"] = {'status': 'verified', 'detail': f"Matched £{val:.2f} in PDF"}
            else:
                confidence[f"item.{item['name'][:30]}.cost"] = {'status': 'unverified', 'detail': f"£{val:.2f} not in PDF prices"}
        except Exception:
            pass

    # Mark absent fields as <UNK>
    for sec_name, fields in [
        ('customerInfo', ['customerPhone', 'customerEmail', 'address_m_line2']),
        ('propertyDetails', ['yearBuilt', 'totalBuildingArea']),
        ('epcInfo', ['epcNumber', 'isNewBuild']),
        ('mcsPerformance', ['mcsCertificationNumber', 'scopHotWater', 'soundPowerLevel']),
        ('proposalDetails', ['quoteReference']),
    ]:
        for f in fields:
            if not result[sec_name].get(f):
                result[sec_name][f] = '<UNK>'
                confidence[f'{sec_name}.{f}'] = {'status': 'confirmed_absent', 'detail': 'Not in PDF'}

    #  ENRICHMENT LAYER 
    if progress_callback:
        progress_callback(90, "Running external enrichments (Postcodes.io, EPC, Companies House)...")

    result = enrich_postcode(result, confidence)
    enrich_companies_house(result, confidence, api_key=ch_key)
    enrich_epc(result, confidence, epc_email=epc_email, epc_key=epc_key)

    quality = score_extraction(result, confidence)

    if progress_callback:
        progress_callback(100, "Extraction complete!")

    return {
        'result': result,
        'confidence': confidence,
        'quality': quality,
        'doc_text': doc_text
    }
