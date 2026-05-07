import DOMPurify from 'dompurify';
import type { MonitoringDiscovery } from '../types';

/**
 * Sanitizes a string value to prevent XSS before rendering in the DOM.
 * All values derived from untrusted backend data must be passed through here.
 */
const sanitize = (value: unknown): string => {
  if (value === null || value === undefined) return '';
  return DOMPurify.sanitize(String(value), { ALLOWED_TAGS: [], ALLOWED_ATTR: [] });
};

/**
 * Parses a JSON string safely. Returns the original string on failure.
 * Guards against prototype pollution by not allowing __proto__ keys.
 */
const tryParseJson = (str: string): unknown => {
  try {
    const parsed = JSON.parse(str);
    // Prevent prototype pollution: reject objects with dangerous keys
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      if ('__proto__' in parsed || 'constructor' in parsed || 'prototype' in parsed) {
        return str;
      }
    }
    return parsed;
  } catch {
    return str;
  }
};

/**
 * Formats the content of a monitoring discovery based on its type.
 * MonitoringDiscovery.content is a JSONField in the backend.
 * All output is sanitized to prevent XSS.
 */
export const formatDiscoveryContent = (discovery: MonitoringDiscovery): string => {
  if (!discovery.content) return 'N/A';
  
  const content = typeof discovery.content === 'string' 
    ? tryParseJson(discovery.content) 
    : discovery.content;

  // Only access properties if content is a plain object
  const isObj = content !== null && typeof content === 'object' && !Array.isArray(content);
  const obj = isObj ? (content as Record<string, unknown>) : null;

  switch (discovery.discovery_type) {
    case 'subdomain':
      return sanitize(obj?.subdomain ?? obj?.name ?? JSON.stringify(content));
    case 'directory':
      return sanitize(obj?.url ?? obj?.path ?? JSON.stringify(content));
    case 'status_change':
      return `Status: ${sanitize(obj?.old_status)} -> ${sanitize(obj?.new_status)}`;
    case 'ip':
      return `IP: ${sanitize(obj?.old_ip)} -> ${sanitize(obj?.new_ip)}`;
    case 'login':
      return sanitize(obj?.url ?? 'New login page detected');
    default:
      return sanitize(typeof content === 'object' ? JSON.stringify(content) : String(content));
  }
};
