from datetime import datetime, timedelta
import requests
from dataclasses import dataclass

@dataclass
class Credential:
    url: str = None
    login: str = None
    password: str = None
    token: str = None
    contracts: str = None # список номеров контрактов через запятую, может быть пустым

@dataclass
class Point:
    lat: float = 0 # широта
    lng: float = 0 # долгота

@dataclass
class Station:
    code: str = None # уникальный идентификатор тс, если есть
    name: str = None # название, если есть
    brand: str = None # бренд, если есть
    point: Point = None # точка, если есть
    address: str = None # адрес, если есть

@dataclass
class Transaction:
    credential: Credential = None
    station: Station = None
    card: str = None # номер карты
    code: str = None # код транзакции, если есть
    date: datetime = None # дата транзакции
    service: str = None # услуга
    sum: float = 0 # сумма
    volume: float = 0 # объем


class InvalidCredentialsError(Exception):
    pass

class InvalidGetTransactionsError(Exception):
    pass

class BaseSystem:
    base_url: str = None
            
    def __init__(self) -> None:
        self.connection = requests.Session()
    
    def auth(self, credential: Credential) -> None:
        self.credential = credential
    
    def get_transactions(self, from_date: datetime, to_date: datetime) -> list[Transaction]:
        raise NotImplementedError()