import requests
import logging
from config import Config

logger = logging.getLogger(__name__)

class RatesService:
    """Сервис получения котировок фиатных валют (к рублю) и криптовалют (к доллару США)."""

    def __init__(self):
        # Поддерживаемые валюты и их человекочитаемые названия
        self.supported_currencies = {
            # Фиатные валюты (к RUB)
            "USD": "Доллар США",
            "EUR": "Евро",
            "BYN": "Белорусский рубль",
            "CAD": "Канадский доллар",
            "GBP": "Фунт стерлингов",
            # Криптовалюты (к USD)
            "BTC": "Bitcoin (Биткоин)",
            "ETH": "Ethereum (Эфириум)",
            "SOL": "Solana (Солана)",
            "KAS": "Kaspa (Каспа)",
            "XMR": "Monero (Монеро)"
        }
        
        self.crypto_symbols = {"BTC", "ETH", "SOL", "KAS", "XMR"}
        self.fiat_symbols = {"USD", "EUR", "BYN", "CAD", "GBP"}

    def is_crypto(self, symbol: str) -> bool:
        return symbol.upper() in self.crypto_symbols

    def fetch_cbr_fiat_rates(self) -> dict[str, float]:
        """Получение курсов фиатных валют (USD, EUR, BYN, CAD, GBP) в RUB из API ЦБ РФ."""
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

    def fetch_crypto_rates_usd(self) -> dict[str, float]:
        """Получение курсов криптовалют (BTC, ETH, SOL, KAS, XMR) к доллару США (USD)."""
        crypto_rates = {}
        crypto_ids = {
            "bitcoin": "BTC",
            "ethereum": "ETH",
            "solana": "SOL",
            "kaspa": "KAS",
            "monero": "XMR"
        }
        
        # 1. Основной источник: CoinGecko API (vs_currencies=usd)
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(crypto_ids.keys())}&vs_currencies=usd"
            headers = {"User-Agent": "TelegramBot/1.0"}
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for cg_id, symbol in crypto_ids.items():
                    if cg_id in data and "usd" in data[cg_id]:
                        price_usd = float(data[cg_id]["usd"])
                        # Округление: KAS до 4 знаков, остальные до 2 знаков
                        decimals = 4 if symbol == "KAS" else 2
                        crypto_rates[symbol] = round(price_usd, decimals)

                if len(crypto_rates) == len(crypto_ids):
                    return crypto_rates
        except Exception as e:
            logger.warning(f"Ошибка запроса к CoinGecko: {e}. Переход на резервный источник CryptoCompare...")

        # 2. Резервный источник: CryptoCompare API (tsyms=USD)
        try:
            fsyms = ",".join(crypto_ids.values())
            url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={fsyms}&tsyms=USD"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for symbol in crypto_ids.values():
                    if symbol in data and "USD" in data[symbol]:
                        price_usd = float(data[symbol]["USD"])
                        decimals = 4 if symbol == "KAS" else 2
                        crypto_rates[symbol] = round(price_usd, decimals)
        except Exception as e:
            logger.error(f"Ошибка запроса к CryptoCompare: {e}")

        return crypto_rates

    def get_all_rates(self) -> dict[str, float]:
        """Получить актуальные курсы всех фиатных валют (к RUB) и криптовалют (к USD)."""
        rates = {}
        
        # 1. Фиатные валюты (к RUB)
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

        # 2. Криптовалюты (к USD)
        try:
            crypto_rates = self.fetch_crypto_rates_usd()
            rates.update(crypto_rates)
        except Exception as e:
            logger.error(f"Ошибка получения криптовалютных курсов в USD: {e}")

        return rates

    def get_rate(self, symbol: str) -> float | None:
        """Получить курс конкретной валюты по ее символу."""
        rates = self.get_all_rates()
        return rates.get(symbol.upper())

rates_service = RatesService()
