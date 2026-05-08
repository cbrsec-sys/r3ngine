import React from 'react';
import { usePlugins } from '../api/pluginsApi';
import PluginComponentLoader from './PluginComponentLoader';

interface PluginComponentProps {
  name: string;
  default: React.ComponentType<any>;
  [key: string]: any;
}

/**
 * PluginComponent is a wrapper that allows a plugin to COMPLETELY OVERRIDE a core UI component.
 * If no plugin provides an override for the given name, it renders the default core component.
 */
export const PluginComponent: React.FC<PluginComponentProps> = ({ 
  name, 
  default: DefaultComponent, 
  ...props 
}) => {
  const { data: plugins } = usePlugins();

  // Find if any plugin provides an override for this component name
  const override = Array.isArray(plugins)
    ? plugins.find(p => 
        p.is_enabled && (
          p.manifest?.ui?.overrides?.some((o: any) => o.name === name) ||
          p.manifest?.ui?.components?.some((c: any) => c.name === name)
        )
      )
    : null;

  if (override) {
    const componentConfig = (override.manifest.ui.overrides || []).find((o: any) => o.name === name) ||
                            (override.manifest.ui.components || []).find((c: any) => c.name === name);
    return (
      <PluginComponentLoader 
        pluginSlug={override.slug}
        componentFile={componentConfig.file}
        {...props}
      />
    );
  }

  return <DefaultComponent {...props} />;
};

export default PluginComponent;
