import logging
from importlib import import_module
from django.conf import settings
from plugins.models import Plugin

logger = logging.getLogger(__name__)

class PluginTemporalRegistry:
    """
    Global store that dynamic loads Temporal Workflows and Activities 
    from enabled plugins based on their manifest.yaml declarations.
    """

    @classmethod
    def _get_enabled_plugin_manifests(cls):
        # We must protect against DB access issues if models aren't ready
        try:
            return list(Plugin.objects.filter(is_enabled=True).values('slug', 'manifest'))
        except Exception as e:
            logger.error(f"PluginTemporalRegistry failed to fetch plugins: {e}")
            return []

    @classmethod
    def get_all_plugin_workflows(cls):
        workflows = []
        for plugin in cls._get_enabled_plugin_manifests():
            slug = plugin['slug']
            manifest = plugin['manifest']
            temporal = manifest.get('temporal', {})
            wf_paths = temporal.get('workflows', [])
            
            for path in wf_paths:
                try:
                    # Format: "backend.temporal_exports.ActiveExploitationWorkflow"
                    # We need to prepend the actual dynamic module path: "plugins_data.plugin_slug."
                    module_path, class_name = path.rsplit('.', 1)
                    full_module_path = f"plugins_data.{slug}.{module_path}"
                    
                    module = import_module(full_module_path)
                    workflow_class = getattr(module, class_name)
                    workflows.append(workflow_class)
                    logger.info(f"Dynamically loaded Temporal workflow: {class_name} from plugin {slug}")
                except Exception as e:
                    logger.error(f"Failed to load workflow {path} from plugin {slug}: {e}")
                    
        return workflows

    @classmethod
    def get_all_plugin_activities(cls):
        activities = []
        for plugin in cls._get_enabled_plugin_manifests():
            slug = plugin['slug']
            manifest = plugin['manifest']
            temporal = manifest.get('temporal', {})
            act_paths = temporal.get('activities', [])
            
            for path in act_paths:
                try:
                    module_path, func_name = path.rsplit('.', 1)
                    full_module_path = f"plugins_data.{slug}.{module_path}"
                    
                    module = import_module(full_module_path)
                    activity_func = getattr(module, func_name)
                    activities.append(activity_func)
                    logger.info(f"Dynamically loaded Temporal activity: {func_name} from plugin {slug}")
                except Exception as e:
                    logger.error(f"Failed to load activity {path} from plugin {slug}: {e}")
                    
        return activities
