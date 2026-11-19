"""Build a review-only lead queue from DealLedger's CC0 broker-direct CSV.

Does NOT modify listings.json: DealLedger does not publish business operating age.
Run from repository root: python scripts/import_dealledger.py
"""
import csv
import io
import json
import pathlib
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlparse

URL = 'https://raw.githubusercontent.com/jeffsosville/dealledger/main/data/public/listings.csv'
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'dealledger_review.json'
EXISTING = ROOT / 'listings.json'
# Conservative city shortlist, NOT a verified 100-mile radius. Review location manually.
CITIES = {
    'austin','round rock','pflugerville','cedar park','leander','georgetown',
    'buda','kyle','san marcos','dripping springs','lakeway','bee cave',
    'bastrop','elgin','manor','hutto','taylor','lockhart','wimberley',
    'new braunfels','seguin','burnet','marble falls','liberty hill',
    'fredericksburg','johnson city','luling','san antonio',
}

def money(value):
    try:
        return float(str(value).replace('$','').replace(',','').strip())
    except (ValueError, TypeError):
        return None

def main():
    with urllib.request.urlopen(urllib.request.Request(URL, headers={'User-Agent':'AcquisitionHQ/1.0 (public CC0 research)'}), timeout=50) as response:
        raw = response.read(30_000_001)
    if len(raw) > 30_000_000:
        raise RuntimeError('Source CSV exceeds 30 MB safety limit; review before raising limit')
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    required = {'id','title','asking_price','city','state','url'}
    if not required.issubset(set(reader.fieldnames or [])):
        raise RuntimeError(f'Unexpected DealLedger CSV columns: {reader.fieldnames}')
    current = json.loads(EXISTING.read_text(encoding='utf-8'))
    known_links = {str(r.get('link','')).rstrip('/').lower() for r in current['listings']}
    known_ids = {str(r.get('id','')) for r in current['listings']}
    leads = {}
    for row in reader:
        city = (row.get('city') or '').strip()
        state = (row.get('state') or '').strip().upper()
        price = money(row.get('asking_price'))
        url = (row.get('url') or '').strip()
        source_id = str(row.get('id') or '').strip()
        if state != 'TX' or city.casefold() not in CITIES:
            continue
        if price is None or not (0 < price <= 2_000_000):
            continue
        if urlparse(url).scheme != 'https' or not urlparse(url).netloc:
            continue
        if not source_id or url.rstrip('/').lower() in known_links or f'dealledger-{source_id}' in known_ids:
            continue
        leads[source_id] = {
            'id': f'dealledger-{source_id}',
            'name': (row.get('title') or 'Untitled listing').strip(),
            'price': price,
            'years': None,
            'industry': (row.get('vertical') or 'Unclassified').strip(),
            'location': f'{city}, TX',
            'cash': money(row.get('cash_flow')),
            'link': url,
            'dealledger_url': (row.get('dealledger_url') or '').strip(),
            'last_seen': (row.get('last_seen') or '').strip(),
            'review_status': 'NEEDS_REVIEW',
            'review_reasons': ['Business operating age not supplied', 'Distance from downtown Austin not verified', 'Broker claims and listing availability not independently verified'],
        }
    result = {
        'source': 'DealLedger CC0 public broker-direct listings',
        'source_url': URL,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'status': 'REVIEW_ONLY_NOT_PUBLISHED',
        'note': 'City shortlist is approximate; operating age is unknown. Do not auto-add to listings.json.',
        'count': len(leads),
        'leads': sorted(leads.values(), key=lambda x: (x['location'], x['price'], x['id']))
    }
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {len(leads)} review-only leads to {OUT.name}; existing listings.json unchanged.')

if __name__ == '__main__':
    main()
