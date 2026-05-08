import logging
import os
from startScan.models import Screenshot, Subdomain, ScanHistory
from .capture import run_capture

# Playwright's sync API uses an event loop under the hood, 
# so we need to allow Django ORM to run in this "pseudo-async" context.
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

logger = logging.getLogger(__name__)

def take_screenshot_and_save(subdomain_id, scan_id, results_dir="/usr/src/scan_results"):
    """
    Orchestrates the capture and database persistence for a single subdomain.
    """
    try:
        subdomain = Subdomain.objects.get(id=subdomain_id)
        scan = ScanHistory.objects.get(id=scan_id)
        
        # Determine the best URL to capture
        url = subdomain.http_url
        if not url:
            # If no URL discovered yet, try to guess or use the name
            url = f"http://{subdomain.name}"
            
        logger.info(f"Processing screenshot for {url} (Subdomain ID: {subdomain_id})")
        
        capture_result = run_capture(url, scan_id, results_dir)
        
        # Save to database if we got at least a screenshot or it was a success
        if capture_result["screenshot_path"]:
            Screenshot.objects.create(
                subdomain=subdomain,
                scan_history=scan,
                url=url,
                title=capture_result["title"],
                status_code=capture_result["status_code"],
                screenshot_path=capture_result["screenshot_path"],
                html_path=capture_result["html_path"],
                response_headers=capture_result.get("response_headers", {}),
                tags=capture_result.get("tags", [])
            )
            
            # Legacy support: update the screenshot_path field on Subdomain model
            subdomain.screenshot_path = capture_result["screenshot_path"]
            subdomain.save()
            
            logger.info(f"Successfully saved screenshot for {subdomain.name}")
            return True
        else:
            logger.warning(f"No screenshot captured for {subdomain.name}")
            
    except Subdomain.DoesNotExist:
        logger.error(f"Subdomain with ID {subdomain_id} does not exist.")
    except ScanHistory.DoesNotExist:
        logger.error(f"ScanHistory with ID {scan_id} does not exist.")
    except Exception as e:
        logger.error(f"Error in take_screenshot_and_save: {str(e)}")
        
    return False
