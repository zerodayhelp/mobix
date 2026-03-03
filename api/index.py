#!/usr/bin/env python3

from flask import Flask, request, jsonify
from flask_cors import CORS
import phonenumbers
from phonenumbers import PhoneNumberType, PhoneNumberFormat
from phonenumbers import carrier as carrier_mod, geocoder as geocoder_mod, timezone as timezone_mod
import logging

app = Flask(__name__)

# ✅ Correct CORS for zeroday.help
CORS(
    app,
    resources={r"/api/*": {
        "origins": [
            "https://zeroday.help",
            "http://localhost:5000",
            "http://127.0.0.1:5000"
        ]
    }},
    supports_credentials=True
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


def get_number_info(number_str: str, region: str = None, language: str = "en") -> dict:
    try:
        parsed = phonenumbers.parse(number_str, region.upper() if region else None)
    except phonenumbers.NumberParseException as e:
        return {"error": "NumberParseException", "message": str(e)}

    return {
        "input": number_str,
        "valid": phonenumbers.is_valid_number(parsed),
        "possible": phonenumbers.is_possible_number(parsed),
        "type": TYPE_MAP.get(phonenumbers.number_type(parsed), "Unknown"),
        "region_code": phonenumbers.region_code_for_number(parsed),
        "country_code": parsed.country_code,
        "international_format": phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL),
        "national_format": phonenumbers.format_number(parsed, PhoneNumberFormat.NATIONAL),
        "e164": phonenumbers.format_number(parsed, PhoneNumberFormat.E164),
        "rfc3966": phonenumbers.format_number(parsed, PhoneNumberFormat.RFC3966),
        "carrier": carrier_mod.name_for_number(parsed, language) or "",
        "geolocation": geocoder_mod.description_for_number(parsed, language) or "",
        "time_zones": list(timezone_mod.time_zones_for_number(parsed)),
    }


@app.route("/")
def index():
    return "Phone Parser API is running."


@app.route("/api/parse", methods=["POST"])
def api_parse():

    data = request.get_json(silent=True) or {}

    number = data.get("number")
    if not number:
        return jsonify({
            "success": False,
            "error": "missing_parameter",
            "message": "`number` is required."
        }), 400

    region = data.get("region")
    language = data.get("language", "en")

    info = get_number_info(number, region, language)

    if "error" in info:
        return jsonify({"success": False, "error": info}), 400

    return jsonify({"success": True, "data": info})
