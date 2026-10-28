"""Service for reconstructing, validating, and querying the electrical network hierarchy."""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
from app.models.hierarchy import HierarchyTreeNode, NetworkHierarchyResponse
from app.services.meter_service import MeterService


class HierarchyService:
    """Reconstructs the hierarchical topology of the utility distribution network."""

    def __init__(self, meter_service: MeterService):
        self.meter_service = meter_service

    def build_network_tree(self) -> NetworkHierarchyResponse:
        """Reconstruct the entire 7-tier distribution network hierarchy.

        Tiers:
            Zone -> Circle -> Division -> Subdivision -> Substation -> Feeder -> DT -> Meters
        """
        raw_meters = self.meter_service.get_all_raw_meters()

        # Track unique entities across each tier
        zones: Dict[str, str] = {}
        circles: Dict[str, Tuple[str, str]] = {}  # code -> (name, parent_zone_code)
        divisions: Dict[str, Tuple[str, str]] = {}  # code -> (name, parent_circle_code)
        subdivisions: Dict[str, Tuple[str, str]] = {}  # code -> (name, parent_division_code)
        substations: Dict[str, Tuple[str, str]] = {}  # code -> (name, parent_subdivision_code)
        feeders: Dict[str, Tuple[str, str]] = {}  # code -> (name, parent_substation_code)
        dts: Dict[str, Tuple[str, str]] = {}  # code -> (name, parent_feeder_code)

        # Map DT code to list of meter IDs
        dt_to_meters: Dict[str, List[str]] = defaultdict(list)

        for item in raw_meters:
            meter_id = item.get("meterId")
            h = item.get("hierarchy", {})

            z = h.get("zone")
            c = h.get("circle")
            d = h.get("division")
            sd = h.get("subdivision")
            ss = h.get("substation")
            f = h.get("feeder")
            dt = h.get("dt")

            z_code = z.get("code") if isinstance(z, dict) else None
            z_name = z.get("name", z_code) if isinstance(z, dict) else None

            c_code = c.get("code") if isinstance(c, dict) else None
            c_name = c.get("name", c_code) if isinstance(c, dict) else None

            d_code = d.get("code") if isinstance(d, dict) else None
            d_name = d.get("name", d_code) if isinstance(d, dict) else None

            sd_code = sd.get("code") if isinstance(sd, dict) else None
            sd_name = sd.get("name", sd_code) if isinstance(sd, dict) else None

            ss_code = ss.get("code") if isinstance(ss, dict) else None
            ss_name = ss.get("name", ss_code) if isinstance(ss, dict) else None

            f_code = f.get("code") if isinstance(f, dict) else None
            f_name = f.get("name", f_code) if isinstance(f, dict) else None

            dt_code = dt.get("code") if isinstance(dt, dict) else item.get("dtCode")
            dt_name = dt.get("name", dt_code) if isinstance(dt, dict) else dt_code

            if z_code and z_name:
                zones[z_code] = z_name
            if c_code and c_name and z_code:
                circles[c_code] = (c_name, z_code)
            if d_code and d_name and c_code:
                divisions[d_code] = (d_name, c_code)
            if sd_code and sd_name and d_code:
                subdivisions[sd_code] = (sd_name, d_code)
            if ss_code and ss_name and sd_code:
                substations[ss_code] = (ss_name, sd_code)
            if f_code and f_name and ss_code:
                feeders[f_code] = (f_name, ss_code)
            if dt_code and dt_name and f_code:
                dts[dt_code] = (dt_name, f_code)

            if dt_code and meter_id:
                dt_to_meters[dt_code].append(meter_id)

        # Build tree upwards from DTs
        # 1. Build DT nodes
        feeder_children: Dict[str, List[HierarchyTreeNode]] = defaultdict(list)
        for dt_code, (dt_name, parent_feeder) in sorted(dts.items()):
            meter_list = sorted(dt_to_meters.get(dt_code, []))
            node = HierarchyTreeNode(
                id=dt_code,
                code=dt_code,
                name=dt_name,
                level="dt",
                meter_count=len(meter_list),
                meter_ids=meter_list,
                children=[],
            )
            feeder_children[parent_feeder].append(node)

        # 2. Build Feeder nodes
        substation_children: Dict[str, List[HierarchyTreeNode]] = defaultdict(list)
        for f_code, (f_name, parent_ss) in sorted(feeders.items()):
            child_dts = feeder_children.get(f_code, [])
            count = sum(c.meter_count for c in child_dts)
            node = HierarchyTreeNode(
                id=f_code,
                code=f_code,
                name=f_name,
                level="feeder",
                meter_count=count,
                children=child_dts,
            )
            substation_children[parent_ss].append(node)

        # 3. Build Substation nodes
        subdivision_children: Dict[str, List[HierarchyTreeNode]] = defaultdict(list)
        for ss_code, (ss_name, parent_sd) in sorted(substations.items()):
            child_feeders = substation_children.get(ss_code, [])
            count = sum(c.meter_count for c in child_feeders)
            node = HierarchyTreeNode(
                id=ss_code,
                code=ss_code,
                name=ss_name,
                level="substation",
                meter_count=count,
                children=child_feeders,
            )
            subdivision_children[parent_sd].append(node)

        # 4. Build Subdivision nodes
        division_children: Dict[str, List[HierarchyTreeNode]] = defaultdict(list)
        for sd_code, (sd_name, parent_div) in sorted(subdivisions.items()):
            child_substations = subdivision_children.get(sd_code, [])
            count = sum(c.meter_count for c in child_substations)
            node = HierarchyTreeNode(
                id=sd_code,
                code=sd_code,
                name=sd_name,
                level="subdivision",
                meter_count=count,
                children=child_substations,
            )
            division_children[parent_div].append(node)

        # 5. Build Division nodes
        circle_children: Dict[str, List[HierarchyTreeNode]] = defaultdict(list)
        for d_code, (d_name, parent_circ) in sorted(divisions.items()):
            child_subdivisions = division_children.get(d_code, [])
            count = sum(c.meter_count for c in child_subdivisions)
            node = HierarchyTreeNode(
                id=d_code,
                code=d_code,
                name=d_name,
                level="division",
                meter_count=count,
                children=child_subdivisions,
            )
            circle_children[parent_circ].append(node)

        # 6. Build Circle nodes
        zone_children: Dict[str, List[HierarchyTreeNode]] = defaultdict(list)
        for c_code, (c_name, parent_zone) in sorted(circles.items()):
            child_divisions = circle_children.get(c_code, [])
            count = sum(c.meter_count for c in child_divisions)
            node = HierarchyTreeNode(
                id=c_code,
                code=c_code,
                name=c_name,
                level="circle",
                meter_count=count,
                children=child_divisions,
            )
            zone_children[parent_zone].append(node)

        # 7. Build Zone nodes (roots)
        root_nodes: List[HierarchyTreeNode] = []
        for z_code, z_name in sorted(zones.items()):
            child_circles = zone_children.get(z_code, [])
            count = sum(c.meter_count for c in child_circles)
            node = HierarchyTreeNode(
                id=z_code,
                code=z_code,
                name=z_name,
                level="zone",
                meter_count=count,
                children=child_circles,
            )
            root_nodes.append(node)

        return NetworkHierarchyResponse(
            root_zones=root_nodes,
            total_zones=len(zones),
            total_substations=len(substations),
            total_feeders=len(feeders),
            total_transformers=len(dts),
            total_meters=len(raw_meters),
        )

    def find_node(
        self, level: str, code: str
    ) -> Optional[HierarchyTreeNode]:
        """Find a specific hierarchy node by tier level and code."""
        tree = self.build_network_tree()
        normalized_level = level.strip().lower()
        normalized_code = code.strip().upper()

        def dfs(node: HierarchyTreeNode) -> Optional[HierarchyTreeNode]:
            if node.level.lower() == normalized_level and node.code.upper() == normalized_code:
                return node
            for child in node.children:
                res = dfs(child)
                if res:
                    return res
            return None

        for root in tree.root_zones:
            match = dfs(root)
            if match:
                return match

        return None
