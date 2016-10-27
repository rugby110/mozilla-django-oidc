try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

from django.core.urlresolvers import reverse
from django.contrib import auth
from django.http import HttpResponseRedirect
from django.views.generic import View

from mozilla_django_oidc.utils import import_from_settings


class OIDCAuthorizationCallbackView(View):
    """OIDC client authentication callback HTTP endpoint"""

    http_method_names = ['post']

    @property
    def failure_url(self):
        return import_from_settings('LOGIN_REDIRECT_URL_FAILURE', '/')

    @property
    def success_url(self):
        return import_from_settings('LOGIN_REDIRECT_URL', '/')

    def login_failure(self):
        return HttpResponseRedirect(self.failure_url)

    def login_success(self):
        auth.login(self.request, self.user)
        return HttpResponseRedirect(self.success_url)

    def post(self, request):
        """Callback handler for OIDC authorization code flow"""

        if 'code' in request.POST and 'state' in request.POST:
            kwargs = {
                'code': request.POST['code'],
                'state': request.POST['state']
            }
            self.user = auth.authenticate(**kwargs)

            if self.user and self.user.is_active:
                return self.login_success()
        return self.login_failure()


class OIDCAuthorizationRequestView(View):
    """OIDC client authentication HTTP endpoint"""

    http_method_names = ['get']

    def __init__(self, *args, **kwargs):
        super(OIDCAuthorizationRequestView, self).__init__(*args, **kwargs)

        self.OIDC_OP_AUTH_ENDPOINT = import_from_settings('OIDC_OP_AUTHORIZATION_ENDPOINT')
        self.OIDC_OP_CLIENT_ID = import_from_settings('OIDC_OP_CLIENT_ID')

    def get(self, request):
        """OIDC client authentication initialization HTTP endpoint"""
        params = {
            'response_type': 'code',
            'scope': 'openid',
            'client_id': self.OIDC_OP_CLIENT_ID,
            'redirect_uri': reverse('oidc_authorization_callback')
        }

        query = urlencode(params)
        redirect_url = '{url}?{query}'.format(url=self.OIDC_OP_AUTH_ENDPOINT, query=query)
        return HttpResponseRedirect(redirect_url)