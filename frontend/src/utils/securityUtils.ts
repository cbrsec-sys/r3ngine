import DOMPurify from 'dompurify';

/**
 * Sanitizes HTML content to prevent XSS attacks.
 * Use this when you must render HTML content from an untrusted source.
 */
export const sanitizeHtml = (html: string): string => {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li', 'code', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'],
    ALLOWED_ATTR: ['href', 'target', 'rel', 'class'],
  });
};

/**
 * Escapes characters that have special meaning in regular expressions.
 */
export const escapeRegExp = (string: string): string => {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
};

/**
 * Basic SQL Injection detection for input fields.
 * Note: This is a client-side helper, the backend MUST handle SQLi prevention.
 */
export const containsSqlInjection = (input: string): boolean => {
  const sqlKeywords = [
    '-- ',
    ';--',
    ' union ',
    ' select ',
    ' insert ',
    ' update ',
    ' delete ',
    ' drop ',
    ' truncate ',
    ' alter ',
    ' exec ',
    ' xp_',
  ];
  const lowercaseInput = input.toLowerCase();
  return sqlKeywords.some(keyword => lowercaseInput.includes(keyword));
};

/**
 * Validates if a URL is safe for redirection or linking.
 */
export const isSafeUrl = (url: string): boolean => {
  if (!url) return false;
  
  // Allow relative URLs
  if (url.startsWith('/') && !url.startsWith('//')) return true;
  
  // Allow only http and https protocols
  try {
    const parsed = new URL(url);
    return ['http:', 'https:'].includes(parsed.protocol);
  } catch {
    return false;
  }
};
