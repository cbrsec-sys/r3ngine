import os
import re
import subprocess
import validators
from django.utils import timezone
from celery.utils.log import get_task_logger

from reNgine.celery import app
from reNgine.opsec_utils import ProxychainsWrapper
from startScan.models import ScanHistory, Email, Employee, Command
from reNgine.common_func import remove_ansi_escape_sequences

logger = get_task_logger(__name__)

def sanitize_command_for_db(cmd):
    """
    Strips 'export HTTP_PROXY=... &&' and 'proxychains4 -f ...' from command
    to ensure the UI displays the actual tool name and clean command.
    """
    if not cmd:
        return cmd
    # Strip export statements (matches both single and double quotes)
    cmd = re.sub(r'^export\s+.*?\s+&&\s+', '', cmd)
    # Strip proxychains4 wrapper with its config file
    cmd = re.sub(r'^(?:[/\w]*/)?proxychains4\s+-f\s+\S+\s+', '', cmd)
    return cmd

@app.task(name='run_command', bind=False, queue='run_command_queue')
def run_command(
        cmd, 
        cwd=None, 
        shell=False, 
        history_file=None, 
        scan_id=None, 
        activity_id=None,
        remove_ansi_sequence=False,
        proxy=None
    ):
    """Run a given command using subprocess module.

    Args:
        cmd (str): Command to run.
        cwd (str): Current working directory.
        echo (bool): Log command.
        shell (bool): Run within separate shell if True.
        history_file (str): Write command + output to history file.
        remove_ansi_sequence (bool): Used to remove ANSI escape sequences from output such as color coding
        proxy (str): If provided, may be used for proxychains wrapping.
    Returns:
        tuple: Tuple with return_code, output.
    """
    logger.info(cmd)
    logger.warning(activity_id)

    conf_path = None
    if proxy:
        proxy_manager = ProxychainsWrapper()
        if proxy_manager.should_wrap():
            cmd, conf_path = proxy_manager.wrap_command(cmd, proxy=proxy)

    # Create a command record in the database
    command_obj = Command.objects.create(
        command=sanitize_command_for_db(cmd),
        time=timezone.now(),
        scan_history_id=scan_id,
        activity_id=activity_id)

    # Run the command using subprocess
    try:
        popen = subprocess.Popen(
            cmd if shell else cmd.split(),
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            universal_newlines=True)
        output = ''
        for stdout_line in iter(popen.stdout.readline, ""):
            item = stdout_line.strip()
            output += '\n' + item
            logger.debug(item)
        popen.stdout.close()
        try:
            popen.wait(timeout=30)
        except subprocess.TimeoutExpired:
            popen.kill()
            return_code = 124 # Timeout
            output += "\nCommand timed out after 30 seconds."
        else:
            return_code = popen.returncode
    except Exception as e:
        logger.error(f"Error executing command {cmd}: {str(e)}")
        output = f"Error executing command: {str(e)}"
        return_code = 127 # Command not found / error
    finally:
        if conf_path and os.path.exists(conf_path):
            os.remove(conf_path)

    command_obj.output = output
    command_obj.return_code = return_code
    command_obj.save()

    if history_file:
        mode = 'a'
        if not os.path.exists(history_file):
            mode = 'w'
        with open(history_file, mode) as f:
            f.write(f'\n{cmd}\n{return_code}\n{output}\n------------------\n')
            
    if remove_ansi_sequence:
        output = remove_ansi_escape_sequences(output)
        
    return return_code, output

def save_email(email_address, scan_history=None):
    if not validators.email(email_address):
        logger.info(f'Email {email_address} is invalid. Skipping.')
        return None, False
    email, created = Email.objects.get_or_create(address=email_address)

    # Add email to ScanHistory
    if scan_history:
        scan_history.emails.add(email)
        scan_history.save()

    return email, created

def save_employee(name, designation='', scan_history=None):
    employee, created = Employee.objects.get_or_create(
        name=name,
        designation=designation)

    # Add employee to ScanHistory
    if scan_history:
        scan_history.employees.add(employee)
        scan_history.save()

    return employee, created
