import simplejson as json
import tornado.web

from psutil import cpu_percent, virtual_memory

class StatsHandler(tornado.web.RequestHandler):

    @classmethod
    def routes(cls):
        return [
            (r'/stats/(.*)', cls),
            (r'/stats', cls)
        ]

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')

    def get(self, key=None):
        vm = virtual_memory()
        cpu = float(cpu_percent())

        stats = {
            'cpu': cpu,
            'memory_percent': vm.percent,
            'memory_used': vm.used,
            'memory_available': vm.available,
            'index': cpu * vm.percent
        }

        if key is None:
            ret = stats
        else:
            if key in stats:
                ret = stats[key]
            else:
                raise tornado.web.HTTPError(404)
            
        self.finish(json.dumps(ret))

