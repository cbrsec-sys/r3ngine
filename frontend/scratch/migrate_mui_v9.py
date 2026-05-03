import os
import re

def migrate_mui(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Grid item migration
    content = re.sub(r'Grid\s+item\s+xs={(\d+)}\s+md={(\d+)}', r'Grid size={{ xs: \1, md: \2 }}', content)
    content = re.sub(r'Grid\s+item\s+xs={([\d.]+)}\s+md={([\d.]+)}', r'Grid size={{ xs: \1, md: \2 }}', content)
    content = re.sub(r'Grid\s+item\s+xs={([\d.]+)}', r'Grid size={{ xs: \1 }}', content)
    content = re.sub(r'Grid\s+item\s+md={([\d.]+)}', r'Grid size={{ md: \1 }}', content)
    content = re.sub(r'Grid\s+item\s+key={([^}]+)}', r'Grid size="grow" key={\1}', content)
    content = re.sub(r'Grid\s+item', r'Grid size="grow"', content)
    
    # InputLabelProps migration
    content = re.sub(r'InputLabelProps={{([^}]+)}}', r'slotProps={{ label: {\1} }}', content)
    
    # paperprops migration
    content = re.sub(r'paperprops={{([^}]+)}}', r'slotProps={{ paper: {\1} }}', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

files = [
    r'd:\Repos\r3ngine\frontend\src\features\scans\components\ScanDetailPage.tsx',
    r'd:\Repos\r3ngine\frontend\src\features\settings\components\ReportSettingsPage.tsx',
    r'd:\Repos\r3ngine\frontend\src\features\settings\components\ReNgineSettingsPage.tsx',
    r'd:\Repos\r3ngine\frontend\src\features\settings\components\ProfileSettingsPage.tsx',
    r'd:\Repos\r3ngine\frontend\src\features\settings\components\OpSecSettingsPage.tsx',
    r'd:\Repos\r3ngine\frontend\src\features\settings\components\NotificationSettingsPage.tsx',
    r'd:\Repos\r3ngine\frontend\src\features\settings\components\LlmToolkitPage.tsx',
    r'd:\Repos\r3ngine\frontend\src\features\settings\components\ApiVaultPage.tsx',
    r'd:\Repos\r3ngine\frontend\src\features\scans\components\StartScanModal.tsx',
    r'd:\Repos\r3ngine\frontend\src\features\monitoring\components\MonitoringStats.tsx',
    r'd:\Repos\r3ngine\frontend\src\features\organizations\components\CreateOrganizationModal.tsx'
]

for file in files:
    migrate_mui(file)
