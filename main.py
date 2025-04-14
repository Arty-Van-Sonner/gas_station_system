
import os

from datetime import datetime

from base import Credential
from gas_station_system import GasStationSystem

from dotenv import load_dotenv 
load_dotenv()


if __name__ == '__main__':
    cred = Credential(
        url = os.getenv('URL'),
        login = os.getenv('LOGIN'),
        password = os.getenv('PASSWORD'),
        contracts = "001,003",
    )
    system = GasStationSystem()
    system.auth(cred)
    
    transactions = system.get_transactions(
        from_date=datetime(2024, 1, 1),
        to_date=datetime(2024, 7, 1),
    )

    print('Transactions count', len(transactions))

    for tr in transactions[:10]:
        print(tr)
    
    