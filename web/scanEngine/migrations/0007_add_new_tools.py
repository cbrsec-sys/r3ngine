from django.db import migrations

def add_new_tools(apps, schema_editor):
    InstalledExternalTool = apps.get_model('scanEngine', 'InstalledExternalTool')
    
    tools = [
        {
            'name': 'baddns',
            'description': 'Subdomain takeover detection tool.',
            'github_url': 'https://github.com/projectdiscovery/baddns',
            'install_command': 'go install github.com/projectdiscovery/baddns/cmd/baddns@latest',
            'is_default': True,
            'is_subdomain_gathering': True,
            'subdomain_gathering_command': 'baddns -d {domain}',
        },
        {
            'name': 'gosearch',
            'description': 'A tool to search for usernames across social networks.',
            'github_url': 'https://github.com/prov3rbs/gosearch',
            'install_command': 'go install github.com/prov3rbs/gosearch/cmd/gosearch@latest',
            'is_default': True,
        },
        {
            'name': 'betterleaks',
            'description': 'A tool for finding secrets like passwords and API keys.',
            'github_url': 'https://github.com/betterleaks/betterleaks',
            'install_command': 'git clone https://github.com/betterleaks/betterleaks && cd betterleaks && make build',
            'is_default': True,
            'is_github_cloned': True,
            'github_clone_path': '/usr/src/github/betterleaks',
        },
        {
            'name': 'username-anarchy',
            'description': 'Username tools for penetration testing.',
            'github_url': 'https://github.com/urbanadventurer/username-anarchy',
            'install_command': 'git clone https://github.com/urbanadventurer/username-anarchy',
            'is_default': True,
            'is_github_cloned': True,
            'github_clone_path': '/usr/src/github/username-anarchy',
        }
    ]
    
    for tool_data in tools:
        InstalledExternalTool.objects.get_or_create(name=tool_data['name'], defaults=tool_data)

def remove_new_tools(apps, schema_editor):
    InstalledExternalTool = apps.get_model('scanEngine', 'InstalledExternalTool')
    tool_names = ['baddns', 'gosearch', 'betterleaks', 'username-anarchy']
    InstalledExternalTool.objects.filter(name__in=tool_names).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('scanEngine', '0006_proxy_use_proxychains'),
    ]

    operations = [
        migrations.RunPython(add_new_tools, remove_new_tools),
    ]
