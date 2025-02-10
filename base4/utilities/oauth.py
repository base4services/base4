import os
from secrets import token_urlsafe

from base4.utilities import base_dotenv
base_dotenv.load_dotenv()

from authlib.integrations.starlette_client import OAuth
from fastapi.requests import Request


oauth = OAuth()

# https://developers.google.com/identity/gsi/web/tools/configurator
# https://console.cloud.google.com/apis/credentials?inv=1&invt=AblEBQ&project=restful-api-162612
oauth.register(
    name='google',
    client_id=os.getenv('OAUTH_GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('OAUTH_GOOGLE_CLIENT_SECRET'),
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
    client_id=os.getenv('OAUTH_FACEBOOK_CLIENT_ID'),
    client_secret=os.getenv('OAUTH_FACEBOOK_CLIENT_SECRET'),
    access_token_url='https://graph.facebook.com/oauth/access_token',
    access_token_params=None,
    authorize_url='https://www.facebook.com/dialog/oauth',
    client_kwargs={'scope': 'email'},
)

oauth.register(
    name='github',
    client_id=os.getenv('OAUTH_GITHUB_CLIENT_ID'),
    client_secret=os.getenv('OAUTH_GITHUB_CLIENT_SECRET'),
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    client_kwargs={'scope': 'user:email'},
)

oauth.register(
    name='apple',
    client_id=os.getenv('OAUTH_APPLE_CLIENT_ID'),
    client_secret=os.getenv('OAUTH_APPLE_CLIENT_SECRET'),
)

oauth.register(
    name='microsoft',
    client_id=os.getenv('OAUTH_MICROSOFT_CLIENT_ID'),
    client_secret=os.getenv('OAUTH_MICROSOFT_CLIENT_SECRET'),
)

async def oauth_login(request: Request, provider_name: str):
    client = oauth.create_client(provider_name)
    if provider_name not in ['google', 'facebook', 'github']:
        raise ValueError("Nepoznat OAuth provider")

    redirect_uri =  f'{request.base_url}api/tenants/oauth/users/{provider_name}/callback'
    if provider_name == 'google':
        nonce_value = token_urlsafe(16)
        request.session["nonce"] = nonce_value
        return await client.authorize_redirect(request, redirect_uri, nonce=nonce_value)
    return await client.authorize_redirect(request, redirect_uri)



async def oauth_callback(request: Request, provider_name: str):

    client = oauth.create_client(provider_name)
    token = await client.authorize_access_token(request)

    if provider_name == 'google':
        stored_nonce = request.session.get("nonce")
        user_info = await client.parse_id_token(token, nonce=stored_nonce)
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
