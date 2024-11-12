import os
import sys
from typing import AnyStr, Dict, List, Optional

import dotenv
from pydantic import BaseModel

dotenv.load_dotenv()


class DatabaseConfig(BaseModel):
    """
    Configuration settings for the database connection.

    Attributes:
        db_name (str): The name of the database.
        db_port (int): The port number for the database connection.
        db_host (str): The hostname or IP address of the database server.
        db_password (str): The password for the database user.
    """

    db_conn: AnyStr
    db_name: AnyStr
    db_postgres_port:int
    db_postgres_host: AnyStr
    db_postgres_user: AnyStr
    db_postgres_password: AnyStr

    def __init__(
        self,
        svc_name: str,
        # /,
        **kwargs,
    ) -> object:
        """
        Initializing DatabaseConfig model, with feature of checking if values
        exists in environments.
        :param kwargs:
        """

        _testmode: bool = kwargs.get('_testmode', False)
        try:
            _dbconf: Dict = self._configuration_db(
                # svc_name=svc_name,
                _testmode=_testmode
            )
        except Exception as e:
            raise

        kwargs = _dbconf

        env_db_name = 'DB_' + svc_name.upper()

        kwargs['db_name'] = os.getenv(env_db_name, None) if not _testmode else 'test_' + os.getenv('DB_PREFIX', None)
        kwargs['db_conn'] = 'conn_' + svc_name if not _testmode else 'conn_test'
        try:
            super().__init__(**kwargs)
        except Exception as e:
            raise

        ...

    def _configuration_db(
        self,
        _testmode: bool,
    ) -> Dict:
        """
        This method gets values from environment files which are necessary for establishing
        connection with a database. If some value is missing it raises detailed error.

        :param _testmode (bool): Checks if application is started in test mode.
        :return: Dictionary of values from environment file with necessary data for
                 configuring database.
        """
        _conf: Dict = {}  # dict({'db_name': db_name})

        varss: tuple = (
            'DB_POSTGRES_HOST',
            'DB_POSTGRES_PORT',
            'DB_POSTGRES_USER',
            'DB_POSTGRES_PASSWORD',
        )

        missing_values: List = list()

        for var in varss:
            value: AnyStr | int = os.getenv(var, None)
            if not value:
                missing_values.append(var)
            _conf[var.lower()] = value

        if len(missing_values) != 0:
            for _v in missing_values:
                print('{}: missing in environment file!\n'.format(_v))

            sys.exit(1)

        return _conf
