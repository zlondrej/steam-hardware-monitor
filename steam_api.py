#!/usr/bin/env python3

import json
import json5
import sys
import argparse
import urllib.parse
import urllib.request
from typing import Optional, Dict, Any

from protobuf_message import ProtobufMessage


class SteamAPIClient:
    """Client for Steam's internal APIs"""

    BASE_URL = "https://api.steampowered.com/IStoreBrowseService"

    # Map service names to their request/response message types
    SERVICES = {
        'GetItems': {
            'request_type': 'GetItemsRequest',
            'response_type': 'GetItemsResponse',
        },
        'GetHardwareItems': {
            'request_type': 'GetHardwareItemsRequest',
            'response_type': 'GetHardwareItemsResponse',
        },
    }

    @staticmethod
    def call(service: str, request_data: Dict[str, Any]) -> Optional[Any]:
        """
        Make a call to a Steam API service.

        Args:
            service: Service name (GetItems or GetHardwareItems)
            request_data: Dictionary representation of the request message

        Returns:
            Decoded response message or None if failed
        """
        if service not in SteamAPIClient.SERVICES:
            print(f"Error: Unknown service '{service}'", file=sys.stderr)
            print(f"Available services: {', '.join(SteamAPIClient.SERVICES.keys())}",
                  file=sys.stderr)
            return None

        service_info = SteamAPIClient.SERVICES[service]
        request_type = service_info['request_type']
        response_type = service_info['response_type']

        # Encode the request
        tool = ProtobufMessage()
        encoded_request = tool.encode(request_type, request_data)

        if encoded_request is None:
            print(f"Error: Failed to encode request", file=sys.stderr)
            return None

        # Build the API URL
        url = f"{SteamAPIClient.BASE_URL}/{service}/v1"
        params = {
            'input_protobuf_encoded': encoded_request,
            'origin': 'https://store.steampowered.com',
        }
        full_url = f"{url}?{urllib.parse.urlencode(params)}"

        try:
            # Make the request
            req = urllib.request.Request(
                full_url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)',
                    'Referer': 'https://store.steampowered.com/',
                }
            )
            with urllib.request.urlopen(req) as response:
                response_bytes = response.read()

            # Decode the response
            import base64
            response_b64 = base64.b64encode(response_bytes).decode('ascii')
            decoded_response = tool.decode(response_type, response_b64)

            if decoded_response is None:
                print(f"Error: Failed to decode response", file=sys.stderr)
                return None

            return decoded_response

        except urllib.error.URLError as e:
            print(f"Error: API request failed: {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return None


def read_json_from_stdin() -> Dict[str, Any]:
    """Read JSON from stdin"""
    return json5.loads(sys.stdin.read().strip())


def main():
    parser = argparse.ArgumentParser(
        description='Call Steam internal APIs with protobuf encoding/decoding'
    )

    parser.add_argument(
        'service', help='Service to call (GetItems or GetHardwareItems)')
    parser.add_argument('request', nargs='?', default=None,
                        help='JSON-encoded request (read from stdin if not provided)')

    args = parser.parse_args()

    # Get request data from argument or stdin
    if args.request:
        try:
            request_data = json5.loads(args.request)
        except json5.JSONDecodeError as e:
            print(f"Error: Invalid JSON in request: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        try:
            request_data = read_json_from_stdin()
        except json5.JSONDecodeError as e:
            print(f"Error: Invalid JSON from stdin: {e}", file=sys.stderr)
            sys.exit(1)

    # Make the API call
    response = SteamAPIClient.call(args.service, request_data)

    if response is not None:
        tool = ProtobufMessage()
        response_dict = tool.message_to_dict(response)
        print(json.dumps(response_dict, indent=2))
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
