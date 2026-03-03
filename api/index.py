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

app = Flask(__name__)

# ✅ STRICT CORS CONFIG (Production)
CORS(
    app,
    resources={r"/api/*": {"origins": "https://zeroday.help"}},
    supports_credentials=True,
)

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


# ✅ IMPORTANT: allow OPTIONS for preflight
@app.route("/api/parse", methods=["POST", "OPTIONS"])
def api_parse():

    # Handle browser preflight request
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers.add("Access-Control-Allow-Origin", "https://zeroday.help")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        return response, 200

    # Normal POST request
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    number = data.get("number") or data.get("phone")
    if not number:
        return jsonify({
            "success": False,
            "error": "missing_parameter",
            "message": "`number` is required."
        }), 400

    region = data.get("region")
    language = data.get("language", "en")

    logging.info("Parsing number=%s region=%s", number, region)
    info = get_number_info(number, region, language)

    if "error" in info:
        return jsonify({"success": False, "error": info}), 400

    return jsonify({"success": True, "data": info}), 200


# Required for Vercel
app = app
