"""Local display metadata; routing always uses Valve's original region codes."""
from dataclasses import dataclass
from functools import lru_cache
from PySide6.QtGui import QIcon
from .core import ASSETS

COUNTRIES = {
    'ae':'الإمارات', 'ar':'الأرجنتين', 'at':'النمسا', 'au':'أستراليا',
    'br':'البرازيل', 'cl':'تشيلي', 'de':'ألمانيا', 'es':'إسبانيا',
    'fi':'فنلندا', 'fr':'فرنسا', 'gb':'المملكة المتحدة', 'gu':'غوام',
    'hk':'هونغ كونغ', 'in':'الهند', 'jp':'اليابان', 'kr':'كوريا الجنوبية',
    'nl':'هولندا', 'pe':'بيرو', 'pl':'بولندا', 'se':'السويد',
    'sg':'سنغافورة', 'us':'الولايات المتحدة', 'za':'جنوب أفريقيا',
}
REGIONS = {
    'ams':('nl','أمستردام'), 'atl':('us','أتلانتا'), 'eze':('ar','بوينس آيرس'),
    'maa2':('in','تشيناي'), 'maa':('in','تشيناي'), 'ord':('us','شيكاغو'),
    'dfw':('us','دالاس'), 'dfra':('de','فرانكفورت • Datapacket'),
    'dfjr':('ae','الفجيرة • Datapacket'), 'dvie':('at','فيينا • Datapacket'),
    'dxb':('ae','دبي'), 'fra':('de','فرانكفورت'), 'gum':('gu','غوام'),
    'hkg':('hk','هونغ كونغ'), 'jnb':('za','جوهانسبرغ'), 'lim':('pe','ليما'),
    'lhr':('gb','لندن'), 'dlhr':('gb','لندن • Datapacket'), 'lax':('us','لوس أنجلوس'),
    'mad':('es','مدريد'), 'bom2':('in','مومباي'), 'bom':('in','مومباي'),
    'par':('fr','باريس'), 'scl':('cl','سانتياغو'), 'gru':('br','ساو باولو'),
    'sea':('us','سياتل'), 'seo':('kr','سيول'), 'sgp':('sg','سنغافورة'),
    'iad':('us','ستيرلينغ'), 'sto2':('se','ستوكهولم • بروما'),
    'sto':('se','ستوكهولم • كيستا'), 'dsto':('se','ستوكهولم • Datapacket'),
    'syd':('au','سيدني'), 'tyo':('jp','طوكيو'), 'vie':('at','فيينا'),
    'waw':('pl','وارسو'), 'hel':('fi','هلسنكي'), 'fsn':('de','فالكنشتاين'),
    'eat':('us','ويناتشي'), 'mwh':('us','ويناتشي'),
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
