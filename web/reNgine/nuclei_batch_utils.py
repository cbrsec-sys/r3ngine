import logging
import subprocess

logger = logging.getLogger(__name__)


def count_templates_for_tag(tag: str, template_dirs: list) -> int:
    """Count nuclei templates matching a given tag by running ``nuclei -tl``.

    Returns 0 on any error so callers treat unknown/unavailable tags as zero-cost.
    """
    if not tag or not template_dirs:
        return 0
    cmd = ['nuclei', '-tl']
    for d in template_dirs:
        cmd += ['-t', d]
    cmd += ['-tags', tag]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        return len(lines)
    except Exception as exc:
        logger.warning('count_templates_for_tag failed for tag %s: %s', tag, exc)
        return 0


def build_tag_batches(tags: list, tag_counts: dict, max_per_batch: int = 100) -> list:
    """Group tags into batches so each batch's total template count <= max_per_batch.

    Uses a greedy first-fit algorithm over the supplied tag order. A tag whose
    individual count already exceeds max_per_batch is placed alone in its own
    batch — further splitting at the file level is not done here.

    This function is pure (no I/O, no randomness) and safe to call from a
    Temporal workflow.

    Args:
        tags: Ordered list of tag strings to batch.
        tag_counts: Mapping of tag -> template count (missing tags treated as 0).
        max_per_batch: Maximum cumulative template count allowed per batch.

    Returns:
        List of batches; each batch is a list of tag strings. Empty when tags=[].
    """
    if not tags:
        return []

    batches: list = []
    current_batch: list = []
    current_count: int = 0

    for tag in tags:
        count = tag_counts.get(tag, 0)
        if current_batch and current_count + count > max_per_batch:
            batches.append(current_batch)
            current_batch = [tag]
            current_count = count
        else:
            current_batch.append(tag)
            current_count += count

    if current_batch:
        batches.append(current_batch)

    return batches
