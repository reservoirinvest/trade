import asyncio
import datetime
import inspect
import re

import pandas as pd
import pytz
import requests
from bs4 import BeautifulSoup
from ib_insync import ib
from nsepy.commons import *
from nsepython import nse_get_fno_lot_sizes, nse_optionchain_scrapper

async def marginsAsync(contracts: list, orders: list, timeout: float=2) -> pd.DataFrame:

    async def wifAsync(ct, o):
        wif = ib.whatIfOrderAsync(ct, o)
        try:
           res = await asyncio.wait_for(wif, timeout=timeout)
        except asyncio.TimeoutError:
           res = None
        return res
    
    wif_tasks = [asyncio.create_task(wifAsync(contract, order), name=contract.conId) for contract, order in zip(contracts, orders)]
    
    res = await asyncio.gather(*wif_tasks)
    
    margins = [{'margin': r.initMarginChange, 'commission': r.commission} for r in res if r]
    conIds = [c.conId for c in contracts]

    results = dict(zip(conIds, margins))

    df = pd.DataFrame(results).transpose()
    
    return df

#Constants

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'DNT': '1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.79 Safari/537.36',
    'Sec-Fetch-User': '?1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-Mode': 'navigate',
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
    'Connection': 'keep-alive',
    'Host': 'www1.nseindia.com',
    'X-Requested-With': 'XMLHttpRequest'
}

opt_headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'DNT': '1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.79 Safari/537.36',
    'Sec-Fetch-User': '?1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-Mode': 'navigate',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
}

session = requests.Session()

indices = ['NIFTY','FINNIFTY','BANKNIFTY']

dd_mmm_yyyy = StrDate.default_format(format="%d-%b-%Y")
dd_mm_yyyy = StrDate.default_format(format="%d-%m-%Y")

EQUITY_SCHEMA = [str, str,
                 dd_mmm_yyyy,
                 float, float, float, float,
                 float, float, float, int, float,
                 int, int, float]
EQUITY_HEADERS = ["Symbol", "Series", "Date", "Prev Close",
                  "Open", "High", "Low", "Last", "Close", "VWAP",
                  "Volume", "Turnover", "Trades", "Deliverable Volume",
                  "%Deliverble"]
EQUITY_SCALING = {"Turnover": 100000,
                  "%Deliverble": 0.01}

INDEX_SCHEMA = [dd_mmm_yyyy,
                float, float, float, float,
                int, float]
INDEX_HEADERS = ['Date',
                 'Open', 'High', 'Low', 'Close',
                 'Volume', 'Turnover']
INDEX_SCALING = {'Turnover': 10000000}

OPTION_SCHEMA = [str, dd_mmm_yyyy, dd_mmm_yyyy, str, float,
                 float, float, float, float,
                 float, float, int, float,
                 float, int, int, float]
OPTION_HEADERS = ['Symbol', 'Date', 'Expiry', 'Option Type', 'Strike Price',
                  'Open', 'High', 'Low', 'Close',
                  'Last', 'Settle Price', 'Number of Contracts', 'Turnover',
                  'Premium Turnover', 'Open Interest', 'Change in OI', 'Underlying']
OPTION_SCALING = {"Turnover": 100000,
                  "Premium Turnover": 100000}

VIX_INDEX_SCHEMA = [dd_mmm_yyyy,
                    float, float, float, float,
                    float, float, float]
VIX_INDEX_HEADERS = ['Date',
                     'Open', 'High', 'Low', 'Close',
                     'Previous', 'Change', '%Change']
VIX_SCALING = {'%Change': 0.01}

FUTURES_SCHEMA = [str, dd_mmm_yyyy, dd_mmm_yyyy,
                  float, float, float, float,
                  float, float, int, float,
                  int, int, float]

FUTURES_HEADERS = ['Symbol', 'Date', 'Expiry',
                   'Open', 'High', 'Low', 'Close',
                   'Last', 'Settle Price', 'Number of Contracts', 'Turnover',
                   'Open Interest', 'Change in OI', 'Underlying']
FUTURES_SCALING = {"Turnover": 100000}

symbol_count = {'CRANESSOFT': u'1', 'ELGITYRE': u'1', 'VIVIMEDLAB': u'1', 'COMSYS': u'1', 'UNIONBANK': u'1', 'SB&TINTL': u'1', 'HIMACHLFUT': u'1', 'GAIL': u'1', 'RUBYMILLS': u'1', 'WALCHANNAG': u'1', 'PFOCUS': u'1', 'TVSELECT': u'1', 'PRECWIRE': u'1', 'GICHSGFIN': u'1', 'HINDUJAVEN': u'1', 'TIPSINDLTD': u'1', 'AMTEKAUTO': u'1', 'GESHIP': u'2', 'ABIRLANUVO': u'1', 'MEGH': u'2', 'GMBREW': u'1', 'GRAPHITE': u'2', 'KPIT': u'2', 'ZENITHBIR': u'1', 'KNRCON': u'1', 'SUPREMEINF': u'1', 'DOLPHINOFF': u'1', 'SUPREMEIND': u'1', 'LAOPALA': u'1', 'PRATIBHA': u'1', 'VISASTEEL': u'1', 'AVTNPL': u'1', 'ORBITCORP': u'1', 'MCLEODRUSS': u'1', 'MALUPAPER': u'1', 'LANCOIN': u'1', 'GUJNRECOKE': u'1', 'GMRINFRA': u'1', 'GAMMONIND': u'1', 'SHREERAMA': u'1', 'FINPIPE': u'1', 'KOLTEPATIL': u'1', 'PIRGLASS': u'1', 'MINDAIND': u'1', 'ATLASCYCLE': u'1', 'MANGTIMBER': u'1', 'DICIND': u'1', 'NCLIND': u'1', 'TALBROAUTO': u'1', 'LOTTEINDIA': u'1', 'THEMISMED': u'1', 'MANGALAM': u'2', 'CAMBRIDGE': u'2', 'AUROPHARMA': u'1', 'CENTEXT': u'2', 'MAX': u'2', 'IMPEXFERRO': u'1', 'RAMCOSYS': u'1', 'ENKEI': u'1', 'HDFC': u'2', 'GANDHITUBE': u'1', 'HELIOSMATH': u'1', 'NORTHGATE': u'2', 'EVERONN': u'1', 'VOLTAS': u'1', 'HINDCOMPOS': u'1', 'ANDHRSUGAR': u'1', 'JPASSOCIAT': u'1', 'SOMANYCERA': u'1', 'PSTL': u'1', 'SYNDIBANK': u'1', 'SUPPETRO': u'1', 'EMCO': u'2', 'JAICORPLTD': u'1', 'BEL': u'2', 'CMC': u'1', 'SHRENUJ': u'1', 'COSMOFILMS': u'1', 'MUNJALAU': u'2', 'SONATSOFTW': u'1', 'ZENITHINFO': u'1', 'COLPAL': u'1', 'HINDUNILVR': u'1', 'ESCORTS': u'2', 'GEOMETRIC': u'1', 'BALAJITELE': u'1', 'CINEMAX': u'2', 'MAHABANK': u'1', 'DLF': u'2', 'RAMANEWS': u'2', 'TTKPRESTIG': u'1', 'BANARISUG': u'1', 'KITPLYIND': u'1', 'KBL': u'1', 'QUINTEGRA': u'1', 'APOLLOSIND': u'1', 'APOLLOTYRE': u'1', 'SPICEMOBIL': u'1', 'CHEMFALKAL': u'1', 'NATCOPHARM': u'1', 'PEACOCKIND': u'1', 'ADORWELD': u'1', 'TTL': u'2', 'JAIBALAJI': u'1', 'ALLCARGO': u'1', 'ELGIEQUIP': u'1', 'PRISMCEM': u'1', 'GRASIM': u'1', 'WILLAMAGOR': u'1', 'AHMEDFORGE': u'1', 'POCHIRAJU': u'1', 'GLORY': u'1', 'BRITANNIA': u'1', 'DYNAMATECH': u'1', 'NFL': u'2', 'GEODESIC': u'1', 'NIPPOBATRY': u'1', 'DISHTV': u'1', 'ATUL': u'2', 'WANBURY': u'1', 'PEARLPOLY': u'1', 'RAJTV': u'1', 'KIRIDYES': u'1', 'IGL': u'2', 'UNIPLY': u'1', 'ASIANELEC': u'1', 'WIPRO': u'1', 'RELIANCE': u'2', 'ORIENTPRES': u'1', 'ASHOKLEY': u'1', 'MRPL': u'1', 'ULTRACEMCO': u'1', 'TATAMOTORS': u'1', 'SPICETELE': u'1', 'RSYSTEMS': u'1', 'VALECHAENG': u'1', 'AMBICAAGAR': u'1', 'NICCO': u'2', 'MUNJALSHOW': u'1', 'PUNJABCHEM': u'1', 'CALSOFT': u'1', 'EIDPARRY': u'1', 'INDLMETER': u'1', 'ARVIND': u'2', 'NOIDATOLL': u'1', 'LLOYDFIN': u'1', 'VARDHACRLC': u'1', 'INDUSINDBK': u'1', 'PRECOT': u'2', 'NANDAN': u'2', 'DENORA': u'1', 'APARINDS': u'1', 'PIRHEALTH': u'1', 'BHARTIARTL': u'1', 'MYSORECEM': u'1', 'CONCOR': u'1', 'EKC': u'2', 'KOTHARIPRO': u'1', 'PEPL': u'1', 'CTE': u'2', 'CUBEXTUB': u'1', 'GEMINI': u'1', 'HITACHIHOM': u'1', 'TTML': u'1', 'MANINDS': u'1', 'WEBELSOLAR': u'1', 'VTL': u'1', 'PRIMESECU': u'1', 'BRIGADE': u'1', 'TATAMETALI': u'1', 'EDELWEISS': u'2', 'GAEL': u'1', 'ROHITFERRO': u'1', 'EDUCOMP': u'1', 'JSL': u'1', 'MANALU': u'2', 'VSTIND': u'1', 'TEXMACOLTD': u'1', 'BSL': u'2', 'OMAXE': u'1', 'SPARC': u'1', 'SIEMENS': u'1', 'JKPAPER': u'1', 'GUFICBIO': u'1', 'GUJSIDHCEM': u'1', 'INDOTECH': u'1', 'FTCPOF5YGR': u'1', 'INDOASIFU': u'1', 'SHASUNCHEM': u'1', 'SRHHYPOLTD': u'1', 'MIRZAINT': u'1', 'SUPRAJIT': u'1', 'INOXLEISUR': u'1', 'MARICO': u'2', 'TVSSRICHAK': u'1', 'INDIANCARD': u'1', 'ZODIACLOTH': u'1', 'PLETHICO': u'1', 'ALEMBICLTD': u'1', 'BANKBARODA': u'1', 'JAYBARMARU': u'1', 'SPIC': u'2', 'UNITY': u'2', 'SINTEX': u'1', 'NETWORK18': u'1', 'DALMIACEM': u'1', 'SURANACORP': u'1', 'QGOLDHALF': u'1', 'JINDALSAW': u'1', 'GITANJALI': u'1', 'MVL': u'2', 'HDIL': u'1', 'TAINWALCHM': u'1', 'PNBGILTS': u'1', 'KOPDRUGS': u'1', 'OPTOCIRCUI': u'1', 'BOMDYEING': u'1', 'EDL': u'2', 'ATNINTER': u'1', 'COREPROTEC': u'1', 'NAHARINDUS': u'1', 'BIRLAERIC': u'1', 'LML': u'2', 'ASIANTILES': u'1', 'CANFINHOME': u'1', 'MORARJETEX': u'1', 'SIYSIL': u'1', 'NEPCMICON': u'1', 'HINDALCO': u'1', 'GMDCLTD': u'1', 'SEJALGLASS': u'1', 'SHLAKSHMI': u'1', 'MARALOVER': u'1', 'CAROLINFO': u'1', 'AREVAT&D': u'1', 'LUMAXAUTO': u'1', 'VISHALEXPO': u'1', 'ABAN': u'2', 'SUNTV': u'1', 'STER': u'2', 'SICAGEN': u'1', 'VIJAYABANK': u'1', 'PRITHVI': u'2', 'MSKPROJ': u'1', 'NITCO': u'1', 'PAREKHPLAT': u'1', 'IVRCLINFRA': u'1', 'MICROTECH': u'1', 'INDBANK': u'2', 'BELCERAMIC': u'1', 'INDOCO': u'2', 'ASIL': u'2', 'INDUSFILA': u'1', 'TV-18': u'1', 'JINDRILL': u'1', 'HTMTGLOBAL': u'1', 'AMBIKCO': u'1', 'SKMEGGPROD': u'1', 'LIBERTSHOE': u'1', 'RIIL': u'1', 'SUZLON': u'2', 'MAHSEAMLES': u'1', 'BHAGWATIHO': u'1', 'KCPSUGIND': u'1', 'TRENT': u'1', 'NUCLEUS': u'1', 'KANORICHEM': u'1', 'POLARIS': u'2', 'RANEHOLDIN': u'1', 'AVAYAGCL': u'1', 'AVENTIS': u'2', 'HINDOILEXP': u'1', 'ABB': u'2', 'ZYLOG': u'1', 'JETAIRWAYS': u'1', 'ANIKINDS': u'1', 'ITDCEM': u'1', 'ICIL': u'1', 'ORIENTPPR': u'1', 'GTNIND': u'1', 'JAYSREETEA': u'1', 'BANG': u'1', 'MONNETISPA': u'1', 'EVEREADY': u'2', 'ALKYLAMINE': u'1', 'TECHM': u'1', 'IILTD': u'1', 'BBTC': u'1', 'TATASPONGE': u'1', 'FCSSOFT': u'1', 'TFL': u'2', 'SHRIRAMEPC': u'1', 'SATYAMCOMP': u'1', 'BIRLAPOWER': u'1', 'CERA': u'2', 'ROLTA': u'2', 'MSPL': u'1', 'ALKALI': u'2', 'TANLA': u'1', 'WABCO-TVS': u'1', 'SUDARSCHEM': u'1', 'BFUTILITIE': u'1', 'INDIANHUME': u'1', 'PNC': u'2', 'PNB': u'2', '3IINFOTECH': u'1', 'NORBTEAEXP': u'1', 'UNICHEMLAB': u'1', 'GMRINDS': u'2', 'PAPERPROD': u'1', 'MANAKSIA': u'2', 'JINDALSTEL': u'1', 'HANUNG': u'1', 'SPENTEX': u'1', 'MIC': u'2', 'PGHH': u'1', 'GRUH': u'1', 'ONMOBILE': u'1', 'ERAINFRA': u'1', 'HIMATSEIDE': u'1', 'HILTON': u'1', 'NOCIL': u'1', 'SANGHIIND': u'1', 'DISHMAN': u'1', 'IGPL': u'1', 'BLKASHYAP': u'1', 'LLOYDSTEEL': u'1', 'MMFL': u'1', 'GODFRYPHLP': u'1', 'SBIN': u'1', 'CHEMPLAST': u'1', 'ACE': u'2', 'SIL': u'2', 'IMPAL': u'1', 'KOHINOOR': u'1', 'ASTRAMICRO': u'1', 'GODREJCP': u'1', 'BALRAMCHIN': u'1', 'TATACOFFEE': u'1', 'INDORAMA': u'1', 'SAKSOFT': u'1', 'HBSTOCK': u'1', 'NESCO': u'1', 'KOUTONS': u'1', 'BEPL': u'1', 'RENUKA': u'1', 'DONEAR': u'1', 'FEDERALBNK': u'1', 'CHI': u'2', 'CELEBRITY': u'1', 'ICRA': u'1', 'ASAL': u'2', 'IDEA': u'2', 'BASF': u'1', 'KIRLOSOIL': u'1', 'MADHAV': u'2', 'HIKAL': u'2', 'STEELTUBES': u'1', 'SAREGAMA': u'1', 'IDFC': u'2', 'DABUR': u'2', 'PHOENIXLMP': u'1', 'TATACHEM': u'1', 'MAARSOFTW': u'1', 'DCMFINSERV': u'1', 'SUJANATOW': u'1', 'LUMAXIND': u'1', 'KSBPUMPS': u'1', 'CAIRN': u'1', 'BCCL': u'1', 'ECEIND': u'1', 'HOVS': u'1', 'MELSTAR': u'2', 'KOTHARIPET': u'1', 'BLUEDART': u'1', 'AZTECSOFT': u'1', 'PATSPINLTD': u'1', 'SURYAJYOTI': u'1', 'SURANAIND': u'1', 'KEYCORPSER': u'1', 'DUNCANSIND': u'1', 'SUNCLAYTON': u'1', 'GOKEX': u'1', 'STAR': u'2', 'OCL': u'2', 'SANWARIA': u'1', 'INDRAMEDCO': u'1', 'ALPHAGEO': u'1', 'MICRO': u'2', 'MALCO': u'1', 'BLBLtd': u'0', 'HINDDORROL': u'1', 'GLAXO': u'2', 'FTCSF3YDIV': u'1', 'JINDALSWHL': u'1', 'ADSL': u'1', 'KSK': u'1', 'WSI': u'2', 'NELCAST': u'1', 'KPRMILL': u'1', 'PRICOL': u'1', 'FINANTECH': u'1', 'HMT': u'1', 'KALPATPOWR': u'1', 'SPSL': u'1', 'VARUN': u'2', 'BIRLACOT': u'1', 'NATNLSTEEL': u'1', 'JKLAKSHMI': u'1', 'MAGMA': u'1', 'ABGSHIP': u'1', 'GOLDSHARE': u'1', 'GABRIEL': u'1', 'TATAELXSI': u'1', 'REDINGTON': u'1', 'HCLTECH': u'1', 'KAUSHALYA': u'1', 'CIMCOBIRLA': u'1', 'AFL': u'1', 'VISHALRET': u'1', 'BEML': u'1', 'PHOENIXLTD': u'1', 'CINEVISTA': u'1', 'MEDIA': u'2', 'KIL': u'2', 'NEYVELILIG': u'1', 'PETRONENGG': u'1', 'AKRUTI': u'1', 'FOURSOFT': u'1', 'GANESHHOUC': u'1', 'HEXAWARE': u'1', 'FINCABLES': u'1', 'JBMA': u'1', 'ARIHANT': u'2', 'MAGNUM': u'2', 'NAHARSPING': u'1', 'SEAMECLTD': u'1', 'MANUGRAPH': u'2', 'JAYAGROGN': u'1', 'HITECHGEAR': u'1', 'BHARATGEAR': u'1', 'BIOCON': u'1', 'VENKEYS': u'1', 'INFOSYSTCH': u'1', 'IFBAGRO': u'1', 'GAMMNINFRA': u'1', 'FIRSTLEASE': u'1', 'WOCKPHARMA': u'1', 'UNIENTER': u'1', 'TRIGYN': u'1', 'BSELINFRA': u'1', 'NTPC': u'1', 'ANGAUTO': u'1', 'ONWARDTEC': u'1', 'SURYAROSNI': u'1', 'TNPETRO': u'1', 'SWARAJMAZD': u'1', 'TODAYS': u'1', 'KABRAEXTRU': u'1', 'ANKURDRUGS': u'1', 'HCC': u'1', 'TINPLATE': u'1', 'JISLJALEQS': u'1', 'ESSELPACK': u'1', 'ANTGRAPHIC': u'1', 'PDUMJEIND': u'1', 'ORCHIDCHEM': u'1', 'PARACABLES': u'1', 'SIMBHSUGAR': u'1', 'KERNEX': u'1', 'BOSCHLTD': u'1', 'APIL': u'1', 'CHETTINAD': u'1', 'ISMTLTD': u'1', 'TUBEINVEST': u'1', 'IRB': u'1', 'GRANULES': u'1', 'MUKANDENGG': u'1', 'PVR': u'1', 'SESHAPAPER': u'1', 'FDC': u'2', 'DEWANHOUS': u'1', 'SANGHVIMOV': u'1', 'STARPAPER': u'1', 'VISAKAIND': u'1', 'VINCARDS': u'1', 'M&MFIN': u'1', 'NIFTYBEES': u'1', 'AXISBANK': u'1', 'UCALFUEL': u'1', 'BILPOWER': u'1', 'APOLLOHOSP': u'1', 'KOPRAN': u'2', 'KOTAKPSUBK': u'1', 'ATLANTA': u'1', 'IPCALAB': u'1', 'AARTIDRUGS': u'1', 'RML': u'2', 'ADHUNIK': u'1', 'TRIL': u'1', 'RAINCOM': u'1', 'BBL': u'1', 'VISESHINFO': u'1', 'RELIGARE': u'2', 'IBN18': u'1', 'MID-DAY': u'1', 'KEC': u'2', 'GTNTEX': u'2', 'GTL': u'2', 'JKIL': u'1', 'SELMCL': u'1', 'IDBI': u'2', 'SKFINDIA': u'1', 'GENUSPOWER': u'1', 'INVSTSMART': u'1', 'ELDERPHARM': u'1', 'ALOKTEXT': u'1', 'MUKTAARTS': u'1', 'TRIVENI': u'2', 'TATAINVEST': u'1', 'ELECTHERM': u'1', 'INDOWIND': u'1', 'CLUTCHAUTO': u'1', 'CENTRALBK': u'1', 'ZEEL': u'2', 'JAGSNPHARM': u'1', 'J&KBANK': u'1', 'ITI': u'2', 'UNITECH': u'1', 'NAUKRI': u'1', 'HORIZONINF': u'1', 'ITC': u'2', 'RALLIS': u'1', 'KTKBANK': u'1', 'INDIABULLS': u'2', 'GHCL': u'1', 'TORNTPOWER': u'1', 'NEULANDLAB': u'1', 'PPAP': u'2', 'VIJSHAN': u'1', 'BASML': u'1', 'NAGARFERT': u'1', 'VISUINTL': u'1', 'FMGOETZE': u'1', 'DHAMPURSUG': u'1', 'SHALPAINTS': u'1', 'RANASUG': u'1', 'GODREJIND': u'2', 'AMBUJACEM': u'1', 'ANANTRAJ': u'1', 'RAMCOIND': u'1', 'ASTRAZEN': u'1', 'DTIL': u'2', 'M&M': u'2', 'JHS': u'1', 'JMCPROJECT': u'1', 'CORDSCABLE': u'1', 'VITLINFO': u'1', 'SOFTTECHGR': u'1', 'DCMSRMCONS': u'1', 'BALKRISIND': u'1', 'CROMPGREAV': u'1', 'HOCL': u'1', 'RUCHISOYA': u'1', 'COMPUTECH': u'2', 'RSWM': u'1', '20MICRONS': u'1', 'SILINV': u'1', 'RECLTD': u'1', 'SUNDARMFIN': u'1', 'FTCSF5YDIV': u'1', 'ABSHEKINDS': u'1', 'UPERGANGES': u'1', 'DREDGECORP': u'1', 'KRISHNAENG': u'1', 'JCTEL': u'2', 'VALUEIND': u'1', 'BAJAJHLDNG': u'1', 'SELAN': u'1', 'CASTROL': u'2', 'CHOLADBS': u'1', 'PAGEIND': u'1', 'CUMMINSIND': u'1', 'SOBHA': u'1', 'ANDHRABANK': u'1', 'MEGASOFT': u'1', 'RUCHIRA': u'1', 'ADVANIHOTR': u'1', 'PARSVNATH': u'1', 'BIL': u'2', 'PVP': u'1', 'KOTAKBANK': u'1', 'NDTV': u'1', 'GARDENSILK': u'1', 'RELGOLD': u'1', 'VIDEOIND': u'1', 'HONAUT': u'1', 'MLL': u'1', 'HINDSANIT': u'1', 'INDIAGLYCO': u'1', 'RBL': u'2', 'LAKSHVILAS': u'1', 'INDSWFTLTD': u'1', 'NAGARCONST': u'1', 'DENABANK': u'1', 'GOACARBON': u'1', 'RATNAMANI': u'1', 'DHANUS': u'1', 'SUBHASPROJ': u'1', 'RJL': u'1', 'OTL': u'2', 'GILLETTE': u'1', 'UFLEX': u'1', 'HCL-INSYS': u'1', 'NRC': u'2', 'BANCOINDIA': u'1', 'YESBANK': u'1', 'NOVOPANIND': u'1', 'PIDILITIND': u'1', 'MOREPENLAB': u'1', 'PRAJIND': u'1', 'KANSAINER': u'1', 'HTMEDIA': u'1', 'ALLSEC': u'1', 'EIMCOELECO': u'1', 'PUNJABTRAC': u'1', 'BANSWRAS': u'1', 'FACT': u'2', 'DWARKESH': u'1', 'SURAJDIAMN': u'1', 'MOSERBAER': u'1', 'IBREALEST': u'1', 'GVKPIL': u'1', 'SRGINFOTEC': u'1', 'CENTUM': u'2', 'MATRIXLABS': u'1', 'GULFOILCOR': u'1', 'BALLARPUR': u'2', '3MINDIA': u'1', 'PENINLAND': u'1', 'ORIENTHOT': u'1', 'NAHARINVST': u'1', 'FOSECOIND': u'1', 'ICSA': u'1', 'ESSARSHIP': u'1', 'SUBEX': u'1', 'ADVANTA': u'2', 'SIMPLEX': u'2', 'GUJFLUORO': u'1', 'FORTIS': u'2', 'INGVYSYABK': u'1', 'LUMAXTECH': u'1', 'DCM': u'2', 'MURLIIND': u'1', 'CREWBOS': u'1', 'RELCAPITAL': u'1', 'LITL': u'1', 'DIGJAM': u'1', 'JUNIORBEES': u'1', 'BERGEPAINT': u'1', 'DCB': u'1', 'BROADCAST': u'2', 'RUCHINFRA': u'1', 'NUCHEM': u'1', 'EICHERMOT': u'1', 'SABTN': u'1', 'ORIENTBANK': u'1', 'DCW': u'1', 'JSWSTEEL': u'1', 'TELEDATAGL': u'1', 'MADRASCEM': u'1', 'SONASTEER': u'1', 'RPGCABLES': u'1', 'EUROCERA': u'1', 'RANEENGINE': u'1', 'GALLANTT': u'2', 'JMTAUTOLTD': u'1', 'HINDSYNTEX': u'1', 'BATLIBOI': u'1', 'KESORAMIND': u'1', 'FEDDERLOYD': u'1', 'WELGUJ': u'1', 'UMITL': u'1', 'DHANBANK': u'1', 'DECCANCE': u'1', 'NAVNETPUBL': u'1', 'WENDT': u'1', 'COREEMBLG': u'1', 'CHENNPETRO': u'1', 'LOKESHMACH': u'1', 'SUNPHARMA': u'1', 'WELSPUNIND': u'1', 'BARTRONICS': u'1', 'DSKULKARNI': u'1', 'KEI': u'2', 'HARRMALAYA': u'1', 'TULIP': u'1', 'MRO-TEK': u'1', 'FTCPOF3YGR': u'1', 'JMFINANCIL': u'1', 'SHRIRAMCIT': u'1', 'MARUTI': u'2', 'VIKASHMET': u'1', 'AFTEK': u'2', 'HINDUJAFO': u'1', 'PRAENG': u'1', 'ZUARIAGRO': u'1', 'NAGREEKEXP': u'1', 'NAHARCAP': u'1', 'ASTRAL': u'1', 'NIITTECH': u'1', 'WINDSOR': u'2', 'KKCL': u'1', 'HCIL': u'1', 'VIPIND': u'1', 'INDHOTEL': u'1', 'SHIVAMAUTO': u'1', 'IFBIND': u'1', 'MONSANTO': u'1', 'SHIVTEX': u'1', 'BPCL': u'1', 'LAKSHMIEFL': u'1', 'ALCHEM': u'2', 'SUPREMETEX': u'1', 'ASHAPURMIN': u'1', 'SUNFLAG': u'1', 'TVTODAY': u'1', 'ADLABSFILM': u'1', 'SARLAPOLY': u'1', 'VAKRANSOFT': u'1', 'AMAR': u'2', 'KRBL': u'1', 'EXCELCROP': u'1', 'NIITLTD': u'1', 'CENTURYTEX': u'1', 'LIQUIDBEES': u'1', 'SOMATEX': u'1', 'IBSEC': u'1', 'LOGIXMICRO': u'1', 'NECLIFE': u'1', 'MANGLMCEM': u'1', 'VLSFINANCE': u'1', 'TCS': u'2', 'TULSI': u'1', 'SUBROS': u'1', 'SHYAMTEL': u'2', 'CRESTANI': u'1', 'AMARAJABAT': u'1', 'SSWL': u'1', 'GUJAPOLLO': u'1', 'TCI': u'2', 'INEABS': u'1', 'DPSCLTD': u'1', 'WHEELS': u'2', 'ALFALAVAL': u'1', 'AUSTRAL': u'1', 'VENUSREM': u'1', 'PONNIERODE': u'1', 'RPGLIFE': u'1', 'GNFC': u'1', 'AEGISCHEM': u'1', 'RAJRAYON': u'1', 'LUPIN': u'2', 'ORIENTABRA': u'1', 'GINNIFILA': u'1', 'CREATIVEYE': u'1', 'ONGC': u'1', 'GKW': u'2', 'BINANIIND': u'1', 'SUVEN': u'2', 'PIRLIFE': u'1', 'AUTOLITIND': u'1', 'KHAITANLTD': u'1', 'PATELENG': u'1', 'ABHISHEK': u'1', 'ASSAMCO': u'1', 'ORIENTCERA': u'1', 'GUJALKALI': u'1', 'SAPL': u'1', 'INFOTECENT': u'1', 'TORNTPHARM': u'1', 'PSL': u'2', 'PBAINFRA': u'1', 'MANGCHEFER': u'1', 'EMAMILTD': u'1', 'DHARSUGAR': u'1', 'BHUSANSTL': u'1', 'SHAHALLOYS': u'1', 'IFCI': u'1', 'HITECHPLAS': u'1', 'WWIL': u'1', 'PRAKASH': u'2', 'CAMLIN': u'2', 'RCOM': u'2', 'SAVITACHEM': u'1', 'CYBERTECH': u'1', 'KARURVYSYA': u'1', 'TIRUMALCHM': u'1', 'AUTOAXLES': u'1', 'GSSAMERICA': u'1', 'GRINDWELL': u'2', 'KOTAKGOLD': u'1', 'SURYAPHARM': u'1', 'FSL': u'2', 'MTNL': u'1', 'UTTAMSUGAR': u'1', 'ETC': u'2', 'PANTALOONR': u'1', 'BRFL': u'1', 'OMAXAUTO': u'1', 'ARIES': u'1', 'JYOTHYLAB': u'1', 'MARKSANS': u'1', 'TATAMTRDVR': u'1', 'GLOBALVECT': u'1', 'AARVEEDEN': u'1', 'OFSS': u'1', 'TATAPOWER': u'1', 'JIKIND': u'2', 'SESAGOA': u'1', 'ASHIMASYN': u'1', 'REMSONSIND': u'1', 'MAHSCOOTER': u'1', 'EMKAY': u'2', 'BLUESTINFO': u'1', 'SOUTHBANK': u'1', 'ENERGYDEV': u'1', 'SUMMIT': u'2', 'FTCPOF3YDV': u'1', 'POLYPLEX': u'1', 'TNPL': u'2', 'SALSTEEL': u'1', 'ELECON': u'2', 'DECOLIGHT': u'1', 'TIIL': u'1', 'KALYANIFRG': u'1', 'WSTCSTPAPR': u'1', 'FIRSTWIN': u'1', 'SRF': u'2', 'MACMILLAN': u'1', 'JOCIL': u'1', 'NUTEK': u'1', 'PIONEEREMB': u'1', 'STERTOOLS': u'1', 'NELCO': u'1', 'SANGHIPOLY': u'1', 'LPDC': u'1', 'MCDOWELL-N': u'1', 'HEG': u'1', 'SRTRANSFIN': u'1', 'POWERGRID': u'1', 'MANALIPETC': u'1', 'SUNDRMBRAK': u'1', 'GPELECT': u'1', 'UCOBANK': u'1', 'TECHNOELEC': u'1', 'HOPFL': u'1', 'HINDMOTOR': u'2', 'CADILAHC': u'1', 'REVATHI': u'2', 'HEROHONDA': u'1', 'EXCELINDUS': u'1', 'ZEENEWS': u'1', 'IOB': u'2', 'AXIS-IT&T': u'1', 'RAMSARUP': u'1', 'LGBFORGE': u'1', 'SOLEMS': u'1', 'MINDTREE': u'1', 'PETRONET': u'2', 'SUNDRMFAST': u'1', 'SURANATELE': u'1', 'KHANDSE': u'1', 'XLTL': u'1', 'SAIL': u'1', 'HOTELRUGBY': u'1', 'SREINTFIN': u'1', 'RELBANK': u'1', 'PAEL': u'1', 'TIMESGTY': u'1', 'ALBK': u'2', 'GOLDTECH': u'2', 'STERLINBIO': u'1', 'SUNILHITEC': u'1', 'AIAENG': u'1', 'ESSAROIL': u'1', 'ARCHIDPLY': u'1', 'VIMTALABS': u'1', 'RCF': u'1', 'SHOPERSTOP': u'1', 'IGARASHI': u'1', 'SHANTIGEAR': u'1', 'MAHLIFE': u'1', 'SUPERSPIN': u'1', 'KALINDEE': u'1', 'VINDHYATEL': u'1', 'RAJESHEXPO': u'1', 'SHARRESLTD': u'1', 'ZENITHCOMP': u'1', 'SAKUMA': u'1', 'NOVAPETRO': u'2', 'JENSONICOL': u'1', 'LT': u'2', 'HAVELLS': u'1', 'SANGAMIND': u'1', 'LICHSGFIN': u'1', 'GREAVESCOT': u'1', 'LGBROS': u'1', 'GTLINFRA': u'1', 'RADAAN': u'1', 'NATIONALUM': u'1', 'UNIPHOS': u'2', 'ANSALINFRA': u'1', 'CRISIL': u'1', 'GMRFER': u'1', 'SOFTPRO': u'1', 'BAJAUTOFIN': u'1', 'INFOMEDIA': u'2', 'SURYALAXMI': u'1', 'BGRENERGY': u'1', 'CESC': u'1', 'BAJAJFINSV': u'1', 'CANBK': u'1', 'HYDRBADIND': u'1', 'AKSHOPTFBR': u'1', 'MUNDRAPORT': u'1', 'ISPATIND': u'1', 'SWARAJENG': u'1', 'MADHUCON': u'1', 'SUJANAUNI': u'1', 'MALWACOTT': u'1', 'UTISUNDER': u'1', 'MADRASFERT': u'1', 'ROHLTD': u'1', 'RAYMOND': u'2', 'OISL': u'1', 'BPL': u'2', 'BANKBEES': u'1', 'CHESLINTEX': u'1', 'JAYNECOIND': u'1', 'REGENCERAM': u'1', 'ALMONDZ': u'1', 'ALPA': u'2', 'SIMPLEXINF': u'1', 'JAGRAN': u'1', 'ZODJRDMKJ': u'1', 'THERMAX': u'1', 'ARL': u'2', 'RADICO': u'2', 'GOLDINFRA': u'1', 'GOLDBEES': u'1', 'DIVISLAB': u'1', 'PREMIER': u'2', 'PLASTIBLEN': u'1', 'TATATEA': u'1', 'SAMTEL': u'2', 'BALAMINES': u'1', 'CARBORUNIV': u'1', 'BLUECHIP': u'1', 'JPHYDRO': u'1', 'TNTELE': u'1', 'PSUBNKBEES': u'1', 'EVINIX': u'1', 'TIL': u'2', 'CCL': u'2', 'ROMAN': u'2', 'ASIANHOTEL': u'1', 'CONSOFINVT': u'1', 'INGERRAND': u'1', 'VARDMNPOLY': u'1', 'EVERESTIND': u'1', 'BOC': u'1', 'MRF': u'2', 'RANBAXY': u'1', 'MPHASIS': u'1', 'BLUESTARCO': u'1', 'CIPLA': u'1', 'KLGSYSTEL': u'1', 'GIPCL': u'1', 'HBLPOWER': u'1', 'CLASSIC': u'2', 'TOKYOPLAST': u'1', 'MAXWELL': u'1', 'CEATLTD': u'1', 'SRHHLINDST': u'1', 'HINDPETRO': u'1', 'BLUEBIRD': u'1', 'NIRMA': u'2', 'VOLTAMP': u'1', 'BURNPUR': u'1', 'RMCL': u'2', 'CLNINDIA': u'1', 'TRICOM': u'1', 'IOC': u'2', 'SITASHREE': u'1', 'BANKRAJAS': u'1', 'OCTAV': u'1', 'KFA': u'1', 'ARCHIES': u'2', 'ANSALHSG': u'1', 'SASKEN': u'1', 'NUCENT': u'2', 'EIHAHOTELS': u'1', 'BVCL': u'1', 'PHILIPCARB': u'1', 'ENTEGRA': u'1', 'PATINTLOG': u'1', 'SABERORGAN': u'1', 'NITINFIRE': u'1', 'AICHAMP': u'1', 'FAME': u'1', 'KAVVERITEL': u'1', 'STCINDIA': u'1', 'RAJSREESUG': u'1', 'VESUVIUS': u'1', 'BIRLACORPN': u'1', 'OILCOUNTUB': u'1', 'REPRO': u'2', 'MIRCELECTR': u'1', 'JDORGOCHEM': u'1', 'INDIAINFO': u'1', 'SANDESH': u'1', 'SIRPAPER': u'1', 'PFIZER': u'1', 'MURUDCERA': u'1', 'LAXMIMACH': u'1', 'EXIDEIND': u'1', 'INDSWFTLAB': u'1', 'SGFL': u'1', 'BANKINDIA': u'1', 'KHAITANELE': u'1', 'PROVOGUE': u'2', 'LLOYDELENG': u'1', 'BHARATFORG': u'1', 'JBCHEPHARM': u'1', 'D-LINK': u'2', 'JKTYRE': u'1', 'GOLDIAM': u'1', 'PANACEABIO': u'1', 'SAMBHAAV': u'1', 'NBVENTURES': u'1', 'ASIANPAINT': u'1', 'ENIL': u'1', 'AROGRANITE': u'1', 'NILKAMAL': u'1', 'KESARENT': u'1', 'VAIBHAVGEM': u'1', 'JUBILANT': u'2', 'BHAGYNAGAR': u'1', 'ESSDEE': u'1', 'HOTELEELA': u'1', 'PTL': u'2', 'SCI': u'2', 'WINSOMYARN': u'1', 'UTTAMSTL': u'1', 'UTVSOF': u'2', 'JKCEMENT': u'1', 'CENTURYPLY': u'1', 'PTC': u'2', 'KAKATCEM': u'1', 'TIDEWATER': u'1', 'AUTOIND': u'1', 'HONDAPOWER': u'1', 'LCCINFOTEC': u'1', 'BINDALAGRO': u'1', 'HIRECT': u'1', 'KSCL': u'1', 'KMSUGAR': u'1', 'ALPSINDUS': u'1', 'TAJGVK': u'1', 'KINETICMOT': u'1', 'IVRPRIME': u'1', 'MBECL': u'1', 'SHREECEM': u'1', 'FIEMIND': u'1', 'DEEPAKFERT': u'1', 'EASTSILK': u'1', 'TATASTEEL': u'1', 'KALECONSUL': u'1', 'GSPL': u'1', 'PARAL': u'1', 'RSSOFTWARE': u'1', 'UBL': u'2', 'CELESTIAL': u'1', 'NMDC': u'1', 'ADANIENT': u'1', 'ASHCO': u'2', 'AMDIND': u'1', 'IOLN': u'1', 'JBFIND': u'1', 'PDUMJEPULP': u'1', 'BHARTISHIP': u'1', 'FTCSF3YGRO': u'1', 'GLENMARK': u'2', 'DYNACONS': u'2', 'KAJARIACER': u'1', 'RNRL': u'1', 'IVC': u'2', 'MUDRA': u'1', 'CENTENKA': u'1', 'ORGINFO': u'1', 'NRBBEARING': u'1', 'GTOFFSHORE': u'1', 'PURVA': u'1', 'HINDZINC': u'1', 'ICICIBANK': u'1', 'GUJRATGAS': u'1', 'IVP': u'2', 'KCP': u'2', 'JYOTISTRUC': u'1', 'SHREYAS': u'1', 'MCDHOLDING': u'1', 'CYBERMEDIA': u'1', 'RKFORGE': u'1', 'ACC': u'2', 'NAGREEKCAP': u'1', 'APTECHT': u'1', 'MAHINDFORG': u'1', 'AARTIIND': u'1', 'ELECTCAST': u'1', 'SIGROUPIND': u'1', 'MOTOGENFIN': u'1', 'BAJAJHIND': u'1', 'STINDIA': u'2', 'MUKANDLTD': u'1', 'SALORAINTL': u'1', 'DAAWAT': u'1', 'IFGLREFRAC': u'1', 'ZANDUPHARM': u'1', 'GARWOFFS': u'1', 'KSERAPRO': u'1', 'BRABOURNE': u'1', 'SKUMARSYNF': u'1', 'DRREDDY': u'1', 'UBHOLDINGS': u'1', 'MASTEK': u'1', 'PATNI': u'1', 'TFCILTD': u'1', 'FAGBEARING': u'1', 'BALPHARMA': u'1', 'FTCSF5YGRO': u'1', 'RELINFRA': u'1', 'IBRETAILS': u'1', 'ORIENTINFO': u'1', 'ZENITHEXPO': u'1', 'CCCL': u'1', 'NITINSPIN': u'1', 'INDNIPPON': u'1', 'GLODYNE': u'1', 'AGRODUTCH': u'1', 'PUNJLLOYD': u'1', 'BHARATRAS': u'1', 'KAMATHOTEL': u'1', 'GOKUL': u'1', 'KOTARISUG': u'1', 'SOLAREX': u'1', 'EASUNREYRL': u'1', 'GPIL': u'1', 'MOTHERSUMI': u'1', 'FCH': u'2', 'MERCK': u'1', 'CUB': u'2', 'GEOJIT': u'2', 'GARWALLROP': u'1', 'TIMETECHNO': u'1', 'GWALCHEM': u'1', 'VARUNSHIP': u'1', 'BATAINDIA': u'1', 'GOLDENTOBC': u'1', 'HDFCBANK': u'1', 'RICOAUTO': u'1', 'BALMLAWRIE': u'1', 'POLARIND': u'1', 'PANORAMUNI': u'1', 'KALSTEELS': u'1', 'MAYTASINFR': u'1', 'NAVINFLUOR': u'1', 'SMSPHARMA': u'1', 'PITTILAM': u'1', 'THOMASCOOK': u'1', 'GSFC': u'1', 'GDL': u'1', 'SAKHTISUG': u'1', 'QNIFTY': u'1', 'RAJVIR': u'1', 'ATFL': u'1', 'INDIACEM': u'1', 'SAGCEM': u'1', 'EIHOTEL': u'1', 'MOTILALOFS': u'1', 'COROMNFERT': u'1', 'TWL': u'1', 'STRTECH': u'1', 'SHIV-VANI': u'1', 'EUROTEXIND': u'1', 'JINDALPOLY': u'1', 'REIAGROLTD': u'1', 'APCOTEXIND': u'1', 'TANTIACONS': u'1', 'TIMKEN': u'1', 'DELTACORP': u'1', 'TATACOMM': u'1', 'RESURGERE': u'2', 'CORPBANK': u'1', 'RPL': u'2', 'WYETH': u'2', 'CHAMBLFERT': u'1', 'JAINSTUDIO': u'1', 'APPAPER': u'1', 'HERCULES': u'1', 'TITAN': u'2', 'AMTEKINDIA': u'1', 'OMNITECH': u'1', 'LAKPRE': u'1', 'VINYLINDIA': u'1', 'GLFL': u'1', 'SGL': u'2', 'THIRUSUGAR': u'1', 'XPROINDIA': u'1', 'BAJAJ-AUTO': u'1', 'SADBHAV': u'2', 'SHREEASHTA': u'1', 'GREENPLY': u'1', 'GSKCONS': u'1', 'ICI': u'2', 'ESABINDIA': u'1', 'BHEL': u'1', 'MAHINDUGIN': u'1', 'SPLIL': u'1', 'JAYPEEHOT': u'1', 'BINANICEM': u'1', 'OUDHSUG': u'1', 'GATI': u'2', 'BONGAIREFN': u'1', 'CANDC': u'1', 'GANGOTRI': u'2', 'INDIANB': u'1', 'BLUECOAST': u'1', 'FTCPOF5YDV': u'1', 'NUMERICPW': u'1', 'DATATECH': u'1', 'PFC': u'1', 'PEARLGLOBL': u'1', 'SATHAISPAT': u'1', 'DCHL': u'1', 'BAJAJELEC': u'1', 'LYKALABS': u'1', 'ZICOM': u'1', 'JINDALPHOT': u'1', 'GENESYS': u'1', 'BAGFILMS': u'1', 'TVSMOTOR': u'1', 'TAKE': u'1', 'AJANTPHARM': u'1', 'USHAMART': u'2', 'DABURPHARM': u'1', 'ENGINERSIN': u'1', 'RPOWER': u'1', 'NSIL': u'2', 'KGL': u'2', 'KSOILS': u'1', 'VGUARD': u'1'}

URLFetchSession = partial(URLFetch, session=session,
                          headers=headers)

derivative_history_url = partial(
    URLFetchSession(
        url='http://www1.nseindia.com/products/dynaContent/common/productsSymbolMapping.jsp?',
        headers = {**headers, **{'Referer': 'https://www1.nseindia.com/products/content/derivatives/equities/historical_fo.htm'}}
        #headers = (lambda a,b: a.update(b) or a)(headers.copy(),{'Referer': 'https://www1.nseindia.com/products/content/derivatives/equities/historical_fo.htm'})
        ),
    segmentLink=9,
    symbolCount='')

index_vix_history_url = URLFetchSession(
    url='http://www1.nseindia.com/products/dynaContent/equities/indices/hist_vix_data.jsp')

index_history_url = URLFetchSession(
    url='http://www1.nseindia.com/products/dynaContent/equities/indices/historicalindices.jsp')

equity_history_url_full = URLFetchSession(
    url='http://www1.nseindia.com/products/dynaContent/common/productsSymbolMapping.jsp')

equity_history_url = partial(equity_history_url_full,
                             dataType='PRICEVOLUMEDELIVERABLE',
                             segmentLink=3, dateRange="")

symbol_count_url = URLFetchSession(
    url='http://www1.nseindia.com/marketinfo/sym_map/symbolCount.jsp')

def nsesymbolpurify(symbol):
    symbol = symbol.replace('&','%26') #URL Parse for Stocks Like M&M Finance
    return symbol

def nsefetch(payload, headers=headers):
    try:
        output = requests.get(payload,headers=headers).json()
    except ValueError:
        s =requests.Session()
        output = s.get("http://nseindia.com",headers=headers)
        output = s.get(payload,headers=headers).json()
    return output

def symlist():

    positions = nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O')

    nselist=[]

    i=0
    for x in range(i, len(positions['data'])):
        nselist=nselist+[positions['data'][x]['symbol']]

    return nselist

def nse_optionchain_scrapper(symbol):
    symbol = nsesymbolpurify(symbol)
    if any(x in symbol for x in indices):
        payload = nsefetch('https://www.nseindia.com/api/option-chain-indices?symbol='+symbol, headers=opt_headers)
    else:
        payload = nsefetch('https://www.nseindia.com/api/option-chain-equities?symbol='+symbol, headers=opt_headers)
    return payload

def nse_get_fno_lot_sizes(symbol="all",mode="list"):
    url="https://archives.nseindia.com/content/fo/fo_mktlots.csv"

    if(mode=="list"):
        s=requests.get(url).text
        res_dict = {}
        for line in s.split('\n'):
          if line != '' and re.search(',', line) and (line.casefold().find('symbol') == -1):
              (code, name) = [x.strip() for x in line.split(',')[1:3]]
              res_dict[code] = int(name)
        if(symbol=="all"):
            return res_dict
        if(symbol!=""):
            return res_dict[symbol.upper()]

    if(mode=="pandas"):
        payload = pd.read_csv(url)
        if(symbol=="all"):
            return payload
        else:
            payload = payload[(payload.iloc[:, 1] == symbol.upper())]
            return payload

def nse_opts(symbol: str) -> pd.DataFrame:

    scraped = nse_optionchain_scrapper(symbol)
    raw_dict = scraped['records']['data']
    dfs = [pd.DataFrame.from_dict(raw_dict[i]).transpose()[2:] 
                for i in range(len(raw_dict))]

    df = pd.concat(dfs).drop(columns='identifier')\
                   .rename_axis('right').reset_index()

    float_cols = ['strikePrice', 'pchangeinOpenInterest', 'impliedVolatility', 
                'lastPrice', 'change', 'pChange', 'bidprice', 'askPrice' , 
                'underlyingValue' ]
    int_cols = ['openInterest', 'changeinOpenInterest', 'totalTradedVolume', 
                'totalBuyQuantity', 'totalSellQuantity', 'bidQty', 'askQty']
    df[float_cols] = df[float_cols].astype('float32')
    df[int_cols] = df[int_cols].astype('int64')
    df.loc[:, 'expiryDate'] = pd.to_datetime(df.expiryDate)

    colmap = { 'underlying': 'symbol', 'expiryDate': 'expiry', 'strikePrice': 'strike',  
            'right': 'right','underlyingValue': 'undPrice', 'openInterest': 'oi',
            'changeinOpenInterest': 'oiChange', 'pchangeinOpenInterest': 'pChangeOI',
            'totalTradedVolume': 'volume', 'totalBuyQuantity': 'totalBuyQty', 
            'totalSellQuantity': 'totalSellQty', 'pChange': 'pChange', 
            'impliedVolatility': 'opt_iv',   'lastPrice': 'lastPrice', 'change': 'change',
            'bidQty': 'bidQty', 'bidprice': 'bid', 'askPrice': 'ask', 'askQty': 'askQty',
            }

    df = df.rename(columns=colmap)[colmap.values()]
    df = df.assign(lot=nse_get_fno_lot_sizes(symbol=symbol))
    df = df.assign(opt_iv = df.opt_iv/100)
    df = df.assign(right=df.right.str[:1])
    df = df.sort_values(['expiry', 'right', 'strike'], 
                        ascending=[True, False, True]).reset_index(drop=True)


    # ..get accurate dte
    nse_tz = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(tz=nse_tz).timestamp()
    nse_tz_expiry = df.expiry.apply(lambda x: nse_tz.localize(datetime.datetime.combine(x.date(), datetime.time(18,0))).timestamp())
    dte = (nse_tz_expiry.apply(datetime.datetime.fromtimestamp) - datetime.datetime.fromtimestamp(now)).apply(datetime.timedelta.total_seconds)/24/3600
    df = df.assign(dte=dte)

    return df

def get_history(symbol, start, end, index=False, futures=False, option_type="",
                expiry_date=None, strike_price="", series='EQ'):
    """This is the function to get the historical prices of any security (index,
        stocks, derviatives, VIX) etc.

        Args:
            symbol (str): Symbol for stock, index or any security
            start (datetime.date): start date
            end (datetime.date): end date
            index (boolean): False by default, True if its a index
            futures (boolean): False by default, True for index and stock futures
            expiry_date (datetime.date): Expiry date for derivatives, Compulsory for futures and options
            option_type (str): It takes "CE", "PE", "CA", "PA" for European and American calls and puts
            strike_price (int): Strike price, Compulsory for options
            series (str): Defaults to "EQ", but can be "BE" etc (refer NSE website for details)

        Returns:
            pandas.DataFrame : A pandas dataframe object 

        Raises:
            ValueError: 
                        1. strike_price argument missing or not of type int when options_type is provided
                        2. If there's an Invalid value in option_type, valid values-'CE' or 'PE' or 'CA' or 'CE'
                        3. If both futures='True' and option_type='CE' or 'PE'
    """
    frame = inspect.currentframe()
    args, _, _, kwargs = inspect.getargvalues(frame)
    del(kwargs['frame'])
    start = kwargs['start']
    end = kwargs['end']
    if (end - start) > datetime.timedelta(130):
        kwargs1 = dict(kwargs)
        kwargs2 = dict(kwargs)
        kwargs1['end'] = start + datetime.timedelta(130)
        kwargs2['start'] = kwargs1['end'] + datetime.timedelta(1)

        t1 = ThreadReturns(target=get_history, kwargs=kwargs1)
        t2 = ThreadReturns(target=get_history, kwargs=kwargs2)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        return pd.concat((t1.result, t2.result))
    else:
        return get_history_quanta(**kwargs)

def get_history_quanta(**kwargs):
    url, params, schema, headers, scaling = validate_params(**kwargs)
    df = url_to_df(url=url,
                   params=params,
                   schema=schema,
                   headers=headers, scaling=scaling)
    return df

def url_to_df(url, params, schema, headers, scaling={}):
    resp = url(**params)
    bs = BeautifulSoup(resp.text, 'lxml')
    tp = ParseTables(soup=bs,
                     schema=schema,
                     headers=headers, index="Date")
    df = tp.get_df()
    for key, val in six.iteritems(scaling):
        df[key] = val * df[key]
    return df

def validate_params(symbol, start, end, index=False, futures=False, option_type="",
                    expiry_date=None, strike_price="", series='EQ'):
    """
                symbol = "SBIN" (stock name, index name and VIX)
                start = date(yyyy,mm,dd)
                end = date(yyyy,mm,dd)
                index = True, False (True even for VIX)
                ---------------
                futures = True, False
                option_type = "CE", "PE", "CA", "PA"
                strike_price = integer number
                expiry_date = date(yyyy,mm,dd)
    """

    params = {}

    if start > end:
        raise ValueError('Please check start and end dates')

    if (futures and not option_type) or (not futures and option_type):  # EXOR
        params['symbol'] = symbol
        params['dateRange'] = ''
        params['optionType'] = 'select'
        params['strikePrice'] = ''
        params['fromDate'] = start.strftime('%d-%b-%Y')
        params['toDate'] = end.strftime('%d-%b-%Y')
        url = derivative_history_url

        try:
            params['expiryDate'] = expiry_date.strftime("%d-%m-%Y")
        except AttributeError as e:
            raise ValueError(
                'Derivative contracts must have expiry_date as datetime.date')

        option_type = option_type.upper()
        if option_type in ("CE", "PE", "CA", "PA"):
            if not isinstance(strike_price, int) and not isinstance(strike_price, float):
                raise ValueError(
                    "strike_price argument missing or not of type int or float")
            # option specific
            if index:
                params['instrumentType'] = 'OPTIDX'
            else:
                params['instrumentType'] = 'OPTSTK'
            params['strikePrice'] = strike_price
            params['optionType'] = option_type
            schema = OPTION_SCHEMA
            headers = OPTION_HEADERS
            scaling = OPTION_SCALING
        elif option_type:
            # this means that there's an invalid value in option_type
            raise ValueError(
                "Invalid value in option_type, valid values-'CE' or 'PE' or 'CA' or 'CE'")
        else:
            # its a futures request
            if index:
                if symbol == 'INDIAVIX':
                    params['instrumentType'] = 'FUTIVX'
                else:
                    params['instrumentType'] = 'FUTIDX'
            else:
                params['instrumentType'] = 'FUTSTK'
            schema = FUTURES_SCHEMA
            headers = FUTURES_HEADERS
            scaling = FUTURES_SCALING
    elif futures and option_type:
        raise ValueError(
            "select either futures='True' or option_type='CE' or 'PE' not both")
    else:  # its a normal request

        if index:
            if symbol == 'INDIAVIX':
                params['fromDate'] = start.strftime('%d-%b-%Y')
                params['toDate'] = end.strftime('%d-%b-%Y')
                url = index_vix_history_url
                schema = VIX_INDEX_SCHEMA
                headers = VIX_INDEX_HEADERS
                scaling = VIX_SCALING
            else:
                if symbol in DERIVATIVE_TO_INDEX:
                    params['indexType'] = DERIVATIVE_TO_INDEX[symbol]
                else:
                    params['indexType'] = symbol
                params['fromDate'] = start.strftime('%d-%m-%Y')
                params['toDate'] = end.strftime('%d-%m-%Y')
                url = index_history_url
                schema = INDEX_SCHEMA
                headers = INDEX_HEADERS
                scaling = INDEX_SCALING
        else:
            params['symbol'] = symbol
            params['series'] = series
            params['symbolCount'] = get_symbol_count(symbol)
            params['fromDate'] = start.strftime('%d-%m-%Y')
            params['toDate'] = end.strftime('%d-%m-%Y')
            url = equity_history_url
            schema = EQUITY_SCHEMA
            headers = EQUITY_HEADERS
            scaling = EQUITY_SCALING

    return url, params, schema, headers, scaling

def get_symbol_count(symbol):
    try:
        return symbol_count[symbol]
    except:
        cnt = symbol_count_url(symbol=symbol).text.lstrip().rstrip()
        symbol_count[symbol] = cnt
        return cnt

def nse_most_active(type="securities",sort="value"):
    payload = nsefetch("https://www.nseindia.com/api/live-analysis-most-active-"+type+"?index="+sort+"", headers=opt_headers)
    payload = pd.DataFrame(payload["data"])
    return payload

def nse_get_top_losers():
    positions = nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O', headers=opt_headers)
    df = pd.DataFrame(positions['data'])
    df = df.sort_values(by="pChange")
    return df.head(5)

def nse_get_top_gainers():
    positions = nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O', headers=opt_headers)
    df = pd.DataFrame(positions['data'])
    df = df.sort_values(by="pChange" , ascending = False)
    return df.head(5)

def nse_get_advances_declines(mode="pandas"):
    try:
        if(mode=="pandas"):
            positions = nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O', headers=opt_headers)
            return pd.DataFrame(positions['data'])
        else:
            return nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O', headers=opt_headers)
    except:
        print("\nPandas is not working for some reason.\n")
        return nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O', headers=opt_headers)

def nse_preopen(key="NIFTY",type="pandas"):
    payload = nsefetch("https://www.nseindia.com/api/market-data-pre-open?key="+key+"", headers=opt_headers)
    if(type=="pandas"):
        payload = pd.DataFrame(payload['data'])
        payload  = pd.json_normalize(payload['metadata'])
        return payload
    else:
        return payload

def nse_preopen_movers(key="FO",filter=1.5):
    preOpen_gainer=nse_preopen(key)
    return preOpen_gainer[preOpen_gainer['pChange'] >1.5],preOpen_gainer[preOpen_gainer['pChange'] <-1.5]

if __name__ == "__main__":

    symbol = 'DLF'
    period = 365 # days
    end = datetime.datetime.now().date()
    start = end - datetime.timedelta(days=period)

    df_history = get_history(symbol, start=start, end=end)
    df_opts = nse_opts(symbol)
    
    print(df_history)
    print("\n\n")
    print(df_opts)
