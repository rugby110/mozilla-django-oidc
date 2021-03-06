try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

from django.core.exceptions import SuspiciousOperation
from django.core.urlresolvers import reverse
from django.contrib import auth
from django.http import HttpResponseRedirect
from django.utils.crypto import get_random_string
from django.views.generic import View

from mozilla_django_oidc.utils import absolutify, import_from_settings


class OIDCAuthenticationCallbackView(View):
    """OIDC client authentication callback HTTP endpoint"""

    http_method_names = ['get']

    @property
    def failure_url(self):
        return import_from_settings('LOGIN_REDIRECT_URL_FAILURE', '/')

    @property
    def success_url(self):
        next_url = self.request.session.get('oidc_login_next', None)
        return next_url or import_from_settings('LOGIN_REDIRECT_URL', '/')

    def login_failure(self):
        return HttpResponseRedirect(self.failure_url)

    def login_success(self):
        auth.login(self.request, self.user)
        return HttpResponseRedirect(self.success_url)

    def get(self, request):
        """Callback handler for OIDC authorization code flow"""

        nonce = request.session.get('oidc_nonce')
        if nonce:
            # Make sure that nonce is not used twice
            del request.session['oidc_nonce']

        if 'code' in request.GET and 'state' in request.GET:
            kwargs = {
                'code': request.GET['code'],
                'state': request.GET['state'],
                'nonce': nonce
            }

            if 'oidc_state' not in request.session:
                return self.login_failure()

            if request.GET['state'] != request.session['oidc_state']:
                msg = 'Session `oidc_state` does not match the OIDC callback state'
                raise SuspiciousOperation(msg)

            self.user = auth.authenticate(**kwargs)

            if self.user and self.user.is_active:
                return self.login_success()
        return self.login_failure()


class OIDCAuthenticationRequestView(View):
    """OIDC client authentication HTTP endpoint"""

    http_method_names = ['get']

    def __init__(self, *args, **kwargs):
        super(OIDCAuthenticationRequestView, self).__init__(*args, **kwargs)

        self.OIDC_OP_AUTH_ENDPOINT = import_from_settings('OIDC_OP_AUTHORIZATION_ENDPOINT')
        self.OIDC_RP_CLIENT_ID = import_from_settings('OIDC_RP_CLIENT_ID')

    def get(self, request):
        """OIDC client authentication initialization HTTP endpoint"""
        state = get_random_string(import_from_settings('OIDC_STATE_SIZE', 32))
        redirect_field_name = import_from_settings('OIDC_REDIRECT_FIELD_NAME', 'next')

        params = {
            'response_type': 'code',
            'scope': 'openid',
            'client_id': self.OIDC_RP_CLIENT_ID,
            'redirect_uri': absolutify(reverse('oidc_authentication_callback')),
            'state': state,
        }

        if import_from_settings('OIDC_USE_NONCE', True):
            nonce = get_random_string(import_from_settings('OIDC_NONCE_SIZE', 32))
            params.update({
                'nonce': nonce
            })
            request.session['oidc_nonce'] = nonce

        request.session['oidc_state'] = state
        request.session['oidc_login_next'] = request.GET.get(redirect_field_name)

        query = urlencode(params)
        redirect_url = '{url}?{query}'.format(url=self.OIDC_OP_AUTH_ENDPOINT, query=query)
        return HttpResponseRedirect(redirect_url)


class OIDCLogoutView(View):
    """Logout helper view"""

    http_method_names = ['get']

    @property
    def redirect_url(self):
        """Return the logout url defined in settings."""
        return import_from_settings('LOGOUT_REDIRECT_URL', '/')

    def get(self, request):
        """Log the user out"""
        auth.logout(request)
        return HttpResponseRedirect(self.redirect_url)
