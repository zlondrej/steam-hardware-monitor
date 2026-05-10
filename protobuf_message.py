#!/usr/bin/env python3
"""
Steam Hardware Protobuf Message Tool
Encode and decode protobuf messages for Steam hardware APIs

Usage:
  protobuf_message encode <message_type> [base64_payload]
  protobuf_message decode <message_type> [base64_payload]

If payload is not provided, it will be read from stdin.
"""

import json
import base64
import sys
import argparse
from typing import Optional, Dict, Any
from google.protobuf.json_format import MessageToDict, ParseDict

# Import the generated protobuf classes
import steam_hardware_pb2


class ProtobufMessage:
    """Encode and decode Steam protobuf messages"""

    # Map of message type names to their classes
    MESSAGE_TYPES = {
        'GetHardwareItemsRequest': steam_hardware_pb2.GetHardwareItemsRequest,
        'GetHardwareItemsResponse': steam_hardware_pb2.GetHardwareItemsResponse,
        'GetItemsRequest': steam_hardware_pb2.GetItemsRequest,
        'GetItemsResponse': steam_hardware_pb2.GetItemsResponse,
    }

    @staticmethod
    def decode(message_type: str, payload: str) -> Optional[Any]:
        """
        Decode a base64-encoded protobuf payload.

        Args:
            message_type: Name of the protobuf message type
            payload: Base64-encoded protobuf payload

        Returns:
            Decoded protobuf message or None if invalid
        """
        if message_type not in ProtobufMessage.MESSAGE_TYPES:
            print(f"Error: Unknown message type '{message_type}'", file=sys.stderr)
            print(f"Available types: {', '.join(sorted(ProtobufMessage.MESSAGE_TYPES.keys()))}",
                  file=sys.stderr)
            return None

        try:
            # Create an instance of the message type
            message_class = ProtobufMessage.MESSAGE_TYPES[message_type]
            message = message_class()

            # Decode from base64
            decoded_bytes = base64.b64decode(payload)

            # Parse the bytes into the message
            message.ParseFromString(decoded_bytes)

            return message
        except Exception as e:
            print(f"Error decoding payload: {e}", file=sys.stderr)
            return None

    @staticmethod
    def encode(message_type: str, data: Dict[str, Any]) -> Optional[str]:
        """
        Encode a protobuf message to base64.

        Args:
            message_type: Name of the protobuf message type
            data: Dictionary representation of the message

        Returns:
            Base64-encoded protobuf payload or None if invalid
        """
        if message_type not in ProtobufMessage.MESSAGE_TYPES:
            print(f"Error: Unknown message type '{message_type}'", file=sys.stderr)
            print(f"Available types: {', '.join(sorted(ProtobufMessage.MESSAGE_TYPES.keys()))}",
                  file=sys.stderr)
            return None

        try:
            # Create an instance of the message type
            message_class = ProtobufMessage.MESSAGE_TYPES[message_type]

            # Parse the dictionary into the message
            message = ParseDict(data, message_class())

            # Serialize to bytes
            encoded_bytes = message.SerializeToString()

            # Encode to base64
            payload = base64.b64encode(encoded_bytes).decode('ascii')

            return payload
        except Exception as e:
            print(f"Error encoding message: {e}", file=sys.stderr)
            return None

    @staticmethod
    def message_to_dict(message: Any) -> Dict[str, Any]:
        """Convert protobuf message to dictionary for display"""
        return MessageToDict(message, preserving_proto_field_name=True)


def read_payload_from_stdin() -> str:
    """Read base64 payload from stdin"""
    return sys.stdin.read().strip()


def decode_command(args):
    """Handle decode command"""
    tool = ProtobufMessage()

    # Get payload from argument or stdin
    payload = args.payload if args.payload else read_payload_from_stdin()

    message = tool.decode(args.message_type, payload)

    if message is not None:
        result_dict = tool.message_to_dict(message)
        print(json.dumps(result_dict, indent=2))
    else:
        print("✗ Failed to decode payload", file=sys.stderr)
        sys.exit(1)


def encode_command(args):
    """Handle encode command"""
    tool = ProtobufMessage()

    # Get payload from argument or stdin
    payload_str = args.payload if args.payload else read_payload_from_stdin()

    try:
        # Parse JSON from payload
        data = json.loads(payload_str)
        encoded = tool.encode(args.message_type, data)

        if encoded is not None:
            print(encoded)
        else:
            print("✗ Failed to encode message", file=sys.stderr)
            sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in payload: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Encode and decode Steam protobuf messages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available message types:
  {', '.join(sorted(ProtobufMessage.MESSAGE_TYPES.keys()))}

Examples:
  # Decode with payload as argument
  protobuf_message decode GetItemsRequest "CgQIwJ9mEg0KB2VuZ2xpc2gaAkNaGgA="

  # Decode from stdin
  echo "CgQIwJ9mEg0KB2VuZ2xpc2gaAkNaGgA=" | protobuf_message decode GetItemsRequest

  # Encode from stdin
  echo '{{"language": "english", "country_code": "US"}}' | protobuf_message encode GetHardwareItemsRequest
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    subparsers.required = True

    # Decode subcommand
    decode_parser = subparsers.add_parser('decode', help='Decode a protobuf message')
    decode_parser.add_argument('message_type', help='Type of protobuf message')
    decode_parser.add_argument('payload', nargs='?', default=None,
                              help='Base64-encoded payload (read from stdin if not provided)')
    decode_parser.set_defaults(func=decode_command)

    # Encode subcommand
    encode_parser = subparsers.add_parser('encode', help='Encode a protobuf message')
    encode_parser.add_argument('message_type', help='Type of protobuf message')
    encode_parser.add_argument('payload', nargs='?', default=None,
                              help='JSON payload (read from stdin if not provided)')
    encode_parser.set_defaults(func=encode_command)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
