import os
import json
import csv
import subprocess
from celery.utils.log import get_task_logger
from reNgine.celery import app
from reNgine.task_utils import run_command, save_email, save_employee
from reNgine.opsec_utils import OpSecManager
from startScan.models import ScanHistory, Email, Employee
from reNgine.definitions import *
from reNgine.osint.linkedin_intelligence import LinkedInScraper
from reNgine.celery_custom_task import RengineTask

logger = get_task_logger(__name__)

@app.task(name='run_holehe', queue='main_scan_queue', base=RengineTask, bind=True)
def run_holehe(self, email_address, scan_history_id):
    """
    Run holehe for a specific email address to find associated social media accounts.
    """
    try:
        scan_history = ScanHistory.objects.get(pk=scan_history_id)
        opsec = OpSecManager()
        proxy = opsec.get_random_proxy()
        
        cmd = ['holehe', email_address, '--only-used']
        
        # holehe doesn't have a direct JSON output to file via CLI easily in some versions, 
        # but we can capture stdout or check if we can use it as a library.
        # For now, let's run it and capture the output.
        
        if proxy:
            # Wrap with proxychains if needed or use holehe's proxy support if available
            # holehe doesn't have native proxy flags in all versions
            cmd = ['proxychains4', '-q'] + cmd
            
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        
        # Simple parsing of holehe output
        found_sites = []
        for line in stdout.splitlines():
            if '[+]' in line:
                site = line.split('[+]')[1].strip()
                found_sites.append(site)
        
        if found_sites:
            email, _ = save_email(email_address, scan_history=scan_history)
            metadata = email.metadata or {}
            metadata['holehe'] = found_sites
            email.metadata = metadata
            email.save()
            
        return found_sites
    except Exception as e:
        logger.error(f"Error running holehe for {email_address}: {str(e)}")
        return []

@app.task(name='run_maigret', queue='main_scan_queue', base=RengineTask, bind=True)
def run_maigret(self, username, scan_history_id):
    """
    Run maigret to find social media profiles for a given username.
    """
    try:
        scan_history = ScanHistory.objects.get(pk=scan_history_id)
        results_dir = f"{scan_history.results_dir}/osint/maigret"
        os.makedirs(results_dir, exist_ok=True)
        
        output_file = f"{results_dir}/{username}.json"
        
        opsec = OpSecManager()
        proxy = opsec.get_random_proxy()
        
        cmd = ['maigret', username, '--json', output_file]
        
        if proxy:
            # maigret supports --proxy
            cmd += ['--proxy', proxy]
            
        subprocess.run(cmd, capture_output=True, text=True)
        
        profiles = []
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                data = json.load(f)
                # maigret JSON structure varies, but we want the list of sites found
                for site, info in data.get('results', {}).items():
                    if info.get('status') == 'CLAIMED':
                        profiles.append({
                            'site': site,
                            'url': info.get('url_user')
                        })
        
        if profiles:
            employee, _ = save_employee(username, scan_history=scan_history)
            metadata = employee.metadata or {}
            metadata['maigret'] = profiles
            employee.metadata = metadata
            employee.save()
            
        return profiles
    except Exception as e:
        logger.error(f"Error running maigret for {username}: {str(e)}")
        return []

@app.task(name='run_linkedint', queue='osint_queue', base=RengineTask, bind=True)
def run_linkedint(self, company_name, scan_history_id):
    """
    Run LinkedIn Scraper (Playwright) to scrape LinkedIn for employees of a company.
    """
    try:
        scan_history = ScanHistory.objects.get(pk=scan_history_id)
        domain = scan_history.domain.name
        
        # 1. Check for credentials
        linkedin_creds = LinkedInCredentials.objects.first()
        hunter_key = HunterIOAPIKey.objects.first()
        
        if not linkedin_creds or not linkedin_creds.username or not linkedin_creds.password:
            logger.warning(f"LinkedIn credentials not configured for {company_name}. Skipping.")
            return []
            
        if not hunter_key or not hunter_key.key:
            logger.warning(f"Hunter.io API key not configured for {company_name}. Skipping.")
            return []

        # 2. Execute using Playwright-based LinkedInScraper
        with LinkedInScraper(
            username=linkedin_creds.username,
            password=linkedin_creds.password,
            hunter_key=hunter_key.key
        ) as scraper:
            employees = scraper.discover_employees(company_name, domain, scan_history)
            
            if employees:
                for emp_data in employees:
                    # Save employee and update designation
                    emp, _ = save_employee(emp_data['name'], scan_history=scan_history)
                    emp.designation = emp_data['designation']
                    emp.save()
                    
                    # Save email if present
                    if 'email' in emp_data:
                        save_email(emp_data['email'], scan_history=scan_history, employee=emp)
            
            return [f"LinkedIn Intelligence processed {len(employees)} employees for {company_name}"]
            
    except Exception as e:
        logger.error(f"Error running LinkedIn Intelligence for {company_name}: {str(e)}")
        return []


@app.task(name='osint_orchestrator', queue='main_scan_queue', base=RengineTask, bind=True)
def osint_orchestrator(self, scan_history_id):
    """
    Orchestrate the new OSINT pipeline.
    """
    scan_history = ScanHistory.objects.get(pk=scan_history_id)
    domain = scan_history.domain.name
    
    # 1. Get already discovered emails
    emails = scan_history.emails.all()
    for email in emails:
        run_holehe.delay(email.address, scan_history_id)
        
    # 2. Get already discovered employees/usernames
    employees = scan_history.employees.all()
    for employee in employees:
        # Use name as username for maigret as a guess, or if it looks like a username
        if employee.name and ' ' not in employee.name:
            run_maigret.delay(employee.name, scan_history_id)
            
    # 3. LinkedInt for the domain/company
    company_name = domain.split('.')[0]
    run_linkedint.delay(company_name, scan_history_id)
