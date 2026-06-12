import argparse,json,tempfile
from .execution_engine import ArtifactExecutionEngine,seed_demo
def demo(a):
    with tempfile.TemporaryDirectory() as td:
        print(json.dumps(seed_demo(td),indent=2))
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--state",default="execution_state")
    p.add_argument("--artifacts",default="artifacts")
    p.add_argument("--runs",default="runs")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=demo)
    sub.add_parser("dashboard").set_defaults(func=lambda a: print(json.dumps(ArtifactExecutionEngine(a.state,a.artifacts,a.runs).dashboard(),indent=2)))
    e=sub.add_parser("export"); e.add_argument("output"); e.set_defaults(func=lambda a: print(json.dumps(ArtifactExecutionEngine(a.state,a.artifacts,a.runs).export(a.output),indent=2)))
    args=p.parse_args(); args.func(args)
if __name__=="__main__": main()
