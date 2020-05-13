
class CloudProvider:
    def __init__(self, logger, config):
        self.logger = logger
        self.config = config

    def sync(self, config):
        raise NotImplementedError()

    def get_docker_uri(self):
        raise NotImplementedError()

    def get_docker_auth(self):
        raise NotImplementedError()
