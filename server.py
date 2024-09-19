from server import PromptServer
from aiohttp import web

@PromptServer.instance.routes.get("/health")
async def health_check(request):
    return web.json_response({"code": 200, "status": "ok"})

def run_server():
    print("[Flow Control] API server started...")