"""Local display metadata; routing always uses Valve's original region codes."""
from .i18n import tr
from dataclasses import dataclass
from functools import lru_cache
from PySide6.QtGui import QIcon
from .core import ASSETS

COUNTRIES = {
    'ae':tr('الإمارات'), 'ar':tr('الأرجنتين'), 'at':tr('النمسا'), 'au':tr('أستراليا'),
    'br':tr('البرازيل'), 'cl':tr('تشيلي'), 'de':tr('ألمانيا'), 'es':tr('إسبانيا'),
    'fi':tr('فنلندا'), 'fr':tr('فرنسا'), 'gb':tr('المملكة المتحدة'), 'gu':tr('غوام'),
    'hk':tr('هونغ كونغ'), 'in':tr('الهند'), 'jp':tr('اليابان'), 'kr':tr('كوريا الجنوبية'),
    'nl':tr('هولندا'), 'pe':tr('بيرو'), 'pl':tr('بولندا'), 'se':tr('السويد'),
    'sg':tr('سنغافورة'), 'us':tr('الولايات المتحدة'), 'za':tr('جنوب أفريقيا'),
}
REGIONS = {
    'ams':('nl',tr('أمستردام')), 'atl':('us',tr('أتلانتا')), 'eze':('ar',tr('بوينس آيرس')),
    'maa2':('in',tr('تشيناي')), 'maa':('in',tr('تشيناي')), 'ord':('us',tr('شيكاغو')),
    'dfw':('us',tr('دالاس')), 'dfra':('de',tr('فرانكفورت • Datapacket')),
    'dfjr':('ae',tr('الفجيرة • Datapacket')), 'dvie':('at',tr('فيينا • Datapacket')),
    'dxb':('ae',tr('دبي')), 'fra':('de',tr('فرانكفورت')), 'gum':('gu',tr('غوام')),
    'hkg':('hk',tr('هونغ كونغ')), 'jnb':('za',tr('جوهانسبرغ')), 'lim':('pe',tr('ليما')),
    'lhr':('gb',tr('لندن')), 'dlhr':('gb',tr('لندن • Datapacket')), 'lax':('us',tr('لوس أنجلوس')),
    'mad':('es',tr('مدريد')), 'bom2':('in',tr('مومباي')), 'bom':('in',tr('مومباي')),
    'par':('fr',tr('باريس')), 'scl':('cl',tr('سانتياغو')), 'gru':('br',tr('ساو باولو')),
    'sea':('us',tr('سياتل')), 'seo':('kr',tr('سيول')), 'sgp':('sg',tr('سنغافورة')),
    'iad':('us',tr('ستيرلينغ')), 'sto2':('se',tr('ستوكهولم • بروما')),
    'sto':('se',tr('ستوكهولم • كيستا')), 'dsto':('se',tr('ستوكهولم • Datapacket')),
    'syd':('au',tr('سيدني')), 'tyo':('jp',tr('طوكيو')), 'vie':('at',tr('فيينا')),
    'waw':('pl',tr('وارسو')), 'hel':('fi',tr('هلسنكي')), 'fsn':('de',tr('فالكنشتاين')),
    'eat':('us',tr('ويناتشي')), 'mwh':('us',tr('ويناتشي')),
}
# New Valve codes can still use an established country in their description.
COUNTRY_NAMES = {'United Arab Emirates':'ae','UAE':'ae','Netherlands':'nl',
    'Germany':'de','India':'in','Argentina':'ar','Austria':'at','South Africa':'za',
    'Peru':'pe','England':'gb','United Kingdom':'gb','Spain':'es','France':'fr',
    'Chile':'cl','Brazil':'br','South Korea':'kr','Sweden':'se','Australia':'au',
    'Japan':'jp','Poland':'pl','Finland':'fi','United States':'us',
    'Georgia':'us','Illinois':'us','Texas':'us','California':'us','Washington':'us','Virginia':'us'}

@dataclass(frozen=True)
class RegionInfo:
    country: str
    city: str
    country_name: str

    def text(self, region):
        title=self.city+(' • '+self.country_name if self.city!=self.country_name and self.country_name else '')
        return title+'\n\u2066'+region.name.split(' (')[0]+' ['+region.code+']\u2069'

    def search(self, region):
        return ' '.join((self.city,self.country_name,self.country,region.name,region.code)).casefold()

def region_info(region):
    country,city=REGIONS.get(region.code,('',region.name))
    if not country:
        suffix=region.name.rsplit('(',1)[-1].rstrip(')')
        country=COUNTRY_NAMES.get(suffix,'')
    return RegionInfo(country,city,COUNTRIES.get(country,''))

@lru_cache(maxsize=32)
def flag_icon(country):
    path=ASSETS/'flags'/(country+'.svg')
    return QIcon(str(path if path.exists() else ASSETS/'flags/xx.svg'))
