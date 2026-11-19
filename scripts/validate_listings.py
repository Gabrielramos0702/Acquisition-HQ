import json, pathlib, urllib.parse
p=pathlib.Path('listings.json')
data=json.loads(p.read_text())
assert isinstance(data.get('listings'),list),'listings must be an array'
ids=set()
for row in data['listings']:
    for field in ('id','name','price','years','industry','location','link'):
        assert field in row, f'missing {field}'
    assert str(row['id']) not in ids, 'duplicate id'
    ids.add(str(row['id']))
    assert isinstance(row['price'],(int,float)) and 0<=row['price']<=2000000
    assert isinstance(row['years'],(int,float)) and row['years']>=5
    u=urllib.parse.urlparse(row['link'])
    assert u.scheme=='https' and u.netloc, 'source must be https'
print(f'Validated {len(ids)} listings. This does not verify availability or source permission.')
