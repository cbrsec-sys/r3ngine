"""Regression tests for PR #66 merge fixes."""
from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIRequestFactory


class SubdomainHasIpFilterTest(TestCase):
    """has_ip query parameter must filter the subdomain queryset."""

    def _get_queryset(self, has_ip_value):
        from api.views import SubdomainDatatableViewSet
        factory = APIRequestFactory()
        url = f'/api/subdomains/?project=test&has_ip={has_ip_value}'
        request = factory.get(url)
        request.query_params = request.GET

        view = SubdomainDatatableViewSet()
        view.request = request
        view.format_kwarg = None

        mock_qs = MagicMock()
        mock_qs.filter.return_value = mock_qs
        mock_qs.exclude.return_value = mock_qs
        mock_qs.distinct.return_value = mock_qs
        mock_qs.select_related.return_value = mock_qs
        mock_qs.prefetch_related.return_value = mock_qs
        mock_qs.order_by.return_value = mock_qs
        view.queryset = mock_qs

        with patch('api.views.Subdomain') as mock_subdomain_cls, \
             patch('api.views.SubdomainDatatableViewSet._latest_subdomain_rows_by_name', return_value=mock_qs):
            mock_subdomain_cls.objects.filter.return_value = mock_qs
            mock_subdomain_cls.objects.all.return_value = mock_qs
            view.get_queryset()

        return mock_qs

    def test_has_ip_true_applies_filter(self):
        qs = self._get_queryset('true')
        # filter(ip_addresses__isnull=False) must have been called
        found = any(
            kwargs.get('ip_addresses__isnull') is False
            for _, kwargs in [c for c in qs.filter.call_args_list]
        )
        self.assertTrue(found, "has_ip=true must add filter(ip_addresses__isnull=False)")

    def test_has_ip_false_applies_filter(self):
        qs = self._get_queryset('false')
        found = any(
            kwargs.get('ip_addresses__isnull') is True
            for _, kwargs in [c for c in qs.filter.call_args_list]
        )
        self.assertTrue(found, "has_ip=false must add filter(ip_addresses__isnull=True)")
