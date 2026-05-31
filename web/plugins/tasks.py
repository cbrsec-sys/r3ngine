import os
import subprocess
import threading
import logging
import yaml
from django.core.cache import cache
from .models import Plugin

logger = logging.getLogger(__name__)

_TOOL_VERIFIED_CACHE_TIMEOUT = None  # persistent until explicitly cleared on plugin install/upgrade


def install_plugin_tools(plugin_slug):
    """
    Task to install tools defined in a plugin's tools.yaml.
    Skips tools whose verification result is already cached from a prior startup.
    Cache is invalidated when the plugin is installed or upgraded.
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
        cache_key = f"plugin_{plugin_slug}_tool_{name}_verified"

        if cache.get(cache_key):
            logger.info(f"Tool {name} for plugin {plugin_slug} already verified (cached), skipping.")
            continue

        install_command = tool.get('install_command')
        validation_command = tool.get('validation_command')

        already_installed = False
        if validation_command:
            res = subprocess.run(
                validation_command,
                shell=True,
                cwd=plugin_dir,
                capture_output=True,
                text=True
            )
            if res.returncode == 0:
                logger.info(f"Tool {name} for plugin {plugin_slug} already installed, skipping install.")
                cache.set(cache_key, True, timeout=_TOOL_VERIFIED_CACHE_TIMEOUT)
                already_installed = True

        if not already_installed:
            if not install_command:
                logger.warning(f"No install command for tool {name} in plugin {plugin_slug}")
                continue

            logger.info(f"Installing tool {name} for plugin {plugin_slug}...")
            try:
                subprocess.run(
                    install_command,
                    shell=True,
                    cwd=plugin_dir,
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.info(f"Successfully installed tool {name}.")

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
                        cache.set(cache_key, True, timeout=_TOOL_VERIFIED_CACHE_TIMEOUT)
                    else:
                        logger.error(f"Tool {name} verification failed: {res.stderr}")
                else:
                    cache.set(cache_key, True, timeout=_TOOL_VERIFIED_CACHE_TIMEOUT)

            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install tool {name}: {e.stderr}")
            except Exception as e:
                logger.error(f"Unexpected error installing tool {name}: {str(e)}")

def verify_all_plugin_tools():
    """
    Background task to verify all enabled plugin tools are installed.
    Runs on startup.
    """
    enabled_plugins = Plugin.objects.filter(is_enabled=True)
    for plugin in enabled_plugins:
        threading.Thread(
            target=install_plugin_tools,
            args=(plugin.slug,),
            daemon=True
        ).start()
