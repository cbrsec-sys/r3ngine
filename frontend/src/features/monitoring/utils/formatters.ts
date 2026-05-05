import type { MonitoringDiscovery } from '../types';

/**
 * Formats the content of a monitoring discovery based on its type.
 * MonitoringDiscovery.content is a JSONField in the backend.
 */
export const formatDiscoveryContent = (discovery: MonitoringDiscovery): string => {
  if (!discovery.content) return 'N/A';
  
  const content = typeof discovery.content === 'string' 
    ? tryParseJson(discovery.content) 
    : discovery.content;

  switch (discovery.discovery_type) {
    case 'subdomain':
      return content.subdomain || content.name || JSON.stringify(content);
    case 'directory':
      return content.url || content.path || JSON.stringify(content);
    case 'status_change':
      return `Status: ${content.old_status} -> ${content.new_status}`;
    case 'ip':
      return `IP: ${content.old_ip} -> ${content.new_ip}`;
    case 'login':
      return content.url || 'New login page detected';
    default:
      return typeof content === 'object' ? JSON.stringify(content) : String(content);
  }
};

const tryParseJson = (str: string) => {
  try {
    return JSON.parse(str);
  } catch (e) {
    return str;
  }
};
