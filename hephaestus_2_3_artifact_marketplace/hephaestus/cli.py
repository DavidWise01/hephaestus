import argparse,json,tempfile
from .marketplace import Marketplace,seed_demo
def demo(a):
    with tempfile.TemporaryDirectory() as td:
        print(json.dumps(seed_demo(td),indent=2))
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--packages",default="packages")
    p.add_argument("--locks",default="lockfiles")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=demo)
    sub.add_parser("dashboard").set_defaults(func=lambda a: print(json.dumps(Marketplace(a.packages,a.locks).dashboard(),indent=2)))
    e=sub.add_parser("export"); e.add_argument("output"); e.set_defaults(func=lambda a: print(json.dumps(Marketplace(a.packages,a.locks).export(a.output),indent=2)))
    args=p.parse_args(); args.func(args)
if __name__=="__main__": main()
