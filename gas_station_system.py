import os
import requests
from bs4 import BeautifulSoup
import json
import time

from datetime import datetime
from base import BaseSystem, Credential, Transaction, Station, InvalidCredentialsError, InvalidGetTransactionsError


class GasStationSystem(BaseSystem):
    base_url: str = os.getenv('BASE_URL')
    url: str
    login_url: str
    account_url: str
    credential: Credential
    cookie: str
    headers: dict
    
    def auth(self, credential: Credential) -> None:
        self.url = str(credential.url)
        if not self.url:
            self.url = self.base_url

        self.credential = credential
        try:
            response = requests.get(self.url)
            response.raise_for_status()

            response_headers = response.headers

            soup = BeautifulSoup(response.text, 'html.parser')

            login_link = soup.find('a', class_='nav-link', string='Войти')

            if login_link:
                login_url_path = login_link['href']

                if login_url_path.startswith('/'):
                    self.login_url = self.url.rstrip('/') + login_url_path
                else:
                    raise InvalidCredentialsError('Incorrect link format on the website')
            else:
                raise InvalidCredentialsError("The link to the login page was not found")
            
            payload = {
                'login': self.credential.login,
                'password': self.credential.password,
            }

            if self.credential.token:
                payload.update({'_token': self.credential.token,})

            self.cookie = response_headers['Set-Cookie']     

            self.headers = {
                'accept-encoding': 'gzip, deflate, br, zstd',
                'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7,sh;q=0.6,sr;q=0.5',
                'x-requested-with': 'XMLHttpRequest',
                'x-winter-request-handler': 'onSignin',
                'x-winter-request-partials': '',
                'cookie': self.cookie,
            }

            response = requests.post(self.login_url, headers=self.headers, data=payload)
            response.raise_for_status()
            
            data = json.loads(response.text)
            account_url_key = 'X_WINTER_REDIRECT'
            if account_url_key in data:
                self.account_url = data[account_url_key]
                print(f'Successful log in. Account url: {self.account_url}')
            else:
                InvalidCredentialsError("Error in the returned JSON format")

        except requests.exceptions.RequestException as e:
            print(f"(auth) Request exception: {e}")
            raise InvalidCredentialsError(e)
        except Exception as e:
            print(f"(auth) Parsing exception: {e}")
            raise InvalidCredentialsError(e)
    
    def get_transactions(self, from_date: datetime, to_date: datetime) -> list[Transaction]:
        transactions = []
        try:
            if self.credential.contracts:
                contracts_list = [contract.strip() for contract in self.credential.contracts.rsplit(',')]
                for contract in contracts_list:
                    transactions = self.transactions_requests(transactions, from_date, to_date, contract)
            else:
                transactions = self.transactions_requests(transactions, from_date, to_date)
        except requests.exceptions.RequestException as e:
            print(f"(get_transactions) Request exception: {e}")
            raise InvalidGetTransactionsError(e)
        except Exception as e:
            print(f"(get_transactions) Parsing exception: {e}")
            raise InvalidGetTransactionsError(e)
        
        return transactions
        
    def transactions_requests(self, transactions: list, from_date: datetime, to_date: datetime, contract = None):
        pages = 1
        page = pages
        int_contract = int(contract)
        str_contract = ''
        if int_contract:
            str_contract = str(int_contract)

        while page <= pages:
            payload = {
                'start_date': from_date.strftime('%Y-%m-%d'),
                'start_time': '',
                'end_date': to_date.strftime('%Y-%m-%d'),
                'end_time': '',
                'contract': str_contract,
                'card': '',
                'page': page,
            }
            
            if page == 1:
                self.headers.update({'x-winter-request-handler': '',})   
                if self.credential.token:
                    payload.update({'_token': self.credential.token,})
            response = requests.post(f'{self.account_url}/transactions?page_size=100', headers = self.headers, data = payload)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            transactions_table = soup.find('table', class_='table')
            if transactions_table:
                headers = [th.text.strip() for th in transactions_table.thead.find_all('th')]
                transactions_list = []
                for row in transactions_table.tbody.find_all('tr'):
                    row_data = {}
                    cells = row.find_all('td')
                    if len(cells) == len(headers):
                        for i, cell in enumerate(cells):
                            row_data[headers[i]] = cell.text.strip()
                        transactions_list.append(row_data)
                for transaction in transactions_list:
                    try:
                        amount = float(transaction['Сумма'])
                    except Exception as e:
                        amount = 0.0
                    try:
                        volume = float(transaction['Объем'])
                    except Exception as e:
                        volume = 0.0    
                    transactions.append(Transaction(
                        credential = self.credential,
                        station = Station(code = transaction['АЗС']),
                        card = transaction['Карта'],
                        code = transaction['Номер'],
                        date = datetime.strptime(transaction['Дата'], '%Y-%m-%d %H:%M:%S'),
                        service = transaction['Товар'],
                        sum = amount,
                        volume = volume,
                    ))

            else:
                InvalidGetTransactionsError("There are no transactions")

            if page == 1:
                pagination_links = soup.find_all('a', class_='page-link')
                if len(pagination_links) > 0:
                    page_numbers = []
                    for link in pagination_links:
                        text = link.text.strip()
                        page_num = None
                        try:
                            if text.isdigit():
                                page_num = int(text)
                            else:
                                raise ValueError()
                        except Exception as e:
                            continue
                        
                        page_numbers.append(page_num)

                if page_numbers:
                    pages = max(page_numbers)
            print(f'contract: {contract}; page: {page}/{pages}')

            page += 1
            time.sleep(1)
        
        return transactions
