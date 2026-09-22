import requests
import logging
from config import Config

logger = logging.getLogger(__name__)

class RatesService:
    """Сервис получения котировок фиатных валют и криптовалют (Kaspa, Monero) к рублю."""

    def __init__(self):
        # Поддерживаемые валюты и их человекочитаемые названия
        self.supported_currencies = {
            "USD": "Доллар США",
            "EUR": "Евро",
            "CAD": "Канадский доллар",
            "GBP": "Фунт стерлингов",
            "KAS": "Kaspa (Каспа)",
            "XMR": "Monero (Монеро)"
        }

    def fetch_cbr_fiat_rates(self) -> dict[str, float]:
        """Получение курсов фиатных валют (USD, EUR, CAD, GBP) из бесплатного API Центрального Банка РФ."""
        url = "https://www.cbr-xml-daily.ru/daily_json.js"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        valutes = data.get("Valute", {})
        
        rates = {}
        for symbol in ["USD", "EUR", "CAD", "GBP"]:
            if symbol in valutes:
                # Номинал (например, 1 валютная единица)
                nominal = valutes[symbol].get("Nominal", 1)
                value = valutes[symbol].get("Value", 0.0)
                rates[symbol] = round(value / nominal, 4)
        return rates

    def fetch_apilayer_fiat_rates(self) -> dict[str, float]:
        """Получение курсов фиатных валют с использованием стороннего API APILayer (при наличии API_KEY)."""
        if not Config.API_KEY:
            raise ValueError("API_KEY для APILayer не указан.")
            
        rates = {}
        for symbol in ["USD", "EUR", "CAD", "GBP"]:
            url = f"https://api.apilayer.com/exchangerates_data/latest?base={symbol}&symbols=RUB"
            headers = {"apikey": Config.API_KEY}
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            data = res.json()
            if "rates" in data and "RUB" in data["rates"]:
                rates[symbol] = round(float(data["rates"]["RUB"]), 4)
        return rates

    def fetch_crypto_rates(self, usd_in_rub: float = None) -> dict[str, float]:
        """Получение курсов криптовалют Kaspa (KAS) и Monero (XMR) к рублю через CoinGecko и CryptoCompare."""
        crypto_rates = {}
        
        # 1. Основной источник: CoinGecko API
        try:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=kaspa,monero&vs_currencies=rub,usd"
            headers = {"User-Agent": "TelegramBot/1.0"}
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if "kaspa" in data:
                    kas_rub = data["kaspa"].get("rub")
                    if not kas_rub and "usd" in data["kaspa"] and usd_in_rub:
                        kas_rub = data["kaspa"]["usd"] * usd_in_rub
                    if kas_rub:
                        crypto_rates["KAS"] = round(float(kas_rub), 4)
                        
                if "monero" in data:
                    xmr_rub = data["monero"].get("rub")
                    if not xmr_rub and "usd" in data["monero"] and usd_in_rub:
                        xmr_rub = data["monero"]["usd"] * usd_in_rub
                    if xmr_rub:
                        crypto_rates["XMR"] = round(float(xmr_rub), 2)

                if len(crypto_rates) == 2:
                    return crypto_rates
        except Exception as e:
            logger.warning(f"Ошибка запроса к CoinGecko: {e}. Переход на резервный источник CryptoCompare...")

        # 2. Резервный источник: CryptoCompare API
        try:
            url = "https://min-api.cryptocompare.com/data/pricemulti?fsyms=KAS,XMR&tsyms=RUB,USD"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if "KAS" in data:
                    kas_rub = data["KAS"].get("RUB") or (data["KAS"].get("USD", 0) * (usd_in_rub or 90.0))
                    if kas_rub:
                        crypto_rates["KAS"] = round(float(kas_rub), 4)
                if "XMR" in data:
                    xmr_rub = data["XMR"].get("RUB") or (data["XMR"].get("USD", 0) * (usd_in_rub or 90.0))
                    if xmr_rub:
                        crypto_rates["XMR"] = round(float(xmr_rub), 2)
        except Exception as e:
            logger.error(f"Ошибка запроса к CryptoCompare: {e}")

        return crypto_rates

    def get_all_rates(self) -> dict[str, float]:
        """Получить актуальные курсы абсолютно всех поддерживаемых валют (USD, EUR, CAD, GBP, KAS, XMR)."""
        rates = {}
        
        # 1. Загрузка фиатных валют (сначала APILayer если есть ключ, иначе ЦБ РФ)
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

        # 2. Загрузка криптовалют (Kaspa, Monero)
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

# Глобальный экземпляр сервиса курсов
rates_service = RatesService()
