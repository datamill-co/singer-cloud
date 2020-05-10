import io
import hashlib

import docker

DOCKERFILE_TEMPLATE = '''
FROM python:3.8

WORKDIR /usr/src/app

RUN mkdir virtualenvs
RUN pip3 install virtualenv

RUN virtualenv virtualenvs/singer-runner && \
    git clone --branch 0.0.2 git@github.com:datamill-co/singer-runner.git && \
    virtualenvs/singer-runner/bin/pip3 install ./singer-runner/

RUN {}
'''

def hash_string(string):
    return hashlib.sha1(string.encode('utf-8')).hexdigest()

def get_install_commands(singer_config_set):
    singer_installs = []
    for name, config in singer_config_set.items():
        singer_installs.append(
            '''virtualenv virtualenvs/{name} && \
    mkdir {name} && \
    git clone {repo} {name} && \
    virtualenvs/{name}/bin/pip install ./{name}/'''.format(name=name, repo=config['repo']))

    return singer_installs

def sync_container_image(config):
    docker_client = docker.from_env()

    singer_installs = get_install_commands(config.get('taps', {}))
    singer_installs += get_install_commands(config.get('targets', {}))

    dockerfile = DOCKERFILE_TEMPLATE.format(' && \\\n'.join(singer_installs))
    dockerfile_hash = hash_string(dockerfile)

    print(dockerfile)
    print(dockerfile_hash)

    local_image_uri = 'singer-cloud:{}'.format(dockerfile_hash)

    ## TODO: check remote registry as well

    try:
        image = docker_client.images.get(local_image_uri)
    except docker.errors.ImageNotFound:
        image = None

    if image is None:
        dockerfile_obj = io.BytesIO(dockerfile.encode('utf-8'))
        image, log_stream = docker_client.images.build(
            fileobj=dockerfile_obj,
            tag=local_image_uri)
