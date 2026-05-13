#!/usr/bin/env python3
"""
Steam Hardware Product Info Tracker - Tracks Changes in Product Info Output
Compares current output against the previous output stored in a state file.
Resistant to file corruption by gracefully handling read/decode errors.
"""

import json
import sys
import argparse
import requests
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any
import tempfile
import os


# ANSI color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RED = '\033[91m'
    CYAN = '\033[96m'


def _stringify_keys(obj: Any) -> Any:
    """
    Recursively convert dicts with numeric keys (0, 1, 2, ...) to lists,
    and stringify other dict keys.
    This ensures arrays stay as lists and numeric keys become strings for other dicts.
    """
    if isinstance(obj, dict):
        # Check if this dict should be converted to a list (numeric keys 0, 1, 2, ...)
        try:
            keys = list(obj.keys())
            if not keys:
                return {}

            # Try to parse keys as integers
            int_keys = []
            for k in keys:
                if isinstance(k, int):
                    int_keys.append(k)
                elif isinstance(k, str) and k.isdigit():
                    int_keys.append(int(k))
                else:
                    raise ValueError("Non-numeric key")

            # Sort and check if consecutive from 0
            int_keys_sorted = sorted(int_keys)
            if int_keys_sorted == list(range(len(int_keys_sorted))):
                # Convert to list - access by sorted order
                result = []
                for i in range(len(int_keys_sorted)):
                    # Find original key for this index
                    original_key = [k for k in keys if (
                        int(k) if isinstance(k, str) else k) == i][0]
                    result.append(_stringify_keys(obj[original_key]))
                return result
        except (ValueError, TypeError, IndexError):
            pass

        # Not a list-like dict, stringify keys
        return {str(k): _stringify_keys(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_stringify_keys(item) for item in obj]
    return obj


class OutputMonitor:
    """Monitor product info output for changes"""

    def __init__(self, state_file: Path, webhook_url: Optional[str] = None, mentions: Optional[List[str]] = None):
        """
        Initialize the monitor with a state file path.

        Args:
            state_file: Path where the last output will be stored
            webhook_url: Optional Discord webhook URL for notifications
            mentions: Optional list of Discord mentions (user/role IDs or strings)
        """
        self.state_file = Path(state_file)
        self.webhook_url = webhook_url
        self.mentions = mentions or []
        self.names_cache = {'app_1675200': 'Steam Deck',
                            'app_4165870': 'Steam Controller',
                            'app_4165890': 'Steam Frame',
                            'app_4165910': 'Steam Machine',
                            'package_1186053': '* Steam Deck #1186053',
                            'package_1186054': '* Steam Deck #1186054',
                            'package_1186055': '* Steam Deck #1186055',
                            'package_1202542': '* Steam Deck #1202542',
                            'package_1202547': '* Steam Deck #1202547',
                            'package_1459457': '? Steam Frame #1459457',
                            'package_1459458': '? Steam Frame #1459458',
                            'package_1459459': '? Steam Frame #1459459',
                            'package_1459460': '? Steam Machine #1459460',
                            'package_1459461': '? Steam Machine #1459461',
                            'package_1459462': '? Steam Machine #1459462',
                            'package_1558609': '* Steam Controller #1558609',
                            'package_1629446': '? Steam Machine #1629446',
                            'package_1629447': '? Steam Machine #1629447',
                            'package_1629448': '? Steam Machine #1629448',
                            'package_1629458': '? Steam Machine #1629458',
                            'package_1629459': '? Steam Machine #1629459',
                            'package_1629460': '? Steam Machine #1629460',
                            'package_1629461': '? Steam Machine #1629461',
                            'package_1629484': '? Steam Frame #1629484',
                            'package_1629485': '? Steam Frame #1629485',
                            'package_1629486': '? Steam Frame #1629486',
                            'package_1629487': '? Steam Frame #1629487',
                            'package_595604': '* Steam Deck #595604',
                            'package_595605': '* Steam Deck #595605',
                            'package_903905': '* Steam Deck #903905',
                            'package_903906': '* Steam Deck #903906',
                            'package_903907': '* Steam Deck #903907',
                            'package_946113': '* Steam Deck #946113',
                            'package_946114': '* Steam Deck #946114',
                            }

        # Ensure parent directory exists
        self.state_file.parent.mkdir(parents=True,
                                     exist_ok=True)

    def get_product_info_output(self) -> Optional[Dict]:
        """
        Execute product info collection code and capture its output.

        Returns:
            The product info dict,
            or None if execution failed
        """
        raw_output = self._get_raw_product_info()
        if raw_output is None:
            return None
        # Convert all numeric keys to strings for consistency with JSON format
        return _stringify_keys(raw_output)

    def _get_raw_product_info(self) -> Optional[Dict]:
        """Get raw product info from Steam API (may have numeric keys)."""
        try:
            from steam.client import SteamClient

            client = SteamClient()
            client.anonymous_login()

            appsids = [
                1675200,  # Steam Deck
                4165870,  # Steam Controller
                4165890,  # Steam Frame
                4165910,  # Steam Machine
            ]

            packageids = [
                1186053,  # Steam Deck 256 GB w/o PSU
                1186054,  # Steam Deck 512 GB OLED w/o PSU
                1186055,  # Steam Deck 1 TB OLED w/o PSU
                1202542,  # Steam Deck 512 GB OLED - Valve Certified Refurbished
                1202547,  # Steam Deck 1TB OLED - Valve Certified Refurbished
                1459457,  # Steam Frame sub
                1459458,  # Steam Frame sub
                1459459,  # Steam Frame sub
                1459460,  # Steam Machine sub
                1459461,  # Steam Machine sub
                1459462,  # Steam Machine sub
                1558609,  # Steam Controller
                1629446,  # Steam Machine sub
                1629447,  # Steam Machine sub
                1629448,  # Steam Machine sub
                1629458,  # Steam Machine sub
                1629459,  # Steam Machine sub
                1629460,  # Steam Machine sub
                1629461,  # Steam Machine sub
                1629484,  # Steam Frame sub
                1629485,  # Steam Frame sub
                1629486,  # Steam Frame sub
                1629487,  # Steam Frame sub
                595604,  # Steam Deck 256 GB
                595605,  # Steam Deck 512 GB
                903905,  # Steam Deck 64 GB LCD - Valve Certified Refurbished
                903906,  # Steam Deck 256 GB LCD - Valve Certified Refurbished
                903907,  # Steam Deck 512 GB LCD - Valve Certified Refurbished
                946113,  # Steam Deck 512 GB OLED
                946114,  # Steam Deck 1 TB OLED
            ]

            return client.get_product_info(
                apps=appsids, packages=packageids)

        except Exception as e:
            print(f"❌ Error getting product info: {e}", file=sys.stderr)
            return None

    def load_previous_output(self) -> Optional[Dict]:
        """
        Load the previous output from state file.

        Returns:
            The previous output dict, or None if file doesn't exist or cannot be read
        """
        if not self.state_file.exists():
            return None

        try:
            # Read and parse JSON
            content = self.state_file.read_text(encoding='utf-8')
            return json.loads(content)
        except Exception:
            # If anything fails, treat as unavailable
            return None

    def load_output_from_file(self, filepath: Path) -> Optional[Dict]:
        """
        Load output from an arbitrary file (JSON format).

        Args:
            filepath: Path to the JSON file to load

        Returns:
            The output dict, or None if cannot be read
        """
        if not filepath.exists():
            print(f"❌ Comparison file not found: {filepath}", file=sys.stderr)
            return None

        try:
            content = filepath.read_text(encoding='utf-8')
            return json.loads(content)
        except Exception as e:
            print(f"❌ Error loading comparison file: {e}", file=sys.stderr)
            return None

    def save_output(self, output: Dict) -> bool:
        """
        Save the output to state file atomically as JSON.
        JSON automatically converts numeric keys to strings; this is reversible.

        Args:
            output: The output dict to save

        Returns:
            True if successful, False otherwise
        """
        try:
            # Write to temporary file first for atomic write
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.state_file.parent,
                prefix='.tmp_',
                suffix='.json'
            )

            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    # JSON with indentation for readability
                    json.dump(output, f, indent=2)

                # Atomic rename
                os.replace(temp_path, self.state_file)
                return True

            except Exception:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                return False

        except Exception:
            return False

    def compare_outputs(self, current: Dict, previous: Optional[Dict]) -> Optional[Dict]:
        """
        Compare current output with previous output.

        Args:
            current: Current output dict from product info collection
            previous: Previous output dict from state file (or None if not available)

        Returns:
            Dictionary with comparison results, or None if no changes
        """

        if previous is None or current == previous:
            return None

        # Detailed comparison
        return self._detailed_comparison(current, previous)

    @staticmethod
    def _detailed_comparison(current: Dict, previous: Dict) -> Dict:
        """Compare apps and packages in detail."""
        changes = {'apps': {}, 'packages': {}}

        # Compare apps
        current_apps = current.get('apps', {})
        previous_apps = previous.get('apps', {})

        all_app_ids = set(current_apps.keys()) | set(previous_apps.keys())

        for app_id in all_app_ids:
            current_data = current_apps.get(app_id)
            previous_data = previous_apps.get(app_id)

            if previous_data is None:
                # New app
                changes['apps'][app_id] = {
                    'status': 'new', 'data': current_data}
            elif current_data is None:
                # Removed app
                changes['apps'][app_id] = {'status': 'removed'}
            else:
                # Check if common or extended changed
                diff = OutputMonitor._compare_item(previous_data, current_data)
                if diff:
                    changes['apps'][app_id] = {
                        'status': 'changed',
                        'diff': diff
                    }

        # Compare packages
        current_packages = current.get('packages', {})
        previous_packages = previous.get('packages', {})

        all_pkg_ids = set(current_packages.keys()) | set(
            previous_packages.keys())

        for pkg_id in all_pkg_ids:
            current_data = current_packages.get(pkg_id)
            previous_data = previous_packages.get(pkg_id)

            if previous_data is None:
                # New package
                changes['packages'][pkg_id] = {
                    'status': 'new', 'data': current_data}
            elif current_data is None:
                # Removed package
                changes['packages'][pkg_id] = {'status': 'removed'}
            else:
                # Check if common or extended changed
                diff = OutputMonitor._compare_item(previous_data, current_data)
                if diff:
                    changes['packages'][pkg_id] = {
                        'status': 'changed',
                        'diff': diff
                    }

        return changes

    @staticmethod
    def _compare_item(previous: Dict, current: Dict) -> Dict:
        """Compare common, extended, and change_number fields of an item."""
        diff = {}

        # Compare common
        prev_common = previous.get('common', {})
        curr_common = current.get('common', {})
        if prev_common != curr_common:
            diff['common'] = OutputMonitor._field_diff(
                prev_common, curr_common)

        # Compare extended
        prev_extended = previous.get('extended', {})
        curr_extended = current.get('extended', {})
        if prev_extended != curr_extended:
            diff['extended'] = OutputMonitor._field_diff(
                prev_extended, curr_extended)

        # Compare _change_number (display as change_number, wrapped in meta)
        prev_change = previous.get('_change_number')
        curr_change = current.get('_change_number')
        if prev_change != curr_change and curr_change is not None:
            diff['meta'] = {
                'change_number': {'status': 'changed', 'old': prev_change, 'new': curr_change}
            }

        return diff

    @staticmethod
    def _field_diff(previous: Dict, current: Dict) -> Dict:
        """Find added, removed, and changed fields."""
        result = {}

        # Added and changed
        for key, curr_val in current.items():
            prev_val = previous.get(key)
            if prev_val is None:
                result[key] = {'status': 'added', 'value': curr_val}
            elif prev_val != curr_val:
                result[key] = {'status': 'changed',
                               'old': prev_val, 'new': curr_val}

        # Removed
        for key in previous:
            if key not in current:
                result[key] = {'status': 'removed', 'value': previous[key]}

        return result

    def _print_changes(self, changes: Dict):
        """Print formatted changes with colors."""
        # Print app changes
        apps = changes.get('apps')
        if apps:
            print(f"{Colors.BOLD}💻 Apps:{Colors.RESET}")
            for app_id, change_info in apps.items():
                self._print_item_change(app_id, change_info, 'app')

        # Print package changes
        packages = changes.get('packages')
        if packages:
            if apps:
                print()  # Spacing
            print(f"{Colors.BOLD}📦 Packages:{Colors.RESET}")
            for pkg_id, change_info in packages.items():
                self._print_item_change(pkg_id, change_info, 'package')

        print()  # Final spacing

    def _print_item_change(self, item_id: str, change_info: Dict, item_type: str):
        """Print a single item's changes."""
        status = change_info.get('status')

        if status == 'new':
            print(f"  {Colors.GREEN}+ {item_type} {item_id}{Colors.RESET}")
        elif status == 'removed':
            print(f"  {Colors.RED}- {item_type} {item_id}{Colors.RESET}")
        elif status == 'changed':
            name = self._get_item_name(item_id, change_info, item_type)
            print(f"  {Colors.CYAN}~ {item_type} {item_id}{Colors.RESET}", end="")
            if name:
                print(f" ({name})", end="")
            print()

            diff = change_info.get('diff', {})
            for field_type, fields in diff.items():
                print(f"      {Colors.BOLD}{field_type}:{Colors.RESET}")
                for field_name, field_change in fields.items():
                    self._print_field_change(
                        field_name, field_change, indent=8)

    def _get_item_name(self, item_id: str, change_info: Dict, item_type: str = 'app') -> Optional[str]:
        """Extract the name from item data. For packages, look up the first app's name."""
        # Check in diff first
        diff = change_info.get('diff', {})
        if 'common' in diff:
            common_diff = diff['common']
            if 'name' in common_diff:
                name_change = common_diff['name']
                if name_change.get('status') == 'added' or name_change.get('status') == 'changed':
                    return name_change.get('new') or name_change.get('value')

        # Check in full data
        data = change_info.get('data', {})
        name = data.get('common', {}).get('name')
        if name:
            return name

        return self.names_cache.get(f'{item_type}_{item_id}')

    def _print_field_change(self, field_name: str, field_change: Dict, indent: int = 0):
        """Print a single field change."""
        prefix = ' ' * indent
        status = field_change.get('status')

        if status == 'added':
            value = field_change.get('value')
            print(f"{prefix}{Colors.GREEN}+ {field_name}: {value}{Colors.RESET}")
        elif status == 'removed':
            value = field_change.get('value')
            print(f"{prefix}{Colors.RED}- {field_name}: {value}{Colors.RESET}")
        elif status == 'changed':
            old = field_change.get('old')
            new = field_change.get('new')
            print(
                f"{prefix}{Colors.YELLOW}~ {field_name}: {old} → {new}{Colors.RESET}")

    def _send_to_discord(self, changes: Dict):
        """
        Send formatted changes to Discord webhook.

        Args:
            changes: The changes dict from comparison
        """
        try:
            embeds = self._build_discord_embeds(changes)

            # Format mentions: numeric IDs -> <@ID>, @role -> stays as-is, role IDs -> <@&ID>
            mentions = []
            for m in self.mentions:
                if m.isdigit():
                    # Numeric ID - assume it's a user mention
                    mentions.append(f'<@&{m}>')
                elif m.startswith('<@&') and m.endswith('>'):
                    # Already formatted role mention
                    mentions.append(m)
                elif m.isdigit() or (m.replace('_', '').replace('-', '').isalnum()):
                    # Could be a role ID - format as role mention
                    if m.isdigit():
                        mentions.append(f'<@&{m}>')
                    else:
                        # Text reference like @role_name - keep as-is for Discord to interpret
                        mentions.append(
                            f'@{m}' if not m.startswith('@') else m)

            content = ' '.join(mentions) if mentions else ''

            payload = {'embeds': embeds}
            if content:
                payload['content'] = content

            response = requests.post(
                self.webhook_url, json=payload, timeout=10)
            if response.status_code not in (200, 204):
                print(
                    f"⚠️  Discord webhook failed: {response.status_code}", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  Failed to send Discord webhook: {e}", file=sys.stderr)

    def _build_discord_embeds(self, changes: Dict) -> List[Dict]:
        """
        Build Discord embed messages for the changes.

        Args:1501231401444446229

        Returns:
            List of embed dictionaries for Discord API
        """
        embeds = []

        # Apps section
        apps = changes.get('apps')
        if apps:
            embed = self._build_section_embed('💻 Apps', apps, 'app')
            embeds.append(embed)

        # Packages section
        packages = changes.get('packages')
        if packages:
            embed = self._build_section_embed(
                '📦 Packages', packages, 'package')
            embeds.append(embed)

        return embeds

    def _build_section_embed(self, title: str, items: Dict, item_type: str) -> Dict:
        """
        Build a Discord embed for a section (apps or packages).

        Args:
            title: Section title
            items: Dict of items with their changes
            item_type: Either 'app' or 'package'

        Returns:
            Discord embed dictionary
        """
        color_map = {
            'new': 0x00FF00,      # Green
            'removed': 0xFF0000,  # Red
            'changed': 0xFFFF00,  # Yellow
        }

        fields = []

        for item_id, change_info in items.items():
            status = change_info.get('status')
            color = color_map.get(status, 0x808080)

            name = self._get_item_name(item_id, change_info, item_type) or f"Unknown {item_type}"
            if status == 'new':
                value = f"+ {name}"
            elif status == 'removed':
                value = f"- {name}"
            elif status == 'changed':
                value = f"~ {name}\n"
                diff = change_info.get('diff', {})
                for field_type, field_data in diff.items():
                    value += f"\n**{field_type.capitalize()}:**\n"
                    for field_name, field_change in field_data.items():
                        field_status = field_change.get('status')
                        if field_status == 'added':
                            val = field_change.get('value')
                            value += f"  - `{field_name}`: `{val}`\n"
                        elif field_status == 'removed':
                            val = field_change.get('value')
                            value += f"  - `{field_name}`: `{val}`\n"
                        elif field_status == 'changed':
                            old = field_change.get('old')
                            new = field_change.get('new')
                            value += f"  ~ `{field_name}`: `{old}` → `{new}`\n"

            fields.append({
                'name': f"{item_type.capitalize()} {item_id}",
                'value': value,
                'inline': False
            })

        embed = {
            'title': title,
            'color': 0x808080,  # Gray for mixed
            'fields': fields,
        }

        return embed

    def _build_names(self, current: Dict, previous: Optional[Dict], changes: Dict):
        """Build a cache of item names for better display in print and Discord."""
        # Build names cache for current output
        if current:
            for app_id, app_data in current.get('apps', {}).items():
                name = app_data.get('common', {}).get('name')
                if name:
                    self.names_cache[f'app_{app_id}'] = name

        # Also add from previous output for removed items
        if previous:
            for app_id, app_data in previous.get('apps', {}).items():
                key = f'app_{app_id}'
                if key not in self.names_cache:
                    name = app_data.get('common', {}).get('name')
                    if name:
                        self.names_cache[key] = name

        if current:
            for pkg_id, pkg_data in current.get('packages', {}).items():
                key = f'package_{pkg_id}'
                name = pkg_data.get('common', {}).get('name')
                if name is None:
                    for appid in pkg_data.get('appids', []):
                        app_name = self.names_cache.get(f'app_{appid}')
                        if app_name:
                            name = f"{app_name} ({pkg_id})"
                            break
                if name is not None:
                    self.names_cache[key] = name

        if previous:
            for pkg_id, pkg_data in previous.get('packages', {}).items():
                key = f'package_{pkg_id}'
                if key not in self.names_cache:
                    name = pkg_data.get('common', {}).get('name')
                    if name is None:
                        for appid in pkg_data.get('appids', []):
                            app_name = self.names_cache.get(f'app_{appid}')
                            if app_name:
                                name = f"{app_name} ({pkg_id})"
                                break
                    if name is not None:
                        self.names_cache[key] = name

    def run(self, compare_file: Optional[Path] = None, debug: bool = False) -> int:
        """
        Execute the monitoring logic.

        Args:
            compare_file: Optional file to compare against instead of fetching
            debug: Debug mode - treat all items as new

        Returns:
            Exit code: 0 if output unchanged, 1 if changed, 2 if error
        """
        # Get current product info output
        if compare_file:
            current_output = self.load_output_from_file(compare_file)
        else:
            current_output = self.get_product_info_output()

        if current_output is None:
            print("❌ Failed to get current output", file=sys.stderr)
            return 2

        # Load previous output (unless debug mode)
        previsous_output = None
        if debug:
            previous_output = {}
        else:
            previous_output = self.load_previous_output()

        # Compare
        changes = self.compare_outputs(current_output, previous_output)

        # Save current output (only if not in compare mode)
        if not compare_file:
            if not self.save_output(current_output):
                print("⚠️  Failed to save state, but comparison is still valid",
                      file=sys.stderr)

        # Print and send changes if any
        if changes is not None:
            self._build_names(current_output, previous_output, changes)
            self._print_changes(changes)
            if self.webhook_url:
                self._send_to_discord(changes)
            return 1

        return 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Monitor changes in Steam product info output',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s product_info_store.json
      Monitor and store output in product_info_store.json

  %(prog)s product_info_store.json --compare other_output.json
      Compare two output files without fetching new data

  %(prog)s product_info_store.json --webhook https://discord.com/api/webhooks/...
      Send changes to Discord webhook

  %(prog)s product_info_store.json --webhook https://... --mentions 123456789 @role_name
      Send changes to Discord with mentions
        '''
    )

    parser.add_argument(
        'state_file',
        help='File to store the last output for comparison'
    )

    parser.add_argument(
        '--compare',
        type=Path,
        help='Compare against this file instead of fetching new data'
    )

    parser.add_argument(
        '--webhook',
        help='Discord webhook URL to send notifications'
    )

    parser.add_argument(
        '--mentions',
        nargs='*',
        default=[],
        help='Discord mentions (user IDs or role references like @role_name)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Debug mode: treat all items as new (ignore previous state)'
    )

    args = parser.parse_args()

    monitor = OutputMonitor(
        Path(args.state_file),
        webhook_url=args.webhook,
        mentions=args.mentions
    )
    exit_code = monitor.run(compare_file=args.compare, debug=args.debug)

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
