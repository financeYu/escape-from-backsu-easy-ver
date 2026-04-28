"""Official data source adapters."""

from content_research.sources.official_data.ecos import ECOSClient
from content_research.sources.official_data.eia import EIAClient
from content_research.sources.official_data.fred import FREDClient
from content_research.sources.official_data.kosis import KOSISClient
from content_research.sources.official_data.opendart import OpenDARTClient
from content_research.sources.official_data.un_comtrade import UNComtradeClient

__all__ = ["ECOSClient", "EIAClient", "FREDClient", "KOSISClient", "OpenDARTClient", "UNComtradeClient"]
