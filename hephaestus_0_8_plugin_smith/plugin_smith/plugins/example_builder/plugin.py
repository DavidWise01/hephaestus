
class ExampleBuilder:
    name = "example_builder"
    permissions = ["artifact:create"]
    def build(self, request):
        return {"artifact":"example","request":request,"status":"generated"}
