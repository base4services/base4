import asyncio
import os
import pprint
import sys
from typing import Literal, Optional

import dotenv
import httpx
import ujson as json

# .


def prepare(url, srv):
    srv = srv.upper()

    omb_username = os.getenv(f'OMBIS_{srv}_USERNAME', None)
    omb_password = os.getenv(f'OMBIS_{srv}_PASSWORD', None)
    omb_url = os.getenv(f'OMBIS_{srv}_URL', None)
    omb_port = os.getenv(f'OMBIS_{srv}_PORT', None)
    omb_prefix = os.getenv(f'OMBIS_{srv}_PREFIX', None)

    if not all([omb_username, omb_password, omb_url, omb_port, omb_prefix]):
        sys.exit("ENV ERROR")

    omb_url = omb_url.rstrip('/')
    omb_prefix = omb_prefix.strip('/')
    url = url.strip('/')

    url = f'{omb_url}:{omb_port}/{omb_prefix}/{url}'

    if '?json' not in url and '&json' not in url:
        if '?' not in url:
            url += '?json'
        else:
            url += '&json'

    auth = httpx.DigestAuth(omb_username, omb_password)

    # print("URL", url)

    return url, auth


def fix_url(url, srv):
    for o in ('00000001', '/00000001', '/rest/web/00000001/', '/rest/web2/00000001/', '/rest/web3/00000001/'):
        if url.startswith(o):
            url = url[len(o) :]
            return url

    return url


async def send(url, body, method, return_type):
    url = fix_url(url, 'master')

    omb_prefix = os.getenv(f'OMBIS_MASTER_PREFIX', None)

    url, auth = prepare(url, 'master')

    if body and 'Fields' in body:
        for key in body['Fields']:
            for o in ('00000001', '/00000001'):
                if body['Fields'][key].startswith(o):
                    body['Fields'][key] = '/rest/web/' + o.strip('/') + body['Fields'][key][len(o) :]

            if body['Fields'][key].startswith('/rest/web'):

                for o in ('/rest/web/00000001/', '/rest/web2/00000001/', '/rest/web3/00000001/'):
                    if body['Fields'][key].startswith(o):
                        body['Fields'][key] = body['Fields'][key].replace(o, omb_prefix)
                        break

    # print("-[ go ombis ]-" + "-" * 100)

    # print("URL : ", url)
    # print("JSON: \n", json.dumps(body, indent=1, ensure_ascii=False))
    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, json=body, headers={'Content-Type': 'application/json'}, auth=auth)

    # print('response.status_code', response.status_code)
    # print("--------------" + '-' * 100)

    if return_type == 'json':

        if response.status_code in (201, 200, 204):
            return json.loads(response.text) if response.text else {}

    return response


async def put(url, body, return_type: Optional[Literal['json', 'response']] = 'json'):
    return await send(url, body, 'PUT', return_type)


async def post(url, body, return_type: Optional[Literal['json', 'response']] = 'json'):
    return await send(url, body, 'POST', return_type)


async def get(url, return_type: Optional[Literal['json', 'response']] = 'json', use_master=False):
    srv = 'master' if use_master else 'readonly'

    url = fix_url(url, srv)
    url, auth = prepare(url, srv)

    # print("-[ get ombis ]-" + "-" * 100)

    print("URL : ", url)

    timeout = httpx.Timeout(
        connect=10.0,  # Timeout for establishing a connection
        read=180.0,  # Timeout for reading a response
        write=10.0,  # Timeout for writing a request
        pool=30.0,  # Timeout for acquiring a connection from the pool
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, headers={'Content-Type': 'application/json'}, auth=auth, timeout=timeout)

    # print('response.status_code', response.status_code)
    # print("--------------" + '-' * 100)

    if return_type == 'json':
        return json.loads(response.text)

    return response


async def main():
    body = {
        "Fields": {
            "ServiceanfrageStatus": "/rest/web/00000001/serviceanfragestatus/17",
            "Bemerkungen": "",
            "SXF_BemerkungIntern": "",
            "AufgabePrioritaet": "/rest/web/00000001/aufgabeprioritaet/2",
            "Belegkreis": "/rest/web/00000001/nummerierung/291",
            "ServiceanfrageArt": "/rest/web/00000001/serviceanfrageart/26",
            "Kunde": "/rest/web/00000001/kunde/23713",
            "Beschreibung": "222",
            "Name": "b4f57d34-4838-4f97-aa25-7993f6fa7638",
        }
    }

    body = {
        "Fields": {
            "ServiceanfrageStatus": "00000001/serviceanfragestatus/17",
            "Bemerkungen": "",
            "SXF_BemerkungIntern": "",
            "AufgabePrioritaet": "00000001/aufgabeprioritaet/2",
            "Belegkreis": "00000001/nummerierung/291",
            "ServiceanfrageArt": "00000001/serviceanfrageart/26",
            "Kunde": "00000001/kunde/23713",
            "Beschreibung": "222",
            "Name": "b4f57d34-4838-4f97-aa25-7993f6fa7638",
        }
    }

    url = 'https://ombis8122.test.int.telmekom.net:8068/rest/web3/00000001/adresse?json'

    data = {
        "Fields": {
            "Name1": "Digi2",
            "MwStNummer": "11122233344",
            "UStIDNummer": "IT11122233344",
            "Steuernummer": "12312312312",
            "Status": "NichtKontrolliert",
            "Sprache": "it",
            "Anrede": "/rest/web3/00000001/anrede/1",
            "Strasse1": "Via roma 1",
            "Ort": "Merano (bz)",
            "PLZ": "39012",
            "Bemerkungen": "123",
            "KommunikationE1": "igor@digitalcube.rs",
            "KommunikationE2": "igor@digitalcube.rs",
            "KommunikationE3": "igor@digitalcube.rs",
            "KommunikationP1": "igor@digitalcube.rs",
            "Latitude": "46.6582417",
            "Longitude": "11.1665083",
            "Gemeinde": "/rest/web3/00000001/land/2446/gemeinde/5351",
            "Provinz": "/rest/web3/00000001/land/2446/provinz/1462",
            "Region": "/rest/web3/00000001/land/2446/region/193",
            "Land": "/rest/web3/00000001/land/2446",
            "KommunikationsinfoH1": " ",
            "Geschlecht": "legalPerson",
        }
    }

    res = await post('adresse', data, return_type='response')

    # print(res)


if __name__ == '__main__':
    # url = 'artikel?Fields=Herstellerkode,HerstellerMatchcode,XF_IMPDENMOD,Basiseinheit,Matchcode,Auslaufartikel,BemerkungenBeiDokumenterfassung,Bemerkungen,Herstellerkode,Gesperrt,Verkauf,VerkaufspreisBW,Artikelart.Code,Artikelart.Name,ArtikelGruppe1.Name,ArtikelGruppe1.Name_it,ArtikelGruppe1.Name_de,ArtikelGruppe2.Name,ArtikelGruppe2.Name_it,ArtikelGruppe2.Name_de,ArtikelGruppe3.Name,ArtikelGruppe3.Name_de,ArtikelGruppe3.Name_it,ArtikelGruppe4.Name,ArtikelGruppe5.Code,RabattfaehigVK,Stueckliste,Code,Name,Name_de,Name_it,Description_de,Description_it,MwStKode.Prozent&cfgOrder=Artikelart.Code,alt(cfgOrder=ArtikelGruppe1.Code)'
    # url = 'verkaufrabatt&fields=ID,Rabatt1,VerkaufRabattgruppe.code,kunderabattgruppe.code'

    #    res = asyncio.run(get(url))
    #    print(res)

    #    asyncio.run(main())

    dotenv.load_dotenv('../../../.env')
    res = asyncio.run(get('adresse?json&reduced&puredata&fields=Full&filter=in(ID,133539)', return_type='response'))

    # res = asyncio.run(get('kunde/33533'))
    # print(type(res))
    # res = asyncio.run(get('/rest/web3/00000001/kunde/33533'))
    # print(type(res))
    # res = asyncio.run(get('00000001/kunde/33533'))
    # print(type(res))
    # res = asyncio.run(get('/00000001/kunde/33533'))
    # print(type(res))
    # res = asyncio.run(get('/rest/web2/00000001/kunde/33533'))
    # print(res)
