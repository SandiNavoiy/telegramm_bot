import requests
import logging
from config import Config

logger = logging.getLogger(__name__)

class RatesService:
    """Сервис получения котировок фиатных валют и криптовалют к рублю."""

    def __init__(self):
        # Поддерживаемые валюты и их человекочитаемые названия
        self.supported_currencies = {
            "USD": "Доллар США",
            "EUR": "Евро",
            "BYN": "Белорусский рубль",
            "CAD": "Канадский доллар",
            "GBP": "Фунт стерлингов",
            "BTC": "Bitcoin (Биткоин)",
            "ETH": "Ethereum (Эфириум)",
            "SOL": "Solana (Солана)",
            "KAS": "Kaspa (Каспа)",
            "XMR": "Monero (Монеро)"
        }

    def fetch_cbr_fiat_rates(self) -> dict[str, float]:
        """Получение курсов фиатных валют (USD, EUR, BYN, CAD, GBP) из API ЦБ РФ."""
        url = "https://www.cbr-xml-daily.ru/daily_json.js"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        valutes = data.get("Valute", {})
        
        rates = {}
        for symbol in ["USD", "EUR", "BYN", "CAD", "GBP"]:
            if symbol in valutes:
                nominal = valutes[symbol].get("Nominal", 1)
                value = valutes[symbol].get("Value", 0.0)
                rates[symbol] = round(value / nominal, 4)
        return rates

    def fetch_apilayer_fiat_rates(self) -> dict[str, float]:
        """Получение курсов фиатных валют через APILayer (если указан API_KEY)."""
        if not Config.API_KEY:
            raise ValueError("API_KEY для APILayer не указан.")
            
        rates = {}
        for symbol in ["USD", "EUR", "BYN", "CAD", "GBP"]:
            url = f"https://api.apilayer.com/exchangerates_data/latest?base={symbol}&symbols=RUB"
            headers = {"apikey": Config.API_KEY}
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            data = res.json()
            if "rates" in data and "RUB" in data["rates"]:
                rates[symbol] = round(float(data["rates"]["RUB"]), 4)
        return rates

    def fetch_crypto_rates(self, usd_in_rub: float = None) -> dict[str, float]:
        """Получение курсов криптовалют (BTC, ETH, SOL, KAS, XMR) к рублю."""
        crypto_rates = {}
        crypto_ids = {
            "bitcoin": "BTC",
            "ethereum": "ETH",
            "solana": "SOL",
            "kaspa": "KAS",
            "monero": "XMR"
        }
        
        # 1. Основной источник: CoinGecko API
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(crypto_ids.keys())}&vs_currencies=rub,usd"
            headers = {"User-Agent": "TelegramBot/1.0"}
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for cg_id, symbol in crypto_ids.items():
                    if cg_id in data:
                        price_rub = data[cg_id].get("rub")
                        if not price_rub and "usd" in data[cg_id] and usd_in_rub:
                            price_rub = data[cg_id]["usd"] * usd_in_rub
                        if price_rub:
                            # Округление: для BTC/ETH/SOL/XMR до целых/сотых, для KAS до 4 знаков
                            decimals = 4 if symbol == "KAS" else (2 if price_rub < 1000 else 2)
                            crypto_rates[symbol] = round(float(price_rub), decimals)

                if len(crypto_rates) == len(crypto_ids):
                    return crypto_rates
        except Exception as e:
            logger.warning(f"Ошибка запроса к CoinGecko: {e}. Переход на резервный источник CryptoCompare...")

        # 2. Резервный источник: CryptoCompare API
        try:
            fsyms = ",".join(crypto_ids.values())
            url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={fsyms}&tsyms=RUB,USD"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for symbol in crypto_ids.values():
                    if symbol in data:
                        price_rub = data[symbol].get("RUB") or (data[symbol].get("USD", 0) * (usd_in_rub or 90.0))
                        if price_rub:
                            decimals = 4 if symbol == "KAS" else 2
                            crypto_rates[symbol] = round(float(price_rub), decimals)
        except Exception as e:
            logger.error(f"Ошибка запроса к CryptoCompare: {e}")

        return crypto_rates

    def get_all_rates(self) -> dict[str, float]:
        """Получить актуальные курсы всех поддерживаемых фиатных и криптовалютных активов."""
        rates = {}
        
        # 1. Загрузка фиатных валют
        fiat_fetched = False
        if Config.API_KEY:
            try:
                rates.update(self.fetch_apilayer_fiat_rates())
                fiat_fetched = True
            except Exception as e:
                logger.warning(f"Ошибка APILayer ({e}), используется ЦБ РФ...")
                
        if not fiat_fetched:
            try:
                rates.update(self.fetch_cbr_fiat_rates())
            except Exception as e:
                logger.error(f"Ошибка получения курсов ЦБ РФ: {e}")

        # 2. Загрузка криптовалют
        usd_rub = rates.get("USD")
        try:
            crypto_rates = self.fetch_crypto_rates(usd_in_rub=usd_rub)
            rates.update(crypto_rates)
        except Exception as e:
            logger.error(f"Ошибка получения криптовалютных курсов: {e}")

        return rates

    def get_rate(self, symbol: str) -> float | None:
        """Получить курс конкретной валюты по ее символу."""
        rates = self.get_all_rates()
        return rates.get(symbol.upper())

rates_service = RatesService()
