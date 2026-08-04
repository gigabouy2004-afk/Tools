import os
import sys
import tempfile
import importlib.util

spec = importlib.util.spec_from_file_location('etf_module', r'd:\Tools\04_ETF_Portfolio_Mapping\ETF_Portfolio_Mapping_V6.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False, encoding='utf-8') as f:
    f.write('Stock Ticker,Other,More\nAAPL,foo,bar\nMSFT,baz,qux\n')
    path = f.name

print('parsed_tickers=', module.extract_tickers_from_file(path))
try:
    sys.argv = ['prog', '-o', 'badfile']
    module.parse_arguments()
except SystemExit as e:
    print('parse_exit=', e.code)

os.unlink(path)
