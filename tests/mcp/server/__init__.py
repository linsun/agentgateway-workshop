"""Minimal stand-in for MCPServer so we can import the servers and call their
tool functions directly, without the real SDK or a running transport."""

class MCPServer:
    def __init__(self, name):
        self.name = name
        self.tools = {}

    def tool(self, *a, **kw):
        def deco(fn):
            self.tools[fn.__name__] = fn
            return fn
        return deco

    def run(self, *a, **kw):
        raise SystemExit("run() should not be called in the harness")
