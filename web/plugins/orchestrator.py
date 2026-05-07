from celery import chain, group
from .models import Plugin
import importlib
import os
import sys

class PluginOrchestrator:
    """Orchestrates the injection of plugin tasks into the scan workflow."""

    @staticmethod
    def get_plugin_task(plugin, ctx):
        """Dynamically loads and returns a Celery task for a plugin."""
        plugin_slug = plugin.slug
        plugin_dir = os.path.join('/usr/src/app/plugins_data', plugin_slug)
        backend_dir = os.path.join(plugin_dir, 'backend')
        
        if not os.path.exists(backend_dir):
            return None
            
        # Add to sys.path if not already there
        if backend_dir not in sys.path:
            sys.path.append(backend_dir)
            
        # Try to find a task module. By convention {plugin_slug}_tasks.py
        module_name = f"{plugin_slug.replace('-', '_')}_tasks"
        try:
            module = importlib.import_module(module_name)
            # Find the main task. By convention it should be named 'run' or the slug
            task_func = getattr(module, 'run', None) or getattr(module, plugin_slug.replace('-', '_'), None)
            if task_func:
                return task_func.si(ctx=ctx)
        except Exception as e:
            print(f"Error loading plugin task for {plugin_slug}: {str(e)}")
            
        return None

    @classmethod
    def inject_tasks(cls, anchor_name, base_task_si, ctx):
        """
        Wraps a core task with its associated plugins.
        Returns a chain or the base task.
        """
        plugins_before = Plugin.objects.filter(
            anchor_step=anchor_name, 
            runtime_position='BEFORE', 
            is_enabled=True
        ).order_by('order_weight')
        
        plugins_after = Plugin.objects.filter(
            anchor_step=anchor_name, 
            runtime_position='AFTER', 
            is_enabled=True
        ).order_by('order_weight')
        
        workflow = []
        
        # Add 'Before' plugins
        for p in plugins_before:
            task = cls.get_plugin_task(p, ctx)
            if task:
                workflow.append(task)
                
        # Add Core task
        workflow.append(base_task_si)
        
        # Add 'After' plugins
        for p in plugins_after:
            task = cls.get_plugin_task(p, ctx)
            if task:
                workflow.append(task)
                
        if len(workflow) > 1:
            return chain(*workflow)
        return base_task_si
