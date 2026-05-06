import re

class PIIGate:
    """
    PIIGate provides anonymization and deanonymization for sensitive data 
    (IPs, Emails, Hostnames) before sending it to external LLMs.
    """
    def __init__(self):
        self.mask_map = {}
        self.reverse_map = {}
        # Basic patterns for common PII
        self.patterns = {
            'IP': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            # Focus on subdomains/internal-looking hostnames
            'HOSTNAME': r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b',
        }

    def anonymize(self, text):
        """
        Replaces PII with look-alike garbage values.
        """
        if not text:
            return text
        
        processed_text = text
        for pii_type, pattern in self.patterns.items():
            matches = re.findall(pattern, processed_text)
            # Use set to avoid redundant processing and ensure consistent masking for same value
            for i, match in enumerate(sorted(set(matches), key=len, reverse=True)):
                mask = f"[{pii_type}_{len(self.mask_map) + 1}]"
                if match not in self.mask_map:
                    self.mask_map[match] = mask
                    self.reverse_map[mask] = match
                processed_text = processed_text.replace(match, self.mask_map[match])
        
        return processed_text

    def deanonymize(self, text):
        """
        Restores original PII values from an anonymized string.
        """
        if not text:
            return text
        
        processed_text = text
        # Replace masks starting from longest to avoid partial replacements
        masks = sorted(self.reverse_map.keys(), key=len, reverse=True)
        for mask in masks:
            processed_text = processed_text.replace(mask, self.reverse_map[mask])
        
        return processed_text
