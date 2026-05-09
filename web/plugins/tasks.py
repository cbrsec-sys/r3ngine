import os
import subprocess
import logging
import yaml
from celery import shared_task
from .models import Plugin

logger = logging.getLogger(__name__)

@shared_task(name='plugins.install_plugin_tools', queue='run_command_queue')
def install_plugin_tools(plugin_slug):
    """
    Task to install tools defined in a plugin's tools.yaml.
    """
    try:
        plugin = Plugin.objects.get(slug=plugin_slug)
    except Plugin.DoesNotExist:
        logger.error(f"Plugin {plugin_slug} not found for tool installation.")
        return

    tools_config = plugin.tools_config
    if not tools_config or 'tools' not in tools_config:
        logger.info(f"No tools to install for plugin {plugin_slug}.")
        return

    plugin_dir = os.path.join('/usr/src/app/plugins_data', plugin_slug)
    
    for tool in tools_config.get('tools', []):
        name = tool.get('name')
        install_command = tool.get('install_command')
        validation_command = tool.get('validation_command')

        if not install_command:
            logger.warning(f"No install command for tool {name} in plugin {plugin_slug}")
            continue

        logger.info(f"Installing tool {name} for plugin {plugin_slug}...")
        
        try:
            # Run install command in the plugin directory
            subprocess.run(
                install_command, 
                shell=True, 
                cwd=plugin_dir, 
                check=True, 
                capture_output=True, 
                text=True
            )
            logger.info(f"Successfully installed tool {name}.")
            
            # Verify installation
            if validation_command:
                res = subprocess.run(
                    validation_command, 
                    shell=True, 
                    cwd=plugin_dir, 
                    capture_output=True, 
                    text=True
                )
                if res.returncode == 0:
                    logger.info(f"Tool {name} verified successfully.")
                else:
                    logger.error(f"Tool {name} verification failed: {res.stderr}")
                    
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install tool {name}: {e.stderr}")
        except Exception as e:
            logger.error(f"Unexpected error installing tool {name}: {str(e)}")

@shared_task(name='plugins.verify_all_plugin_tools', queue='run_command_queue')
def verify_all_plugin_tools():
    """
    Background task to verify all enabled plugin tools are installed.
    Runs on startup.
    """
    enabled_plugins = Plugin.objects.filter(is_enabled=True)
    for plugin in enabled_plugins:
        install_plugin_tools.delay(plugin.slug)
