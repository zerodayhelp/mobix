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

# ✅ ALLOW ALL CORS (Development/Proxy)
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

# Configure CORS headers manually for all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
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
        "<code>{'number': '+441632960960'}</code></p>"
    )


# ✅ IMPORTANT: allow OPTIONS for preflight and proxy to external API
@app.route("/api/parse", methods=["POST", "OPTIONS"])
def api_parse():
    external_api_url = "https://mobixv2-git-main-tekorixs-projects.vercel.app/api/parse"

    # Handle browser preflight request
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        return response, 200

    # Get request data
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    
    # Validate required parameter
    number = data.get("number") or data.get("phone")
    if not number:
        return jsonify({
            "success": False,
            "error": "missing_parameter",
            "message": "`number` is required."
        }), 400

    try:
        # Forward request to external API
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.post(
            external_api_url,
            json=data,
            headers=headers,
            timeout=10
        )
        
        # Check if external API returned a valid response
        if response.status_code == 200:
            try:
                result = response.json()
                # Add CORS headers to the response
                resp = jsonify(result)
                resp.headers.add('Access-Control-Allow-Origin', '*')
                resp.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
                resp.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
                return resp, 200
            except json.JSONDecodeError:
                # If external API returns invalid JSON, return error
                return jsonify({
                    "success": False,
                    "error": "external_api_error",
                    "message": "External API returned invalid response"
                }), 502
        else:
            # External API returned error status
            return jsonify({
                "success": False,
                "error": "external_api_error",
                "message": f"External API returned status {response.status_code}",
                "details": response.text[:200] if response.text else "No details available"
            }), response.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "error": "timeout",
            "message": "Request to external API timed out"
        }), 504
        
    except requests.exceptions.ConnectionError:
        return jsonify({
            "success": False,
            "error": "connection_error",
            "message": "Could not connect to external API"
        }), 503
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            "success": False,
            "error": "request_error",
            "message": f"Request failed: {str(e)}"
        }), 500


# Required for Vercel
app = app
