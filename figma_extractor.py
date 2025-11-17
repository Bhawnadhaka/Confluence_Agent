# modules/figma_extractor.py
import requests
import logging ,time 

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


class FigmaPrototypeAnalyzer:


    def __init__(self, token: str, file_key: str, node_id: str):
        self.token = token
        self.file_key = file_key
        self.node_id = node_id
        self.headers = {"X-Figma-Token": self.token}
        self.node_name_map = {}
        self.node_parent_map = {}
        self.valid_destination_nodes = set()
        self.frame_data = []
        self.raw_node_data = None


    def fetch_all_frames(self) -> list[dict]:
        """Fetch all frame-level data (screens) from parent node with retry handling."""
        api_url = f"https://api.figma.com/v1/files/{self.file_key}/nodes?ids={self.node_id}"
        max_retries = 3
        delay = 5  # seconds

        for attempt in range(max_retries):
            try:
                response = requests.get(api_url, headers=self.headers, timeout=120)
                response.raise_for_status()
                data = response.json()
                break  

            except requests.exceptions.ChunkedEncodingError:
                logging.warning(f" Figma API connection dropped (attempt {attempt+1}/{max_retries}). Retrying in {delay}s...")
                time.sleep(delay)

            except requests.exceptions.RequestException as e:
                logging.error(f" Request failed (attempt {attempt+1}/{max_retries}): {e}")
                time.sleep(delay)
        else:
            # If loop finishes without break
            raise RuntimeError("Failed to fetch Figma frames after multiple attempts.")

       
        self.raw_node_data = data
        children = data["nodes"][self.node_id]["document"].get("children", [])

        results = []
        for child in children:
            if child["type"] in ["FRAME", "SECTION"]:
                node_id = child["id"]
                results.append(
                    {
                        "screen_name": child.get("name", "Unnamed"),
                        "url": f"https://www.figma.com/file/{self.file_key}/?type=design&node-id={node_id}",
                        "node_id": node_id,
                    }
                )

        self.frame_data = results
        return results


    def get_node_images(self, node_ids: list[str]) -> dict:
        """Fetch image URLs for given node IDs."""
        if not node_ids:
            return {}
        clean_ids = [self._clean_node_id(n) for n in node_ids]
        ids_param = ",".join(clean_ids)
        url = f"https://api.figma.com/v1/images/{self.file_key}?ids={ids_param}&format=png"
        response = requests.get(url, headers=self.headers, timeout=120)
        if response.status_code == 200:
            return response.json().get("images", {})
        return {}

    def _clean_node_id(self, node_id: str) -> str:
        return node_id.split(";")[0] if ";" in node_id else node_id

    def _find_parent_frame(self, node_id: str) -> str:
        """Find parent frame of a given node."""
        if any(f["node_id"] == node_id for f in self.frame_data):
            return node_id

        visited = set()
        current_id = node_id
        while current_id and current_id not in visited:
            visited.add(current_id)
            parent_id = self.node_parent_map.get(current_id)
            if not parent_id:
                break
            if any(f["node_id"] == parent_id for f in self.frame_data):
                return parent_id
            current_id = parent_id
        return node_id

    def _traverse_collect(self, node, parent_id=None, raw_interactions=None):
        """Traverse nodes to collect metadata and prototype links."""
        if raw_interactions is None:
            raw_interactions = []

        node_id = node.get("id")
        clean_id = self._clean_node_id(node_id)
        self.node_name_map[clean_id] = node.get("name", "Unnamed")
        self.node_parent_map[clean_id] = parent_id

        if node.get("type") in ["FRAME", "SECTION"]:
            self.valid_destination_nodes.add(clean_id)

        transition_node_id = node.get("transitionNodeID")
        if transition_node_id:
            raw_interactions.append(
                {
                    "from_id": clean_id,
                    "from_name": node.get("name", "Unnamed"),
                    "to_id": self._clean_node_id(transition_node_id),
                    "animation": node.get("transitionType", "Instant"),
                }
            )

        for child in node.get("children", []):
            self._traverse_collect(child, clean_id, raw_interactions)

        return raw_interactions

    def extract_interactions(self) -> list[dict]:
        """Extract prototype interactions (with image URLs)."""
        data = self.raw_node_data
        if not data:
            url = f"https://api.figma.com/v1/files/{self.file_key}/nodes?ids={self.node_id}"
            response = requests.get(url, headers=self.headers, timeout=300)
            if response.status_code != 200:
                return []
            data = response.json()

        nodes = data.get("nodes", {})
        if self.node_id not in nodes:
            return []

        document = nodes[self.node_id]["document"]
        raw_interactions = self._traverse_collect(document)

        # Filter interactions to valid destination frames
        valid_interactions = [
            {
                "from_id": r["from_id"],
                "from_name": r["from_name"],
                "to_id": r["to_id"],
                "to_name": self.node_name_map.get(r["to_id"], "Unknown"),
                "animation": r["animation"],
            }
            for r in raw_interactions
            if r["to_id"] in self.valid_destination_nodes
        ]

        if not valid_interactions:
            return []

        # Fetch node images
        all_nodes = set()
        for i in valid_interactions:
            all_nodes.add(i["from_id"])
            all_nodes.add(i["to_id"])
        node_images = self.get_node_images(list(all_nodes))

        for inter in valid_interactions:
            inter["from_url"] = node_images.get(inter["from_id"], "")
            inter["to_url"] = node_images.get(inter["to_id"], "")

        return valid_interactions

    def enrich_with_frame_urls(self, interactions: list[dict]) -> list[dict]:
        """Attach frame image URLs."""
        all_frame_ids = [f["node_id"] for f in self.frame_data]
        frame_images = self.get_node_images(all_frame_ids)

        for inter in interactions:
            from_frame = self._find_parent_frame(inter["from_id"])
            to_frame = self._find_parent_frame(inter["to_id"])
            inter["from_frame_url"] = frame_images.get(from_frame, inter.get("from_url", ""))
            inter["to_frame_url"] = frame_images.get(to_frame, inter.get("to_url", ""))
        return interactions

    def run_extraction(self) -> dict:
       
        frames = self.fetch_all_frames()
        interactions = self.extract_interactions()
        enriched = self.enrich_with_frame_urls(interactions) if interactions else []


        for inter in enriched:
           inter["from_frame_url"] = inter.get("from_frame_url") or inter.get("from_url")
           inter["to_frame_url"] = inter.get("to_frame_url") or inter.get("to_url")
        
        return {
            "frames": frames,
            "interactions": enriched,
            "total_frames": len(frames),
            "total_interactions": len(enriched),
        }
