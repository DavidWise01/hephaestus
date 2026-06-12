import argparse,json,tempfile
from .fabric import FabricLayer,seed_demo
def demo(a):
    with tempfile.TemporaryDirectory() as td:
        print(json.dumps(seed_demo(td),indent=2))
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--state",default="fabric_state")
    p.add_argument("--deployments",default="deployments")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=demo)
    sub.add_parser("dashboard").set_defaults(func=lambda a: print(json.dumps(FabricLayer(a.state,a.deployments).dashboard(),indent=2)))
    e=sub.add_parser("export"); e.add_argument("output"); e.set_defaults(func=lambda a: print(json.dumps(FabricLayer(a.state,a.deployments).export(a.output),indent=2)))
    a=p.parse_args(); a.func(a)
if __name__=="__main__": main()
