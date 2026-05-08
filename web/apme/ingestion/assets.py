"""
APME Ingestion — Assets

Converts reNgine Subdomain, IpAddress, Port, and EndPoint models
into APME graph nodes and edges.
"""

import logging
import uuid
from typing import List, Tuple

from apme.models.node import Node
from apme.models.edge import Edge

logger = logging.getLogger(__name__)


def _make_id(prefix: str, value: str) -> str:
    return f"{prefix}::{value}"


def ingest_subdomains(target_id: int) -> Tuple[List[Node], List[Edge]]:
    """
    Ingests Subdomains and their IP addresses for a given target domain.
    """
    from startScan.models import Subdomain

    nodes: List[Node] = []
    edges: List[Edge] = []

    subdomains = Subdomain.objects.filter(
        target_domain_id=target_id
    ).prefetch_related("ip_addresses", "ip_addresses__ports")

    for sub in subdomains:
        # Domain node
        domain_node = Node(
            id=_make_id("domain", sub.name),
            type="Asset",
            subtype="domain",
            confidence=1.0,
            source="reNgine:subdomain_discovery",
            properties={
                "name": sub.name,
                "http_status": sub.http_status,
                "is_cdn": sub.is_cdn,
                "scan_history_id": scan_history_id,
            },
        )
        nodes.append(domain_node)

        # IP Address nodes + RESOLVES_TO edges
        for ip_obj in sub.ip_addresses.all():
            ip_id = _make_id("ip", ip_obj.address)
            ip_node = Node(
                id=ip_id,
                type="Asset",
                subtype="ip",
                confidence=1.0,
                source="reNgine:ip_discovery",
                properties={
                    "address": ip_obj.address,
                    "is_cdn": ip_obj.is_cdn,
                    "is_private": ip_obj.is_private,
                },
            )
            nodes.append(ip_node)

            try:
                edges.append(Edge(
                    from_id=domain_node.id,
                    to_id=ip_id,
                    type="RESOLVES_TO",
                    confidence=1.0,
                ))
            except ValueError as exc:
                logger.warning(f"APME Ingestion: {exc}")

            # Port/Service nodes + HOSTS edges
            for port in ip_obj.ports.all():
                service_id = _make_id("service", f"{ip_obj.address}:{port.number}")
                service_node = Node(
                    id=service_id,
                    type="Asset",
                    subtype="service",
                    confidence=1.0,
                    source="reNgine:port_scan",
                    properties={
                        "port": port.number,
                        "service_name": port.service_name or "",
                        "is_uncommon": port.is_uncommon,
                    },
                )
                nodes.append(service_node)

                try:
                    edges.append(Edge(
                        from_id=ip_id,
                        to_id=service_id,
                        type="HOSTS",
                        confidence=1.0,
                    ))
                except ValueError as exc:
                    logger.warning(f"APME Ingestion: {exc}")

    logger.info(
        f"APME Ingestion [assets]: {len(nodes)} nodes, {len(edges)} edges "
        f"(target_id={target_id})"
    )
    return nodes, edges


def ingest_endpoints(target_id: int) -> Tuple[List[Node], List[Edge]]:
    """Ingests EndPoint models for a given target linked to their subdomain."""
    from startScan.models import EndPoint

    nodes: List[Node] = []
    edges: List[Edge] = []

    endpoints = EndPoint.objects.filter(
        subdomain__target_domain_id=target_id
    ).select_related("subdomain")

    for ep in endpoints:
        ep_id = _make_id("endpoint", ep.http_url)
        ep_node = Node(
            id=ep_id,
            type="Asset",
            subtype="endpoint",
            confidence=1.0,
            source="reNgine:endpoint_discovery",
            properties={
                "url": ep.http_url,
                "http_status": ep.http_status,
                "matched_gf_patterns": ep.matched_gf_patterns or "",
            },
        )
        nodes.append(ep_node)

        if ep.subdomain:
            domain_id = _make_id("domain", ep.subdomain.name)
            try:
                edges.append(Edge(
                    from_id=domain_id,
                    to_id=ep_id,
                    type="HOSTS",
                    confidence=1.0,
                ))
            except ValueError as exc:
                logger.warning(f"APME Ingestion: {exc}")

    logger.info(
        f"APME Ingestion [endpoints]: {len(nodes)} nodes, {len(edges)} edges"
    )
    return nodes, edges
