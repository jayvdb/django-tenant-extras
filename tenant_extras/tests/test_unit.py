import sys
import mock
import json

from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.db import connection
from django.test.utils import override_settings

from ..middleware import LocaleRedirectMiddleware, TenantLocaleMiddleware

@override_settings(MULTI_TENANT_DIR='/clients', INSTALLED_APPS=(), LOCALE_PATHS=())
class TenantLocaleMiddlewareTests(TestCase):
    def setUp(self):
        super(TenantLocaleMiddlewareTests, self).setUp()

        self.rf = RequestFactory()
        self.middleware = TenantLocaleMiddleware()

    def test_valid_tenant_locale(self):
        with mock.patch("tenant_extras.middleware.connection") as mock_c, \
             mock.patch("tenant_extras.middleware._translation") as mock_t, \
             mock.patch("os.path.isdir", return_value=True):

            mock_c.tenant = mock.Mock(client_name="tenant_a")
            request = self.rf.get('/nl/')
            result = self.middleware.process_request(request)

            last_call_path = mock_t.call_args_list[-1][0][0]
            self.assertEquals(last_call_path, '/clients/tenant_a/locale')

            mock_c.tenant = mock.Mock(client_name="tenant_b")
            request = self.rf.get('/nl/')
            result = self.middleware.process_request(request)

            last_call_path = mock_t.call_args_list[-1][0][0]
            self.assertEquals(last_call_path, '/clients/tenant_b/locale')

                    
class LocaleRedirectMiddlewareTests(TestCase):

    def setUp(self):
        self.rf = RequestFactory()
        self.middleware = LocaleRedirectMiddleware()

    def test_slash_with_anon_user(self):
        request = self.rf.get('/')
        result = self.middleware.process_request(request)

        self.assertEqual(result.url, '/en/')

    def test_nl_with_anon_user(self):
        request = self.rf.get('/nl/')
        result = self.middleware.process_request(request)

        self.assertIsNone(result, 'Should not alter the request if language set in url')

    def test_cookie_with_anon_user(self):
        request = self.rf.get('/en/')
        request.COOKIES['django_language'] = 'nl'
        result = self.middleware.process_request(request)

        self.assertEqual(result.url, '/nl/')

    def test_go_path_with_anon_user(self):
        request = self.rf.get('/go/projects')
        result = self.middleware.process_request(request)

        self.assertIsNone(result, 'Go paths should not redirect')

    def test_admin_path_with_anon_user(self):
        request = self.rf.get('/admin')
        result = self.middleware.process_request(request)

        self.assertEqual(result.url, '/en/admin')


class ExposedTenantPropertiesContextProcessorTestCase(TestCase):

    def setUp(self):
        self.rf = RequestFactory()

    def test_tenant_specific_property_list(self):
        with mock.patch('tenant_extras.utils.get_tenant_properties') as get_tenant_properties:
            from ..context_processors import exposed_tenant_properties

            get_tenant_properties().EXPOSED_TENANT_PROPERTIES = ['test']
            get_tenant_properties().TEST = 'value-for-test'

            context = exposed_tenant_properties(self.rf)
            self.assertEqual(context['TEST'], 'value-for-test')
            self.assertEqual(context['settings'], json.dumps({'TEST': 'value-for-test'}))

    def test_default_settings_property_list(self):
        with mock.patch('django.conf.settings') as settings:
            from ..context_processors import exposed_tenant_properties

            settings.EXPOSED_TENANT_PROPERTIES = ['test']
            settings.TEST = 'value-for-test'

            context = exposed_tenant_properties(self.rf)
            self.assertEqual(context['TEST'], 'value-for-test')
            self.assertEqual(context['settings'], json.dumps({'TEST': 'value-for-test'}))
    
    def test_no_exposed_tenant_properties_setting(self):
        with mock.patch('tenant_extras.utils.get_tenant_properties') as get_tenant_properties, \
                mock.patch('django.conf.settings', spec={}) as settings:
            
            from ..context_processors import exposed_tenant_properties
            
            get_tenant_properties.return_value = {}

            context = exposed_tenant_properties(self.rf)
            self.assertEqual(context, {})



