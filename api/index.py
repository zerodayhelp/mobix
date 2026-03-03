#!/usr/bin/env python3
"""
Flask phone number parsing API using the `phonenumbers` library.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import phonenumbers
from phonenumbers import PhoneNumberType, PhoneNumberFormat
from phonenumbers import carrier as carrier_mod, geocoder as geocoder_mod, timezone as timezone_mod
import logging
import requests
import json

app = Flask(__name__)

# ✅ CORS CONFIG for Cross-Origin Requests from zeroday.help
CORS(
    app,
    resources={r"/*": {"origins": ["https://zeroday.help", "http://localhost", "http://localhost:3000", "http://localhost:5000", "http://127.0.0.1", "http://127.0.0.1:3000", "http://127.0.0.1:5000"]}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]
)

# Configure CORS headers manually for all responses
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin', '')
    allowed_origins = [
        "https://zeroday.help",
        "http://localhost",
        "http://localhost:3000", 
        "http://localhost:5000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5000"
    ]
    
    # Allow specific origins
    if origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)
    else:
        # For development, allow all (remove this in production)
        response.headers.add('Access-Control-Allow-Origin', '*')
    
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Accept, Origin')
    response.headers.add('Access-Control-Allow-Methods', 'GET, PUT, POST, DELETE, OPTIONS, HEAD, PATCH')
    response.headers.add('Access-Control-Max-Age', '86400')  # 24 hours
    return response

logging.basicConfig(level=logging.INFO)

TYPE_MAP = {
    PhoneNumberType.MOBILE: "Mobile",
    PhoneNumberType.FIXED_LINE: "Fixed Line",
    PhoneNumberType.FIXED_LINE_OR_MOBILE: "Fixed Line or Mobile",
    PhoneNumberType.TOLL_FREE: "Toll Free",
    PhoneNumberType.PREMIUM_RATE: "Premium Rate",
    PhoneNumberType.SHARED_COST: "Shared Cost",
    PhoneNumberType.VOIP: "VoIP",
    PhoneNumberType.PERSONAL_NUMBER: "Personal Number",
    PhoneNumberType.PAGER: "Pager",
    PhoneNumberType.UAN: "UAN",
    PhoneNumberType.UNKNOWN: "Unknown"
}


def get_number_info(number_str: str, region: str | None = None, language: str = "en") -> dict:
    try:
        if region:
            parsed = phonenumbers.parse(number_str, region.upper())
        else:
            parsed = phonenumbers.parse(number_str, None)
    except phonenumbers.NumberParseException as e:
        return {"error": "NumberParseException", "message": str(e)}

    is_valid = phonenumbers.is_valid_number(parsed)
    is_possible = phonenumbers.is_possible_number(parsed)
    number_type = phonenumbers.number_type(parsed)
    type_str = TYPE_MAP.get(number_type, "Unknown")

    international_format = phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL)
    national_format = phonenumbers.format_number(parsed, PhoneNumberFormat.NATIONAL)
    e164_format = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
    rfc3966 = phonenumbers.format_number(parsed, PhoneNumberFormat.RFC3966)

    region_code = phonenumbers.region_code_for_number(parsed)
    country_code = parsed.country_code

    try:
        carrier_name = carrier_mod.name_for_number(parsed, language) or ""
    except Exception:
        carrier_name = ""

    try:
        geo_description = geocoder_mod.description_for_number(parsed, language) or ""
    except Exception:
        geo_description = ""

    try:
        tz = list(timezone_mod.time_zones_for_number(parsed))
    except Exception:
        tz = []

    return {
        "input": number_str,
        "region_hint": (region.upper() if region else None),
        "valid": is_valid,
        "possible": is_possible,
        "type": type_str,
        "type_code": int(number_type),
        "region_code": region_code,
        "country_code": int(country_code),
        "international_format": international_format,
        "national_format": national_format,
        "e164": e164_format,
        "rfc3966": rfc3966,
        "carrier": carrier_name,
        "geolocation": geo_description,
        "time_zones": tz,
    }


@app.route("/", methods=["GET"])
def index():
    return (
        "<h3>Phone number parsing API</h3>"
        "<p>POST JSON to <code>/api/parse</code> with "
        "<code>{'number': '+331632960960'}</code></p>"
    )


# ✅ API endpoint for phone number parsing
@app.route("/api/parse", methods=["POST", "OPTIONS"])
def api_parse():
    # Handle browser preflight request
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        origin = request.headers.get('Origin', '')
        allowed_origins = [
            "https://zeroday.help",
            "http://localhost",
            "http://localhost:3000", 
            "http://localhost:5000",
            "http://127.0.0.1",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5000"
        ]
        
        if origin in allowed_origins:
            response.headers.add("Access-Control-Allow-Origin", origin)
        else:
            response.headers.add("Access-Control-Allow-Origin", "*")
            
        response.headers.add("Access-Control-Allow-Credentials", "true")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, Accept, Origin")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT, DELETE, HEAD, PATCH")
        response.headers.add("Access-Control-Max-Age", "86400")
        return response, 200

    # Get request data
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    
    # Validate required parameter
    number = data.get("number") or data.get("phone")
    if not number:
        error_resp = jsonify({
            "success": False,
            "error": "missing_parameter",
            "message": "`number` is required."
        })
        error_resp.headers.add('Access-Control-Allow-Origin', '*')
        return error_resp, 400

    region = data.get("region")
    language = data.get("language", "en")

    logging.info("Parsing number=%s region=%s language=%s", number, region, language)
    
    # Use the phonenumbers library directly
    info = get_number_info(number, region, language)

    if "error" in info:
        error_resp = jsonify({"success": False, "error": info})
        error_resp.headers.add('Access-Control-Allow-Origin', '*')
        return error_resp, 400

    success_resp = jsonify({"success": True, "data": info})
    success_resp.headers.add('Access-Control-Allow-Origin', '*')
    return success_resp, 200


# Required for Vercel
app = app
