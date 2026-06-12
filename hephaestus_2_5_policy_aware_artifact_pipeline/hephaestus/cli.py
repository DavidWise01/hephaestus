import argparse,json,tempfile
from .pipeline import Pipeline,seed_demo
def demo(a):
    with tempfile.TemporaryDirectory() as td:
        print(json.dumps(seed_demo(td),indent=2))
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--receipts",default="receipts")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=demo)
    sub.add_parser("dashboard").set_defaults(func=lambda a: print(json.dumps(Pipeline(a.receipts).dashboard(),indent=2)))
    e=sub.add_parser("export"); e.add_argument("output"); e.set_defaults(func=lambda a: print(json.dumps(Pipeline(a.receipts).export(a.output),indent=2)))
    a=p.parse_args(); a.func(a)
if __name__=="__main__": main()
