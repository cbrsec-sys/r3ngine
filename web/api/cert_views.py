"""Certificate Intelligence REST API views."""

import logging
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

logger = logging.getLogger(__name__)


class CertificateIntelView(APIView):
    """
    GET /api/certs/?scan_id=<id>

    Returns all CertificateIntelligence records for a scan, ordered by
    risk (expired first, then weak-cipher, then self-signed).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from startScan.models import CertificateIntelligence

        scan_id = request.query_params.get("scan_id")
        if not scan_id:
            return Response(
                {"error": "scan_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            scan_id = int(scan_id)
        except (ValueError, TypeError):
            return Response(
                {"error": "scan_id must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        certs = (
            CertificateIntelligence.objects
            .filter(scan_history_id=scan_id)
            .order_by("-is_expired", "-has_weak_cipher", "-self_signed", "host")
        )

        results = [
            {
                "id": c.id,
                "host": c.host,
                "port": c.port,
                "subject_cn": c.subject_cn,
                "subject_an": c.subject_an or [],
                "issuer_cn": c.issuer_cn,
                "issuer_org": c.issuer_org,
                "not_before": c.not_before.isoformat() if c.not_before else None,
                "not_after": c.not_after.isoformat() if c.not_after else None,
                "tls_version": c.tls_version,
                "cipher": c.cipher,
                "fingerprint_sha256": c.fingerprint_sha256,
                "self_signed": c.self_signed,
                "mismatched": c.mismatched,
                "is_expired": c.is_expired,
                "has_weak_cipher": c.has_weak_cipher,
            }
            for c in certs
        ]

        return Response({"count": len(results), "results": results})
