import datetime
import os

import dotenv
import tortoise.timezone
from tortoise.transactions import in_transaction

dotenv.load_dotenv()

default_id_user = os.getenv('DEFAULT_ID_USER', '00000000-0000-0000-0000-000000000000')


class OmbisLookupTableService:

    async def populate_ombis_lookup_table(
        self, data, additional_data: dict = None, additional_source_data: dict = None, display_name_term="f['DisplayName']", ids=None
    ):

        if not additional_data:
            additional_data = {}

        if not additional_source_data:
            additional_source_data = {}

        conn = self.conn_name

        current = {str(e.external_id): e for e in await self.model.filter(external_source='OMBIS').all()}
        added, updated, skipped = 0, 0, 0
        async with in_transaction(conn):
            for id_item in data:
                try:
                    # DON'T remove f - used in eval
                    f = data[id_item]['Fields']
                    external_id = str(id_item)
                    display_name = eval(display_name_term)  # f['Code'] + ' - ' + f['DisplayName']
                    source = data[id_item]

                    if external_id in current:
                        if source != current[external_id].source:
                            current[external_id].display_name = display_name
                            current[external_id].source = source

                            current['last_updated_by'] = default_id_user
                            await current[external_id].save()
                            updated += 1
                        else:
                            skipped += 1
                    else:
                        kwa = {
                            'external_id': external_id,
                            'display_name': display_name,
                            'created_by': default_id_user,
                            'logged_user_id': default_id_user,
                            'source': source,
                            'external_source': 'OMBIS',
                            'is_valid': True,
                            'validated': tortoise.timezone.now(),
                        }
                        if ids:
                            if id_value := ids.get(f["Code"]):
                                kwa["id"] = id_value
                        kwa.update(additional_data)
                        if int(external_id) in additional_source_data:
                            kwa.update(additional_source_data[int(external_id)])
                        e = self.model(**kwa)
                        await e.save()
                        added += 1

                except Exception as e:
                    raise

        return {'added': added, 'updated': updated, 'skipped': skipped}
