from django.db import models
from startScan.models import ScanHistory
from targetApp.models import Domain

class StressTestResult(models.Model):
    scan_history = models.ForeignKey(ScanHistory, on_delete=models.CASCADE, related_name='stress_results')
    target_domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='stress_results', null=True, blank=True)
    tool_used = models.CharField(max_length=50, default="k6")
    concurrency_used = models.IntegerField(default=0)
    duration = models.CharField(max_length=50, blank=True, null=True)
    
    total_requests = models.IntegerField(default=0)
    successful_requests = models.IntegerField(default=0)
    failed_requests = models.IntegerField(default=0)
    
    avg_latency_ms = models.FloatField(default=0.0)
    p95_latency_ms = models.FloatField(default=0.0)
    p99_latency_ms = models.FloatField(default=0.0)
    max_requests_per_second = models.FloatField(default=0.0)
    
    is_kill_switch_triggered = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Stress Test Result'
        verbose_name_plural = 'Stress Test Results'

    def __str__(self):
        return f"Stress Test Result for Scan {self.scan_history.id} - {self.tool_used}"
