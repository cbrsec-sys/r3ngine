#!/usr/bin/python
import logging

logger = logging.getLogger('django')

# Mapping of detected technologies to Nuclei tags
# This helps in running targeted scans based on the technology stack
TECH_TO_NUCLEI_TAGS = {
    'wordpress': ['wordpress', 'wp-plugin', 'wp-theme'],
    'apache': ['apache', 'htaccess'],
    'nginx': ['nginx'],
    'php': ['php', 'phpunit'],
    'laravel': ['laravel'],
    'django': ['django'],
    'react': ['react'],
    'vue': ['vue'],
    'angular': ['angular'],
    'jquery': ['jquery'],
    'bootstrap': ['bootstrap'],
    'drupal': ['drupal'],
    'joomla': ['joomla'],
    'magento': ['magento'],
    'shopify': ['shopify'],
    'firebase': ['firebase'],
    'aws': ['aws', 's3', 'ec2'],
    'azure': ['azure'],
    'google cloud': ['gcp'],
    'docker': ['docker'],
    'kubernetes': ['k8s', 'kubernetes'],
    'jenkins': ['jenkins'],
    'gitlab': ['gitlab'],
    'github': ['github'],
    'jira': ['jira'],
    'confluence': ['confluence'],
    'redis': ['redis'],
    'mongodb': ['mongodb'],
    'mysql': ['mysql'],
    'postgresql': ['postgresql'],
    'elasticsearch': ['elasticsearch'],
    'grafana': ['grafana'],
    'prometheus': ['prometheus'],
    'node.js': ['nodejs', 'express'],
    'express': ['express'],
    'spring boot': ['spring-boot', 'spring'],
    'java': ['java', 'jsp'],
    'asp.net': ['aspnet', 'dotnet'],
    'iis': ['iis'],
    'coldfusion': ['coldfusion'],
    'rails': ['rails', 'ruby'],
    'python': ['python'],
    'tomcat': ['tomcat'],
    'weblogic': ['weblogic'],
    'jboss': ['jboss'],
    'websphere': ['websphere'],
    'sap': ['sap'],
    'oracle': ['oracle'],
}

def get_nuclei_tags_from_techs(techs):
    """Generate targeted Nuclei tags based on a list of technologies.
    
    Args:
        techs (list): List of technology names discovered by httpx.
        
    Returns:
        list: Targeted Nuclei tags.
    """
    if not techs:
        return []
        
    tags = set()
    for tech in techs:
        tech_lower = tech.lower()
        # Direct mapping
        if tech_lower in TECH_TO_NUCLEI_TAGS:
            tags.update(TECH_TO_NUCLEI_TAGS[tech_lower])
        
        # Substring matching for more flexibility
        for key, value in TECH_TO_NUCLEI_TAGS.items():
            if key in tech_lower or tech_lower in key:
                tags.update(value)
                
        # Always add the tech itself as a potential tag
        # (Sanitize: remove spaces and special chars if needed)
        sanitized_tech = tech_lower.replace(' ', '-').replace('.', '')
        tags.add(sanitized_tech)
        
    return list(tags)
