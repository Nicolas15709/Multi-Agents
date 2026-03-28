import json
from pathlib import Path
from typing import Dict, List


class TemplateRegistry:
    def __init__(self, path: str):
        self.path = Path(path)
        self.data = self._load()

    def _load(self) -> Dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def list_templates(self) -> List[Dict]:
        return self.data.get("templates", [])

    def get_template(self, template_id: str) -> Dict:
        for item in self.list_templates():
            if item["id"] == template_id:
                return item
        raise KeyError(f"Template not found: {template_id}")

    def summary(self) -> Dict:
        return {
            "count": len(self.list_templates()),
            "categories": sorted({item["category"] for item in self.list_templates()}),
        }
