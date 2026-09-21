"""grpcurl must probe ports the scan found, not the port the URL happened to use.

Every discovered web host used to be probed as `grpcurl -plaintext host:443`.
That cannot succeed whatever is listening: -plaintext speaks cleartext and 443
is a TLS port. It cost a three-second connect timeout per host and filled the
command log with "Failed to dial".
"""
from unittest import TestCase

from reNgine.tasks.crawl import grpc_probe_targets


class TestPortSelection(TestCase):

    def test_well_known_grpc_port_is_probed_in_plaintext(self):
        self.assertEqual(
            grpc_probe_targets([(50051, None)], 443, True),
            [(50051, False)],
        )

    def test_tls_port_is_probed_with_tls(self):
        self.assertEqual(
            grpc_probe_targets([(443, 'https')], 443, True),
            [(443, True)],
        )

    def test_service_name_marks_a_port_worth_probing(self):
        """An unusual port whose service says grpc is still a candidate."""
        self.assertEqual(
            grpc_probe_targets([(7777, 'grpc')], 80, False),
            [(7777, False)],
        )

    def test_service_name_marks_tls_on_an_unusual_port(self):
        self.assertEqual(
            grpc_probe_targets([(7777, 'grpc-ssl')], 80, False),
            [(7777, True)],
        )

    def test_uninteresting_open_ports_are_not_probed(self):
        """The port scan ran and found nothing gRPC-shaped — probe nothing."""
        self.assertEqual(
            grpc_probe_targets([(22, 'ssh'), (25, 'smtp'), (3306, 'mysql')], 443, True),
            [],
        )

    def test_results_are_ordered_and_capped(self):
        ports = [(p, None) for p in (50052, 50051, 9443, 9091, 9090, 8443, 8081, 8080, 443)]
        targets = grpc_probe_targets(ports, 443, True)
        self.assertEqual(len(targets), 5)
        self.assertEqual([p for p, _ in targets], sorted(p for p, _ in targets))
        self.assertEqual(targets[0], (443, True))

    def test_duplicate_port_entries_collapse(self):
        """The same port can arrive once per IP address of the host."""
        self.assertEqual(
            grpc_probe_targets([(50051, None), (50051, None)], 80, False),
            [(50051, False)],
        )


class TestFallbackWithoutPortScanData(TestCase):
    """A scan configured without port_scan must not lose gRPC coverage."""

    def test_https_url_falls_back_to_tls_not_plaintext(self):
        self.assertEqual(grpc_probe_targets([], 443, True), [(443, True)])

    def test_http_url_falls_back_to_plaintext(self):
        self.assertEqual(grpc_probe_targets([], 80, False), [(80, False)])

    def test_explicit_url_port_is_kept(self):
        self.assertEqual(grpc_probe_targets([], 8090, False), [(8090, False)])


class TestTheOriginalDefect(TestCase):

    def test_plaintext_is_never_chosen_for_443(self):
        for open_ports in ([], [(443, 'https')], [(443, None)]):
            for port, use_tls in grpc_probe_targets(open_ports, 443, True):
                if port == 443:
                    self.assertTrue(
                        use_tls,
                        'port 443 must never be probed with -plaintext',
                    )
