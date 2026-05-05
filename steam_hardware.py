#!/usr/bin/env python3
"""
Steam Hardware Monitor - Using Official Protobuf Library
Checks Steam Controller availability via Steam's Protobuf API

This version uses the generated protobuf classes from steam_hardware_pb2
for proper message deserialization and full field mapping.
"""

import requests
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import base64

# Import the generated protobuf classes
from steam_hardware_pb2 import (
    CHardwarePackageDetails,
    CHardwareItem,
    GetHardwareItemsResponse,
    GetHardwareItemsRequest,
    HardwareRequestOptions,
)


class SteamHardware:
    """Monitor Steam hardware availability using Protobuf API"""

    # API configuration
    API_URL = "https://api.steampowered.com/IStoreBrowseService/GetHardwareItems/v1"

    @staticmethod
    def encode_request(hardware_id: int, country_code: str = "CZ") -> str:
        """
        Encode GetHardwareItemsRequest parameters using protobuf library.

        Args:
            hardware_id: Steam hardware ID
            country_code: Country code

        Returns:
            Base64-encoded protobuf message string
        """
        # Create request with nested options
        request = GetHardwareItemsRequest()
        request.hardware_id = hardware_id
        request.options.language = 'english'
        request.options.country_code = country_code

        # Serialize to bytes and base64 encode
        serialized = request.SerializeToString()
        encoded = base64.b64encode(serialized).decode('utf-8')
        return encoded

    def __init__(self, hardware_id: int, country_code: str):
        self.state_file = Path(__file__).parent / ".steam_status.json"
        self.log_file = Path(__file__).parent / "monitor.log"

        # Generate API parameters dynamically using protobuf
        self.API_PARAMS = {
            'origin': 'https://store.steampowered.com',
            'input_protobuf_encoded': self.encode_request(hardware_id, country_code)
        }

    def fetch_hardware_data(self) -> Optional[Dict]:
        """Fetch and parse hardware data from Steam API"""
        try:
            response = requests.get(
                self.API_URL,
                params=self.API_PARAMS,
                timeout=10,
                headers={'User-Agent': 'Mozilla/5.0'}
            )

            if response.status_code != 200:
                return None

            # Deserialize the protobuf response
            # The response is a CHardwareItem message
            hardware_item = CHardwareItem()
            hardware_item.ParseFromString(response.content)

            if not hardware_item.HasField('package_details'):
                return None

            details = hardware_item.package_details

            return {
                'packageid': details.packageid,
                'inventory_available': details.inventory_available,
                'high_pending_orders': details.high_pending_orders,
                'account_restricted_from_purchasing': details.account_restricted_from_purchasing,
                'requires_reservation': details.requires_reservation,
                'rtime_estimated_notification': details.rtime_estimated_notification,
                'notification_token': details.notification_token,
                'reservation_state': details.reservation_state,
                'expired': details.expired,
                'time_expires': details.time_expires,
                'time_reserved': details.time_reserved,
                'allow_quantity_purchase': details.allow_quantity_purchase,
                'max_quantity_per_purchase': details.max_quantity_per_purchase,
                'allow_purchase_in_country': details.allow_purchase_in_country,
                'estimated_delivery_soonest_business_days': details.estimated_delivery_soonest_business_days,
                'estimated_delivery_latest_business_days': details.estimated_delivery_latest_business_days,
            }

        except requests.RequestException as e:
            return None
        except Exception as e:
            print(f"Error parsing protobuf: {e}", file=sys.stderr)
            return None

    def check_availability(self) -> Dict:
        """Check current availability status"""
        hardware_data = self.fetch_hardware_data()

        if hardware_data is None:
            return {
                'available': None,
                'error': 'Failed to fetch or parse API response',
                'timestamp': datetime.now().isoformat()
            }

        return {
            'available': hardware_data.get('inventory_available'),
            'method': 'protobuf_api',
            'timestamp': datetime.now().isoformat(),
            'data': hardware_data,
            'package_id': hardware_data.get('packageid')
        }


# Known hardware package IDs (from SteamDB)
KNOWN_HARDWARE_SUB_IDS = {
    'steam_controller': 1558609
}


def resolve_package_id(package_id_input) -> int:
    """
    Resolve package ID from either numeric ID or string alias.

    Args:
        package_id_input: Either an integer or string alias from KNOWN_HARDWARE_SUB_IDS

    Returns:
        Resolved numeric package ID

    Raises:
        ValueError: If package_id is invalid
    """
    resolved_id = KNOWN_HARDWARE_SUB_IDS.get(
        package_id_input, package_id_input)

    try:
        return int(resolved_id)
    except ValueError:
        available_aliases = ', '.join(KNOWN_HARDWARE_SUB_IDS.keys())
        raise ValueError(
            f"Invalid package_id: {package_id_input}. "
            f"Must be numeric ID or one of: {available_aliases}"
        )


def notify_webhook(package_id: int, args: argparse.Namespace) -> bool:
    """Send availability status to Discord webhook"""

    # import logging

    # # Enabling debugging at http.client level (requests->urllib3->http.client)
    # # you will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
    # # the only thing missing will be the response.body which is not logged.
    # from http.client import HTTPConnection
    # HTTPConnection.debuglevel = 1

    # # you need to initialize logging, otherwise you will not see anything from requests
    # logging.basicConfig()
    # logging.getLogger().setLevel(logging.DEBUG)
    # requests_log = logging.getLogger("urllib3")
    # requests_log.setLevel(logging.DEBUG)
    # requests_log.propagate = True

    product_info_url = "https://store.steampowered.com/api/packagedetails"
    product_info_params = {
        'packageids': package_id,
        'language': 'english',
        'cc': args.country_code
    }
    product_info_response = requests.get(
        product_info_url, params=product_info_params, timeout=5)
    product_info_response_json = product_info_response.json()
    # print(json.dumps(product_info_response_json, indent=2))
    product_info_data = product_info_response_json.get(
        str(package_id), {}).get('data', {})
    product_name = product_info_data.get('name', 'Steam Hardware')
    product_image = product_info_data.get('header_image')

    product_page_url = f"https://store.steampowered.com/sub/{package_id}"

    role_mention = f"<@&{args.role_id}> " if args.role_id else ""

    webhook_payload = {
        "content": f"{role_mention} {product_name} is now available for purchase!",
        "embeds": [
            {
                "title": f"{product_name} on Steam Store",
                "color": 0x00FF00,
                "url": product_page_url
            }
        ]
    }

    if product_image:
        webhook_payload['embeds'][0]['image'] = {
            "url": product_image
        }

    response = requests.post(
        args.webhook_url, json=webhook_payload, timeout=10)
    return response.status_code == 204  # Discord returns 204 No Content


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Monitor Steam hardware availability using Protobuf API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f'''
Known package IDs:
{chr(10).join(f"  {k}: {v}" for k, v in KNOWN_HARDWARE_SUB_IDS.items())}
'''
    )
    parser.add_argument(
        '-p', '--package-id',
        required=True,
        help='Package ID (numeric or alias like "steam_controller")'
    )
    parser.add_argument(
        '-c', '--country-code',
        required=True,
        help='Country code (e.g., US, CA, DE, etc..)'
    )

    parser.add_argument(
        '-w', '--webhook-url',
        help='Discord webhook URL to send notifications'
    )

    parser.add_argument(
        '-r', '--role-id',
        help='Discord role ID to mention in notifications'
    )

    parser.add_argument(
        '--test-notify',
        action='store_true',
        help='''Don't check the status, just send a test notification to the webhook (requires --webhook-url)'''
    )
    args = parser.parse_args()

    # Resolve package ID
    try:
        package_id = resolve_package_id(args.package_id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Debug mode: test webhook without checking availability
    if args.test_notify:
        if not args.webhook_url:
            print("Error: --webhook-url required for test notification",
                  file=sys.stderr)
            sys.exit(1)

        print(f"🧪 Test mode: Sending test notification to webhook...")

        if notify_webhook(package_id, args):
            print("✅ Test notification sent successfully!")
            sys.exit(0)
        else:
            print("❌ Failed to send test notification", file=sys.stderr)
            sys.exit(1)

    # Normal mode: check availability
    monitor = SteamHardware(package_id, args.country_code)

    availability = monitor.check_availability()
    print(json.dumps(availability, indent=2))

    if availability['available'] is True:
        if args.webhook_url:
            notify_webhook(package_id, args)
        sys.exit(0)  # In stock
    elif availability['available'] is False:
        sys.exit(1)  # Out of stock
    else:
        sys.exit(2)  # Error or unknown status
