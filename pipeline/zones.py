import json
import os

class ZoneManager:
    def __init__(self, layout_path):
        self.layout_path = layout_path
        self.stores_layout = {}
        self.load_layout()

    def load_layout(self):
        if not os.path.exists(self.layout_path):
            print(f"Warning: Layout file not found at {self.layout_path}")
            return
        try:
            with open(self.layout_path, "r") as f:
                self.stores_layout = json.load(f)
        except Exception as e:
            print(f"Error loading layout: {e}")

    def get_zone_for_point(self, store_id, camera_id, point):
        """
        point: (x, y)
        Returns: (zone_id, sku_zone) or (None, None)
        """
        store = self.stores_layout.get(store_id)
        if not store:
            return None, None

        zones = store.get("zones", {})
        for zone_id, zone_data in zones.items():
            if zone_data.get("camera_id") == camera_id:
                polygon = zone_data.get("polygon", [])
                if self.is_point_in_polygon(point, polygon):
                    return zone_id, zone_data.get("sku_zone")
        
        return None, None

    @staticmethod
    def is_point_in_polygon(point, polygon):
        """
        Ray-casting algorithm to determine if a point is inside a polygon.
        point: (x, y)
        polygon: list of [x, y] coordinates
        """
        if not polygon:
            return False
            
        x, y = point
        n = len(polygon)
        inside = False
        p1x, p1y = polygon[0]
        
        for i in range(n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xints:
                            inside = not inside
            p1x, p1y = p2x, p2y
            
        return inside
