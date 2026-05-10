import logging
from reNgine.celery import app
from reNgine.celery_custom_task import RengineTask
from apme.llm_orchestrator import LLMPathOrchestrator

logger = logging.getLogger(__name__)

@app.task(name='run_llm_apme', queue='main_scan_queue', base=RengineTask, bind=True)
def run_llm_apme(self, scan_history_id):
    """
    On-demand Celery task for LLM-assisted Attack Path Modeling.
    """
    logger.info(f"Task run_llm_apme started for scan_history_id={scan_history_id}")
    orchestrator = LLMPathOrchestrator()
    result = orchestrator.run(scan_history_id)
    
    if "error" in result:
        logger.error(f"run_llm_apme failed: {result['error']}")
        return {"status": "failed", "error": result["error"]}
        
    logger.info(f"run_llm_apme completed successfully. Paths found: {result.get('total_paths', 0)}")
    return {"status": "success", "total_paths": result.get("total_paths", 0)}
