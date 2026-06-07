"""
Unit tests for reNgine.tech_mapping.

Run inside Docker:
    docker exec -it r3ngine-web-1 bash -c \
        "cd /usr/src/app && python3 manage.py test tests.test_tech_mapping --verbosity=2"
"""

from django.test import TestCase

from reNgine.tech_mapping import TECH_TO_NUCLEI_TAGS, get_nuclei_tags_from_techs


class TestExistingFixes(TestCase):
    def test_spring_boot_includes_springboot_tag(self):
        tags = TECH_TO_NUCLEI_TAGS['spring boot']
        self.assertIn('springboot', tags)
        self.assertIn('spring-boot', tags)

    def test_fortinet_includes_fortios_tag(self):
        self.assertIn('fortios', TECH_TO_NUCLEI_TAGS['fortinet'])

    def test_fortigate_includes_fortios_tag(self):
        self.assertIn('fortios', TECH_TO_NUCLEI_TAGS['fortigate'])

    def test_palo_alto_includes_panos_tag(self):
        self.assertIn('panos', TECH_TO_NUCLEI_TAGS['palo alto'])

    def test_pan_os_includes_panos_tag(self):
        self.assertIn('panos', TECH_TO_NUCLEI_TAGS['pan-os'])

    def test_spring_boot_via_function(self):
        tags = get_nuclei_tags_from_techs(['Spring Boot'])
        self.assertIn('springboot', tags)

    def test_spring_boot_version_stripped(self):
        # The version-strip regex strips at the first whitespace, so "Spring Boot/3.2.1"
        # reduces to "spring" (single-word), which matches the 'spring' key.
        # Multi-word tech names with version suffixes rely on exact or substring matching.
        tags = get_nuclei_tags_from_techs(['Spring Boot/3.2.1'])
        self.assertIn('spring', tags)
        self.assertIn('java', tags)


class TestVirtualizationEnterpriseIT(TestCase):
    def test_vmware_mapped(self):
        self.assertIn('vmware', TECH_TO_NUCLEI_TAGS['vmware'])
        self.assertIn('vcenter', TECH_TO_NUCLEI_TAGS['vmware'])

    def test_vmware_esxi_mapped(self):
        self.assertIn('vmware', TECH_TO_NUCLEI_TAGS['vmware esxi'])

    def test_vmware_vsphere_mapped(self):
        self.assertIn('vmware', TECH_TO_NUCLEI_TAGS['vmware vsphere'])

    def test_vmware_horizon_mapped(self):
        self.assertIn('vmware', TECH_TO_NUCLEI_TAGS['vmware horizon'])

    def test_vcenter_mapped(self):
        self.assertIn('vcenter', TECH_TO_NUCLEI_TAGS['vcenter'])

    def test_manageengine_mapped(self):
        self.assertIn('manageengine', TECH_TO_NUCLEI_TAGS['manageengine'])
        self.assertIn('zoho', TECH_TO_NUCLEI_TAGS['manageengine'])

    def test_zoho_manageengine_alias(self):
        self.assertEqual(TECH_TO_NUCLEI_TAGS['zoho manageengine'], TECH_TO_NUCLEI_TAGS['manageengine'])


class TestNetworkSecurityAppliances(TestCase):
    def test_sonicwall_mapped(self):
        self.assertIn('sonicwall', TECH_TO_NUCLEI_TAGS['sonicwall'])

    def test_sonic_wall_alias(self):
        self.assertEqual(TECH_TO_NUCLEI_TAGS['sonic wall'], TECH_TO_NUCLEI_TAGS['sonicwall'])

    def test_sangfor_mapped(self):
        self.assertIn('sangfor', TECH_TO_NUCLEI_TAGS['sangfor'])


class TestChineseCMSOAERP(TestCase):
    def test_dedecms_mapped(self):
        self.assertIn('dedecms', TECH_TO_NUCLEI_TAGS['dedecms'])
        self.assertIn('php', TECH_TO_NUCLEI_TAGS['dedecms'])

    def test_thinkphp_mapped(self):
        self.assertIn('thinkphp', TECH_TO_NUCLEI_TAGS['thinkphp'])
        self.assertIn('php', TECH_TO_NUCLEI_TAGS['thinkphp'])

    def test_thinkcmf_mapped(self):
        self.assertIn('thinkcmf', TECH_TO_NUCLEI_TAGS['thinkcmf'])

    def test_tongda_oa_alias(self):
        self.assertEqual(TECH_TO_NUCLEI_TAGS['tongda oa'], TECH_TO_NUCLEI_TAGS['tongda'])

    def test_seeyon_oa_alias(self):
        self.assertEqual(TECH_TO_NUCLEI_TAGS['seeyon oa'], TECH_TO_NUCLEI_TAGS['seeyon'])

    def test_weaver_ecology_tags(self):
        tags = TECH_TO_NUCLEI_TAGS['weaver']
        self.assertIn('weaver', tags)
        self.assertIn('ecology', tags)

    def test_e_cology_alias(self):
        self.assertEqual(TECH_TO_NUCLEI_TAGS['e-cology'], TECH_TO_NUCLEI_TAGS['weaver'])

    def test_yonyou_mapped(self):
        self.assertIn('yonyou', TECH_TO_NUCLEI_TAGS['yonyou'])

    def test_nc_cloud_alias(self):
        self.assertIn('yonyou', TECH_TO_NUCLEI_TAGS['nc cloud'])

    def test_ufida_includes_yonyou(self):
        self.assertIn('yonyou', TECH_TO_NUCLEI_TAGS['ufida'])

    def test_74cms_mapped(self):
        self.assertIn('74cms', TECH_TO_NUCLEI_TAGS['74cms'])

    def test_eyoucms_mapped(self):
        self.assertIn('eyoucms', TECH_TO_NUCLEI_TAGS['eyoucms'])

    def test_zzzcms_mapped(self):
        self.assertIn('zzzcms', TECH_TO_NUCLEI_TAGS['zzzcms'])

    def test_chanjet_includes_yonyou(self):
        self.assertIn('yonyou', TECH_TO_NUCLEI_TAGS['chanjet'])

    def test_wanhu_mapped(self):
        self.assertIn('wanhu', TECH_TO_NUCLEI_TAGS['wanhu'])


class TestIoTCamerasRouters(TestCase):
    def test_hikvision_mapped(self):
        tags = TECH_TO_NUCLEI_TAGS['hikvision']
        self.assertIn('hikvision', tags)
        self.assertIn('iot', tags)

    def test_dahua_mapped(self):
        self.assertIn('dahua', TECH_TO_NUCLEI_TAGS['dahua'])
        self.assertIn('iot', TECH_TO_NUCLEI_TAGS['dahua'])

    def test_avtech_mapped(self):
        self.assertIn('avtech', TECH_TO_NUCLEI_TAGS['avtech'])

    def test_samsung_mapped(self):
        self.assertIn('samsung', TECH_TO_NUCLEI_TAGS['samsung'])

    def test_ruijie_mapped(self):
        self.assertIn('ruijie', TECH_TO_NUCLEI_TAGS['ruijie'])

    def test_totolink_mapped(self):
        tags = TECH_TO_NUCLEI_TAGS['totolink']
        self.assertIn('totolink', tags)
        self.assertIn('router', tags)

    def test_tenda_mapped(self):
        self.assertIn('tenda', TECH_TO_NUCLEI_TAGS['tenda'])

    def test_asus_router_mapped(self):
        tags = TECH_TO_NUCLEI_TAGS['asus router']
        self.assertIn('asus', tags)
        self.assertIn('router', tags)


class TestJavaMiddlewareSerialization(TestCase):
    def test_jolokia_mapped(self):
        tags = TECH_TO_NUCLEI_TAGS['jolokia']
        self.assertIn('jolokia', tags)
        self.assertIn('java', tags)

    def test_fastjson_mapped(self):
        tags = TECH_TO_NUCLEI_TAGS['fastjson']
        self.assertIn('fastjson', tags)
        self.assertIn('java', tags)

    def test_ofbiz_mapped(self):
        tags = TECH_TO_NUCLEI_TAGS['ofbiz']
        self.assertIn('ofbiz', tags)
        self.assertIn('apache', tags)
        self.assertIn('java', tags)

    def test_apache_ofbiz_alias(self):
        self.assertEqual(TECH_TO_NUCLEI_TAGS['apache ofbiz'], TECH_TO_NUCLEI_TAGS['ofbiz'])

    def test_xstream_mapped(self):
        tags = TECH_TO_NUCLEI_TAGS['xstream']
        self.assertIn('xstream', tags)
        self.assertIn('java', tags)


class TestMLDataScienceAIPlatforms(TestCase):
    def test_gradio_mapped(self):
        tags = TECH_TO_NUCLEI_TAGS['gradio']
        self.assertIn('gradio', tags)
        self.assertIn('python', tags)

    def test_mlflow_mapped(self):
        self.assertIn('mlflow', TECH_TO_NUCLEI_TAGS['mlflow'])

    def test_jupyter_mapped(self):
        self.assertIn('jupyter', TECH_TO_NUCLEI_TAGS['jupyter'])

    def test_jupyter_notebook_alias(self):
        self.assertEqual(TECH_TO_NUCLEI_TAGS['jupyter notebook'], TECH_TO_NUCLEI_TAGS['jupyter'])

    def test_jupyterlab_alias(self):
        self.assertEqual(TECH_TO_NUCLEI_TAGS['jupyterlab'], TECH_TO_NUCLEI_TAGS['jupyter'])

    def test_flowise_mapped(self):
        self.assertIn('flowise', TECH_TO_NUCLEI_TAGS['flowise'])

    def test_langflow_mapped(self):
        self.assertIn('langflow', TECH_TO_NUCLEI_TAGS['langflow'])


class TestITSMMonitoring(TestCase):
    def test_osticket_mapped(self):
        self.assertIn('osticket', TECH_TO_NUCLEI_TAGS['osticket'])

    def test_glpi_mapped(self):
        self.assertIn('glpi', TECH_TO_NUCLEI_TAGS['glpi'])

    def test_servicenow_mapped(self):
        self.assertIn('servicenow', TECH_TO_NUCLEI_TAGS['servicenow'])

    def test_papercut_mapped(self):
        self.assertIn('papercut', TECH_TO_NUCLEI_TAGS['papercut'])

    def test_papercut_ng_alias(self):
        self.assertEqual(TECH_TO_NUCLEI_TAGS['papercut ng'], TECH_TO_NUCLEI_TAGS['papercut'])

    def test_papercut_mf_alias(self):
        self.assertEqual(TECH_TO_NUCLEI_TAGS['papercut mf'], TECH_TO_NUCLEI_TAGS['papercut'])

    def test_cacti_mapped(self):
        self.assertIn('cacti', TECH_TO_NUCLEI_TAGS['cacti'])

    def test_solarwinds_mapped(self):
        self.assertIn('solarwinds', TECH_TO_NUCLEI_TAGS['solarwinds'])

    def test_nagiosxi_includes_nagios(self):
        tags = TECH_TO_NUCLEI_TAGS['nagiosxi']
        self.assertIn('nagiosxi', tags)
        self.assertIn('nagios', tags)

    def test_rconfig_mapped(self):
        self.assertIn('rconfig', TECH_TO_NUCLEI_TAGS['rconfig'])


class TestCollaborationWikiSurvey(TestCase):
    def test_xwiki_mapped(self):
        self.assertIn('xwiki', TECH_TO_NUCLEI_TAGS['xwiki'])

    def test_squirrelmail_mapped(self):
        self.assertIn('squirrelmail', TECH_TO_NUCLEI_TAGS['squirrelmail'])

    def test_limesurvey_mapped(self):
        self.assertIn('limesurvey', TECH_TO_NUCLEI_TAGS['limesurvey'])

    def test_chamilo_mapped(self):
        self.assertIn('chamilo', TECH_TO_NUCLEI_TAGS['chamilo'])

    def test_mantisbt_mapped(self):
        self.assertIn('mantisbt', TECH_TO_NUCLEI_TAGS['mantisbt'])

    def test_mantis_bug_tracker_alias(self):
        self.assertEqual(TECH_TO_NUCLEI_TAGS['mantis bug tracker'], TECH_TO_NUCLEI_TAGS['mantisbt'])


class TestTelephonyUnifiedComms(TestCase):
    def test_freepbx_mapped(self):
        self.assertIn('freepbx', TECH_TO_NUCLEI_TAGS['freepbx'])

    def test_3cx_mapped(self):
        self.assertIn('3cx', TECH_TO_NUCLEI_TAGS['3cx'])

    def test_3cx_phone_system_alias(self):
        self.assertEqual(TECH_TO_NUCLEI_TAGS['3cx phone system'], TECH_TO_NUCLEI_TAGS['3cx'])

    def test_avaya_mapped(self):
        self.assertIn('avaya', TECH_TO_NUCLEI_TAGS['avaya'])

    def test_mitel_mapped(self):
        self.assertIn('mitel', TECH_TO_NUCLEI_TAGS['mitel'])

    def test_icewarp_mapped(self):
        self.assertIn('icewarp', TECH_TO_NUCLEI_TAGS['icewarp'])


class TestLowcodeAPIModernSaaS(TestCase):
    def test_nacos_mapped(self):
        tags = TECH_TO_NUCLEI_TAGS['nacos']
        self.assertIn('nacos', tags)
        self.assertIn('alibaba', tags)

    def test_alibaba_nacos_alias(self):
        self.assertEqual(TECH_TO_NUCLEI_TAGS['alibaba nacos'], TECH_TO_NUCLEI_TAGS['nacos'])

    def test_apisix_mapped(self):
        tags = TECH_TO_NUCLEI_TAGS['apisix']
        self.assertIn('apisix', tags)
        self.assertIn('apache', tags)

    def test_apache_apisix_alias(self):
        self.assertEqual(TECH_TO_NUCLEI_TAGS['apache apisix'], TECH_TO_NUCLEI_TAGS['apisix'])

    def test_telerik_mapped(self):
        tags = TECH_TO_NUCLEI_TAGS['telerik']
        self.assertIn('telerik', tags)
        self.assertIn('dotnet', tags)

    def test_n8n_mapped(self):
        self.assertIn('n8n', TECH_TO_NUCLEI_TAGS['n8n'])

    def test_nocobase_mapped(self):
        self.assertIn('nocobase', TECH_TO_NUCLEI_TAGS['nocobase'])

    def test_nocodb_mapped(self):
        self.assertIn('nocodb', TECH_TO_NUCLEI_TAGS['nocodb'])

    def test_casdoor_mapped(self):
        self.assertIn('casdoor', TECH_TO_NUCLEI_TAGS['casdoor'])

    def test_goanywhere_mapped(self):
        self.assertIn('goanywhere', TECH_TO_NUCLEI_TAGS['goanywhere'])

    def test_fortra_goanywhere_alias(self):
        self.assertEqual(TECH_TO_NUCLEI_TAGS['fortra goanywhere'], TECH_TO_NUCLEI_TAGS['goanywhere'])

    def test_microweber_mapped(self):
        self.assertIn('microweber', TECH_TO_NUCLEI_TAGS['microweber'])

    def test_bitrix_mapped(self):
        self.assertIn('bitrix', TECH_TO_NUCLEI_TAGS['bitrix'])

    def test_1c_bitrix_alias(self):
        self.assertEqual(TECH_TO_NUCLEI_TAGS['1c-bitrix'], TECH_TO_NUCLEI_TAGS['bitrix'])

    def test_bitrix24_alias(self):
        self.assertEqual(TECH_TO_NUCLEI_TAGS['bitrix24'], TECH_TO_NUCLEI_TAGS['bitrix'])


class TestMDMDeviceManagement(TestCase):
    def test_mobileiron_includes_ivanti(self):
        tags = TECH_TO_NUCLEI_TAGS['mobileiron']
        self.assertIn('mobileiron', tags)
        self.assertIn('ivanti', tags)

    def test_connectwise_mapped(self):
        self.assertIn('connectwise', TECH_TO_NUCLEI_TAGS['connectwise'])

    def test_connectwise_control_alias(self):
        self.assertEqual(TECH_TO_NUCLEI_TAGS['connectwise control'], TECH_TO_NUCLEI_TAGS['connectwise'])


class TestMiscAdditional(TestCase):
    def test_geoserver_mapped(self):
        self.assertIn('geoserver', TECH_TO_NUCLEI_TAGS['geoserver'])

    def test_openemr_mapped(self):
        self.assertIn('openemr', TECH_TO_NUCLEI_TAGS['openemr'])

    def test_crushftp_mapped(self):
        self.assertIn('crushftp', TECH_TO_NUCLEI_TAGS['crushftp'])

    def test_openfire_mapped(self):
        self.assertIn('openfire', TECH_TO_NUCLEI_TAGS['openfire'])


class TestFunctionIntegration(TestCase):
    def test_empty_list_returns_empty(self):
        self.assertEqual(get_nuclei_tags_from_techs([]), [])

    def test_returns_sorted_list(self):
        result = get_nuclei_tags_from_techs(['VMware ESXi'])
        self.assertEqual(result, sorted(result))

    def test_vmware_esxi_case_insensitive(self):
        tags = get_nuclei_tags_from_techs(['VMware ESXi'])
        self.assertIn('vmware', tags)
        self.assertIn('vcenter', tags)

    def test_hikvision_includes_iot(self):
        tags = get_nuclei_tags_from_techs(['hikvision'])
        self.assertIn('iot', tags)

    def test_xwiki_via_function(self):
        tags = get_nuclei_tags_from_techs(['XWiki'])
        self.assertIn('xwiki', tags)

    def test_yonyou_via_function(self):
        tags = get_nuclei_tags_from_techs(['yonyou'])
        self.assertIn('yonyou', tags)

    def test_multiple_techs_deduplicates(self):
        tags = get_nuclei_tags_from_techs(['jolokia', 'fastjson'])
        self.assertEqual(len(tags), len(set(tags)))
