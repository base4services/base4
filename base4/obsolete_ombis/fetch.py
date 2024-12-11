import asyncio
import datetime
import os
import sys
import time

import dotenv
import ujson as json
from base4.utilities.common import split_list

current_file_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(current_file_dir + '/..')  # src
import shared.ombis.ombis_util as ombis
from base4.utilities.files import get_file_path


async def fetch_ids(url: str, chunks_of_ids: list[str], fields='Full', refs=None, result_file: str = '/tmp/result.json', fields_for_log=['ID']):
    await fetchall(
        url,
        fields,
        refs,
        0,
        0,
        result_file,
        fields_for_log,
        avoid_paging=True,
        additional_filter='filter=in(ID,' + ','.join([str(x) for x in chunks_of_ids]) + ')',
        merge_result_with_existing_output_file=True,
    )


async def fetchall(
    url,
    fields,
    refs,
    offset,
    limit,
    result_file,
    fields_for_log,
    additional_filter: str = None,
    avoid_paging: bool = False,
    max_limit: int = None,
    merge_result_with_existing_output_file: bool = False,
):
    start_at = time.time()

    base_url = url + '?json&reduced&puredata&order=ID'

    if refs:
        base_url += f'&refs={refs}'

    if fields:
        base_url += f'&fields={fields}'

    nr = offset
    all = {}

    while True:

        iter = 0
        if fields_for_log:
            print(iter)

        while True:
            try:
                url = base_url

                if not avoid_paging:
                    url += '&maxrows=' + str(limit) + '&skiprows=' + str(offset)

                if avoid_paging:
                    if max_limit:
                        url += '&maxrows=' + str(max_limit)

                if additional_filter:
                    url += '&' + additional_filter

                res = await ombis.get(url)
                break
            except Exception as e:
                iter += 1
                if iter > 10:
                    print("ERROR ACCESSING OMBIS AFTER 10 attempts, exiting process")
                    sys.exit()

                print(f"ERROR ACCESSING OMBIS trying again in {iter} sec")
                await asyncio.sleep(iter)
                continue

        if 'Data' not in res:
            break
        if len(res['Data']) == 0:
            break

        offset += limit

        for item in res['Data']:

            if item['Fields']['ID'] in all:
                print("ID exists", item['Fields']['ID'])
                raise NameError("ID exists")

            all[item['Fields']['ID']] = item

            nr += 1
            if fields_for_log:
                print(nr, [item['Fields'][f] for f in fields_for_log])  # item['Fields']['ID'], item['Fields']['Nummer'], item['Fields']['DisplayName'])

        if avoid_paging:
            break

    if not merge_result_with_existing_output_file:
        with open(result_file, 'wt') as f:
            json.dump(all, f, indent=1, ensure_ascii=False, sort_keys=True)
    else:
        try:
            with open(result_file, 'rt') as f:
                try:
                    existing = json.load(f)
                except Exception as e:
                    existing = {}
        except Exception as e:
            existing = {}

        all = {str(k): v for k, v in all.items()}
        existing.update(all)
        with open(result_file, 'wt') as f:
            json.dump(existing, f, indent=1, ensure_ascii=False, sort_keys=True)

        print('saved in', result_file, 'len', os.path.getsize(result_file))

    return round(time.time() - start_at, 4)


async def fetch_clients(result_file='clients.json'):
    await fetchall(
        'kunde',  # ?reduced&puredata&order=ID',
        fields='Full',  # 'ID,Nummer,DisplayName',
        refs='Rechtssitz',  # None
        offset=0,
        limit=200,
        result_file=result_file,
        fields_for_log=['ID', 'Nummer', 'DisplayName'],
    )


async def fetch_sites(result_file='sites.json'):
    await fetchall(
        'lieferadresse',
        fields='Full',
        refs='adresse',  # None
        offset=0,
        limit=200,
        result_file=result_file,
        fields_for_log=['ID', 'DisplayName'],
    )


async def fetch_countries(result_file='countries.json'):
    await fetchall('land', fields='Full', refs=None, offset=0, limit=1000, result_file=result_file, fields_for_log=["ID"])


async def fetch_municipalities(result_file='municipalities.json'):
    await fetchall('gemeinde', fields='Full', refs=None, offset=0, limit=1000, result_file=result_file, fields_for_log=['ID', 'DisplayName'])


async def fetch_provinces(result_file='provinces.json'):
    await fetchall('Provinz', fields='Full', refs=None, offset=0, limit=1000, result_file=result_file, fields_for_log=['ID', 'DisplayName'])


async def fetch_regions(result_file='regions.json'):
    await fetchall('Region', fields='Full', refs=None, offset=0, limit=1000, result_file=result_file, fields_for_log=['ID', 'Code', 'Name'])


async def fetch_addresses(result_file):
    await fetchall('adresse', fields='Full', refs=None, offset=0, limit=500, result_file=result_file, fields_for_log=['ID', 'Suchbegriff'])


async def fetch_employees(result_file='employees.json'):
    await fetchall(
        'mitarbeiter',
        fields='Full',
        refs=None,
        offset=0,
        limit=500,
        result_file=result_file,
        fields_for_log=['ID', 'DisplayName'],
    )


async def fetch_users(result_file='users.json'):
    await fetchall('user', fields='Full', refs=None, offset=0, limit=500, result_file=result_file, fields_for_log=['ID', 'DisplayName'])


async def fetch_logusers(result_file='logusers.json'):
    await fetchall('loguser', fields='Full', refs=None, offset=0, limit=500, result_file=result_file, fields_for_log=['ID', 'DisplayName'])


async def fetch_activities(result_file='activities.json'):
    await fetchall('taetigkeit', fields='Full', refs=None, offset=0, limit=500, result_file=result_file, fields_for_log=['ID', 'DisplayName'])


async def fetch_timesheets(result_file='timesheets.json'):
    await fetchall(
        'dienstleistungszeit',
        fields='Full',
        refs=None,
        offset=260000,
        limit=1000,
        result_file=result_file,
        fields_for_log=['ID', 'DisplayName'],
        avoid_paging=True,
        max_limit=5,
    )
    # await fetchall('dienstleistungszeit', fields='Full', refs=None, offset=260000, limit=1000, result_file=result_file, fields_for_log=['ID', 'DisplayName'])


async def fetch_timesheets_for_specific_month(year: int, month: int, result_file: str, max_limit: int = None):
    first = f'{year}-{month:02d}-01'
    first = datetime.datetime.strptime(first, '%Y-%m-%d')
    last = first + datetime.timedelta(days=32)
    last = last.replace(day=1)

    await fetchall(
        'dienstleistungszeit',
        fields='Full',
        refs=None,
        offset=0,
        limit=0,
        result_file=result_file,
        fields_for_log=['ID', 'DisplayName'],
        avoid_paging=True,
        max_limit=max_limit,
        additional_filter=f'filter=and(ge(Datum,\'{first.date()}\'),lt(Datum,\'{last.date()}\'))',
    )


async def fetch_tickets_for_fetched_timesheets(timesheets_json, tickets_json, max_limit=None):
    with open(timesheets_json, 'rt') as f:
        timesheets = json.load(f)

    tickets = set()
    iter = 0
    for ts in timesheets:
        f = timesheets[ts]['Fields']
        if 'Serviceanfrage' in f:
            ticket_id = int(f['Serviceanfrage'].split('/')[-1])
            tickets.add(ticket_id)
            iter += 1

    tickets = sorted(list(tickets))

    chunks = split_list(tickets, 200)

    try:
        os.unlink(tickets_json)
    except Exception as e:
        pass

    iter = 0
    for chunk in chunks:
        print(chunk)
        print(iter, len(chunks))
        iter += 1

        await fetch_ids(
            'serviceanfrage',
            chunk,
            fields='Full',
            refs=None,
            result_file=tickets_json,
            # fields_for_log=['ID', 'Nummer', 'DisplayName']
            fields_for_log=None,
        )
        # break

    # print(iter, len(tickets))


async def fetch_departments(result_file='departments.json'):
    await fetchall('nummerierung', fields='Full', refs=None, offset=0, limit=500, result_file=result_file, fields_for_log=['ID', 'Code'])


async def fetch_org_units(result_file='org_units.json'):
    await fetchall('abteilung', fields='Full', refs=None, offset=0, limit=500, result_file=result_file, fields_for_log=['ID', 'Code'])


async def fetch_timesheet_with_affected_tickets_for_month(year, month):

    max_limit = None

    from base4.utilities.files import get_file_path

    await fetch_timesheets_for_specific_month(year, month, result_file=get_file_path(f'/ombis_repo/timesheets-{year}-{month:02}.json'), max_limit=max_limit)

    await fetch_tickets_for_fetched_timesheets(
        get_file_path(f'/ombis_repo/timesheets-{year}-{month:02}.json'),
        get_file_path(f'/ombis_repo/tickets-{year}-{month:02}.json'),
        max_limit=max_limit,
    )


# async def main():
#     ...
#     # await fetch_clients()
#     # await fetch_sites()
#     # await fetch_countries()
#     # await fetch_municipalities()
#     # await fetch_provinces()
#     # await fetch_regions()
#     # await fetch_addresses()
#     # await fetch_employees()
#     # await fetch_users()
#     # await fetch_departments()
#     # await fetch_org_units()
#     for i in [6,4,3,2,1]:
#         await fetch_timesheet_with_affected_tickets_for_month(2024, i)
#
#
# if __name__ == "__main__":
#     dotenv.load_dotenv(get_file_path('.env'))
#     asyncio.run(main())
