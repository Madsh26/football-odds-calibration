"""Download documented league-season CSVs; existing files are never overwritten."""
from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
from urllib.request import Request, urlopen


def main():
    root=Path(__file__).resolve().parent
    cfg=json.loads((root/'config.json').read_text(encoding='utf-8'))
    snapshot={}
    for manifest in ['source_snapshot.csv','covid_source_manifest.csv']:
        path=root/'data'/manifest
        if path.exists():
            for row in csv.DictReader(io.StringIO(path.read_text(encoding='utf-8-sig'))):
                snapshot[Path(row['file']).name]=row['sha256']
    log_file=root/'data/downloads.json'
    log=json.loads(log_file.read_text(encoding='utf-8')) if log_file.exists() else {}
    for league in cfg['leagues']:
        for season in cfg.get('covid',{}).get('seasons',cfg['seasons']):
            raw=root/'data'/('raw' if season in cfg['seasons'] else 'raw_covid')
            raw.mkdir(parents=True,exist_ok=True)
            name=f'{league}_{season}.csv';file=raw/name
            if file.exists(): print(f'Preserved: {name}');continue
            code=season[2:4]+season[-2:]
            url=f'https://www.football-data.co.uk/mmz4281/{code}/{league}.csv'
            with urlopen(Request(url,headers={'User-Agent':'football-calibration-research/1.0'}),timeout=60) as response:
                content=response.read()
            reader=csv.DictReader(io.StringIO(content.decode('utf-8-sig')))
            required={'Div','Date','HomeTeam','AwayTeam','FTR','FTHG','FTAG'}
            if season in cfg['seasons']: required |= {'B365CH','PSCH'}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError(f'{url}: unexpected response, not a valid results CSV')
            digest=hashlib.sha256(content).hexdigest()
            if name in snapshot and digest != snapshot[name]:
                raise ValueError(f'{name}: source differs from the recorded snapshot. Review provenance before updating data; no file was saved.')
            file.write_bytes(content)
            log[name]=dict(url=url,downloaded_utc=datetime.now(timezone.utc).isoformat(),sha256=digest)
            log_file.write_text(json.dumps(log,indent=2),encoding='utf-8')
            print(f'Downloaded: {name}')

if __name__=='__main__': main()
