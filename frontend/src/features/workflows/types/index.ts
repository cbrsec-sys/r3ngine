export type WorkflowSlug =
  | 'user-hunt'
  | 'url-bypass'
  | 'wordpress'
  | 'host-recon'
  | 'cidr-recon'
  | 'code-scan'
  | 'domain-recon'
  | 'subdomain-recon'
  | 'url-crawl'
  | 'url-dirsearch'
  | 'url-fuzz'
  | 'url-params-fuzz'
  | 'url-vuln';

export interface WorkflowMeta {
  slug: WorkflowSlug;
  label: string;
  description: string;
  inputLabel: string;
  inputPlaceholder: string;
  inputType: 'domain' | 'url' | 'cidr' | 'email' | 'username' | 'path' | 'ip';
  category: 'recon' | 'vuln' | 'crawl' | 'osint' | 'code' | 'network';
}

export const WORKFLOW_REGISTRY: WorkflowMeta[] = [
  {
    slug: 'user-hunt',
    label: 'User Hunt',
    description: 'Search for user accounts and password leaks across platforms.',
    inputLabel: 'Target (username or email)',
    inputPlaceholder: 'johndoe or user@example.com',
    inputType: 'username',
    category: 'osint',
  },
  {
    slug: 'url-bypass',
    label: 'URL Bypass (4xx)',
    description: 'Attempt to bypass 4xx access restrictions using header manipulation.',
    inputLabel: 'URL',
    inputPlaceholder: 'https://example.com/admin',
    inputType: 'url',
    category: 'vuln',
  },
  {
    slug: 'wordpress',
    label: 'WordPress Scan',
    description: 'Scan WordPress sites for plugin vulnerabilities and misconfigurations.',
    inputLabel: 'URL',
    inputPlaceholder: 'https://example.com',
    inputType: 'url',
    category: 'vuln',
  },
  {
    slug: 'host-recon',
    label: 'Host Recon',
    description: 'Port scan, service detection, SSH audit, and HTTP probe for a host/IP.',
    inputLabel: 'Host or IP',
    inputPlaceholder: '192.0.2.1 or target.example.com',
    inputType: 'ip',
    category: 'recon',
  },
  {
    slug: 'cidr-recon',
    label: 'CIDR Recon',
    description: 'Discover and scan hosts within a CIDR network range.',
    inputLabel: 'CIDR Range',
    inputPlaceholder: '192.168.1.0/24',
    inputType: 'cidr',
    category: 'network',
  },
  {
    slug: 'code-scan',
    label: 'Code Scan',
    description: 'Scan source code or git repositories for secrets and vulnerabilities.',
    inputLabel: 'Repository or Path',
    inputPlaceholder: 'https://github.com/user/repo or /path/to/code',
    inputType: 'path',
    category: 'code',
  },
  {
    slug: 'domain-recon',
    label: 'Domain Recon',
    description: 'Quick domain intelligence: WHOIS, DNS, SSL, WAF, ASN.',
    inputLabel: 'Domain',
    inputPlaceholder: 'example.com',
    inputType: 'domain',
    category: 'recon',
  },
  {
    slug: 'subdomain-recon',
    label: 'Subdomain Recon',
    description: 'Discover and verify subdomains with takeover detection.',
    inputLabel: 'Domain',
    inputPlaceholder: 'example.com',
    inputType: 'domain',
    category: 'recon',
  },
  {
    slug: 'url-crawl',
    label: 'URL Crawl',
    description: 'Multi-source URL discovery (passive + active crawlers).',
    inputLabel: 'URL',
    inputPlaceholder: 'https://example.com',
    inputType: 'url',
    category: 'crawl',
  },
  {
    slug: 'url-dirsearch',
    label: 'Directory Search',
    description: 'Find hidden directories and files on a web server.',
    inputLabel: 'URL',
    inputPlaceholder: 'https://example.com',
    inputType: 'url',
    category: 'crawl',
  },
  {
    slug: 'url-fuzz',
    label: 'URL Fuzz',
    description: 'Comprehensive web content fuzzing with feroxbuster and ffuf.',
    inputLabel: 'URL',
    inputPlaceholder: 'https://example.com',
    inputType: 'url',
    category: 'vuln',
  },
  {
    slug: 'url-params-fuzz',
    label: 'Parameter Fuzz',
    description: 'Discover and test hidden HTTP parameters.',
    inputLabel: 'URL',
    inputPlaceholder: 'https://example.com/search',
    inputType: 'url',
    category: 'vuln',
  },
  {
    slug: 'url-vuln',
    label: 'URL Vulnerability',
    description: 'Scan URL patterns for XSS, LFI, SSRF, RCE, IDOR (gf + dalfox + nuclei).',
    inputLabel: 'URL',
    inputPlaceholder: 'https://example.com/search?q=test',
    inputType: 'url',
    category: 'vuln',
  },
];

export interface StartWorkflowPayload {
  target?: string;
  target_type?: string;
  urls?: string[];
  cidr?: string;
  domain?: string;
  profile_name?: string;
  yaml_configuration?: Record<string, unknown>;
}

export interface StartWorkflowResponse {
  workflow_id: string;
  status: 'started';
}
