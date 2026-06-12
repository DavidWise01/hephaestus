import argparse,json,tempfile
from .mesh import Mesh,seed_demo
def demo(a):
    with tempfile.TemporaryDirectory() as td: print(json.dumps(seed_demo(td),indent=2))
def main():
    p=argparse.ArgumentParser(); p.add_argument("--db",default="mesh.db")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=demo)
    sub.add_parser("health").set_defaults(func=lambda a: print(json.dumps(Mesh(a.db).health(),indent=2)))
    sub.add_parser("dashboard").set_defaults(func=lambda a: print(json.dumps(Mesh(a.db).dashboard(),indent=2)))
    e=sub.add_parser("export"); e.add_argument("output"); e.set_defaults(func=lambda a: print(json.dumps(Mesh(a.db).export(a.output),indent=2)))
    a=p.parse_args(); a.func(a)
if __name__=="__main__": main()
