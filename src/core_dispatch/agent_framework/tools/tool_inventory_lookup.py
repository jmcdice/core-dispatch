# src/core_dispatch/agent_framework/tools/tool_inventory_lookup.py

import difflib

class InventoryLookupTool:
    """
    Example inventory lookup tool. In reality, you could query a DB, an API, etc.
    This is just a mock dictionary for demonstration.
    """
    def __init__(self):
        # Include 'discontinued' so we can say it's out of season
        self.inventory = {
            "organic almond milk": {
                "quantity": 10,
                "aisle": 5,
                "discontinued": False
            },
            "signature coffee": {
                "quantity": 24,
                "aisle": 12,
                "discontinued": False
            },
            "paddle boards": {
                "quantity": 0,
                "aisle": None,
                "discontinued": True  # Seasonally discontinued
            }
        }

    def lookup(self, item_name: str) -> str:
        """
        Return a short, plain-text description of the inventory result,
        or 'not_found' if unavailable.

        Also attempts fuzzy matching if an exact match is not found.
        """
        item_lower = item_name.lower()

        # 1) Direct exact match
        if item_lower in self.inventory:
            data = self.inventory[item_lower]
            return self._format_inventory_response(item_lower, data)

        # 2) Fuzzy match if no exact match
        # Try to find the closest key in self.inventory, cutoff=0.6 is arbitrary
        close_matches = difflib.get_close_matches(item_lower, self.inventory.keys(), n=1, cutoff=0.6)
        if close_matches:
            matched_item = close_matches[0]
            data = self.inventory[matched_item]
            return self._format_inventory_response(matched_item, data)

        return "not_found"

    def _format_inventory_response(self, item: str, data: dict) -> str:
        """
        Helper method to format the response string for the user.
        """
        if data.get("discontinued", False):
            return f"{item} is discontinued."
        else:
            return f"{data['quantity']} in aisle {data['aisle']}"

