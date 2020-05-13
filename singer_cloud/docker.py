import io
import hashlib

import docker

DOCKERFILE_TEMPLATE = '''
FROM python:3.8

WORKDIR /usr/src/app

RUN mkdir virtualenvs
RUN pip3 install virtualenv

RUN virtualenv virtualenvs/singer-runner && \
    git clone --branch 0.0.2 https://github.com/datamill-co/singer-runner.git && \
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

def sync_container_image(logger, provider, config, force_new_image=False, no_cache=False):
    docker_client = docker.from_env()
    docker_ll_client = docker.APIClient(base_url='unix://var/run/docker.sock')

    logger.info('Creating Dockerfile')

    singer_installs = get_install_commands(config.get('taps', {}))
    singer_installs += get_install_commands(config.get('targets', {}))

    dockerfile = DOCKERFILE_TEMPLATE.format(' && \\\n'.join(singer_installs))
    dockerfile_hash = hash_string(dockerfile)

    local_image_uri = 'singer-cloud:{}'.format(dockerfile_hash)

    logger.info('Logging into remote container image repo')
    remote_uri_base = provider.get_docker_uri()
    remote_image_uri = '{}:{}'.format(remote_uri_base, dockerfile_hash)
    docker_auth = provider.get_docker_auth()
    docker_client.login(**docker_auth)
    push_to_remote = True

    if not force_new_image:
        logger.info('Checking local container image repo if image already exists: {}'.format(local_image_uri))
        try:
            image = docker_client.images.get(local_image_uri)
        except docker.errors.ImageNotFound:
            image = None

        if not image:
            logger.info('Checking remote container image repo if image already exists: {}'.format(remote_image_uri))
            try:
                image = docker_client.images.get(remote_image_uri)

                ## TODO: pull?

                if not force_new_image:
                    push_to_remote = False
            except docker.errors.ImageNotFound:
                image = None

    print(image)

    if force_new_image or image is None:
        if force_new_image:
            logger.info('Forcing new image build: {}'.format(local_image_uri))
        else:
            logger.info('Existing image not found. Building a new one: {}'.format(local_image_uri))

        dockerfile_obj = io.BytesIO(dockerfile.encode('utf-8'))
        output_stream = docker_ll_client.build(
            decode=True,
            fileobj=dockerfile_obj,
            tag=local_image_uri)

        for message in output_stream:
            error = message.get('errorDetail')
            if error:
                raise Exception(error['message'])

            logger.info(message.get('stream'))

            print(message)

        image = docker_client.images.get(local_image_uri)

    ## TODO: remove old images? locally and remote?

    image.tag(remote_uri_base, tag=dockerfile_hash)

    if push_to_remote:
        logger.info('Pushing container image to remote: {}'.format(remote_image_uri))

        output_stream = docker_client.images.push(
            repository=remote_uri_base,
            tag=dockerfile_hash,
            stream=True,
            decode=True)

        for message in output_stream: ## TODO: shared function with build stream?
            error = message.get('errorDetail')
            if error:
                raise Exception(error['message'])

            logger.info(message.get('stream'))

            print(message)
