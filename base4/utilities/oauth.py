# auth/oauth.py
from secrets import token_urlsafe

from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request

from auth.config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    FACEBOOK_CLIENT_ID,
    FACEBOOK_CLIENT_SECRET,
    GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET,
)

# MS, APPLE, GITHUB , FB
oauth = OAuth()

# https://developers.google.com/identity/gsi/web/tools/configurator
# https://console.cloud.google.com/apis/credentials?inv=1&invt=AblEBQ&project=restful-api-162612
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    client_kwargs={
        'scope': 'openid email profile',
    },
)

# https://developers.facebook.com/apps/
# https://developers.facebook.com/tools/explorer/1155968609426519/\
# https://developers.facebook.com/apps/1155968609426519/settings/advanced/
oauth.register(
    name='facebook',
    client_id=FACEBOOK_CLIENT_ID,
    client_secret=FACEBOOK_CLIENT_SECRET,
    access_token_url='https://graph.facebook.com/oauth/access_token',
    access_token_params=None,
    authorize_url='https://www.facebook.com/dialog/oauth',
    client_kwargs={'scope': 'email'},
)

oauth.register(
    name='github',
    client_id=GITHUB_CLIENT_ID,
    client_secret=GITHUB_CLIENT_SECRET,
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    client_kwargs={'scope': 'user:email'},
)

async def oauth_login(request: Request, provider_name: str):
    client = oauth.create_client(provider_name)
    if provider_name not in ['google', 'facebook', 'github']:
        raise ValueError("Nepoznat OAuth provider")

    redirect_uri = request.url_for('auth_callback', provider_name=provider_name)
    if provider_name == 'google':
        nonce_value = token_urlsafe(16)
        request.session["nonce"] = nonce_value
        return await client.authorize_redirect(request, redirect_uri, nonce=nonce_value)
    return await client.authorize_redirect(request, redirect_uri)



async def oauth_callback(request: Request, provider_name: str):

    client = oauth.create_client(provider_name)
    token = await client.authorize_access_token(request)

    print(request.session.get('nonce'))
    if provider_name == 'google':
        stored_nonce = request.session.get("nonce")
        user_info = await client.parse_id_token(token, nonce=stored_nonce)
        ...
    else:
        # ostali provider-i (Facebook, GitHub) imaju drugacije rute za user_info
        if provider_name == 'facebook':
            resp = await client.get('https://graph.facebook.com/me?fields=id,name,email', token=token)
            user_info = resp.json()
        elif provider_name == 'github':
            resp = await client.get('user', token=token)
            user_info = resp.json()
        else:
            user_info = {}

    # Ovde biste obradili user_info, upisali/azurirali korisnika u bazi itd.
    # i generisali sopstveni token (JWT) za dalju komunikaciju

    return user_info
