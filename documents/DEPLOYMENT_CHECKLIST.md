# v3.5 CVE Enrichment Deployment Checklist

## Pre-Deployment

- [ ] Review all changes since v3.4.1
- [ ] Run unit test suite: `python manage.py test tests/test_cve_enrichment.py`
- [ ] Run correlation tests: `python manage.py test tests/test_correlation.py`
- [ ] Run integration tests: `python manage.py test tests/test_integration.py`
- [ ] Verify Docker images build successfully
- [ ] Verify database backups exist and are restorable

---

## Database Migrations

```bash
# 1. Create database backup
pg_dump -U postgres r3ngine_db > backup_pre_v3.5.sql

# 2. Review pending migrations
python manage.py showmigrations startScan

# 3. Apply migrations
python manage.py migrate

# 4. Verify new tables/columns
python manage.py shell
>>> from django.db import connection
>>> with connection.cursor() as cursor:
...     cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'startScan_cveid'")
...     cols = [r[0] for r in cursor.fetchall()]
...     assert 'cvss_v31_base_score' in cols, "MISSING: cvss_v31_base_score"
...     assert 'epss_score' in cols, "MISSING: epss_score"
...     assert 'attack_vector' in cols, "MISSING: attack_vector"
...     print("CveId columns verified ✅")
```

**Expected migrations to be applied:**

| Migration | Description |
|---|---|
| `startScan 0035_add_cve_enrichment_fields` | CveId enrichment fields + related_cves M2M |
| `startScan 0036_create_vulnerability_history` | VulnerabilityHistory tracking model |

---

## Code Deployment

- [ ] Deploy `web/reNgine/cve_enrichment.py`
- [ ] Deploy `web/reNgine/correlation.py`
- [ ] Deploy `web/startScan/models.py`
- [ ] Deploy `web/startScan/management/commands/sync_cve_data.py`
- [ ] Deploy `web/startScan/migrations/0035_add_cve_enrichment_fields.py`
- [ ] Deploy `web/startScan/migrations/0036_create_vulnerability_history.py`

---

## Configuration

- [ ] Set `NVD_API_KEY` in `.env` (optional — increases rate limit to 50 req/30s)
- [ ] Test API connectivity:

```python
# Inside Django shell
from reNgine.cve_enrichment import CVEEnrichmentService
service = CVEEnrichmentService()
cve = service.enrich_cve('CVE-2021-44228')  # Log4Shell — should always have data
print(f"CVSS: {cve.cvss_v31_base_score}")   # Expected: 10.0
print(f"KEV:  {cve.is_cisa_kev}")           # Expected: True
```

---

## Initial Data Load

- [ ] Run initial CVE enrichment for all existing records:

```bash
python manage.py sync_cve_data --all --limit 1000
```

- [ ] Monitor logs for API errors:

```bash
docker logs r3ngine_web --follow | grep -i "cve\|enrichment\|nvd\|epss"
```

- [ ] Verify enrichment progress:

```python
from startScan.models import CveId
total = CveId.objects.count()
enriched = CveId.objects.filter(cvss_v31_base_score__isnull=False).count()
print(f"{enriched}/{total} CVEs enriched ({100*enriched//total if total else 0}%)")
```

---

## Cron Jobs (Optional)

Add to crontab inside the `web` container or orchestration config:

```bash
# Daily CVE sync at 2 AM
0 2 * * * cd /app && python manage.py sync_cve_data --all

# Hourly CISA KEV sync
0 * * * * cd /app && python manage.py sync_cve_data --kev
```

---

## Rollback Plan

If critical issues occur after deployment:

1. Stop all active scans via the UI
2. Roll back code: `git checkout v3.4.1`
3. Reverse migrations to last known good state:
   ```bash
   python manage.py migrate startScan 0034
   ```
4. Restart application containers
5. Restore database backup if data corruption occurred:
   ```bash
   psql -U postgres r3ngine_db < backup_pre_v3.5.sql
   ```

---

## Post-Deployment Verification

- [ ] Start a test scan on a known target
- [ ] Verify correlation engine runs without `AttributeError`
- [ ] Confirm CVE enrichment logs appear for new CVE discoveries
- [ ] Confirm `VulnerabilityHistory` records are created after scan
- [ ] Test API endpoint: `GET /api/v1/tools/cve_details/?cve_id=CVE-2021-44228`
  - Expected response includes `cvss_v31_base_score`, `epss_score`, `attack_vector`
- [ ] Monitor application logs for 24 hours after deployment

---

## Performance Baseline

Record before → after metrics:

| Metric | Before | After |
|---|---|---|
| Scan correlation time | _____ ms | _____ ms |
| CVE lookup time (cached) | _____ ms | _____ ms |
| CVE lookup time (cold) | _____ ms | _____ ms |
| Database size | _____ MB | _____ MB |
| Enriched CVE count | _____ | _____ |

---

## Rollout Strategy

### Option 1: Big Bang (Recommended for < 100 CVEs in system)

Deploy all changes at once, monitor for 24 hours.

### Option 2: Phased (Recommended for large CVE databases)

1. Deploy code changes (no migrations yet)
2. Run migrations during maintenance window
3. Run enrichment gradually: `sync_cve_data --limit 50` hourly until complete

### Option 3: Feature Flag (Maximum safety)

1. Deploy code with enrichment call disabled in `correlation.py`
2. Enable after verifying migration and initial enrichment succeeded
3. Controlled rollback available at any point
